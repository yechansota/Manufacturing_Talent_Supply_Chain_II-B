"""Ingest OEWS May 2025 national industry-specific estimates for NAICS 336300
and re-validate the analysis frame against the pre-registered selection rules.

Steps
  1. Read the pinned workbook directly from the zip (the archive is not extracted).
  2. Keep AREA == U.S. and NAICS == 336300; verify total employment.
  3. Parse numerics. Non-numeric tokens (e.g. "*", "**") become missing; the raw
     token is kept in <col>_raw so nothing is silently lost.
  4. De-duplicate OCC_CODE: OEWS publishes some codes (e.g. 51-2090) both as a
     broad row and as a detailed row. Keep one row per code (detailed > broad >
     minor > major > total) after checking that duplicates carry identical values.
  5. Re-apply the selection rules from prereg.yaml and compare with the frame.

Outputs: DuckDB table `oews_3363`, outputs/validation/oews_frame_validation.csv,
         outputs/validation/oews_feeders_threshold_alt.csv

Usage:
    python -m src.ingest_oews [--config config/prereg.yaml] [--no-strict]
"""
from __future__ import annotations

import argparse
import io
import sys
import zipfile
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from .config import REPO_ROOT, load_config, repo_path
from .frame import frame_table

REQUIRED_COLS = ["AREA", "NAICS", "NAICS_TITLE", "OCC_CODE", "OCC_TITLE", "O_GROUP",
                 "TOT_EMP", "EMP_PRSE", "PCT_TOTAL", "H_MEAN", "MEAN_PRSE", "H_MEDIAN", "A_MEDIAN"]
NUMERIC_COLS = ["TOT_EMP", "EMP_PRSE", "PCT_TOTAL", "H_MEAN", "MEAN_PRSE", "H_MEDIAN", "A_MEDIAN"]
GROUP_PRIORITY = {"detailed": 0, "broad": 1, "minor": 2, "major": 3, "total": 4}


class OewsError(RuntimeError):
    """Raised when the OEWS file violates the pre-registered expectations."""


def read_oews_member(zip_path: Path, member: str) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as zf:
        if member not in zf.namelist():
            raise OewsError(f"{member} not found in {zip_path.name}; members: {zf.namelist()}")
        data = zf.read(member)
    df = pd.read_excel(io.BytesIO(data), dtype=str, keep_default_na=False)
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise OewsError(f"{member}: missing columns {missing}")
    return df


def parse_numeric(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in NUMERIC_COLS:
        raw = out[col].astype(str).str.strip()
        num = pd.to_numeric(raw.str.replace(",", "", regex=False), errors="coerce")
        out[f"{col}_raw"] = raw.where(num.isna(), "")   # keep non-numeric token, if any
        out[col] = num
    return out


def dedupe_occupations(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per OCC_CODE; return (deduped, log of dropped duplicates)."""
    d = df.assign(_prio=df["O_GROUP"].map(GROUP_PRIORITY).fillna(9))
    dup_codes = d.loc[d["OCC_CODE"].duplicated(keep=False), "OCC_CODE"].unique()
    log_rows = []
    for code in dup_codes:
        grp = d[d["OCC_CODE"] == code]
        identical = grp[NUMERIC_COLS].nunique(dropna=False).max() == 1
        if not identical:
            raise OewsError(f"OCC_CODE {code} has duplicate rows with different values")
        log_rows.append({"OCC_CODE": code, "O_GROUP_rows": ";".join(grp["O_GROUP"]), "identical_values": identical})
    kept = d.sort_values(["OCC_CODE", "_prio"]).drop_duplicates("OCC_CODE").drop(columns="_prio")
    return kept, pd.DataFrame(log_rows, columns=["OCC_CODE", "O_GROUP_rows", "identical_values"])


def rule_pass(row: pd.Series, rule: dict[str, Any]) -> bool:
    return bool(pd.notna(row["TOT_EMP"]) and pd.notna(row["EMP_PRSE"])
                and row["TOT_EMP"] >= rule["min_employment"] and row["EMP_PRSE"] < rule["max_rse"])


def feeder_candidates(oews: pd.DataFrame, rule: dict[str, Any], min_employment: int) -> pd.DataFrame:
    """Mechanical feeder rule: major group, detailed rows, not 'All Other', size and precision."""
    c = oews[(oews["OCC_CODE"].str.startswith(rule["major_group"] + "-"))
             & (oews["O_GROUP"] == "detailed")
             & ~oews["OCC_TITLE"].str.contains("All Other", case=False)
             & (oews["TOT_EMP"] >= min_employment) & (oews["EMP_PRSE"] < rule["max_rse"])]
    return c.sort_values("TOT_EMP", ascending=False)


def validate_frame(cfg: dict[str, Any], oews: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    rules = cfg["frame"]["selection_rules"]
    design_excl = cfg["frame"].get("design_exclusions_from_feeder", {})
    frame = frame_table(cfg)
    by_code = oews.set_index("OCC_CODE")
    rows, problems = [], []

    for rec in frame.itertuples(index=False):
        r = by_code.loc[rec.soc6] if rec.soc6 in by_code.index else None
        rule = rules["target"] if rec.role.startswith("target") else rules["feeder"]
        passed = rule_pass(r, rule) if r is not None else False
        rows.append({"soc6": rec.soc6, "role": rec.role, "in_oews_3363": r is not None,
                     "title": r["OCC_TITLE"] if r is not None else "",
                     "tot_emp": r["TOT_EMP"] if r is not None else None,
                     "emp_rse": r["EMP_PRSE"] if r is not None else None,
                     "h_median": r["H_MEDIAN"] if r is not None else None,
                     "rule_applied": ("target" if rec.role.startswith("target")
                                      else "feeder" if rec.role == "feeder_core"
                                      else "feeder (informational)"),
                     "rule_pass": passed, "note": ""})
        if rec.role in {"target_core", "feeder_core"} and not passed:
            problems.append(f"{rec.soc6} ({rec.role}) fails its selection rule on OEWS May 2025")

    # Every occupation that satisfies the mechanical feeder rule must be in feeders_core
    # or carry a documented design exclusion.
    cands = feeder_candidates(oews, rules["feeder"], rules["feeder"]["min_employment"])
    in_frame = set(cfg["frame"]["feeders_core"])
    for code in cands["OCC_CODE"]:
        if code in in_frame:
            continue
        if code in design_excl:
            for row in rows:
                if row["soc6"] == code:
                    row["note"] = f"meets feeder rule; design exclusion: {design_excl[code]}"
            continue
        if code in cfg["frame"].get("excluded", []):
            continue
        problems.append(f"{code} meets the feeder rule but is not in feeders_core and has no design exclusion")
    for code in in_frame - set(cands["OCC_CODE"]):
        problems.append(f"{code} is in feeders_core but does not meet the feeder rule")

    return pd.DataFrame(rows), problems


def ingest(cfg: dict[str, Any], root: Path = REPO_ROOT, strict: bool | None = None) -> dict[str, Any]:
    ocfg = cfg["data_versions"]["oews"]
    strict = cfg.get("strict_version_check", True) if strict is None else strict
    zip_path = repo_path(cfg["paths"]["raw_oews"], root) / ocfg["file"]
    if not zip_path.exists():
        raise OewsError(f"missing file: {zip_path}")

    df = read_oews_member(zip_path, ocfg["member"])
    sub = df[(df["AREA"].str.strip() == ocfg["area"]) & (df["NAICS"].str.strip() == ocfg["naics"])]
    if sub.empty:
        raise OewsError(f"No rows for AREA={ocfg['area']} NAICS={ocfg['naics']}")
    sub = parse_numeric(sub)
    oews, dup_log = dedupe_occupations(sub)

    problems: list[str] = []
    total = oews.loc[oews["OCC_CODE"] == "00-0000", "TOT_EMP"]
    if total.empty or int(total.iloc[0]) != ocfg["expected_total_employment"]:
        problems.append(f"total employment {total.tolist()} != expected {ocfg['expected_total_employment']}")

    validation, frame_problems = validate_frame(cfg, oews)
    problems += frame_problems

    out_dir = repo_path(cfg["paths"]["validation_out"], root)
    out_dir.mkdir(parents=True, exist_ok=True)
    validation.to_csv(out_dir / "oews_frame_validation.csv", index=False)
    dup_log.to_csv(out_dir / "oews_duplicate_codes.csv", index=False)

    # Feeder set for the alternative multiverse threshold (e.g. 2,000).
    rule = cfg["frame"]["selection_rules"]["feeder"]
    design_excl = set(cfg["frame"].get("design_exclusions_from_feeder", {}))
    alt = []
    for thr in cfg["multiverse"]["feeder_employment_threshold"]:
        c = feeder_candidates(oews, rule, thr)
        c = c[~c["OCC_CODE"].isin(design_excl | set(cfg["frame"].get("excluded", [])))]
        alt.append(c.assign(threshold=thr)[["threshold", "OCC_CODE", "OCC_TITLE", "TOT_EMP", "EMP_PRSE"]])
    pd.concat(alt).to_csv(out_dir / "oews_feeders_threshold_alt.csv", index=False)

    if problems:
        msg = "OEWS validation problems:\n  - " + "\n  - ".join(problems)
        if strict:
            raise OewsError(msg)
        print("WARNING (non-strict mode):\n" + msg, file=sys.stderr)

    db_path = repo_path(cfg["paths"]["duckdb"], root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    keep = ["NAICS", "NAICS_TITLE", "OCC_CODE", "OCC_TITLE", "O_GROUP", *NUMERIC_COLS,
            *[f"{c}_raw" for c in NUMERIC_COLS]]
    table = oews[keep].assign(reference_period=ocfg["reference_period"])
    with duckdb.connect(str(db_path)) as con:
        con.register("oews_df", table)
        con.execute("CREATE OR REPLACE TABLE oews_3363 AS SELECT * FROM oews_df")
    return {"rows": len(table), "validation": validation, "dup_log": dup_log, "problems": problems,
            "out_dir": out_dir}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    ap.add_argument("--no-strict", action="store_true")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    try:
        res = ingest(cfg, strict=False if args.no_strict else None)
    except OewsError as exc:
        print(f"FAILED\n{exc}", file=sys.stderr)
        return 1
    print(f"OK: {res['rows']} OEWS rows for NAICS {cfg['data_versions']['oews']['naics']}")
    print(f"Duplicate codes collapsed: {res['dup_log']['OCC_CODE'].tolist()}")
    print(res["validation"].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
