"""Observed occupational mix inside NAICS 3363, OEWS May 2021-2025 (deviation log DL-29).

Inputs:  data/raw/oews_history/oesm21in4.zip ... oesm24in4.zip (optional; supplied by the author)
         data/raw/oews/oesm25in4.zip (the registered May 2025 file)
Each file is read directly from its zip (member nat4d_M<year>_dl.xlsx), restricted to NAICS 336300, parsed with the
registered OEWS rules (non-numeric tokens -> missing, duplicate codes resolved detailed > broad > ...).

May 2021-2025 share one estimation method (MB3), but OEWS pools three years of survey panels and BLS does not
encourage time-series use; changes are reported as observed descriptive differences with an approximate z
(z = delta / sqrt(SE_2021^2 + SE_2025^2), SE = employment x RSE, independence assumed) and are never combined with
the KSA estimands. Every change is also reported from May 2022 (endpoint check, DL-32), and the change in the mean-wage
premium of 49-9041 carries a z on the log wage ratio.

Outputs: outputs/history/oews_3363_2021_2025.csv  (every detailed occupation and the total, by year)
         outputs/history/maintenance_mix.csv       (maintenance family, close pool and context, by year + change)
Wage premiums of 49-9041 over the other targets are reported on mean hourly wages (published RSE) and, for reference,
on annual medians (no published error).
Usage:   python -m src.history
"""
from __future__ import annotations

import argparse
import io
import re
import warnings
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import REPO_ROOT, load_config, repo_path
from .ingest_oews import NUMERIC_COLS, dedupe_occupations, parse_numeric

YEARS = (2021, 2022, 2023, 2024, 2025)
# 2021-2025 is the reported change; 2022-2025 is the endpoint check. Each May estimate pools six semiannual panels
# over three years, so May 2021 / May 2022 and May 2025 share no panel.
PERIODS = ((2021, 2025), (2022, 2025))
NAICS = "336300"
CONTEXT = {"51-9162": "CNC tool programmers", "17-3024": "Electro-mechanical and mechatronics technicians",
           "51-1011": "First-line supervisors of production workers", "51-4111": "Tool and die makers"}


def change_rows(mix: pd.DataFrame, first: int, last: int) -> pd.DataFrame:
    """Change from `first` to `last`: employment (z from the published RSEs) and the mean-wage premium of 49-9041
    (z on the log ratio, SE of a log mean approximated by its RSE; DL-32)."""
    a = mix[mix.year == first].set_index("soc6"); b = mix[mix.year == last].set_index("soc6")
    chg = pd.DataFrame({"emp_change": b.emp - a.emp, "emp_change_pct": 100 * (b.emp / a.emp - 1),
                        "a_median_change_pct": 100 * (b.a_median / a.a_median - 1),
                        "h_mean_change_pct": 100 * (b.h_mean / a.h_mean - 1),
                        "premium_mean_change_pts": b.premium_mean_49_9041_over_pct - a.premium_mean_49_9041_over_pct})
    se = np.sqrt((a.emp * a.emp_rse / 100) ** 2 + (b.emp * b.emp_rse / 100) ** 2)
    chg["z_change"] = np.where(se > 0, chg.emp_change / se, np.nan)
    ia, ib = a.loc["49-9041"], b.loc["49-9041"]
    dlog = np.log(ib.h_mean / b.h_mean) - np.log(ia.h_mean / a.h_mean)
    se_log = np.sqrt(((ia.mean_prse ** 2 + a.mean_prse ** 2) + (ib.mean_prse ** 2 + b.mean_prse ** 2))) / 100
    chg["premium_mean_change_z"] = np.where(chg.premium_mean_change_pts.notna(), dlog / se_log, np.nan)
    chg = chg.reset_index().assign(year=f"{first}-{last}")
    return chg.merge(a[["role", "title"]].reset_index(), on="soc6", how="left")


def zip_path(year: int, cfg: dict[str, Any], root: Path) -> Path:
    if year == 2025:
        return repo_path(cfg["paths"]["raw_oews"], root) / cfg["data_versions"]["oews"]["file"]
    return repo_path("data/raw/oews_history", root) / f"oesm{year % 100:02d}in4.zip"


def read_year(path: Path, year: int) -> pd.DataFrame:
    """NAICS 336300 rows of one OEWS national industry-specific file (4-digit workbook)."""
    with zipfile.ZipFile(path) as zf:
        member = next((n for n in zf.namelist() if re.search(rf"nat4d_M{year}_dl\.xlsx$", n)), None)
        if member is None:
            raise ValueError(f"{path.name}: no nat4d_M{year}_dl.xlsx member")
        data = zf.read(member)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")                       # openpyxl style warnings in BLS workbooks
        df = pd.read_excel(io.BytesIO(data), dtype=str, keep_default_na=False)
    df.columns = [str(c).strip().upper() for c in df.columns]
    if "O_GROUP" not in df.columns and "OCC_GROUP" in df.columns:   # files before May 2019 name the column OCC_GROUP
        df = df.rename(columns={"OCC_GROUP": "O_GROUP"})
    df = df[df["NAICS"].str.strip() == NAICS].copy()
    if df.empty:
        raise ValueError(f"{path.name}: NAICS {NAICS} not found")
    df = parse_numeric(df)
    df, _ = dedupe_occupations(df)
    keep = ["OCC_CODE", "OCC_TITLE", "O_GROUP", *NUMERIC_COLS]
    return df[keep].assign(year=year, source=f"{path.name}:{member}")


def run(cfg: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, pd.DataFrame] | None:
    paths = {y: zip_path(y, cfg, root) for y in YEARS}
    missing = [y for y, p in paths.items() if not p.exists()]
    if missing:
        print(f"[skip] OEWS history files missing for {missing} (optional input, DL-29)")
        return None
    allyears = pd.concat([read_year(p, y) for y, p in paths.items()], ignore_index=True)
    allyears = allyears[allyears.O_GROUP.isin(["detailed", "total"]) | allyears.OCC_CODE.isin(["51-2090"])]

    est = repo_path("outputs/estimates", root)
    h1 = pd.read_csv(est / "h1_decisions.csv")
    close = sorted(h1[(h1.domain == "S") & (h1.feeder_role == "feeder_core") & h1.close_rule].feeder)
    targets = list(cfg["frame"]["targets_core"])
    piv = lambda col: allyears.pivot_table(index="year", columns="OCC_CODE", values=col, aggfunc="first")
    emp, rse, wage = piv("TOT_EMP"), piv("EMP_PRSE"), piv("A_MEDIAN")
    hmean, mrse = piv("H_MEAN"), piv("MEAN_PRSE")     # mean wages carry a published RSE; medians do not
    total = emp["00-0000"]
    fam = emp[targets].sum(axis=1)

    rows = []
    groups = ([(c, "maintenance target") for c in targets] + [(c, "close feeder (Skills H1)") for c in close]
              + [(c, "context") for c in CONTEXT])
    for c, role in groups:
        for y in YEARS:
            rows.append({"year": y, "soc6": c, "role": role, "emp": emp.at[y, c], "emp_rse": rse.at[y, c],
                         "a_median": wage.at[y, c], "h_mean": hmean.at[y, c], "mean_prse": mrse.at[y, c],
                         "share_of_industry_pct": 100 * emp.at[y, c] / total[y],
                         "share_of_family_pct": 100 * emp.at[y, c] / fam[y] if role == "maintenance target" else np.nan,
                         "premium_49_9041_over_pct": 100 * (wage.at[y, "49-9041"] / wage.at[y, c] - 1)
                         if role == "maintenance target" and c != "49-9041" else np.nan,
                         "premium_mean_49_9041_over_pct": 100 * (hmean.at[y, "49-9041"] / hmean.at[y, c] - 1)
                         if role != "context" and c != "49-9041" else np.nan})
    for y in YEARS:
        rows.append({"year": y, "soc6": "FAMILY", "role": "maintenance family (5 targets)", "emp": fam[y],
                     "share_of_industry_pct": 100 * fam[y] / total[y]})
        pool = emp.loc[y, close].sum()
        rows.append({"year": y, "soc6": "CLOSE_POOL", "role": "close-feeder pool (" + ", ".join(close) + ")",
                     "emp": pool, "share_of_industry_pct": 100 * pool / total[y]})
        rows.append({"year": y, "soc6": "00-0000", "role": "industry total (OEWS)", "emp": total[y],
                     "a_median": wage.at[y, "00-0000"], "h_mean": hmean.at[y, "00-0000"]})
    mix = pd.DataFrame(rows)
    mix["title"] = mix.soc6.map(allyears.drop_duplicates("OCC_CODE", keep="last").set_index("OCC_CODE").OCC_TITLE)

    # change between two years with approximate z values (independence of the two estimates assumed)
    changes = [change_rows(mix, y0, y1) for y0, y1 in PERIODS]
    mix = pd.concat([mix, *changes], ignore_index=True)

    out = repo_path("outputs/history", root)
    out.mkdir(parents=True, exist_ok=True)
    allyears.to_csv(out / "oews_3363_2021_2025.csv", index=False)
    mix.to_csv(out / "maintenance_mix.csv", index=False)
    return {"all": allyears, "mix": mix}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    res = run(load_config(args.config))
    if res is None:
        return 0
    m = res["mix"]
    pd.set_option("display.width", 250)
    yrs = m[m.year.astype(str).str.fullmatch(r"\d{4}")]
    print(yrs.pivot_table(index=["role", "soc6"], columns="year", values="emp", aggfunc="first").to_string())
    print(m[m.year.astype(str).str.contains("-")][["year", "soc6", "role", "emp_change", "emp_change_pct", "z_change",
                                                    "premium_mean_change_pts", "premium_mean_change_z"]].round(1).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
