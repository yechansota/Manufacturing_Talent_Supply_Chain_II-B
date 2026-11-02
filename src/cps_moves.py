"""Observed production -> maintenance moves in matched CPS months (deviation log DL-37, readings DL-40; exploratory).

The Current Population Survey interviews a household for four consecutive months, so the same person's main-job
occupation can be compared across two consecutive months. With dependent interviewing, a respondent who still works for
last month's employer (PUIODP1) and reports unchanged duties keeps last month's occupation code; a new code is
assigned only after a change of employer or duties.

  Groups   Census 2018 occupation codes (main job): M = maintenance targets {6355, 7330, 7340, 7350, 7360};
           P = codes whose SOC begins 51-; C = 8030 (machinists, the one close feeder with its own code);
           mixed codes 7905 (CNC tool operators with programmers) and 8225 (multiple machine tool setters with other
           metal and plastic workers) reported separately; R = other P codes.
  Q1       Share of P person-month pairs (manufacturing at t-1) observed in M at t; any employer and same employer.
  Q2       Among workers in M at t who were in another occupation at t-1: the share coming from P. Destination
           universe (manufacturing at t, primary, DL-40a) and the universe as written in DL-37 (manufacturing at t-1).
  Q3       Q1 rate ratio, C vs R (prediction logged before data: greater than 1).
  Origin   Origin composition of the Q2 entrants by t-1 occupation group (DL-43).
  Checks   (i) persistence at t+1, (ii) excluding March 2020-December 2021, (iii) Census industry 3570
           (NAICS 3361-3363), (iv) excluding pairs with allocated occupation or industry. Check (iv) is the README
           headline and the main estimate is reported beside it as the registered primary (DL-42).
  Weights  PWCMPWGT at t. Intervals: household-cluster bootstrap, B = 1,000, seed 20261027 (approximate: the public
           files carry no design variables). Reporting rule: NCHS data presentation standards for proportions
           (n >= 30, at least one event, interval-width rules).
  Units    Q1 also per 10,000 production workers per month and annualized as 1 - (1 - p)^12 (DL-45); illustrative
           NAICS 3363 scale of the same-employer rate (DL-45).

Inputs:  data/raw/cps/basic/{mon}{yy}pub.zip (January 2020 - latest), data/raw/census_codes/*.xlsx;
         data/raw/oews/oesm25in4.zip and outputs/practice/pool_arithmetic.csv (scale illustration only)
Cache:   data/interim/cps_employed.npz (employed person records; rebuilt with --rebuild)
Outputs: outputs/cps_moves/q1_rates.csv, q2_shares.csv, q3_ratios.csv, q2_origin_composition.csv,
         allocation_diagnostic.csv, scale_illustration.csv, m_codes_by_sector.csv (DL-46), link_quality.csv,
         cps_summary.md
Usage:   python -m src.cps_moves [--rebuild] [--draws B]
"""
from __future__ import annotations

import argparse
import re
import warnings
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import REPO_ROOT, load_config, repo_path

# 1-based inclusive positions; identical in the January 2020 and January 2025 record layouts
FIELDS = {"HRHHID": (1, 15), "HRMONTH": (16, 17), "HRYEAR4": (18, 21), "HRINTSTA": (57, 58), "HRMIS": (63, 64),
          "HRHHID2": (71, 75), "PRTAGE": (122, 123), "PESEX": (129, 130), "PULINENO": (147, 148),
          "PEMLR": (180, 181), "PUIODP1": (426, 427), "PXIO1ICD": (767, 768), "PXIO1OCD": (769, 770),
          "PWCMPWGT": (846, 855), "PEIO1ICD": (856, 859), "PTIO1OCD": (860, 863)}
MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()
M_CODES = {6355: "47-2111", 7330: "49-904X", 7340: "49-9071", 7350: "49-9043", 7360: "49-9044"}
C_CODES = {8030: "51-4041"}
MIXED = {7905: "51-9160", 8225: "51-4XXX"}
MOTOR_VEHICLES = 3570
SEED, B_DEFAULT = 20261027, 1000
EXCLUDE_WINDOW = (2020 * 12 + 2, 2021 * 12 + 11)          # March 2020 .. December 2021 (month index = 12*y + m - 1)
ALLOCATED = set(range(30, 44))
HEADLINE_CHECK = "iv_no_allocation"                       # DL-42
ROLE = {"main": "registered primary", HEADLINE_CHECK: "headline (DL-42)"}
ORIGINS = ["production_mfg", "production_outside_mfg", "other_install_maint_repair", "construction_extraction",
           "transport_material_moving", "architecture_engineering", "other"]       # DL-43, in this order


def soc_major(codes: pd.Series, soc_of: dict[int, str]) -> pd.Series:
    """Two-digit SOC major group of Census occupation codes ('' when unmapped)."""
    major = {c: s[:2] for c, s in soc_of.items()}
    return codes.map(major).fillna("")


def origin_group(occ_p: pd.Series, ind_p: pd.Series, soc_of: dict[int, str], mfg: set[int]) -> np.ndarray:
    """DL-43 origin of an entrant to M from the t-1 occupation and industry (mutually exclusive, in ORIGINS order)."""
    maj = soc_major(occ_p, soc_of)
    notM = ~occ_p.isin(list(M_CODES))
    in_mfg = ind_p.isin(list(mfg))
    return np.select([(maj == "51") & in_mfg, maj == "51", (maj == "49") & notM, (maj == "47") & notM,
                      maj == "53", maj == "17"], ORIGINS[:-1], ORIGINS[-1])


def annualize(p_pct: float | np.ndarray) -> float | np.ndarray:
    """Monthly percent -> annual percent, 1 - (1 - p)^12 (constant monthly rate; DL-45)."""
    return 100 * (1 - (1 - np.asarray(p_pct, dtype=float) / 100) ** 12)


# ---------------------------------------------------------------------------------------------------------------
# Inputs
def census_codes(root: Path) -> tuple[set[int], set[int], dict[int, str]]:
    """P codes (SOC 51-), manufacturing industry codes (NAICS 31-33), and the SOC of every occupation code."""
    base = repo_path("data/raw/census_codes", root)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        occ = pd.read_excel(base / "2018-occupation-code-list-and-crosswalk.xlsx", sheet_name="2018 Census Occ Code List",
                            header=None, dtype=str)
    occ = occ.iloc[:, 1:4]; occ.columns = ["title", "code", "soc"]
    occ = occ[occ.code.fillna("").str.strip().str.fullmatch(r"\d{4}")]
    soc_of = {int(c): str(s).strip() for c, s in zip(occ.code, occ.soc)}
    p_codes = {c for c, s in soc_of.items() if s.startswith("51-")}
    mfg: set[int] = set()
    for f, sheet in (("2017-industry-code-list-with-crosswalk.xlsx", "2017 Census Industry Code List"),
                     ("2022-Census-Industry-Code-List-with-Crosswalk.xlsx", "2022 Census Ind Code List ")):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            t = pd.read_excel(base / f, sheet_name=sheet, header=None, dtype=str)
        t = t.iloc[:, 3:5]; t.columns = ["code", "naics"]
        t = t[t.code.fillna("").str.strip().str.fullmatch(r"\d{4}")]
        nai = t.naics.fillna("").str.strip()
        mfg |= {int(c) for c, n in zip(t.code, nai) if re.match(r"^(31|32|33)", n) or n.startswith("Part of 31")}
    for c, s in {**M_CODES, **C_CODES, **MIXED}.items():
        if soc_of.get(c) != s:
            raise ValueError(f"Census code {c}: expected SOC {s}, found {soc_of.get(c)}")
    if MOTOR_VEHICLES not in mfg:
        raise ValueError("industry 3570 not classified as manufacturing")
    return p_codes, mfg, soc_of


def month_files(root: Path) -> list[tuple[int, Path]]:
    d = repo_path("data/raw/cps/basic", root)
    out = []
    for p in sorted(d.glob("*pub.zip")):
        m = re.fullmatch(r"([a-z]{3})(\d{2})pub\.zip", p.name)
        if m:
            out.append(((2000 + int(m.group(2))) * 12 + MONTHS.index(m.group(1)), p))
    return sorted(out)


def parse_month(path: Path, mindex: int) -> dict[str, np.ndarray]:
    """Employed person records (PEMLR 1-2) of one monthly file."""
    sl = {k: slice(a - 1, b) for k, (a, b) in FIELDS.items()}
    cols: dict[str, list] = {k: [] for k in FIELDS}
    with zipfile.ZipFile(path) as zf, zf.open(zf.namelist()[0]) as fh:
        for raw in fh:
            if raw[sl["PEMLR"]].strip() not in (b"1", b"2"):
                continue
            for k, s in sl.items():
                cols[k].append(raw[s].strip())
    yr, mo = int(cols["HRYEAR4"][0]), int(cols["HRMONTH"][0])
    if yr * 12 + mo - 1 != mindex or len(set(cols["HRMONTH"])) != 1:
        raise ValueError(f"{path.name}: year/month fields do not match the file name")
    out = {"hh": np.array(cols["HRHHID"], dtype=np.int64), "hh2": np.array(cols["HRHHID2"], dtype=np.int64),
           "line": np.array(cols["PULINENO"], dtype=np.int16), "mis": np.array(cols["HRMIS"], dtype=np.int8),
           "age": np.array(cols["PRTAGE"], dtype=np.int16), "sex": np.array(cols["PESEX"], dtype=np.int8),
           "iodp1": np.array([int(v) for v in cols["PUIODP1"]], dtype=np.int8),
           "xind": np.array([int(v) for v in cols["PXIO1ICD"]], dtype=np.int16),
           "xocc": np.array([int(v) for v in cols["PXIO1OCD"]], dtype=np.int16),
           "w": np.array(cols["PWCMPWGT"], dtype=np.float64) / 1e4,
           "ind": np.array(cols["PEIO1ICD"], dtype=np.int16), "occ": np.array(cols["PTIO1OCD"], dtype=np.int16)}
    out["m"] = np.full(len(out["hh"]), mindex, dtype=np.int32)
    out["n_records_month"] = np.array([len(out["hh"])])
    return out


def load_employed(root: Path, rebuild: bool = False) -> tuple[pd.DataFrame, list[str]]:
    files = month_files(root)
    cache = repo_path("data/interim", root) / "cps_employed.npz"
    names = [p.name for _, p in files]
    if cache.exists() and not rebuild:
        z = np.load(cache, allow_pickle=False)
        if list(z["files"]) == names:
            return pd.DataFrame({k: z[k] for k in z.files if k != "files"}), names
    parts = [parse_month(p, mi) for mi, p in files]
    df = pd.DataFrame({k: np.concatenate([q[k] for q in parts]) for k in parts[0] if k != "n_records_month"})
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, files=np.array(names), **{k: df[k].to_numpy() for k in df.columns})
    return df, names


# ---------------------------------------------------------------------------------------------------------------
# Linking
KEYS = ["hh", "hh2", "line"]


def link(df: pd.DataFrame) -> pd.DataFrame:
    """Pairs (t-1, t) of the same employed person in consecutive months, plus the t+1 record when linked."""
    prev = df[KEYS + ["m", "mis", "sex", "age", "occ", "ind", "xocc", "xind"]].copy()
    prev["m"] = prev["m"] + 1
    pr = df.merge(prev, on=KEYS + ["m"], suffixes=("", "_p"))
    ok = (pr.mis == pr.mis_p + 1) & ~pr.mis.isin([1, 5]) & (pr.sex == pr.sex_p) & (pr.age - pr.age_p).isin([0, 1])
    pr = pr[ok].copy()
    nxt = df[KEYS + ["m", "mis", "sex", "age", "occ"]].copy()
    nxt["m"] = nxt["m"] - 1
    nxt = nxt.rename(columns={"mis": "mis_n", "sex": "sex_n", "age": "age_n", "occ": "occ_n"})
    pr = pr.merge(nxt, on=KEYS + ["m"], how="left")
    good_n = (pr.mis_n == pr.mis + 1) & (pr.sex_n == pr.sex) & (pr.age_n - pr.age).isin([0, 1])
    pr["occ_n"] = pr.occ_n.where(good_n)
    return pr.reset_index(drop=True)


def link_quality(df: pd.DataFrame, pr: pd.DataFrame) -> pd.DataFrame:
    """Share of employed records in month-in-sample 2-4 / 6-8 whose previous month is in the data and that link."""
    months = set(df.m.unique())
    elig = df[~df.mis.isin([1, 5]) & (df.m - 1).isin(months)]
    a = elig.groupby(elig.m // 12).size().rename("eligible_records")
    b = pr.groupby(pr.m // 12).size().rename("linked_pairs")
    q = pd.concat([a, b], axis=1).fillna(0).astype(int)
    q["link_rate_pct"] = 100 * q.linked_pairs / q.eligible_records
    return q.rename_axis("year").reset_index()


# ---------------------------------------------------------------------------------------------------------------
# Estimates
def checks(pr: pd.DataFrame) -> dict[str, pd.Series]:
    """Boolean masks over pairs; (i) is applied to events, not to pairs (see entry_drop)."""
    alloc = pr.xocc.isin(ALLOCATED) | pr.xind.isin(ALLOCATED) | pr.xocc_p.isin(ALLOCATED) | pr.xind_p.isin(ALLOCATED)
    window = pr.m.between(*EXCLUDE_WINDOW)
    t = pd.Series(True, index=pr.index)
    return {"main": t, "i_persistence": t, "ii_excl_2020_2021": ~window, "iii_industry_3570": t, "iv_no_allocation": ~alloc}


def build_columns(pr: pd.DataFrame, p_codes: set[int], mfg: set[int],
                  soc_of: dict[int, str] | None = None) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Weighted numerator/denominator columns per pair for every reported quantity; metadata per quantity."""
    inM, inM_p = pr.occ.isin(list(M_CODES)), pr.occ_p.isin(list(M_CODES))
    same = pr.iodp1 == 1
    spurious = inM & ~inM_p & pr.occ_n.notna() & ~pr.occ_n.isin(list(M_CODES))
    origin = np.select([pr.occ_p.isin(list(C_CODES)), pr.occ_p == 7905, pr.occ_p == 8225, pr.occ_p.isin(list(p_codes))],
                       ["close_8030", "mixed_7905", "mixed_8225", "rest"], "other")
    entry_origin = origin_group(pr.occ_p, pr.ind_p, soc_of, mfg) if soc_of is not None else None
    cols, meta = {}, []
    w = pr.w.to_numpy()
    none = pd.Series(False, index=pr.index)
    for ck, keep in checks(pr).items():
        ev_any = inM & ~(spurious if ck == "i_persistence" else none)
        ev_same = ev_any & same
        if ck == "iii_industry_3570":
            u1 = pr.ind_p == MOTOR_VEHICLES; u2d = pr.ind == MOTOR_VEHICLES; u2w = pr.ind_p == MOTOR_VEHICLES
        else:
            u1 = pr.ind_p.isin(list(mfg)); u2d = pr.ind.isin(list(mfg)); u2w = pr.ind_p.isin(list(mfg))
        base1 = keep & u1 & pr.occ_p.isin(list(p_codes))
        for grp in ["all_P", "close_8030", "mixed_7905", "mixed_8225", "rest"]:
            g = base1 if grp == "all_P" else base1 & (origin == grp)
            for evn, ev in (("any_employer", ev_any), ("same_employer", ev_same)):
                key = f"q1|{ck}|{grp}|{evn}"
                cols[key + "|num"] = w * (g & ev); cols[key + "|den"] = w * g
                meta.append({"key": key, "q": "q1", "check": ck, "group": grp, "event": evn,
                             "n_den": int(g.sum()), "n_num": int((g & ev).sum())})
        drop_entry = spurious if ck == "i_persistence" else none
        for uni, u in (("destination_mfg_t", u2d), ("as_written_mfg_t-1", u2w)):
            entrants = keep & u & inM & ~inM_p & ~drop_entry
            for evn, sub in (("any_employer", entrants), ("same_employer", entrants & same)):
                key = f"q2|{ck}|{uni}|{evn}"
                fromP = sub & pr.occ_p.isin(list(p_codes))
                cols[key + "|num"] = w * fromP; cols[key + "|den"] = w * sub
                meta.append({"key": key, "q": "q2", "check": ck, "group": uni, "event": evn,
                             "n_den": int(sub.sum()), "n_num": int(fromP.sum())})
                if entry_origin is None or uni != "destination_mfg_t" or ck == "iii_industry_3570":
                    continue
                for og in ORIGINS:                                           # DL-43
                    k2 = f"q2o|{ck}|{og}|{evn}"
                    hit = sub & (entry_origin == og)
                    cols[k2 + "|num"] = w * hit; cols[k2 + "|den"] = w * sub
                    meta.append({"key": k2, "q": "q2o", "check": ck, "group": og, "event": evn,
                                 "n_den": int(sub.sum()), "n_num": int(hit.sum())})
    return pd.DataFrame(cols), meta


def allocation_diagnostic(pr: pd.DataFrame, p_codes: set[int], mfg: set[int]) -> pd.DataFrame:
    """DL-42 evidence: share of pairs with an allocated occupation or industry code in either month."""
    alloc = pr.xocc.isin(ALLOCATED) | pr.xind.isin(ALLOCATED) | pr.xocc_p.isin(ALLOCATED) | pr.xind_p.isin(ALLOCATED)
    inM, inM_p = pr.occ.isin(list(M_CODES)), pr.occ_p.isin(list(M_CODES))
    mfg_p, mfg_t = pr.ind_p.isin(list(mfg)), pr.ind.isin(list(mfg))
    changed = pr.occ != pr.occ_p
    groups = {
        "all linked pairs": pd.Series(True, index=pr.index),
        "manufacturing at t-1, same occupation code": mfg_p & ~changed,
        "manufacturing at t-1, occupation code changed": mfg_p & changed,
        "Q1 events (P in manufacturing at t-1, in M at t)": mfg_p & pr.occ_p.isin(list(p_codes)) & inM,
        "Q2 entrants (in M and manufacturing at t, not in M at t-1)": mfg_t & inM & ~inM_p,
        "in M at t-1 and at t, manufacturing at t": mfg_t & inM & inM_p,
    }
    rows = [{"group": g, "pairs": int(m.sum()), "allocated": int((m & alloc).sum()),
             "pct_allocated": 100 * (m & alloc).sum() / m.sum()} for g, m in groups.items()]
    for lab, m in (("occupation code changes, manufacturing at t-1: all pairs", mfg_p),
                   ("occupation code changes, manufacturing at t-1: no allocation", mfg_p & ~alloc),
                   ("occupation code changes, manufacturing at t-1: with allocation", mfg_p & alloc)):
        rows.append({"group": lab, "pairs": int(m.sum()), "allocated": int((m & changed).sum()),
                     "pct_allocated": 100 * (m & changed).sum() / m.sum()})
    out = pd.DataFrame(rows)
    out.columns = ["group", "pairs", "count", "pct"]                    # count/pct = allocated, or changed for the last three
    return out


def oews_production_3363(cfg: dict[str, Any], root: Path) -> float:
    """OEWS May 2025, NAICS 336300, SOC 51-0000 employment (DL-45 illustration)."""
    from .ingest_oews import parse_numeric, read_oews_member
    ocfg = cfg["data_versions"]["oews"]
    df = read_oews_member(repo_path(cfg["paths"]["raw_oews"], root) / ocfg["file"], ocfg["member"])
    row = df[(df.AREA.str.strip() == ocfg["area"]) & (df.NAICS.str.strip() == ocfg["naics"]) & (df.OCC_CODE == "51-0000")]
    val = parse_numeric(row).TOT_EMP.dropna().unique()
    if len(val) != 1:
        raise ValueError("OEWS 51-0000 for NAICS 336300 not found uniquely")
    return float(val[0])


M_SOCS = ["47-2111", "49-9041", "49-9043", "49-9044", "49-9045", "49-9071"]


def m_codes_by_sector(cfg: dict[str, Any], root: Path) -> pd.DataFrame:
    """DL-46: national employment of each SOC in the M codes by NAICS sector (OEWS May 2025) and its manufacturing share."""
    import io
    import zipfile
    ocfg = cfg["data_versions"]["oews"]
    zp = repo_path(cfg["paths"]["raw_oews"], root) / ocfg["file"]
    with zipfile.ZipFile(zp) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith("natsector_m2025_dl.xlsx"))
        df = pd.read_excel(io.BytesIO(zf.read(name)), dtype=str)
    df.columns = [c.upper() for c in df.columns]
    df = df[df.OCC_CODE.isin(M_SOCS)].copy()
    df["TOT_EMP"] = pd.to_numeric(df.TOT_EMP.str.replace(",", ""), errors="coerce")
    rows = []
    for soc, g in df.groupby("OCC_CODE"):
        tot = g.TOT_EMP.sum()
        mfg = g.loc[g.NAICS.str.strip() == "31-33", "TOT_EMP"].sum()
        top = g.sort_values("TOT_EMP", ascending=False).iloc[0]
        rows.append({"soc": soc, "title": g.OCC_TITLE.iloc[0], "sum_of_sector_rows": tot, "manufacturing_31_33": mfg,
                     "manufacturing_share_pct": 100 * mfg / tot if tot else np.nan,
                     "largest_sector": f"{top.NAICS} {top.NAICS_TITLE}", "largest_sector_emp": top.TOT_EMP,
                     "sectors_with_withheld_employment": int(g.TOT_EMP.isna().sum())})
    return pd.DataFrame(rows)


def scale_illustration(q1: pd.DataFrame, cfg: dict[str, Any], root: Path) -> pd.DataFrame | None:
    """DL-45: annualized same-employer Q1 rate x 3363 production jobs, beside DL-13 family separations."""
    pool = repo_path("outputs/practice", root) / "pool_arithmetic.csv"
    if not pool.exists():
        return None
    pa = pd.read_csv(pool)
    sep = float(pa.loc[pa.quantity.str.startswith("Illustrative annual separations"), "value"].iloc[0])
    exits = float(pa.loc[pa.quantity.str.strip().str.startswith("of which labor-force exits"), "value"].iloc[0])
    jobs = oews_production_3363(cfg, root)
    rows = []
    for ck in (HEADLINE_CHECK, "main"):
        r = q1[(q1.check == ck) & (q1.group == "all_P") & (q1.event == "same_employer")].iloc[0]
        a, alo, ahi = annualize([r.pct, r.lo, r.hi])
        rows.append({"estimate": ROLE[ck], "check": ck, "monthly_pct": r.pct, "annual_pct": a, "annual_lo": alo,
                     "annual_hi": ahi, "production_jobs_3363_oews_may2025": jobs, "illustrative_moves_per_year": jobs * a / 100,
                     "illustrative_lo": jobs * alo / 100, "illustrative_hi": jobs * ahi / 100,
                     "family_illustrative_separations_per_year": sep, "family_illustrative_exits_per_year": exits,
                     "note": "illustrative (DL-45): assumes the NAICS 3363 rate equals the manufacturing-wide CPS rate "
                             "and a constant monthly rate; not a headline"})
    return pd.DataFrame(rows)


def nchs_rule(n: int, events: int, p: float, lo: float, hi: float) -> tuple[bool, str]:
    width = hi - lo
    if n < 30:
        return False, "n < 30"
    if events < 1:
        return False, "no event"
    if width >= 30:
        return False, "interval width >= 30 points"
    if width > 5 and (p <= 0 or width / p > 1.3):
        return False, "relative interval width > 130%"
    return True, ""


def bootstrap(pr: pd.DataFrame, cols: pd.DataFrame, draws: int, seed: int = SEED) -> np.ndarray:
    """Household-cluster bootstrap over the households in `pr`: replicate column totals (draws x columns)."""
    hh_id = pr.groupby(["hh", "hh2"], sort=False).ngroup().to_numpy()
    X = cols.groupby(hh_id).sum().to_numpy()
    H = X.shape[0]
    rng = np.random.default_rng(seed)
    out = np.empty((draws, cols.shape[1]))
    for b in range(draws):
        cnt = np.bincount(rng.integers(0, H, H), minlength=H)
        out[b] = cnt @ X
    return out


def run(cfg: dict[str, Any], root: Path = REPO_ROOT, draws: int = B_DEFAULT, rebuild: bool = False) -> dict[str, Any] | None:
    files = month_files(root)
    if not files:
        print("[skip] CPS basic monthly files not present (optional input, DL-37)")
        return None
    p_codes, mfg, soc_of = census_codes(root)
    df, names = load_employed(root, rebuild)
    pr_all = link(df)
    lq = link_quality(df, pr_all)
    # pairs that can enter any universe: manufacturing at t-1 or at t (clusters = their households)
    pr = pr_all[pr_all.ind_p.isin(list(mfg)) | pr_all.ind.isin(list(mfg))].reset_index(drop=True)
    diag = allocation_diagnostic(pr_all, p_codes, mfg)
    cols, meta = build_columns(pr, p_codes, mfg, soc_of)
    tot = cols.sum().to_numpy()
    reps = bootstrap(pr, cols, draws)
    idx = {c: i for i, c in enumerate(cols.columns)}
    rows = []
    for mt in meta:
        k = mt["key"]
        num, den = tot[idx[k + "|num"]], tot[idx[k + "|den"]]
        rn, rd = reps[:, idx[k + "|num"]], reps[:, idx[k + "|den"]]
        p = 100 * num / den if den > 0 else np.nan
        with np.errstate(invalid="ignore", divide="ignore"):
            rp = 100 * rn / rd
        lo, hi = (np.nanpercentile(rp, [2.5, 97.5]) if den > 0 else (np.nan, np.nan))
        ok, why = nchs_rule(mt["n_den"], mt["n_num"], p, lo, hi)
        rows.append({**mt, "pct": p, "lo": lo, "hi": hi, "reportable": ok, "not_reportable_reason": why,
                     "_rep": rp})
    res = pd.DataFrame(rows)
    res["role"] = res.check.map(ROLE).fillna("check")
    q1 = res[res.q == "q1"].drop(columns=["_rep", "q"]).reset_index(drop=True)
    q1["per_10000"] = 100 * q1.pct
    q1["per_10000_lo"], q1["per_10000_hi"] = 100 * q1.lo, 100 * q1.hi
    q1["annual_pct"], q1["annual_lo"], q1["annual_hi"] = annualize(q1.pct), annualize(q1.lo), annualize(q1.hi)
    q2 = res[res.q == "q2"].drop(columns=["_rep", "q"]).reset_index(drop=True)
    q2o = res[res.q == "q2o"].drop(columns=["_rep", "q"]).reset_index(drop=True)
    q2o["order"] = q2o.group.map({g: i for i, g in enumerate(ORIGINS)})
    q2o = q2o.sort_values(["check", "event", "order"]).drop(columns="order").reset_index(drop=True)
    scale = scale_illustration(q1, cfg, root)
    rr_rows = []
    for ck in q1.check.unique():
        for evn in ("any_employer", "same_employer"):
            a = res[(res.q == "q1") & (res.check == ck) & (res.group == "close_8030") & (res.event == evn)].iloc[0]
            b = res[(res.q == "q1") & (res.check == ck) & (res.group == "rest") & (res.event == evn)].iloc[0]
            both = bool(a.reportable and b.reportable)
            with np.errstate(invalid="ignore", divide="ignore"):
                rr_rep = a._rep / b._rep
            rr = a.pct / b.pct if b.pct > 0 else np.nan
            lo, hi = np.nanpercentile(rr_rep[np.isfinite(rr_rep)], [2.5, 97.5]) if np.isfinite(rr_rep).any() else (np.nan, np.nan)
            rr_rows.append({"check": ck, "role": ROLE.get(ck, "check"), "event": evn, "rate_close_pct": a.pct,
                            "rate_rest_pct": b.pct, "ratio": rr,
                            "lo": lo, "hi": hi, "reportable": both, "events_close": a.n_num, "events_rest": b.n_num,
                            "share_draws_ratio_gt_1": float(np.mean(rr_rep[np.isfinite(rr_rep)] > 1))})
    q3 = pd.DataFrame(rr_rows)
    out = repo_path("outputs/cps_moves", root); out.mkdir(parents=True, exist_ok=True)
    q1.to_csv(out / "q1_rates.csv", index=False); q2.to_csv(out / "q2_shares.csv", index=False)
    q3.to_csv(out / "q3_ratios.csv", index=False); lq.to_csv(out / "link_quality.csv", index=False)
    q2o.to_csv(out / "q2_origin_composition.csv", index=False)
    diag.to_csv(out / "allocation_diagnostic.csv", index=False)
    msec = m_codes_by_sector(cfg, root)
    msec.to_csv(out / "m_codes_by_sector.csv", index=False)
    if scale is not None:
        scale.to_csv(out / "scale_illustration.csv", index=False)
    first, last = names[0], names[-1]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fmt = lambda d: d.round(4).to_markdown(index=False)
    md = [f"# Observed production -> maintenance moves, matched CPS months (DL-37, DL-40) — exploratory\n\nGenerated: {ts}\n",
          f"Files: {len(names)} monthly files, {first} to {last}. Employed person records: {len(df):,}. Linked pairs: {len(pr_all):,} "
          f"({len(pr):,} with manufacturing at t-1 or t). "
          f"Bootstrap: household clusters, B = {draws}, seed {SEED}. Rates are percent per month.\n",
          "## Link quality\n", fmt(lq), "\n## Q1 — P (manufacturing at t-1) observed in M at t\n", fmt(q1),
          "\n## Q2 — entrants to M: share coming from P\n", fmt(q2), "\n## Q3 — rate ratio, machinists (8030) vs other production codes\n", fmt(q3),
          "\n## Origin composition of entrants to M in manufacturing (DL-43)\n", fmt(q2o),
          "\n## Allocation diagnostic (DL-42)\n", fmt(diag),
          "\n## Where the maintenance occupations are employed, OEWS May 2025 (DL-46)\n", fmt(msec)]
    if scale is not None:
        md += ["\n## Illustrative NAICS 3363 scale of the same-employer rate (DL-45)\n", fmt(scale.drop(columns="note")),
               "\n" + scale.note.iloc[0] + "\n"]
    md.append(f"\nHeadline (DL-42): check `{HEADLINE_CHECK}`; the `main` rows are the registered primary.\n")
    (out / "cps_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"q1": q1, "q2": q2, "q3": q3, "q2o": q2o, "diag": diag, "scale": scale, "link_quality": lq,
            "n_records": len(df), "n_pairs": len(pr_all), "n_pairs_mfg": len(pr), "files": names}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    ap.add_argument("--rebuild", action="store_true", help="re-read every monthly file instead of the cache")
    ap.add_argument("--draws", type=int, default=B_DEFAULT)
    args = ap.parse_args(argv)
    res = run(load_config(args.config), draws=args.draws, rebuild=args.rebuild)
    if res is None:
        return 0
    pd.set_option("display.width", 250)
    print(f"records {res['n_records']:,}; pairs {res['n_pairs']:,}; files {len(res['files'])}")
    print(res["link_quality"].to_string(index=False))
    for k in ("q1", "q2", "q3", "q2o", "diag"):
        print(res[k].round(4).to_string(index=False))
    if res["scale"] is not None:
        print(res["scale"].drop(columns="note").round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
