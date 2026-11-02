"""Practice layer — answers the practitioner questions (deviation log DL-12, DL-13, DL-14, DL-21).

  Top 10   Which production occupations employed in NAICS 3363 are closest to the maintenance family?
           Every SOC-51 detailed occupation with OEWS 3363 employment and an O*NET profile, ranked by point D;
           P against the frozen reference set. Point estimates only — outside the registered frame (DL-12).
  Pool     How large is the close-feeder pool relative to maintenance headcount and replacement need (DL-13)?
  Factors  What does BLS say drives demand (EP Table 1.12): the NAICS 336300 row if present, else the
           all-industry row, else 'no entry' (DL-14).
  Training How long does each occupation take to learn (O*NET OJ / PT / RW categories, Job Zone; DL-21)?
  Gaps     Element-level deficit contributions for the frame feeders (figure input; same arithmetic as D).
  Industry BLS National Employment Matrix, NAICS 336300: projected change inside the industry for the frame (DL-23),
           with the industry-scale baseline and each occupation's BLS adjustment relative to it (DL-28); used in the
           pathway table. The full two-stage reading, industry output, Job Zone pattern and automation counts run in
           II-A (DL-36).
  Pathway  Side-by-side layers for each core feeder (DL-25b).

Outputs: outputs/practice/*.csv and practice_summary.md
Usage:   python -m src.practice
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from .config import REPO_ROOT, load_config, repo_path
from .deficit import contributions, total_deficit
from .profiles import FAMILY, build_profiles, load_domain

PROFILE_OVERRIDE = {"51-2090": ["51-2092.00"], "51-2028": ["51-2022.00", "51-2023.00"]}
TRAIN_SCALES = {"OJ": "On-the-job training", "PT": "On-site / in-plant training", "RW": "Related work experience"}
OVER_ONE_YEAR = {"OJ": 6, "PT": 6, "RW": 6}          # first category that is "over 1 year"


def production_ranking(cfg: dict[str, Any], root: Path) -> pd.DataFrame:
    with duckdb.connect(str(repo_path(cfg["paths"]["duckdb"], root)), read_only=True) as con:
        oews = con.execute("SELECT * FROM oews_3363 WHERE O_GROUP = 'detailed'").df().set_index("OCC_CODE")
        sep = con.execute("SELECT * FROM ep_separations WHERE occupation_type = 'Line item'").df().set_index("nem_code")
        edu = con.execute("SELECT * FROM ep_education").df().set_index("nem_code")
        emp_all = con.execute("SELECT OCC_CODE, TOT_EMP FROM oews_3363").df().set_index("OCC_CODE")["TOT_EMP"]
        data = {d: load_domain(con, d, cfg) for d in ("K", "S", "A")}
    prod = [c for c in oews.index if c.startswith("51-")]
    rows = []
    for d, dd in data.items():
        targets, _ = build_profiles(dd, cfg, emp_all)
        fam = targets[FAMILY]
        ref_mask = ~dd.codes.isin(fam.member_codes)
        D_ref = total_deficit(contributions(fam.z, fam.w, dd.Z.to_numpy()[ref_mask]), fam.w)
        for soc in prod:
            codes = PROFILE_OVERRIDE.get(soc, [soc + ".00"])
            if not all(c in dd.Z.index for c in codes):
                rows.append({"domain": d, "soc6": soc, "onet_codes": ";".join(codes), "has_profile": False})
                continue
            z = dd.Z.loc[codes].to_numpy().mean(axis=0)
            D = float(total_deficit(contributions(fam.z, fam.w, z[None, :]), fam.w)[0])
            rows.append({"domain": d, "soc6": soc, "onet_codes": ";".join(codes), "has_profile": True,
                         "D": D, "P": 100.0 * float(np.mean(D_ref <= D + 1e-12))})   # tie tolerance (DL-22)
    r = pd.DataFrame(rows)
    r["title"] = r.soc6.map(oews["OCC_TITLE"])
    r["emp_3363"] = r.soc6.map(oews["TOT_EMP"])
    r["emp_rse"] = r.soc6.map(oews["EMP_PRSE"])
    r["h_median_3363"] = r.soc6.map(oews["H_MEDIAN"])
    r["ep_change_pct"] = r.soc6.map(sep["emp_change_pct"])
    r["ep_transfer_rate_pct"] = r.soc6.map(sep["transfer_rate_pct"])
    r["ojt_bls"] = r.soc6.map(edu["ojt"])
    r["in_registered_frame"] = r.soc6.isin(cfg["frame"]["feeders_core"] + cfg["frame"]["sensitivity_occupations"])
    r["emp_withheld"] = r.emp_3363.isna()            # OEWS '**' (withheld) -> not usable as a pool size
    r["small_or_imprecise"] = (r.emp_3363 < 1000) | (r.emp_rse >= 10) | r.emp_withheld
    r["rank"] = r[r.has_profile].groupby("domain")["D"].rank(method="min")
    return r.sort_values(["domain", "rank"])


def pool_arithmetic(cfg: dict[str, Any], root: Path) -> pd.DataFrame:
    est = repo_path("outputs/estimates", root)
    h1 = pd.read_csv(est / "h1_decisions.csv")
    close = h1[(h1.domain == "S") & (h1.feeder_role == "feeder_core") & h1.close_rule].feeder.tolist()
    with duckdb.connect(str(repo_path(cfg["paths"]["duckdb"], root)), read_only=True) as con:
        o = con.execute("SELECT OCC_CODE, TOT_EMP FROM oews_3363").df().set_index("OCC_CODE")["TOT_EMP"]
        s = con.execute("SELECT * FROM ep_separations WHERE occupation_type = 'Line item'").df().set_index("nem_code")
    T = cfg["frame"]["targets_core"]
    tgt = o.reindex(T)
    seps = (tgt * s.loc[T, "separations_rate_pct"] / 100)
    exits = (tgt * s.loc[T, "lf_exit_rate_pct"] / 100)
    pool = float(o.reindex(close).sum())
    big = cfg["frame"]["feeders_core"]
    return pd.DataFrame([
        {"quantity": "Maintenance family employment in 3363", "value": float(tgt.sum()), "note": "OEWS May 2025"},
        {"quantity": "Close-feeder pool in 3363 (S, H1 met)", "value": pool, "note": "; ".join(close)},
        {"quantity": "Pool / family employment", "value": pool / float(tgt.sum()), "note": "ratio"},
        {"quantity": "All core-feeder employment in 3363", "value": float(o.reindex(big).sum()), "note": "12 feeders"},
        {"quantity": "Illustrative annual separations, family (3363)", "value": float(seps.sum()),
         "note": "3363 employment x EP all-industry separation rate (assumes equal rates)"},
        {"quantity": "  of which labor-force exits", "value": float(exits.sum()), "note": "same assumption"},
        {"quantity": "Annual separations / close-feeder pool", "value": float(seps.sum()) / pool,
         "note": "share of the close pool that would have to move each year if it were the only source"},
        {"quantity": "Illustrative annual occupational transfers out of the close pool",
         "value": float((o.reindex(close) * s.loc[close, "transfer_rate_pct"] / 100).sum()),
         "note": "3363 employment x EP all-industry occupational transfer rate (Table 1.10); destination unknown (DL-25)"},
    ])


def bls_factors(cfg: dict[str, Any], root: Path) -> pd.DataFrame:
    path = repo_path(cfg["paths"]["raw_ep"], root) / cfg["data_versions"]["ep"]["occupation_file"]["file"]
    t = pd.read_excel(path, sheet_name="Table 1.12", header=1, dtype=str, keep_default_na=False)
    t.columns = ["occ_title", "occ_code", "ind_title", "ind_code", "factor"]
    t = t.apply(lambda c: c.str.strip())
    with duckdb.connect(str(repo_path(cfg["paths"]["duckdb"], root)), read_only=True) as con:
        s = con.execute("SELECT * FROM ep_separations WHERE occupation_type = 'Line item'").df().set_index("nem_code")
    codes = cfg["frame"]["targets_core"] + cfg["frame"]["targets_sensitivity"] + cfg["frame"]["feeders_core"] + ["51-9162"]
    rows = []
    for c in codes:
        g = t[t.occ_code == c]
        pick = g[g.ind_code == "336300"]
        level = "NAICS 336300"
        if pick.empty:
            pick, level = g[g.ind_code == "TE1000"], "All industries"
        rows.append({"soc6": c, "title": s.loc[c, "nem_title"] if c in s.index else "",
                     "ep_change_pct": s.loc[c, "emp_change_pct"] if c in s.index else np.nan,
                     "ep_openings_k": s.loc[c, "openings_k"] if c in s.index else np.nan,
                     "factor_level": level if not pick.empty else "no entry",
                     "factor_text": pick.factor.iloc[0] if not pick.empty else "",
                     "n_industry_rows": len(g),
                     "other_industries": "; ".join(f"{i} {tt}" for i, tt in zip(g.ind_code, g.ind_title))
                                         if pick.empty else ""})
    return pd.DataFrame(rows)


def training_time(cfg: dict[str, Any], root: Path) -> pd.DataFrame:
    raw = repo_path(cfg["paths"]["raw_onet"], root)
    t = pd.read_csv(raw / "training_and_experience.csv", dtype=str, keep_default_na=False)
    cats = pd.read_csv(raw / "training_and_experience_categories.csv", dtype=str, keep_default_na=False)
    jz = pd.read_csv(raw / "job_zones.csv", dtype=str, keep_default_na=False).set_index("O*NET-SOC Code")["Job Zone"]
    t = t[t["Scale ID"].isin(TRAIN_SCALES)].copy()
    t["cat"] = t["Category"].astype(int)
    t["pct"] = t["Data Value"].astype(float)
    label = cats.assign(cat=cats.Category.astype(int)).set_index(["Scale ID", "cat"])["Category Description"]
    with duckdb.connect(str(repo_path(cfg["paths"]["duckdb"], root)), read_only=True) as con:
        o = con.execute("SELECT OCC_CODE, TOT_EMP FROM oews_3363").df().set_index("OCC_CODE")["TOT_EMP"]
    roles = [(c, "target") for c in cfg["frame"]["targets_core"]] + [(c, "feeder") for c in cfg["frame"]["feeders_core"]] \
        + [(c, "negative_control") for c in cfg["frame"]["negative_controls"]]
    rows = []
    for soc, role in roles:
        codes = PROFILE_OVERRIDE.get(soc, [soc + ".00"])
        r = {"soc6": soc, "role": role, "onet_codes": ";".join(codes), "emp_3363": o.get(soc, np.nan),
             "job_zone": ";".join(sorted({jz.get(c, "") for c in codes}))}
        for sc in TRAIN_SCALES:
            dist = (t[(t["O*NET-SOC Code"].isin(codes)) & (t["Scale ID"] == sc)]
                    .groupby("cat")["pct"].mean().sort_index())            # equal-weight mean over codes
            dist = dist / dist.sum() * 100
            med = int(dist.index[np.searchsorted(dist.cumsum().to_numpy(), 50.0)])
            r[f"{sc}_median_category"] = med
            r[f"{sc}_median_label"] = label[(sc, med)]
            r[f"{sc}_share_over_1yr_pct"] = float(dist[dist.index >= OVER_ONE_YEAR[sc]].sum())
        sup = t[t["O*NET-SOC Code"].isin(codes)]["Recommend Suppress"].eq("Y").mean()
        r["suppress_share"] = float(sup)
        r["source"] = ";".join(sorted(t[t["O*NET-SOC Code"].isin(codes)]["Domain Source"].unique()))
        rows.append(r)
    df = pd.DataFrame(rows)
    tg = df[df.role == "target"]
    w = tg.emp_3363 / tg.emp_3363.sum()
    fam = {"soc6": "FAMILY", "role": "family (employment-weighted)", "emp_3363": tg.emp_3363.sum()}
    for sc in TRAIN_SCALES:
        fam[f"{sc}_share_over_1yr_pct"] = float((w * tg[f"{sc}_share_over_1yr_pct"]).sum())
    return pd.concat([df, pd.DataFrame([fam])], ignore_index=True)


def gap_matrix(cfg: dict[str, Any], root: Path) -> pd.DataFrame:
    """Per element: w_k * max(0, z_target - z_feeder) / sum(w). Summing over k reproduces D."""
    with duckdb.connect(str(repo_path(cfg["paths"]["duckdb"], root)), read_only=True) as con:
        emp_all = con.execute("SELECT OCC_CODE, TOT_EMP FROM oews_3363").df().set_index("OCC_CODE")["TOT_EMP"]
        data = {d: load_domain(con, d, cfg) for d in ("K", "S", "A")}
    rows = []
    for d, dd in data.items():
        targets, feeders = build_profiles(dd, cfg, emp_all)
        fam = targets[FAMILY]
        for f, pr in feeders.items():
            c = contributions(fam.z, fam.w, pr.z[None, :])[0] / fam.w.sum()
            assert np.isclose(c.sum(), total_deficit(contributions(fam.z, fam.w, pr.z[None, :]), fam.w)[0])
            for k, e in enumerate(dd.elements):
                rows.append({"domain": d, "feeder": f, "role": pr.role, "element_id": e,
                             "element_name": dd.element_names[e], "target_z": fam.z[k], "feeder_z": pr.z[k],
                             "weight": fam.w[k], "contribution": c[k]})
    return pd.DataFrame(rows)


NEM_FILE = "National_Employment_Matrix_IND_336300.csv"


def read_nem(path: Path) -> pd.DataFrame:
    """Parse the BLS NEM CSV export (codes are written as ="xx-xxxx"; employment in thousands)."""
    t = pd.read_csv(path, dtype=str, keep_default_na=False)
    t["code"] = t["Occupation Code"].str.replace(r'[="]', "", regex=True).str.strip()
    num = {"2025 Employment": "emp_2025_k", "Projected 2035 Employment": "emp_2035_k",
           "2025 Percent of Industry": "pct_ind_2025", "Projected 2035 Percent of Industry": "pct_ind_2035",
           "Employment Change, 2025-2035": "change_k", "Employment Percent Change, 2025-2035": "change_pct"}
    for src, dst in num.items():
        t[dst] = pd.to_numeric(t[src], errors="raise")
    return t.rename(columns={"Occupation Title": "title", "Occupation Type": "type"})[["code", "title", "type", *num.values()]]


def nem_baseline(t: pd.DataFrame) -> dict[str, float]:
    """Industry-scale baseline (DL-28): the modal percent change among line items.

    BLS rescales the shares of occupations it does not adjust when it changes others, so they all share one
    percent change; it is the mode as long as it covers the largest group of line items."""
    li = t[t["type"].str.contains("Line item", case=False)]
    vc = li.change_pct.value_counts()
    base = float(vc.index[0])
    at = li.change_pct == base
    return {"baseline_change_pct": base, "n_line_items": int(len(li)), "n_at_baseline": int(at.sum()),
            "emp_2025_k_at_baseline": float(li.emp_2025_k[at].sum()), "emp_2025_k_line_items": float(li.emp_2025_k.sum()),
            "second_mode_count": int(vc.iloc[1]) if len(vc) > 1 else 0}


def bls_adjustment_pct(change_pct, baseline_pct: float):
    """Occupation change relative to the industry-scale baseline, in percent: (1 + c) / (1 + b) - 1."""
    return 100.0 * ((1 + np.asarray(change_pct, float) / 100) / (1 + baseline_pct / 100) - 1)


def industry_projection(cfg: dict[str, Any], root: Path) -> pd.DataFrame | None:
    path = repo_path(cfg["paths"]["raw_ep"], root) / NEM_FILE
    if not path.exists():
        print(f"[skip] {NEM_FILE} not found in data/raw/ep (optional input, DL-23)")
        return None
    t = read_nem(path).set_index("code")
    base = nem_baseline(t)
    total = t.loc["00-0000"]
    roles = ([(c, "target_core") for c in cfg["frame"]["targets_core"]]
             + [(c, "feeder_core") for c in cfg["frame"]["feeders_core"]]
             + [(c, "context") for c in ("51-9162", "51-1011", "51-4111", "53-7062")])
    rows = [{"soc6": "00-0000", "role": "industry total", **total.drop(["title", "type"]).to_dict(), "title": total.title}]
    for c, role in roles:
        if c not in t.index:
            rows.append({"soc6": c, "role": role, "title": "(not in NEM 336300)"})
            continue
        r = t.loc[c]
        rows.append({"soc6": c, "role": role, "title": r.title, **r.drop(["title", "type"]).to_dict()})
    df = pd.DataFrame(rows)
    df["change_vs_industry_pts"] = df.change_pct - float(total.change_pct)
    df["baseline_change_pct"] = base["baseline_change_pct"]
    li = df.soc6 != "00-0000"
    df["bls_adjusted"] = np.where(li, df.change_pct != base["baseline_change_pct"], np.nan)
    df["bls_adjustment_pct"] = np.where(li, bls_adjustment_pct(df.change_pct, base["baseline_change_pct"]), np.nan)
    df.attrs["baseline"] = base
    return df


def pathway_table(cfg: dict[str, Any], root: Path, nem: pd.DataFrame | None, tr: pd.DataFrame) -> pd.DataFrame:
    """Side-by-side layers for each core feeder (DL-25b). Columns are never combined into a score."""
    est, lay = repo_path("outputs/estimates", root), repo_path("outputs/layers", root)
    h1 = pd.read_csv(est / "h1_decisions.csv")
    s = h1[(h1.domain == "S") & (h1.feeder_role == "feeder_core")].set_index("feeder")
    w = pd.read_csv(lay / "wage_layer.csv").set_index("soc6")
    ep = pd.read_csv(lay / "ep_layer.csv").set_index("soc6")
    g = pd.read_csv(lay / "regulatory_gates.csv").set_index("soc6")
    t = tr.set_index("soc6")
    df = pd.DataFrame(index=pd.Index(cfg["frame"]["feeders_core"], name="soc6"))
    df["S_P_upper"] = s["P_hi"]; df["S_close_H1"] = s["close_rule"]
    df["jobs_3363"] = w["emp_3363"]
    df["change_inside_3363_pct"] = nem.set_index("soc6")["change_pct"] if nem is not None else float("nan")
    df["wage_gap_to_family_usd"] = w["gap_to_family_approx"]; df["wage_gap_pct"] = w["gap_to_family_pct"]
    df["own_OJT_median"] = t["OJ_median_label"]
    df["bls_typical_ojt"] = ep["ojt"]
    df["transfer_rate_pct"] = ep["transfer_rate_pct"]
    df["servicing_importance_max"] = g[["onet_importance_repairing", "onet_importance_equipment_maintenance"]].max(axis=1)
    return df.reset_index().sort_values("S_P_upper")


def run(cfg: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, pd.DataFrame]:
    out = repo_path("outputs/practice", root)
    out.mkdir(parents=True, exist_ok=True)
    rank = production_ranking(cfg, root)
    pool = pool_arithmetic(cfg, root)
    fac = bls_factors(cfg, root)
    tr = training_time(cfg, root)
    gaps = gap_matrix(cfg, root)
    gaps.to_csv(out / "gap_matrix.csv", index=False)
    nem = industry_projection(cfg, root)
    if nem is not None:
        nem.to_csv(out / "nem_336300.csv", index=False)
    path = pathway_table(cfg, root, nem, tr)
    path.to_csv(out / "pathway_table.csv", index=False)
    rank.to_csv(out / "production_ranking_3363.csv", index=False)
    top = {d: rank[(rank.domain == d) & rank.has_profile].nsmallest(10, "D") for d in ("S", "K", "A")}
    for d, g in top.items():
        g.to_csv(out / f"top10_{d}.csv", index=False)
    pool.to_csv(out / "pool_arithmetic.csv", index=False)
    fac.to_csv(out / "bls_factors.csv", index=False)
    tr.to_csv(out / "training_time.csv", index=False)
    cols = ["rank", "soc6", "title", "P", "emp_3363", "emp_rse", "h_median_3363", "ep_change_pct", "in_registered_frame", "small_or_imprecise"]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    md = [f"# Practice layer (DL-12, DL-13, DL-14, DL-21) — exploratory / descriptive\n\nGenerated: {ts}\n",
          f"Production occupations with 3363 employment: {rank.soc6.nunique()}; with an O*NET profile: "
          f"{rank[rank.has_profile].soc6.nunique()}.\n"]
    for d in ("S", "K", "A"):
        md += [f"\n## Top 10 — {d}{' (A: negative control failed; not interpreted)' if d == 'A' else ''}\n",
               top[d][cols].round(2).to_markdown(index=False)]
    md += ["\n\n## Pool arithmetic (illustrative)\n", pool.round(3).to_markdown(index=False),
           "\n\n## BLS EP Table 1.12 factors\n", fac[["soc6", "title", "ep_change_pct", "factor_level", "factor_text"]].to_markdown(index=False),
           "\n\n## Training time (O*NET)\n", tr.round(1).to_markdown(index=False)]
    if nem is not None:
        b = nem.attrs["baseline"]
        md += ["\n\n## Projections inside NAICS 336300 (BLS National Employment Matrix, DL-23, DL-28)\n",
               f"Industry-scale baseline (modal change of line items, DL-28): {b['baseline_change_pct']:+.1f}% — "
               f"{b['n_at_baseline']} of {b['n_line_items']} line items, {b['emp_2025_k_at_baseline']:.1f}k of "
               f"{b['emp_2025_k_line_items']:.1f}k 2025 jobs ({100 * b['emp_2025_k_at_baseline'] / b['emp_2025_k_line_items']:.1f}%); "
               f"next most common value covers {b['second_mode_count']} line items. "
               "BLS adjustment = (1 + change) / (1 + baseline) − 1.\n",
               nem[["soc6", "role", "title", "emp_2025_k", "emp_2035_k", "change_pct", "change_vs_industry_pts",
                    "bls_adjustment_pct", "pct_ind_2025", "pct_ind_2035"]].round(1).to_markdown(index=False)]
    (out / "practice_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"rank": rank, "top": top, "pool": pool, "factors": fac, "training": tr, "nem": nem, "pathway": path}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    res = run(load_config(args.config))
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 60)
    print(res["top"]["S"][["rank", "soc6", "title", "P", "emp_3363", "small_or_imprecise"]].round(1).to_string(index=False))
    print(res["pool"].round(3).to_string(index=False))
    print(res["training"][["soc6", "role", "job_zone", "OJ_median_label", "OJ_share_over_1yr_pct",
                           "PT_share_over_1yr_pct", "RW_share_over_1yr_pct"]].round(1).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
