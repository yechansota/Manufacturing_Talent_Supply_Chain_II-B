"""Output audit (E-checks): every number downstream of the registered estimators is re-derived or cross-checked.

  E1  tie structure of P in the registered path (self-ties exact, no near-ties)    -> justifies DL-22
  E2  the same feeder -> family P computed by every code path agrees
  E3  bootstrap sensitivity files: shape, ranges, seeds, exact re-execution
  E4  MI-SE changes Knowledge only; S and A differ from the registered run by Monte Carlo noise only
  E5  element-level gap matrix sums to D
  E6  training layer re-derived from the raw O*NET file; category labels behind 'over 1 year'
  E7  production ranking: employment, coverage, missing profiles
  E8  pool arithmetic re-derived from OEWS and EP
  E9  BLS Table 1.12 factors present in the raw workbook as reported
  E10 vintage exclusions equal the DL-20 list
  E11 Abilities subgroup sizes equal DL-17
  E12 deviation log ids contiguous and unique
  E13 figures newer than the outputs they draw
  E14 BLS National Employment Matrix (NAICS 336300) parsed and internally consistent (DL-23)
  E15 NEM 2025 staffing pattern agrees with OEWS May 2025 inside 3363; levels differ by a common factor (DL-25c)
  E16 independent re-implementation from the raw files reproduces D, P, C, pi, wages and pool (DL-25d)
  E17 CES series parsed correctly; its 2025 annual average equals the NEM 2025 industry total (DL-26)
  E18 robustness module (DL-27): exact re-execution; leave-one-target-out P re-derived through the registered evaluator
  E19 OEWS history (DL-29): May 2021 and 2025 values re-read from the raw zips; 2025 equals the registered ingest;
      SHA-256 in MANIFEST
  E20 multiple comparisons and endpoints (DL-32): BH at decision_rules.fdr_q re-derived by a step-up search for H1;
      endpoint z of the wage premium of 49-9041 over the close feeders re-derived from the yearly OEWS file
  E21 family with 49-1011 added (DL-35): registered P reproduced; Skills P re-derived with pandas arithmetic
  E22 CPS observed moves (DL-37): every monthly file re-read with a dict-based linker; pairs and unweighted counts for
      Q1 (all production, machinists) and Q2 (destination) compared with the module outputs
  E23 CPS additions (DL-42, 43, 45, 46): allocation diagnostic and origin-composition counts re-derived from the raw
      files; origin shares sum to 100 and origins 1 + 2 equal Q2; annualization, scale illustration and M codes by
      sector recomputed
  E24 two-stage NEM reading (DL-28): the baseline is the modal change of the line items and exactly the line items
      without a Table 1.12 row for 336300 or all industries; the BLS adjustment column re-derived

Numbering after the split into two repositories (DL-36); the mapping to the single-repository numbering is in
docs/Technical Documentation.md.

Status: PASS / NOTE (true, must be disclosed) / FLAG (needs a decision).
Outputs: outputs/review/output_audit.csv, output_audit.md
Usage:   python -m src.output_audit
"""
from __future__ import annotations

import argparse
import hashlib
import math
import re
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from .config import REPO_ROOT, load_config, repo_path
from .profiles import FAMILY

ROWS: list[dict[str, str]] = []


def check(cid: str, title: str, status: str, detail: str) -> None:
    ROWS.append({"id": cid, "check": title, "status": status, "detail": detail})


def run(cfg: dict[str, Any], root: Path = REPO_ROOT) -> pd.DataFrame:
    ROWS.clear()
    est, prc, sen = (repo_path(p, root) for p in ("outputs/estimates", "outputs/practice", "outputs/sensitivity"))
    pp = pd.read_csv(est / "point_pairs.csv")
    ref = pd.read_csv(est / "reference_distribution.csv")
    fam_pp = pp[pp.target == FAMILY].set_index(["domain", "feeder"])

    # E1 ------------------------------------------------------------------------------------------
    worst_self, worst_near, n_pairs = 0.0, np.inf, 0
    for (d, t), g in pp.groupby(["domain", "target"]):
        r = ref[(ref.domain == d) & (ref.target == t)]
        Dr, codes = r.D.to_numpy(), r.onet_code.to_numpy()
        for row in g.itertuples():
            n_pairs += 1
            mem = row.feeder_codes.split(";")
            is_self = np.isin(codes, mem) if len(mem) == 1 else np.zeros(len(codes), bool)
            if is_self.any():
                worst_self = max(worst_self, float(np.abs(Dr[is_self] - row.D).max()))
            other = Dr[~is_self]
            worst_near = min(worst_near, float(np.abs(other - row.D).min()))
    check("E1", "Registered P: self-ties exact, no near-ties (all targets, all domains)",
          "PASS" if worst_self == 0 and worst_near > 1e-9 else "FLAG",
          f"{n_pairs} feeder×target×domain pairs; max |D_self − D_feeder| = {worst_self:.1e}; "
          f"smallest gap to any other reference occupation = {worst_near:.2e}")

    # E2 ------------------------------------------------------------------------------------------
    paths = {}
    rk = pd.read_csv(prc / "production_ranking_3363.csv")
    rk = rk[rk.has_profile & rk.in_registered_frame].rename(columns={"soc6": "feeder"}).set_index(["domain", "feeder"]).P
    paths["practice ranking"] = rk
    ds = pd.read_csv(sen / "distances.csv")
    paths["distances (D path)"] = ds[(ds.metric == "D (registered)") & (ds.role != "summary")].set_index(["domain", "feeder"]).percentile
    ab = pd.read_csv(sen / "abilities_subgroups.csv")
    paths["abilities 'all'"] = ab[ab.group == "all"].assign(domain="A").set_index(["domain", "feeder"]).P
    mv = pd.read_csv(repo_path("outputs/multiverse/multiverse_feeders.csv", root))
    prim = mv[(mv.standardization == "z") & (mv.weights == "importance_minus_one") & (mv.suppress == "keep")
              & (mv.not_relevant == "as_published") & (mv.feeder_threshold == 4000) & (mv.family_weights == "employment_share")]
    paths["multiverse primary spec"] = prim.set_index(["domain", "feeder"]).P
    vt = pd.read_csv(sen / "vintage.csv")       # vintage path reproduces P at min_year = 0 (asserted in code)
    msgs, ok = [], True
    for name, s in paths.items():
        j = s.to_frame("x").join(fam_pp.P, how="inner")
        dev = float((j.x - j.P).abs().max())
        ok &= dev < 1e-9
        msgs.append(f"{name}: {len(j)} pairs, max |ΔP| {dev:.1e}")
    check("E2", "Feeder → family P agrees across every code path", "PASS" if ok else "FLAG",
          "; ".join(msgs) + "; vintage path asserts equality at min_year = 0")

    # E3 ------------------------------------------------------------------------------------------
    seeds = {"copula": 20261004, "comonotone": 20261005, "mi_se": 20261006}
    H1_THR = next(x["threshold_upper_ci_percentile"] for x in cfg["estimands"]["secondary"] if x["id"] == "H1")
    reg = pd.read_csv(est / "bootstrap_pairs.csv")
    reg_f = reg[reg.target == FAMILY].assign(close_rule=lambda x: x.P_hi <= H1_THR)
    h1 = pd.read_csv(est / "h1_decisions.csv").set_index(["domain", "feeder"]).close_rule
    assert (reg_f.set_index(["domain", "feeder"]).close_rule.reindex(h1.index) == h1).all(), "h1_decisions disagree with P_hi <= 25"
    msgs, ok = [], True
    for v, seed in seeds.items():
        f = sen / f"bootstrap_{v}.csv"
        b = pd.read_csv(f)
        good = (b.B.eq(1000).all() and b.seed.eq(seed).all() and len(b) == len(reg_f)
                and b[["P_lo", "P_hi"]].notna().all().all() and (b.P_lo <= b.P_hi).all()
                and b.P_lo.between(0, 100).all() and b.P_hi.between(0, 100).all()
                and set(zip(b.domain, b.feeder)) == set(zip(reg_f.domain, reg_f.feeder)))
        rr = sen / f"bootstrap_{v}_rerun.csv"
        same = None
        if rr.exists():
            c = pd.read_csv(rr).drop(columns="seconds")
            same = c.equals(b.drop(columns="seconds"))
        ok &= bool(good) and same is not False
        msgs.append(f"{v}: B={b.B.iloc[0]}, seed={b.seed.iloc[0]}, rows={len(b)}, ranges ok={good}, "
                    f"re-execution identical={same}")
    check("E3", "Bootstrap sensitivity files: shape, ranges, seeds, exact re-execution",
          "PASS" if ok else "FLAG", "; ".join(msgs))

    # E4 ------------------------------------------------------------------------------------------
    with duckdb.connect(str(repo_path(cfg["paths"]["duckdb"], root)), read_only=True) as con:
        miss = con.execute("SELECT domain, SUM(CASE WHEN se IS NULL THEN 1 ELSE 0 END) n FROM onet_ratings "
                           "WHERE scale_id IN ('LV','IM') GROUP BY 1").df().set_index("domain").n
        oews = con.execute("SELECT * FROM oews_3363").df().set_index("OCC_CODE")
        sep = con.execute("SELECT * FROM ep_separations WHERE occupation_type = 'Line item'").df().set_index("nem_code")
        rat = con.execute("SELECT onet_code, MIN(date_year) y FROM onet_ratings GROUP BY 1").df().set_index("onet_code").y
    mi = pd.read_csv(sen / "bootstrap_mi_se.csv").merge(
        reg_f[["domain", "feeder", "P_hi", "close_rule"]], on=["domain", "feeder"], suffixes=("", "_reg"))
    sa = mi[mi.domain.isin(["S", "A"])]
    flips = int(((mi.P_hi <= 25) != mi.close_rule).sum())
    check("E4", "MI-SE alters Knowledge only; S/A differences are Monte Carlo noise",
          "PASS" if miss.get("S", 0) == 0 and miss.get("A", 0) == 0 and flips == 0 else "NOTE",
          f"missing SE rows (LV+IM): " + ", ".join(f"{k} {int(v)}" for k, v in miss.items())
          + f"; S/A max |ΔP_hi| vs registered {float((sa.P_hi - sa.P_hi_reg).abs().max()):.2f} points "
          f"(different seeds); H1 decision flips vs registered: {flips}")

    # E5 ------------------------------------------------------------------------------------------
    gm = pd.read_csv(prc / "gap_matrix.csv")
    s = gm.groupby(["domain", "feeder"]).contribution.sum().to_frame("D_gap").join(fam_pp.D)
    dev = float((s.D_gap - s.D).abs().max())
    neg = int((gm.contribution < 0).sum())
    check("E5", "Element-level gap matrix sums to D; no negative contributions",
          "PASS" if dev < 1e-12 and neg == 0 else "FLAG", f"{len(s)} pairs, max |ΣC − D| {dev:.1e}; negative cells {neg}")

    # E6 ------------------------------------------------------------------------------------------
    raw = repo_path(cfg["paths"]["raw_onet"], root)
    te = pd.read_csv(raw / "training_and_experience.csv", dtype=str, keep_default_na=False)
    te = te[te["Scale ID"].isin(["OJ", "PT", "RW"])]
    te = te.assign(cat=te.Category.astype(int), pct=te["Data Value"].astype(float))
    sums = te.groupby(["O*NET-SOC Code", "Scale ID"]).pct.sum()
    cats = pd.read_csv(raw / "training_and_experience_categories.csv", dtype=str, keep_default_na=False)
    cats = cats[cats["Scale ID"].isin(["OJ", "PT", "RW"])].assign(cat=lambda x: x.Category.astype(int))
    lab = cats.set_index(["Scale ID", "cat"])["Category Description"]
    bound_ok = all(lab[(sc, 6)].lower().startswith("over 1 year") and "up to and including 1 year" in lab[(sc, 5)].lower()
                   for sc in ("OJ", "PT", "RW"))
    tt = pd.read_csv(prc / "training_time.csv")
    one = te[(te["O*NET-SOC Code"] == "49-9041.00") & (te["Scale ID"] == "OJ")]
    redo = float(one[one.cat >= 6].pct.sum() / one.pct.sum() * 100)
    got = float(tt.loc[tt.soc6 == "49-9041", "OJ_share_over_1yr_pct"].iloc[0])
    tg = tt[tt.role == "target"]
    fam_redo = float((tg.emp_3363 / tg.emp_3363.sum() * tg.OJ_share_over_1yr_pct).sum())
    fam_got = float(tt.loc[tt.soc6 == "FAMILY", "OJ_share_over_1yr_pct"].iloc[0])
    check("E6", "Training layer re-derived from raw O*NET; 'over 1 year' boundary = category 6 on OJ, PT, RW",
          "PASS" if bound_ok and abs(redo - got) < 1e-9 and abs(fam_redo - fam_got) < 1e-9 and sums.between(99, 101).mean() > 0.99
          else "FLAG",
          f"category sums within 100±1 for {sums.between(99, 101).mean():.1%} of occupation×scale cells "
          f"(min {sums.min():.1f}, max {sums.max():.1f}); 49-9041 OJ >1 yr re-derived {redo:.2f} vs {got:.2f}; "
          f"family {fam_redo:.2f} vs {fam_got:.2f}; boundary labels verified={bound_ok}")

    # E7 ------------------------------------------------------------------------------------------
    rk_all = pd.read_csv(prc / "production_ranking_3363.csv")
    det = oews[(oews.O_GROUP == "detailed") & oews.index.str.startswith("51-")]
    a_emp = rk_all.drop_duplicates("soc6").set_index("soc6").emp_3363
    b_emp = det.TOT_EMP.reindex(a_emp.index)
    same = (a_emp == b_emp) | (a_emp.isna() & b_emp.isna())
    emp_ok = bool(same.all())
    withheld = a_emp[a_emp.isna()].index.tolist()
    nop = rk_all[~rk_all.has_profile].drop_duplicates("soc6")
    check("E7", "Production ranking covers every SOC-51 detailed occupation in OEWS 3363",
          "PASS" if emp_ok and rk_all.soc6.nunique() == len(det) else "FLAG",
          f"{rk_all.soc6.nunique()} of {len(det)} occupations; employment matches OEWS={emp_ok} "
          f"(withheld in OEWS: {', '.join(withheld) if withheld else 'none'}); "
          f"no O*NET profile: " + ", ".join(f"{r.soc6} {r.title}" for r in nop.itertuples()))

    # E8 ------------------------------------------------------------------------------------------
    pa = pd.read_csv(prc / "pool_arithmetic.csv").set_index("quantity").value
    T = cfg["frame"]["targets_core"]
    seps = float((oews.loc[T, "TOT_EMP"] * sep.loc[T, "separations_rate_pct"] / 100).sum())
    close = reg_f[(reg_f.domain == "S") & (reg_f.feeder_role == "feeder_core") & reg_f.close_rule].feeder
    pool = float(oews.loc[close, "TOT_EMP"].sum())
    ok = (abs(pa["Maintenance family employment in 3363"] - oews.loc[T, "TOT_EMP"].sum()) < 1e-9
          and abs(pa["Close-feeder pool in 3363 (S, H1 met)"] - pool) < 1e-9
          and abs(pa["Illustrative annual separations, family (3363)"] - seps) < 1e-9)
    check("E8", "Pool arithmetic re-derived from OEWS and EP", "PASS" if ok else "FLAG",
          f"family {oews.loc[T, 'TOT_EMP'].sum():,.0f}; close pool {pool:,.0f} ({', '.join(close)}); "
          f"separations {seps:,.1f}/yr; ratio {seps / pool:.3f}")

    # E9 ------------------------------------------------------------------------------------------
    path = repo_path(cfg["paths"]["raw_ep"], root) / cfg["data_versions"]["ep"]["occupation_file"]["file"]
    t12 = pd.read_excel(path, sheet_name="Table 1.12", header=1, dtype=str, keep_default_na=False)
    t12.columns = ["occ_title", "occ_code", "ind_title", "ind_code", "factor"]
    ind = t12.assign(c=t12.ind_code.str.strip()).drop_duplicates("c").set_index("c").ind_title.str.strip()
    bf = pd.read_csv(prc / "bls_factors.csv")
    bad = []
    for r in bf.itertuples():
        rows = t12[t12.occ_code.str.strip() == r.soc6]
        if r.factor_level == "no entry":
            if rows.ind_code.str.strip().isin(["336300", "TE1000"]).any():
                bad.append(f"{r.soc6} has a 336300/TE1000 row")
            if len(rows) != r.n_industry_rows:
                bad.append(f"{r.soc6} other-industry count {len(rows)} vs {r.n_industry_rows}")
        else:
            code = "336300" if r.factor_level.startswith("NAICS") else "TE1000"
            hit = rows[rows.ind_code.str.strip() == code]
            if hit.empty or hit.factor.iloc[0].strip() != str(r.factor_text).strip():
                bad.append(f"{r.soc6} text mismatch")
    check("E9", "BLS Table 1.12 factors match the raw workbook", "PASS" if not bad else "FLAG",
          f"{len(bf)} occupations checked; " + ("all match" if not bad else "; ".join(bad))
          + f"; 336300 = '{ind.get('336300', '?')}', TE1000 = '{ind.get('TE1000', '?')}'")

    # E10 -----------------------------------------------------------------------------------------
    frame_codes = set(pp.feeder_codes.str.split(";").explode()) | {t + ".00" for t in T}
    old = sorted(c for c in frame_codes if rat.get(c, 9999) < 2018)
    check("E10", "Vintage exclusions equal the DL-20 list", "PASS" if old == ["51-2023.00", "51-2031.00", "51-4072.00"] else "FLAG",
          f"frame codes rated before 2018: {old}; universe kept {int((rat >= 2018).sum())} of {len(rat)}; "
          f"earliest rating year in the universe {int(rat.min())}")

    # E11 -----------------------------------------------------------------------------------------
    n = ab.drop_duplicates("group").set_index("group").n_elements.to_dict()
    check("E11", "Abilities subgroup sizes equal DL-17 (21/10/9/12 of 52)",
          "PASS" if n == {"all": 52, "cognitive": 21, "psychomotor": 10, "physical": 9, "sensory": 12} else "FLAG", str(n))

    # E12 -----------------------------------------------------------------------------------------
    log = repo_path("outputs/deviation_log.md", root).read_text(encoding="utf-8")
    ids = [int(x) for x in re.findall(r"^\| DL-(\d+) \|", log, flags=re.M)]
    check("E12", "Deviation log ids contiguous and unique", "PASS" if ids == list(range(1, len(ids) + 1)) else "FLAG",
          f"DL-1 … DL-{max(ids)}; {len(ids)} rows")

    # E13 -----------------------------------------------------------------------------------------
    fig = repo_path("figures", root)
    deps = {"fig1_h1_proximity_skills.png": est / "bootstrap_pairs.csv",
            "fig2_cps_moves.png": repo_path("outputs/cps_moves", root) / "q2_origin_composition.csv",
            "fig3_proximity_vs_pool.png": prc / "production_ranking_3363.csv",
            "fig4_skill_gap_heatmap.png": prc / "gap_matrix.csv",
            "fig5_h2_concentration_skills.png": est / "point_pairs.csv",
            "fig7_multiverse.png": repo_path("outputs/multiverse", root) / "multiverse_specs.csv",
            "fig8_uncertainty_models.png": sen / "uncertainty_models.csv",
            "figS1_abilities_negative_control.png": sen / "abilities_subgroups.csv"}
    deps = {f: dep for f, dep in deps.items() if dep.exists()}          # optional layers may be absent
    stale = [f for f, dep in deps.items() if not (fig / f).exists() or (fig / f).stat().st_mtime < dep.stat().st_mtime]
    check("E13", "Figures are newer than the outputs they draw", "PASS" if not stale else "FLAG",
          "stale: " + ", ".join(stale) if stale else f"{len(deps)} figure/input pairs checked")

    # E14 -----------------------------------------------------------------------------------------
    from .practice import NEM_FILE, read_nem
    import hashlib
    nem_path = repo_path(cfg["paths"]["raw_ep"], root) / NEM_FILE
    if not nem_path.exists():
        check("E14", "NEM 336300 within-industry projections (DL-23)", "NOTE", "optional input not present; layer skipped")
    else:
        t = read_nem(nem_path)
        raw_t = pd.read_csv(nem_path, dtype=str, keep_default_na=False)
        ti = t.set_index("code")
        lvl1 = raw_t["Display Level"].astype(str).eq("1").to_numpy()
        major = t[lvl1]
        sum_dev = abs(major.emp_2025_k.sum() - ti.loc["00-0000", "emp_2025_k"])
        grp_dev = abs(ti.loc[["49-9041", "49-9043", "49-9044"], "emp_2025_k"].sum() - ti.loc["49-9040", "emp_2025_k"])
        chg_dev = float((t.emp_2035_k - t.emp_2025_k - t.change_k).abs().max())
        big = t[t.emp_2025_k >= 5]
        pct_dev = float((100 * big.change_k / big.emp_2025_k - big.change_pct).abs().max())
        want = set(cfg["frame"]["targets_core"] + cfg["frame"]["feeders_core"])
        missing = sorted(want - set(t.code))
        man = pd.read_csv(repo_path("data/raw/MANIFEST.csv", root)).set_index("path").sha256
        h = hashlib.sha256(nem_path.read_bytes()).hexdigest()
        in_man = man.get(f"data/raw/ep/{NEM_FILE}") == h
        out_nem = pd.read_csv(prc / "nem_336300.csv").set_index("soc6")
        same = all(abs(out_nem.loc[c, "change_pct"] - ti.loc[c, "change_pct"]) < 1e-9 for c in want if c in ti.index)
        ok = sum_dev <= 0.5 and grp_dev <= 0.15 and chg_dev <= 0.15 and pct_dev <= 1.0 and not missing and in_man and same
        check("E14", "NEM 336300 parsed and internally consistent (DL-23)", "PASS" if ok else "FLAG",
              f"{len(t)} rows; Σ major groups − total = {sum_dev:.1f}k (rounding); 49-9040 parts − group = {grp_dev:.2f}k; "
              f"max |2035 − 2025 − change| = {chg_dev:.2f}k; max |recomputed % − published %| (≥5k jobs) = {pct_dev:.2f} pts; "
              f"frame codes missing: {missing or 'none'}; SHA-256 in MANIFEST={in_man}; output equals source={same}")

    # E15 -----------------------------------------------------------------------------------------
    if nem_path.exists():
        li = t[t.type == "Line Item"].set_index("code")
        o_all = oews.reset_index()
        tot_o = float(o_all.loc[o_all.OCC_CODE == "00-0000", "TOT_EMP"].iloc[0])
        lvl = o_all[o_all.O_GROUP.isin(["detailed", "broad"])].drop_duplicates("OCC_CODE").set_index("OCC_CODE")
        j = li.join(lvl[["TOT_EMP"]], how="inner").dropna(subset=["TOT_EMP"])
        j = j[j.index.isin(o_all[o_all.O_GROUP == "detailed"].OCC_CODE) | (j.index == "51-2090")]
        share_o = 100 * j.TOT_EMP / tot_o
        corr = float(np.corrcoef(share_o, j.pct_ind_2025)[0, 1])
        dmax = float((share_o - j.pct_ind_2025).abs().max())
        ratio_tot = float(ti.loc["00-0000", "emp_2025_k"] * 1000 / tot_o)
        big = j[j.TOT_EMP >= 5000]
        r_big = (big.emp_2025_k * 1000 / big.TOT_EMP)
        ok = corr > 0.999 and dmax < 0.1 and abs(r_big - ratio_tot).max() < 0.01
        check("E15", "NEM 2025 staffing pattern = OEWS May 2025 inside 3363; totals differ by a common factor (DL-25c)",
              "PASS" if ok else "FLAG",
              f"{len(j)} matched occupations; share correlation {corr:.5f}; max |share difference| {dmax:.3f} pts "
              f"(NEM publishes shares to one decimal, so differences below 0.1 are within one rounding unit); NEM/OEWS total {ratio_tot:.4f}; occupations with ≥ 5,000 "
              f"jobs: level ratio {r_big.min():.3f}–{r_big.max():.3f}. Levels come from different control totals (NEM: CES-based "
              f"industry employment; OEWS: its own survey estimate); shares and percent changes are unaffected.")

    # E16 -----------------------------------------------------------------------------------------
    import subprocess
    import sys as _sys
    res = subprocess.run([_sys.executable, "-I", str(repo_path("scripts/independent_check.py", root))],
                         capture_output=True, text=True)
    last = [l for l in res.stdout.splitlines() if l.startswith("max |independent")]
    check("E16", "Independent re-implementation from raw files reproduces D, P, C, pi, wages, pool (DL-25d)",
          "PASS" if res.returncode == 0 else "FLAG",
          (last[0] if last else res.stderr[-300:]) + "; reads raw O*NET CSV and the OEWS zip only, no project code")

    # E17 -----------------------------------------------------------------------------------------
    from .trend import SERIES, find_file, read_monthly
    ces = find_file(root)
    if ces is None:
        check("E17", "CES observed trend (DL-26)", "NOTE", "optional input not present; layer skipped")
    else:
        mm = read_monthly(ces)
        ann = pd.read_csv(prc / "ces_3363_annual.csv")
        redo = mm.assign(year=mm.date.dt.year).groupby("year").emp_k.agg(["mean", "size"])
        same = bool(np.allclose(redo["mean"].to_numpy(), ann.emp_k.to_numpy()) and (redo["size"].to_numpy() == ann.months.to_numpy()).all())
        months_ok = bool(mm.date.is_monotonic_increasing and not mm.date.duplicated().any()
                         and (mm.date.diff().dropna().dt.days.between(28, 31)).all())
        raw_head = pd.read_excel(ces, header=None, dtype=str).fillna("").astype(str) if ces.suffix == ".xlsx" else None
        nsa = raw_head is not None and raw_head.apply(lambda c: c.str.contains("Not Seasonally Adjusted", regex=False)).any().any()
        man = pd.read_csv(repo_path("data/raw/MANIFEST.csv", root)).set_index("path").sha256
        rel = ces.relative_to(root).as_posix()
        in_man = man.get(rel) == hashlib.sha256(ces.read_bytes()).hexdigest()
        a25 = float(ann.loc[(ann.year == 2025) & ann.complete, "emp_k"].iloc[0])
        nem25 = float(ti.loc["00-0000", "emp_2025_k"]) if nem_path.exists() else float("nan")
        ok = same and months_ok and in_man and (nsa or ces.suffix == ".csv") and abs(a25 - nem25) <= 0.05 + 1e-9
        check("E17", "CES parsed; 2025 annual average equals the NEM 2025 industry total (DL-26)", "PASS" if ok else "FLAG",
              f"{ces.name}: {len(mm)} months {mm.date.min():%Y-%m}–{mm.date.max():%Y-%m}, consecutive={months_ok}, "
              f"not seasonally adjusted={nsa}; annual averages re-derived={same}; 2025 CES average {a25:.2f}k vs NEM "
              f"2025 total {nem25:.1f}k; SHA-256 in MANIFEST={in_man}")

    # E18 -----------------------------------------------------------------------------------------
    from .bootstrap import Spec, evaluate
    from .robustness import run as robustness_run
    from .sensitivity import load_all
    rb = repo_path("outputs/robustness", root)
    if not (rb / "domain_summary.csv").exists():
        check("E18", "Robustness module (DL-27)", "FLAG", "outputs/robustness not found; run python -m src.robustness")
    else:
        saved = {k: pd.read_csv(rb / f"{k}.csv") for k in ("element_splits", "leave_one_out", "h2_forms", "domain_summary")}
        redo = robustness_run(cfg, root, write=False)
        same = all(np.allclose(saved[k].select_dtypes("number").to_numpy(dtype=float),
                               redo[k].select_dtypes("number").to_numpy(dtype=float), equal_nan=True)
                   and saved[k].shape == redo[k].shape for k in saved)
        arrays, specs, _, _ = load_all(cfg, root)
        lo = saved["leave_one_out"]
        maxdiff, n_cmp, n_off = 0.0, 0, 0
        for d in ("S", "K", "A"):
            a, sp = arrays[d], specs[d]
            fam = sp.family_index
            mem, mix = sp.target_members[fam], sp.target_mix[fam]
            for drop in range(len(mem)):
                keep = np.arange(len(mem)) != drop
                sp2 = Spec([FAMILY], [mem[keep]], [mix[keep] / mix[keep].sum()], sp.feeder_names, sp.feeder_roles,
                           sp.feeder_members, 0)
                P = evaluate(a.L, a.I, sp2, cfg["estimands"]["primary"]["top_m"])["P"][0]
                got = lo[(lo.domain == d) & (lo.kind == "target") & (lo.dropped == a.codes[mem[drop]])].set_index("feeder").P
                diff = np.abs(got.loc[sp.feeder_names].to_numpy() - P)
                maxdiff = max(maxdiff, float(diff.max())); n_cmp += len(diff); n_off += int((diff > 1e-9).sum())
        ds = saved["domain_summary"].set_index("domain")
        es = saved["element_splits"]
        neg0 = bool((es[(es.role == "negative_control") & es.domain.isin(["S", "K"])].share_half_sets_P_le_thr == 0).all())
        ok = same and maxdiff <= 100 / 905 + 1e-9 and (es.n_half_sets == 1000).all() and neg0
        check("E18", "Robustness module re-executes exactly; leave-one-target-out matches the registered evaluator (DL-27)",
              "PASS" if ok else "FLAG",
              f"re-execution identical={same}; leave-one-target-out: {n_cmp} feeder×target P compared with "
              f"src.bootstrap.evaluate, max |diff| {maxdiff:.3g} ({n_off} differ by one 1/905 tie step at most); "
              f"negative control never P ≤ 25 in S/K half-sets={neg0}; S same top 3 in both halves "
              f"{ds.loc['S', 'share_splits_both_halves_same_top3']:.3f}, K {ds.loc['K', 'share_splits_both_halves_same_top3']:.3f}")

    # E19 -----------------------------------------------------------------------------------------
    import io
    import warnings
    import zipfile
    from .history import zip_path
    man = pd.read_csv(repo_path("data/raw/MANIFEST.csv", root)).set_index("path").sha256
    hist = repo_path("outputs/history/maintenance_mix.csv", root)
    if not hist.exists():
        check("E19", "OEWS history (DL-29)", "NOTE", "optional input not present; layer skipped")
    else:
        mix = pd.read_csv(hist)
        codes = list(cfg["frame"]["targets_core"])
        ok_vals, notes = True, []
        for y in (2021, 2025):
            zp = zip_path(y, cfg, root)
            with zipfile.ZipFile(zp) as zf:
                mem = [n for n in zf.namelist() if n.endswith(f"nat4d_M{y}_dl.xlsx")]
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    raw = pd.read_excel(io.BytesIO(zf.read(mem[0])), dtype=str)
            raw.columns = [c.upper() for c in raw.columns]
            raw = raw[(raw.NAICS.str.strip() == "336300") & raw.OCC_CODE.isin(codes)].drop_duplicates("OCC_CODE").set_index("OCC_CODE")
            got = mix[mix.year.astype(str) == str(y)].set_index("soc6")
            e_ok = all(float(raw.loc[c, "TOT_EMP"].replace(",", "")) == float(got.loc[c, "emp"]) for c in codes)
            w_ok = all(np.isclose(float(raw.loc[c, "H_MEAN"]), float(got.loc[c, "h_mean"])) for c in codes)
            ok_vals &= e_ok and w_ok and len(mem) == 1
            notes.append(f"{y}: employment {e_ok}, mean wage {w_ok}")
        with duckdb.connect(str(repo_path(cfg["paths"]["duckdb"], root)), read_only=True) as con:
            reg = con.execute("SELECT OCC_CODE, TOT_EMP FROM oews_3363").df().set_index("OCC_CODE").TOT_EMP
        y25 = mix[mix.year.astype(str) == "2025"].set_index("soc6")
        same25 = all(float(reg[c]) == float(y25.loc[c, "emp"]) for c in codes)
        hashes = all(man.get(f"data/raw/oews_history/oesm{y % 100:02d}in4.zip") ==
                     hashlib.sha256(zip_path(y, cfg, root).read_bytes()).hexdigest() for y in (2021, 2022, 2023, 2024))
        ok = ok_vals and same25 and hashes
        check("E19", "OEWS history re-read from raw zips; 2025 equals the registered ingest (DL-29)", "PASS" if ok else "FLAG",
              "; ".join(notes) + f"; 2025 = registered oews_3363: {same25}; 2021–2024 SHA-256 in MANIFEST: {hashes}")

    # E20 -----------------------------------------------------------------------------------------
    def step_up(p: np.ndarray, q: float) -> np.ndarray:
        """Benjamini-Hochberg as the textbook step-up search (independent of the adjusted-p code path)."""
        o = np.argsort(p, kind="stable"); n = len(p)
        ok_k = [k for k in range(1, n + 1) if p[o][k - 1] <= k * q / n]
        rej = np.zeros(n, bool)
        if ok_k:
            rej[o[:max(ok_k)]] = True
        return rej

    q_fdr = float(cfg["decision_rules"]["fdr_q"])
    fdr_p = repo_path("outputs/robustness/fdr_h1.csv", root)
    if not fdr_p.exists():
        check("E20", "Multiple comparisons, endpoints and rule choice (DL-32)", "FLAG", "outputs/robustness/fdr_h1.csv not found")
    else:
        notes, ok = [], True
        h1d = pd.read_csv(repo_path("outputs/estimates/h1_decisions.csv", root))
        B = int(pd.read_csv(repo_path("outputs/estimates/bootstrap_meta.csv", root)).B.iloc[0])
        p_ok = bool(np.allclose(h1d.p_one_sided, (h1d.n_draws_P_above_thr + 1) / (B + 1)))
        fd = pd.read_csv(fdr_p)
        sk = fd[fd.domain.isin(["S", "K"])]
        rej = step_up(sk.p_one_sided.to_numpy(), q_fdr)
        fdr_ok = bool((rej == sk.bh_reject_SK.to_numpy()).all()) and len(sk) == 24
        n_changed = int(sk.decision_changed_by_fdr.sum())
        ok &= p_ok and fdr_ok
        notes.append(f"H1: p = (k+1)/(B+1) re-derived={p_ok}; BH step-up over {len(sk)} S/K core tests matches={fdr_ok}; "
                     f"close {int(sk.close_rule.sum())} → after FDR {int(sk.close_after_fdr.sum())} ({n_changed} changed)")
        if hist.exists():
            hh = pd.read_csv(repo_path("outputs/history/oews_3363_2021_2025.csv", root))
            w = hh.pivot_table(index="year", columns="OCC_CODE", values="H_MEAN", aggfunc="first")
            r_ = hh.pivot_table(index="year", columns="OCC_CODE", values="MEAN_PRSE", aggfunc="first")
            mix = pd.read_csv(hist)
            zs = {}
            for c in ("51-4081", "51-4041", "51-9161"):         # premium of 49-9041 over the close feeders (README 3.5)
                for y0 in (2021, 2022):
                    d = math.log(w.at[2025, "49-9041"] / w.at[2025, c]) - math.log(w.at[y0, "49-9041"] / w.at[y0, c])
                    se = math.sqrt(sum(r_.at[y, cc] ** 2 for y in (y0, 2025) for cc in ("49-9041", c))) / 100
                    got = float(mix[(mix.year.astype(str) == f"{y0}-2025") & (mix.soc6 == c)].premium_mean_change_z.iloc[0])
                    zs[(c, y0)] = (d / se, got)
            z_ok = all(abs(a_ - b_) < 1e-9 for a_, b_ in zs.values())
            ok &= z_ok
            notes.append("premium of 49-9041 over the close feeders re-derived from the yearly file: "
                         + ", ".join(f"{c} z {zs[(c, 2021)][0]:.1f} / {zs[(c, 2022)][0]:.1f}" for c in ("51-4081", "51-4041", "51-9161"))
                         + f" (2021→25 / 2022→25; match {z_ok})")
        check("E20", "Multiple comparisons (BH at fdr_q) and endpoint z of the wage premium re-derived (DL-32)",
              "PASS" if ok else "FLAG", "; ".join(notes))

    # E21 -----------------------------------------------------------------------------------------
    sup_p = repo_path("outputs/robustness/family_plus_49_1011.csv", root)
    if not sup_p.exists():
        check("E21", "Family with 49-1011 added (DL-35)", "NOTE", "check not run")
    else:
        from .bootstrap import build_spec, load_arrays
        sup = pd.read_csv(sup_p)
        pp = pd.read_csv(repo_path("outputs/estimates/point_pairs.csv", root))
        reg = pp[pp.target == FAMILY].set_index(["domain", "feeder"]).P
        base_ok = bool(np.allclose(sup.set_index(["domain", "feeder"]).P_registered, reg.loc[list(zip(sup.domain, sup.feeder))]))
        # independent re-derivation for the S domain with pandas arithmetic
        with duckdb.connect(str(repo_path(cfg["paths"]["duckdb"], root)), read_only=True) as con:
            empl = con.execute("SELECT OCC_CODE, TOT_EMP FROM oews_3363").df().set_index("OCC_CODE")["TOT_EMP"]
            aS = load_arrays(con, "S", cfg)
        L = pd.DataFrame(aS.L, index=aS.codes); I = pd.DataFrame(aS.I, index=aS.codes)
        Z = (L - L.mean()) / L.std(ddof=1); W = (I - 1).clip(0, 4)        # same construction as src.deficit (sample SD; w = I - 1 clipped to [0, 4])
        core = list(cfg["frame"]["targets_core"])
        codes = [c + ".00" for c in core] + ["49-1011.00"]
        wts = np.append(empl.reindex(core).to_numpy(float), float(empl["49-1011"])); wts = wts / wts.sum()
        zt, wt = (Z.loc[codes].T * wts).T.sum(), (W.loc[codes].T * wts).T.sum()
        ref = Z.drop(index=codes)
        dref = (wt * (zt - ref).clip(lower=0)).sum(axis=1) / wt.sum()
        spS = build_spec(aS, cfg, empl)
        maxd = 0.0
        for f, mem in zip(spS.feeder_names, spS.feeder_members):
            zf = Z.iloc[mem].mean()
            d = float((wt * (zt - zf).clip(lower=0)).sum() / wt.sum())
            p_ = 100 * float((dref <= d).mean())
            got = float(sup[(sup.domain == "S") & (sup.feeder == f)].P_with_49_1011.iloc[0])
            maxd = max(maxd, abs(p_ - got))
        close3 = sup[(sup.domain == "S") & (sup.role == "feeder_core")].nsmallest(3, "P_with_49_1011").feeder.tolist()
        ok = base_ok and maxd <= 100 / len(ref) + 1e-9      # at most one tie step (self-tie, DL-22)
        check("E21", "Family with 49-1011 added: registered P reproduced; Skills P re-derived with pandas (DL-35)",
              "PASS" if ok else "FLAG",
              f"registered P column matches point_pairs={base_ok}; S re-derivation max |diff| {maxd:.3g} (one tie step of "
              f"100/{len(ref)} allowed); weight of 49-1011 {sup.weight_49_1011.iloc[0]:.3f}; three closest core feeders on Skills: {close3}")

    # E24 -----------------------------------------------------------------------------------------
    if not nem_path.exists():
        check("E24", "Two-stage NEM reading (DL-28)", "NOTE", "optional NEM input not present; layer skipped")
    else:
        li = t[t["type"].str.contains("Line item", case=False)].set_index("code")
        base = float(li.change_pct.mode().iloc[0])
        occ_xlsx = repo_path(cfg["paths"]["raw_ep"], root) / cfg["data_versions"]["ep"]["occupation_file"]["file"]
        f12 = pd.read_excel(occ_xlsx, sheet_name="Table 1.12", header=1, dtype=str, keep_default_na=False)
        f12.columns = ["occ_title", "occ_code", "ind_title", "ind_code", "factor"]
        f12 = f12.apply(lambda c: c.str.strip())
        applies = set(f12.loc[f12.ind_code.isin(["336300", "TE1000"]), "occ_code"])
        at_base = li.change_pct == base
        has_f = li.index.isin(applies)
        exact = bool((at_base == ~has_f).all())
        nem_out = pd.read_csv(prc / "nem_336300.csv").set_index("soc6").drop(index="00-0000")
        nem_out = nem_out[nem_out.change_pct.notna()]
        adj = 100 * ((1 + nem_out.change_pct / 100) / (1 + base / 100) - 1)
        adj_ok = bool(np.allclose(adj, nem_out.bls_adjustment_pct) and (nem_out.baseline_change_pct == base).all())
        ok = exact and adj_ok
        check("E24", "Two-stage NEM reading: baseline = occupations without a BLS factor; adjustments re-derived (DL-28)",
              "PASS" if ok else "FLAG",
              f"baseline {base:+.1f}% = mode of {len(li)} line items ({int(at_base.sum())} at baseline); "
              f"at baseline ⇔ no Table 1.12 row for 336300 or all industries: {exact} "
              f"({int((at_base & ~has_f).sum())} + {int((~at_base & has_f).sum())} of {len(li)}); "
              f"adjustments of {len(nem_out)} rows re-derived={adj_ok}")

    # E22-E23 -------------------------------------------------------------------------------------
    q1_p = repo_path("outputs/cps_moves/q1_rates.csv", root)
    if not q1_p.exists():
        check("E22", "CPS observed moves (DL-37)", "NOTE", "layer not run")
    else:
        _cps_stream_checks(root)

    df = pd.DataFrame(ROWS)
    df = df.iloc[df.id.str[1:].astype(int).argsort(kind="stable")].reset_index(drop=True)
    out = repo_path("outputs/review", root)
    df.to_csv(out / "output_audit.csv", index=False)
    md = ["# Output audit (E-checks)\n", df.to_markdown(index=False), "",
          f"PASS {int((df.status == 'PASS').sum())} · NOTE {int((df.status == 'NOTE').sum())} · FLAG {int((df.status == 'FLAG').sum())}"]
    (out / "output_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return df


def _cps_stream_checks(root: Path) -> None:
    """CPS checks: one streaming pass over the raw CPS files with string slicing and dict-based linking."""
    import zipfile
    from .cps_moves import census_codes, M_CODES, C_CODES, ORIGINS
    p_codes, mfg, soc_of = census_codes(root)
    files = sorted(repo_path("data/raw/cps/basic", root).glob("*pub.zip"),
                   key=lambda f: (int(f.name[3:5]), "jan feb mar apr may jun jul aug sep oct nov dec".split().index(f.name[:3])))
    mon = "jan feb mar apr may jun jul aug sep oct nov dec".split()
    A = set(range(30, 44))
    M, C = set(M_CODES), set(C_CODES)
    major = {c: s_[:2] for c, s_ in soc_of.items()}
    win = (2020 * 12 + 2, 2021 * 12 + 11)

    def origin_of(occ_p: int, ind_p: int) -> str:
        mj = major.get(occ_p, "")
        if mj == "51":
            return ORIGINS[0] if ind_p in mfg else ORIGINS[1]
        if mj == "49" and occ_p not in M:
            return ORIGINS[2]
        if mj == "47" and occ_p not in M:
            return ORIGINS[3]
        return {"53": ORIGINS[4], "17": ORIGINS[5]}.get(mj, ORIGINS[6])

    # E22 / E23 counters (employed records, PEMLR 1-2, any age, as in src/cps_moves.py)
    n_pairs = den = num_any = num_same = c_den = c_any = q2_den = q2_num = 0
    diag = {k: [0, 0] for k in ("all", "mfg_same", "mfg_changed", "q1ev", "q2ent", "Mstay")}
    chg = {k: [0, 0] for k in ("all", "noalloc", "alloc")}
    orig = {(ck, ev, og): 0 for ck in ("main", "iv_no_allocation") for ev in ("any_employer", "same_employer") for og in ORIGINS}
    orig_den = {(ck, ev): 0 for ck in ("main", "iv_no_allocation") for ev in ("any_employer", "same_employer")}
    q1_young = [0, 0]                                   # Q1 denominator / events with age < 16 in either month
    emp_prev: dict | None = None; m_prev = None
    for f in files:
        mi = (2000 + int(f.name[3:5])) * 12 + mon.index(f.name[:3])
        emp: dict[tuple, tuple] = {}
        with zipfile.ZipFile(f) as zf, zf.open(zf.namelist()[0]) as fh:
            for raw in fh:
                s_ = raw.decode("latin-1")
                emlr = s_[179:181].strip()
                key = (s_[0:15], s_[70:75], s_[146:148])
                age = int(s_[121:123])
                if emlr in ("1", "2"):
                    emp[key] = (int(s_[62:64]), s_[128:130], age, int(s_[859:863]), int(s_[855:859]), s_[425:427].strip(),
                                int(s_[768:770]), int(s_[766:768]))
        if emp_prev is not None and m_prev == mi - 1:
            for key, (mis, sex, age, occ, ind, iodp1, xo, xi) in emp.items():
                pv = emp_prev.get(key)
                if pv is None or mis in (1, 5) or mis != pv[0] + 1 or sex != pv[1] or age - pv[2] not in (0, 1):
                    continue
                n_pairs += 1
                occ_p, ind_p = pv[3], pv[4]
                alloc = xo in A or xi in A or pv[6] in A or pv[7] in A
                inM, inMp = occ in M, occ_p in M
                diag["all"][0] += 1; diag["all"][1] += alloc
                if ind_p in mfg:
                    k_ = "mfg_same" if occ == occ_p else "mfg_changed"
                    diag[k_][0] += 1; diag[k_][1] += alloc
                    for k2, cond in (("all", True), ("noalloc", not alloc), ("alloc", alloc)):
                        if cond:
                            chg[k2][0] += 1; chg[k2][1] += occ != occ_p
                if occ_p in p_codes and ind_p in mfg:
                    den += 1
                    if min(age, pv[2]) < 16:
                        q1_young[0] += 1; q1_young[1] += inM
                    if inM:
                        num_any += 1; num_same += iodp1 == "1"
                        diag["q1ev"][0] += 1; diag["q1ev"][1] += alloc
                    if occ_p in C:
                        c_den += 1; c_any += inM
                if inM and ind in mfg and not inMp:
                    q2_den += 1; q2_num += occ_p in p_codes
                    diag["q2ent"][0] += 1; diag["q2ent"][1] += alloc
                    og = origin_of(occ_p, ind_p)
                    for ck, ok_ in (("main", True), ("iv_no_allocation", not alloc)):
                        if not ok_:
                            continue
                        for ev, ok2 in (("any_employer", True), ("same_employer", iodp1 == "1")):
                            if ok2:
                                orig_den[(ck, ev)] += 1; orig[(ck, ev, og)] += 1
                if inM and inMp and ind in mfg:
                    diag["Mstay"][0] += 1; diag["Mstay"][1] += alloc
        emp_prev, m_prev = emp, mi

    # E22
    q1 = pd.read_csv(repo_path("outputs/cps_moves/q1_rates.csv", root)).set_index(["check", "group", "event"])
    q2 = pd.read_csv(repo_path("outputs/cps_moves/q2_shares.csv", root)).set_index(["check", "group", "event"])
    exp = {("all_P", "any_employer"): (den, num_any), ("all_P", "same_employer"): (den, num_same),
           ("close_8030", "any_employer"): (c_den, c_any)}
    ok = all((int(q1.at[("main", g, e), "n_den"]), int(q1.at[("main", g, e), "n_num"])) == v for (g, e), v in exp.items())
    ok = ok and (int(q2.at[("main", "destination_mfg_t", "any_employer"), "n_den"]),
                 int(q2.at[("main", "destination_mfg_t", "any_employer"), "n_num"])) == (q2_den, q2_num)
    summ_txt = repo_path("outputs/cps_moves/cps_summary.md", root).read_text(encoding="utf-8")
    ok = ok and f"Linked pairs: {n_pairs:,}" in summ_txt
    check("E22", "CPS observed moves: pairs and unweighted counts re-derived from the raw monthly files with a dict-based "
          "linker (DL-37, DL-40)", "PASS" if ok else "FLAG",
          f"{len(files)} files; pairs {n_pairs:,}; production pairs {den:,}, into maintenance {num_any} (same employer "
          f"{num_same}); machinists {c_den:,} / {c_any}; maintenance entrants in manufacturing {q2_den}, from production {q2_num}")

    # E23 — allocation diagnostic (DL-42), origin composition (DL-43), scale illustration (DL-45)
    parts, ok = [], True
    dg = pd.read_csv(repo_path("outputs/cps_moves/allocation_diagnostic.csv", root))
    exp_d = [diag["all"], diag["mfg_same"], diag["mfg_changed"], diag["q1ev"], diag["q2ent"], diag["Mstay"],
             chg["all"], chg["noalloc"], chg["alloc"]]
    ok_d = [list(map(int, r)) for r in dg[["pairs", "count"]].to_numpy()] == exp_d
    parts.append(f"diagnostic {'=' if ok_d else '≠'} ({diag['q2ent'][1]} of {diag['q2ent'][0]} entrants allocated)")
    qo = pd.read_csv(repo_path("outputs/cps_moves/q2_origin_composition.csv", root))
    ok_o = all(int(qo[(qo.check == ck) & (qo.event == ev) & (qo.group == og)].n_num.iloc[0]) == n
               for (ck, ev, og), n in orig.items())
    ok_o = ok_o and all(int(qo[(qo.check == ck) & (qo.event == ev)].n_den.iloc[0]) == n for (ck, ev), n in orig_den.items())
    sums_q2 = True
    for ck in ("main", "i_persistence", "ii_excl_2020_2021", "iv_no_allocation"):
        for ev in ("any_employer", "same_employer"):
            sub = qo[(qo.check == ck) & (qo.event == ev)]
            r2 = q2.loc[(ck, "destination_mfg_t", ev)]
            sums_q2 &= abs(sub.pct.sum() - 100) < 1e-9
            sums_q2 &= int(sub[sub.group.isin(ORIGINS[:2])].n_num.sum()) == int(r2.n_num) and int(sub.n_den.iloc[0]) == int(r2.n_den)
            sums_q2 &= abs(sub[sub.group.isin(ORIGINS[:2])].pct.sum() - float(r2.pct)) < 1e-9
    parts.append(f"origin counts {'=' if ok_o else '≠'}; origins 1+2 = Q2 and shares sum to 100 in all 8 cells: {sums_q2}")
    sc_p = repo_path("outputs/cps_moves/scale_illustration.csv", root)
    ok_s = True
    if sc_p.exists():
        sc = pd.read_csv(sc_p)
        for r in sc.itertuples():
            a = 100 * (1 - (1 - r.monthly_pct / 100) ** 12)
            ok_s &= abs(a - r.annual_pct) < 1e-9 and abs(r.production_jobs_3363_oews_may2025 * a / 100 - r.illustrative_moves_per_year) < 1e-6
        parts.append(f"scale illustration recomputed: {ok_s}")
    ok_m = True
    ms_p = repo_path("outputs/cps_moves/m_codes_by_sector.csv", root)
    if ms_p.exists():
        import openpyxl
        ms = pd.read_csv(ms_p).set_index("soc")
        with zipfile.ZipFile(repo_path("data/raw/oews/oesm25in4.zip", root)) as zf:
            member = next(n for n in zf.namelist() if n.lower().endswith("natsector_m2025_dl.xlsx"))
            import io
            wb = openpyxl.load_workbook(io.BytesIO(zf.read(member)), read_only=True)
        ws = wb.worksheets[0]
        it = ws.iter_rows(values_only=True)
        hdr = [str(h).upper() for h in next(it)]
        ci, cn, ce = hdr.index("OCC_CODE"), hdr.index("NAICS"), hdr.index("TOT_EMP")
        tot: dict[str, float] = {}; mf: dict[str, float] = {}
        for r in it:
            soc = r[ci]
            if soc in ms.index:
                v = r[ce]
                v = float(str(v).replace(",", "")) if v not in (None, "") and str(v).replace(",", "").replace(".", "").isdigit() else 0.0
                tot[soc] = tot.get(soc, 0.0) + v
                if str(r[cn]).strip() == "31-33":
                    mf[soc] = mf.get(soc, 0.0) + v
        ok_m = all(abs(tot[s] - ms.at[s, "sum_of_sector_rows"]) < 0.5 and abs(mf.get(s, 0) - ms.at[s, "manufacturing_31_33"]) < 0.5
                   for s in ms.index)
        parts.append(f"M codes by sector re-read with openpyxl: {ok_m} (49-9071 in manufacturing "
                     f"{100 * mf.get('49-9071', 0) / tot.get('49-9071', 1):.1f}%)")
    ok = ok_d and ok_o and sums_q2 and ok_s and ok_m
    check("E23", "CPS additions (DL-42, 43, 45, 46): allocation diagnostic and origin counts re-derived from the raw files; origin "
          "shares sum to 100 and origins 1+2 equal Q2; annualization recomputed; M codes by sector re-read",
          "PASS" if ok else "FLAG", "; ".join(parts))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    df = run(load_config(args.config))
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 200)
    print(df.to_string(index=False))
    return int((df.status == "FLAG").sum() > 0)


if __name__ == "__main__":
    raise SystemExit(main())
