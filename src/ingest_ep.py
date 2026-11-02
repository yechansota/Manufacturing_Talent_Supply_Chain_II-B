"""Ingest BLS Employment Projections 2025–35 tables and the O*NET-SOC -> NEM crosswalk.

Tables
  * occupation.xlsx  / Table 1.10  occupational separations and openings (annual averages)
  * education.xlsx   / Table 5.4   education, work experience, on-the-job training assignments
  * nem-onet-to-soc-crosswalk.xlsx / Crosswalk

Checks (strict mode fails on any):
  * sheet title contains the pinned projection period / reference year
  * crosswalk "As of" date matches the pinned value
  * every frame SOC code is present in Table 1.10 and Table 5.4
  * crosswalk cross-check: every O*NET code BLS assigns to a frame SOC code is
    mapped in prereg.yaml (primary / sensitivity_codes) or listed in excluded_codes,
    and every code we map is assigned by BLS to that same SOC code.

Text cells are read with keep_default_na=False so category labels such as
"None" are kept as text instead of becoming missing values.

Outputs: DuckDB tables ep_separations, ep_education, ep_onet_nem_crosswalk;
         outputs/validation/ep_crosswalk_check.csv, ep_frame_extract.csv

Usage:
    python -m src.ingest_ep [--config config/prereg.yaml] [--no-strict]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from .config import REPO_ROOT, load_config, repo_path
from .frame import frame_table, resolve_codes

SEPARATIONS_RENAME = {
    "2025 National Employment Matrix title": "nem_title",
    "2025 National Employment Matrix code": "nem_code",
    "Occupation type": "occupation_type",
    "Employment, 2025": "emp_2025_k",
    "Employment, 2035": "emp_2035_k",
    "Employment change, numeric, 2025–35": "emp_change_k",
    "Employment change, percent, 2025–35": "emp_change_pct",
    "Labor force exit rate, 2025–35 annual average": "lf_exit_rate_pct",
    "Occupational transfer rate, 2025–35 annual average": "transfer_rate_pct",
    "Total occupational separations rate, 2025–35 annual average": "separations_rate_pct",
    "Labor force exits, 2025–35 annual average": "lf_exits_k",
    "Occupational transfers, 2025–35 annual average": "transfers_k",
    "Total occupational separations, 2025–35 annual average": "separations_k",
    "Occupational openings, 2025–35 annual average": "openings_k",
}
EDUCATION_RENAME = {
    "2025 National Employment Matrix title": "nem_title",
    "2025 National Employment Matrix code": "nem_code",
    "Typical education needed for entry": "entry_education",
    "Work experience in a related occupation": "related_work_experience",
    "Typical on-the-job training needed to attain competency in the occupation": "ojt",
}
CROSSWALK_RENAME = {
    "O*NET-SOC code": "onet_code",
    "O*NET-SOC title": "onet_title",
    "NEM Code": "nem_code",
    "NEM title": "nem_title",
}


class EpError(RuntimeError):
    """Raised when an EP workbook violates the pre-registered expectations."""


def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s)).strip()


def read_bls_sheet(path: Path, sheet: str, header_contains: str) -> tuple[pd.DataFrame, list[str]]:
    """Return (table, preamble lines). Header row = first row containing `header_contains`."""
    raw = pd.read_excel(path, sheet_name=sheet, header=None, dtype=str, keep_default_na=False)
    hdr_idx = next((i for i, r in raw.iterrows() if any(header_contains.lower() in _norm(v).lower() for v in r)), None)
    if hdr_idx is None:
        raise EpError(f"{path.name}/{sheet}: header row containing '{header_contains}' not found")
    preamble = [_norm(v) for i in range(hdr_idx) for v in raw.iloc[i] if _norm(v)]
    df = raw.iloc[hdr_idx + 1:].copy()
    df.columns = [_norm(c) for c in raw.iloc[hdr_idx]]
    df = df.loc[:, [c for c in df.columns if c]]
    return df.reset_index(drop=True), preamble


def _rename_strict(df: pd.DataFrame, mapping: dict[str, str], where: str) -> pd.DataFrame:
    missing = [c for c in mapping if c not in df.columns]
    if missing:
        raise EpError(f"{where}: missing columns {missing}; found {list(df.columns)}")
    return df[list(mapping)].rename(columns=mapping)


def load_separations(path: Path, spec: dict[str, Any]) -> pd.DataFrame:
    df, pre = read_bls_sheet(path, spec["sheet"], "Matrix code")
    if not any(spec["title_must_contain"] in line for line in pre):
        raise EpError(f"{path.name}/{spec['sheet']}: title does not contain '{spec['title_must_contain']}': {pre[:1]}")
    df = _rename_strict(df, SEPARATIONS_RENAME, f"{path.name}/{spec['sheet']}")
    df["nem_code"] = df["nem_code"].str.strip()
    df = df[df["nem_code"].str.fullmatch(r"\d{2}-\d{4}")]
    for col in [c for c in df.columns if c not in {"nem_title", "nem_code", "occupation_type"}]:
        df[col] = pd.to_numeric(df[col].str.replace(",", "", regex=False), errors="coerce")
    return df.assign(title_line=pre[0] if pre else "")


def load_education(path: Path, spec: dict[str, Any]) -> pd.DataFrame:
    df, pre = read_bls_sheet(path, spec["sheet"], "Matrix code")
    if not any(spec["title_must_contain"] in line for line in pre):
        raise EpError(f"{path.name}/{spec['sheet']}: title does not contain '{spec['title_must_contain']}'")
    df = _rename_strict(df, EDUCATION_RENAME, f"{path.name}/{spec['sheet']}")
    df["nem_code"] = df["nem_code"].str.strip()
    df = df[df["nem_code"].str.fullmatch(r"\d{2}-\d{4}")]
    for col in ("entry_education", "related_work_experience", "ojt"):
        df[col] = df[col].map(_norm)
    return df.assign(title_line=pre[0] if pre else "")


def load_crosswalk(path: Path, spec: dict[str, Any]) -> pd.DataFrame:
    df, pre = read_bls_sheet(path, spec["sheet"], "O*NET-SOC code")
    if not any(spec["as_of"] in line for line in pre):
        raise EpError(f"{path.name}: 'As of {spec['as_of']}' not found in preamble {pre}")
    df = _rename_strict(df, CROSSWALK_RENAME, f"{path.name}/{spec['sheet']}")
    df = df.apply(lambda s: s.map(_norm))
    return df[df["onet_code"].str.fullmatch(r"\d{2}-\d{4}\.\d{2}")]


def crosswalk_check(cfg: dict[str, Any], xw: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    overrides = cfg["onet_crosswalk"].get("overrides", {})
    frame = frame_table(cfg)
    rows, problems = [], []
    for rec in frame.itertuples(index=False):
        ours = {code for code, _ in resolve_codes(rec.soc6, cfg)}
        excluded = set((overrides.get(rec.soc6, {}) or {}).get("excluded_codes", {}) or {})
        bls = set(xw.loc[xw["nem_code"] == rec.soc6, "onet_code"])
        unmapped = bls - ours - excluded
        foreign = {c for c in ours if not xw.loc[xw["onet_code"] == c, "nem_code"].eq(rec.soc6).any()}
        status = "OK" if not unmapped and not foreign else "PROBLEM"
        rows.append({"soc6": rec.soc6, "role": rec.role, "bls_onet_codes": ";".join(sorted(bls)),
                     "mapped_codes": ";".join(sorted(ours)), "excluded_codes": ";".join(sorted(excluded)),
                     "unmapped_bls_codes": ";".join(sorted(unmapped)),
                     "mapped_but_not_bls": ";".join(sorted(foreign)), "status": status})
        if unmapped:
            problems.append(f"{rec.soc6}: BLS assigns {sorted(unmapped)} but prereg neither maps nor excludes them")
        if foreign:
            problems.append(f"{rec.soc6}: prereg maps {sorted(foreign)} but BLS assigns them to another NEM code")
    return pd.DataFrame(rows), problems


def ingest(cfg: dict[str, Any], root: Path = REPO_ROOT, strict: bool | None = None) -> dict[str, Any]:
    ecfg = cfg["data_versions"]["ep"]
    strict = cfg.get("strict_version_check", True) if strict is None else strict
    raw_dir = repo_path(cfg["paths"]["raw_ep"], root)
    paths = {k: raw_dir / ecfg[k]["file"] for k in ("occupation_file", "education_file", "crosswalk_file")}
    for p in paths.values():
        if not p.exists():
            raise EpError(f"missing file: {p}")

    sep = load_separations(paths["occupation_file"], ecfg["occupation_file"])
    edu = load_education(paths["education_file"], ecfg["education_file"])
    xw = load_crosswalk(paths["crosswalk_file"], ecfg["crosswalk_file"])

    problems: list[str] = []
    frame = frame_table(cfg)
    sep_line = sep[sep["occupation_type"].str.strip() == "Line item"]
    for name, table in (("Table 1.10", sep_line), ("Table 5.4", edu)):
        missing = sorted(set(frame["soc6"]) - set(table["nem_code"]))
        if missing:
            problems.append(f"{name}: frame codes missing {missing}")
    dup = sep_line["nem_code"].duplicated().sum() + edu["nem_code"].duplicated().sum()
    if dup:
        problems.append(f"{dup} duplicated NEM codes in Table 1.10 line items / Table 5.4")

    xw_check, xw_problems = crosswalk_check(cfg, xw)
    problems += xw_problems

    out_dir = repo_path(cfg["paths"]["validation_out"], root)
    out_dir.mkdir(parents=True, exist_ok=True)
    xw_check.to_csv(out_dir / "ep_crosswalk_check.csv", index=False)
    extract = (frame.merge(sep_line.drop(columns=["title_line"]), left_on="soc6", right_on="nem_code", how="left")
               .merge(edu[["nem_code", "entry_education", "related_work_experience", "ojt"]], on="nem_code", how="left"))
    extract.to_csv(out_dir / "ep_frame_extract.csv", index=False)

    if problems:
        msg = "EP validation problems:\n  - " + "\n  - ".join(problems)
        if strict:
            raise EpError(msg)
        print("WARNING (non-strict mode):\n" + msg, file=sys.stderr)

    db_path = repo_path(cfg["paths"]["duckdb"], root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as con:
        for name, table in (("ep_separations", sep), ("ep_education", edu), ("ep_onet_nem_crosswalk", xw)):
            con.register("tmp_df", table)
            con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM tmp_df")
            con.unregister("tmp_df")
    return {"separations": sep, "education": edu, "crosswalk": xw, "xw_check": xw_check,
            "extract": extract, "problems": problems}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    ap.add_argument("--no-strict", action="store_true")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    try:
        res = ingest(cfg, strict=False if args.no_strict else None)
    except EpError as exc:
        print(f"FAILED\n{exc}", file=sys.stderr)
        return 1
    print(f"OK: Table 1.10 {len(res['separations'])} rows, Table 5.4 {len(res['education'])} rows, "
          f"crosswalk {len(res['crosswalk'])} rows")
    print(res["xw_check"][["soc6", "role", "bls_onet_codes", "mapped_codes", "excluded_codes", "status"]]
          .to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
