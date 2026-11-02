"""Observed employment trend for NAICS 3363 (BLS CES, series CEU3133630001; deviation log DL-26).

Reads one of these files from data/raw/ces/ (whichever is present):
  * a FRED CSV export      — columns: observation_date (or DATE), CEU3133630001       (monthly, thousands)
  * a BLS SeriesReport xlsx — a header row starting with 'Year', then Jan..Dec[, Annual] (thousands)
Annual averages are the mean of the 12 monthly not-seasonally-adjusted values (BLS computes CES annual averages
the same way); years with fewer than 12 months are kept as partial and are not used for annual comparisons.

Outputs: outputs/practice/ces_3363_annual.csv, outputs/practice/ces_3363_monthly.csv
Usage:   python -m src.trend
"""
from __future__ import annotations

import argparse
import warnings
from pathlib import Path
from typing import Any

import pandas as pd

from .config import REPO_ROOT, load_config, repo_path

SERIES = "CEU3133630001"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def find_file(root: Path) -> Path | None:
    d = repo_path("data/raw/ces", root)
    if not d.exists():
        return None
    files = sorted(p for p in d.iterdir() if p.suffix.lower() in {".csv", ".xlsx"} and not p.name.startswith("."))
    return files[0] if files else None


def read_monthly(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        t = pd.read_csv(path)
        date_col = next(c for c in t.columns if c.lower() in {"observation_date", "date"})
        val_col = next(c for c in t.columns if c != date_col)
        if val_col.upper() != SERIES:
            raise ValueError(f"{path.name}: expected series {SERIES}, found column {val_col}")
        t = t.rename(columns={date_col: "date", val_col: "emp_k"})
        t["date"] = pd.to_datetime(t["date"])
        t["emp_k"] = pd.to_numeric(t["emp_k"], errors="coerce")
        return t.dropna(subset=["emp_k"])[["date", "emp_k"]]
    warnings.filterwarnings("ignore", message="Workbook contains no default style")   # BLS export styling only
    raw = pd.read_excel(path, header=None, dtype=str)
    text = raw.fillna("").astype(str)
    if not text.apply(lambda c: c.str.contains(SERIES, regex=False)).any().any():
        raise ValueError(f"{path.name}: series id {SERIES} not found in the workbook header")
    hdr = int(text.index[text.iloc[:, 0].str.strip() == "Year"][0])
    t = pd.read_excel(path, header=hdr)
    t = t[pd.to_numeric(t["Year"], errors="coerce").notna()]
    long = t.melt(id_vars="Year", value_vars=[m for m in MONTHS if m in t.columns], var_name="m", value_name="emp_k")
    long["emp_k"] = pd.to_numeric(long["emp_k"], errors="coerce")
    long["date"] = pd.to_datetime(long["Year"].astype(int).astype(str) + "-" + long["m"], format="%Y-%b")
    return long.dropna(subset=["emp_k"]).sort_values("date")[["date", "emp_k"]]


def run(cfg: dict[str, Any], root: Path = REPO_ROOT) -> pd.DataFrame | None:
    path = find_file(root)
    if path is None:
        print("[skip] no CES file in data/raw/ces (optional input, DL-26)")
        return None
    m = read_monthly(path)
    if m.date.duplicated().any():
        raise ValueError("duplicate months in CES file")
    m["year"] = m.date.dt.year
    a = m.groupby("year").agg(emp_k=("emp_k", "mean"), months=("emp_k", "size")).reset_index()
    a["complete"] = a.months == 12
    out = repo_path("outputs/practice", root)
    m.to_csv(out / "ces_3363_monthly.csv", index=False)
    a.to_csv(out / "ces_3363_annual.csv", index=False)
    print(f"{path.name}: {len(m)} months, {m.date.min():%Y-%m} to {m.date.max():%Y-%m}; complete years {int(a.complete.sum())}")
    return a


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    a = run(load_config(args.config))
    if a is not None:
        print(a.tail(12).round(1).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
