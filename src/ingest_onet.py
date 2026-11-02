"""Ingest O*NET rating files (CSV, release pinned in prereg.yaml) into DuckDB.

Validation performed (fails loudly in strict mode):
  * exact column header match against the data dictionary
  * row count, occupation count, element count vs. published values
  * scale IDs restricted to the pre-registered set (IM, LV)
  * one row per (occupation, element, scale) — no duplicates
Raw files are never modified; SHA-256 checksums are stored with the metadata.

Usage:
    python -m src.ingest_onet [--config config/prereg.yaml] [--no-strict]
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from .config import REPO_ROOT, load_config, repo_path

NUMERIC_COLS = {
    "Data Value": "data_value",
    "N": "n",
    "Standard Error": "se",
    "Lower CI Bound": "ci_lo",
    "Upper CI Bound": "ci_hi",
}
TEXT_COLS = {
    "O*NET-SOC Code": "onet_code",
    "Title": "title",
    "Element ID": "element_id",
    "Element Name": "element_name",
    "Scale ID": "scale_id",
    "Scale Name": "scale_name",
    "Recommend Suppress": "suppress",
    "Not Relevant": "not_relevant",
    "Date": "date_raw",
    "Domain Source": "domain_source",
}
MISSING_TOKENS = {"", "n/a", "na"}


class IngestError(RuntimeError):
    """Raised when a raw file violates the pre-registered schema."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_rating_file(path: Path, expected_columns: list[str]) -> pd.DataFrame:
    """Read a rating CSV as text (no type inference) and verify the header."""
    # utf-8-sig transparently strips a BOM if present.
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    cols = [c.strip() for c in df.columns]
    if cols != expected_columns:
        missing = [c for c in expected_columns if c not in cols]
        extra = [c for c in cols if c not in expected_columns]
        raise IngestError(
            f"{path.name}: header mismatch. missing={missing} unexpected={extra} "
            f"(order also must match the data dictionary)"
        )
    df.columns = cols
    return df


def clean_ratings(df: pd.DataFrame, file_key: str, domain: str) -> tuple[pd.DataFrame, dict[str, int]]:
    """Rename to snake_case, coerce numerics, normalise flags, parse year."""
    out = df.rename(columns={**TEXT_COLS, **NUMERIC_COLS}).copy()
    issues: dict[str, int] = {}

    for col in TEXT_COLS.values():
        out[col] = out[col].astype(str).str.strip()

    for col in NUMERIC_COLS.values():
        raw = out[col].astype(str).str.strip()
        is_missing_token = raw.str.lower().isin(MISSING_TOKENS)
        num = pd.to_numeric(raw.where(~is_missing_token), errors="coerce")
        # Non-empty, non-"n/a" values that failed to parse are data problems.
        issues[f"{col}_unparsable"] = int((~is_missing_token & num.isna()).sum())
        out[col] = num.astype("float64")

    for col in ("suppress", "not_relevant"):
        flag = out[col].str.upper()
        out[col] = flag.where(flag.isin(["Y", "N"]))  # anything else -> missing

    out["date_year"] = pd.to_numeric(
        out["date_raw"].str.extract(r"(\d{4})", expand=False), errors="coerce"
    ).astype("Int64")
    out["soc6"] = out["onet_code"].str.slice(0, 7)
    out["file_key"] = file_key
    out["domain"] = domain
    return out, issues


def validate_file(df: pd.DataFrame, spec: dict[str, Any], onet_cfg: dict[str, Any],
                  allowed_scales: set[str]) -> list[str]:
    """Return a list of human-readable problems (empty list = pass)."""
    problems: list[str] = []
    name = spec["file"]
    if len(df) != spec["expected_rows"]:
        problems.append(f"{name}: rows={len(df)} expected={spec['expected_rows']}")
    n_occ = df["onet_code"].nunique()
    if n_occ != onet_cfg["expected_occupations"]:
        problems.append(f"{name}: occupations={n_occ} expected={onet_cfg['expected_occupations']}")
    n_el = df["element_id"].nunique()
    if n_el != spec["expected_elements"]:
        problems.append(f"{name}: elements={n_el} expected={spec['expected_elements']}")
    scales = set(df["scale_id"].unique())
    if not scales <= allowed_scales:
        problems.append(f"{name}: unexpected scale IDs {sorted(scales - allowed_scales)}")
    dup = df.duplicated(subset=["onet_code", "element_id", "scale_id"]).sum()
    if dup:
        problems.append(f"{name}: {dup} duplicate (occupation, element, scale) rows")
    if df["data_value"].isna().any():
        problems.append(f"{name}: {int(df['data_value'].isna().sum())} rows with missing Data Value")
    return problems


def ingest(cfg: dict[str, Any], root: Path = REPO_ROOT, strict: bool | None = None) -> dict[str, Any]:
    onet_cfg = cfg["data_versions"]["onet"]
    strict = cfg.get("strict_version_check", True) if strict is None else strict
    scales_cfg = cfg["measurement"]["scales"]
    allowed_scales = {scales_cfg["level"]["id"], scales_cfg["importance"]["id"]}
    raw_dir = repo_path(cfg["paths"]["raw_onet"], root)

    frames, meta_rows, problems = [], [], []
    for key, spec in onet_cfg["files"].items():
        path = raw_dir / spec["file"]
        if not path.exists():
            problems.append(f"missing file: {path}")
            continue
        df = read_rating_file(path, onet_cfg["expected_columns"])
        df, issues = clean_ratings(df, key, spec["domain"])
        file_problems = validate_file(df, spec, onet_cfg, allowed_scales)
        file_problems += [f"{spec['file']}: {k}={v}" for k, v in issues.items() if v]
        problems += file_problems
        meta_rows.append({
            "file_key": key,
            "file": spec["file"],
            "domain": spec["domain"],
            "sha256": sha256(path),
            "rows": len(df),
            "occupations": df["onet_code"].nunique(),
            "elements": df["element_id"].nunique(),
            "n_problems": len(file_problems),
        })
        frames.append(df)

    if problems:
        msg = "O*NET ingest validation problems:\n  - " + "\n  - ".join(problems)
        if strict:
            raise IngestError(msg)
        print("WARNING (non-strict mode):\n" + msg, file=sys.stderr)
    if not frames:
        raise IngestError("No O*NET files were ingested.")

    ratings = pd.concat(frames, ignore_index=True)
    meta = pd.DataFrame(meta_rows)
    meta["onet_release"] = onet_cfg["release"]

    db_path = repo_path(cfg["paths"]["duckdb"], root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as con:
        con.register("ratings_df", ratings)
        con.execute("CREATE OR REPLACE TABLE onet_ratings AS SELECT * FROM ratings_df")
        con.register("meta_df", meta)
        con.execute("CREATE OR REPLACE TABLE onet_file_meta AS SELECT * FROM meta_df")
    return {"db_path": db_path, "rows": len(ratings), "problems": problems, "meta": meta}


def _rel(p: Path) -> str:
    """Repository-relative path for console output (keeps machine-specific paths out of results_log.txt)."""
    try:
        return Path(p).resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(p)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    ap.add_argument("--no-strict", action="store_true", help="warn instead of failing on validation problems")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    try:
        res = ingest(cfg, strict=False if args.no_strict else None)
    except IngestError as exc:
        print(f"FAILED\n{exc}", file=sys.stderr)
        return 1
    print(f"OK: {res['rows']:,} rating rows -> {_rel(res['db_path'])}")
    print(res["meta"].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
