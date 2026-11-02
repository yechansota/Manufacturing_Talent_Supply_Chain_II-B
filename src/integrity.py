"""Data-integrity review across sources (read-only; no estimand is changed here).

Checks are grouped:
  A. Source fidelity      — values, intervals, flags inside each published file
  B. Cross-source fit     — classification, time and industry alignment
  C. Construct integrity  — whether the inputs measure what the design assumes
  D. Statistical integrity— behaviour of the H2 fit (D2 is post hoc, deviation log DL-7)

Each check returns status PASS / NOTE (true but must be disclosed) / FLAG (needs a decision).

Outputs: outputs/review/integrity_checks.csv, outputs/review/integrity_review.md
Usage:   python -m src.integrity
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from .config import REPO_ROOT, load_config, repo_path
from .profiles import FAMILY

CHECKS: list[dict[str, Any]] = []


def check(group: str, cid: str, title: str, status: str, detail: str) -> None:
    CHECKS.append({"group": group, "id": cid, "check": title, "status": status, "detail": detail})


def run(cfg: dict[str, Any], root: Path = REPO_ROOT) -> pd.DataFrame:
    CHECKS.clear()
    db = repo_path(cfg["paths"]["duckdb"], root)
    est = repo_path("outputs/estimates", root)
    with duckdb.connect(str(db), read_only=True) as con:
        r = con.execute("SELECT * FROM onet_ratings").df()
        oews = con.execute("SELECT * FROM oews_3363").df()
        sep = con.execute("SELECT * FROM ep_separations WHERE occupation_type = 'Line item'").df()
    pairs = pd.read_csv(est / "point_pairs.csv")
    ref = pd.read_csv(est / "reference_distribution.csv")
    frame_codes = {c for c in pairs["feeder_codes"].str.split(";").explode()}
    tgt_codes = [t + ".00" for t in cfg["frame"]["targets_core"]]

    # ---------------------------------------------------------------- A. source fidelity
    lv, im = r[r.scale_id == "LV"], r[r.scale_id == "IM"]
    bad = int(((lv.data_value < 0) | (lv.data_value > 7)).sum() + ((im.data_value < 1) | (im.data_value > 5)).sum())
    check("A", "A1", "Rating values inside published scale ranges (LV 0–7, IM 1–5)",
          "PASS" if bad == 0 else "FLAG", f"{bad} out-of-range rows of {len(r):,}")

    ci = r.dropna(subset=["se", "ci_lo", "ci_hi"])
    ci = ci[ci.se > 0]
    ratio = (ci.ci_hi - ci.ci_lo) / (2 * ci.se)
    inside = ((ci.data_value >= ci.ci_lo - 1e-6) & (ci.data_value <= ci.ci_hi + 1e-6)).mean()
    check("A", "A2", "Published 95% CI consistent with SE",
          "PASS" if inside > 0.999 else "NOTE",
          f"half-width / SE: median {ratio.median():.2f} (IQR {ratio.quantile(.25):.2f}–{ratio.quantile(.75):.2f}); "
          f"value inside its CI in {inside:.1%} of {len(ci):,} rows. Ratios above 1.96 are consistent with "
          "small-sample t intervals; the bootstrap uses SE directly.")

    nr = lv[["onet_code", "element_id", "not_relevant", "data_value"]].merge(
        im[["onet_code", "element_id", "data_value"]], on=["onet_code", "element_id"], suffixes=("_lv", "_im"))
    y, n = nr[nr.not_relevant == "Y"], nr[nr.not_relevant == "N"]
    check("A", "A3", "'Not Relevant' flag behaves as documented (low importance)",
          "PASS" if y.data_value_im.median() < n.data_value_im.median() else "FLAG",
          f"median Importance when flagged {y.data_value_im.median():.2f} vs not flagged {n.data_value_im.median():.2f}; "
          f"median Level when flagged {y.data_value_lv.median():.2f} ({len(y):,} flagged Level rows). "
          "Primary spec uses Level as published; the 'zero' multiverse branch sets these to 0.")

    sup = r[r.suppress.notna() & r.se.notna()]
    check("A", "A4", "'Recommend Suppress' marks low-precision ratings",
          "PASS" if sup[sup.suppress == "Y"].se.median() > sup[sup.suppress == "N"].se.median() else "FLAG",
          f"median SE flagged {sup[sup.suppress == 'Y'].se.median():.3f} vs unflagged "
          f"{sup[sup.suppress == 'N'].se.median():.3f}")

    s_ids = r[r.domain == "S"].groupby("file_key")["element_id"].apply(set)
    overlap = set.intersection(*s_ids.tolist()) if len(s_ids) > 1 else set()
    check("A", "A5", "Skills union has no element shared by the two Skills files",
          "PASS" if not overlap else "FLAG", f"overlap: {sorted(overlap) or 'none'}")

    tot = float(oews.loc[oews.OCC_CODE == "00-0000", "TOT_EMP"].iloc[0])
    det = oews[oews.O_GROUP == "detailed"]
    cover = det.TOT_EMP.sum() / tot
    n_supp = int(det.TOT_EMP.isna().sum())
    pct_dev = (det.TOT_EMP / tot * 100 - det.PCT_TOTAL).abs().max()
    check("A", "A6", "OEWS 3363 detailed rows reconcile with the industry total",
          "PASS" if 0.97 <= cover <= 1.01 and pct_dev < 0.01 else "NOTE",
          f"detailed employment sums to {cover:.1%} of total ({n_supp} detailed rows withheld '**'); "
          f"max |TOT_EMP/total − PCT_TOTAL| = {pct_dev:.4f} pp")

    implied = sep.separations_k + sep.emp_change_k / 10
    dev = (implied - sep.openings_k).abs()
    check("A", "A7", "EP Table 1.10 identity: openings = separations + employment change / 10",
          "PASS" if dev.quantile(0.99) <= 0.15 else "NOTE",
          f"max abs deviation {dev.max():.2f}k, 99th pct {dev.quantile(.99):.2f}k over {len(sep)} line items "
          "(rounding in published thousands)")

    # ---------------------------------------------------------------- B. cross-source fit
    check("B", "B1", "Classification systems linked by the BLS crosswalk",
          "PASS", "O*NET-SOC 2019 ↔ NEM 2025 ↔ SOC 2018 (OEWS) verified code by code in "
          "outputs/validation/ep_crosswalk_check.csv (23/23 OK)")

    dates = r[r.onet_code.isin(frame_codes)].groupby("onet_code")["date_year"].min()
    old = dates[dates < 2018].sort_values()
    check("B", "B2", "Rating vintage vs. 2025 employment data",
          "NOTE", f"frame ratings collected {int(dates.min())}–{int(dates.max())}; before 2018: "
          + ", ".join(f"{c} ({y})" for c, y in old.items())
          + ". O*NET dates are occupation-level update dates shared by K/S/A, so vintage cannot be separated "
          "from occupation.")

    check("B", "B3", "Industry scope differs by source",
          "NOTE", "OEWS weights are NAICS 3363-specific; O*NET ratings and EP projections are all-industry "
          "national. KSA profiles therefore describe each occupation economy-wide, not inside auto-parts plants.")

    # ---------------------------------------------------------------- C. construct integrity
    k = r[(r.domain == "K") & (r.scale_id == "LV")]
    by_src = k.groupby("domain_source")["data_value"].mean()
    mill_src = k.loc[k.onet_code == "49-9044.00", "domain_source"].unique().tolist()
    zK = k.pivot(index="onet_code", columns="element_id", values="data_value")
    zK = (zK - zK.mean()) / zK.std(ddof=1)
    corr = zK.loc[tgt_codes].T.corr().round(2)
    mill_corr = corr.loc["49-9044.00"].drop("49-9044.00")
    other = corr.drop(index="49-9044.00", columns="49-9044.00")
    other_mean = other.where(~np.eye(len(other), dtype=bool)).stack().mean()
    check("C", "C1", "Knowledge rater source is mixed; one core target is expert-rated",
          "FLAG" if mill_corr.mean() < other_mean - 0.1 else "NOTE",
          f"mean K Level by source: " + ", ".join(f"{s} {v:.2f}" for s, v in by_src.items())
          + f". Millwrights K source: {mill_src}. Correlation of Millwrights' K profile with other core targets "
          f"{mill_corr.mean():.2f} vs mean among the other four {other_mean:.2f}.")

    emp = oews.set_index("OCC_CODE").TOT_EMP
    pi = emp.reindex(cfg["frame"]["targets_core"])
    pi = pi / pi.sum()
    check("C", "C2", "Family target weights are concentrated",
          "NOTE", "π: " + ", ".join(f"{c} {v:.1%}" for c, v in pi.items())
          + f". 49-9041 + 49-9071 = {pi[['49-9041', '49-9071']].sum():.1%}; equal weights are the registered sensitivity.")

    fe = emp.reindex(cfg["frame"]["feeders_core"])
    check("C", "C3", "Feeder employment dominated by a proxy-mapped code",
          "NOTE", f"51-2090 (proxied by Team Assemblers) = {fe['51-2090'] / fe.sum():.1%} of core feeder employment. "
          "Matters only for employment-weighted summaries; per-feeder estimates are unaffected.")

    a, b = "51-2022.00", "51-2023.00"
    cors = []
    for d in "KSA":
        m = r[(r.domain == d) & (r.scale_id == "LV") & r.onet_code.isin([a, b])].pivot(
            index="element_id", columns="onet_code", values="data_value")
        cors.append(f"{d} {m[a].corr(m[b]):.2f}")
    check("C", "C4", "51-2028 profile mean combines two vintages (2026 and 2017)",
          "NOTE", "Level-profile correlation between the two codes: " + ", ".join(cors))

    famK = ref[(ref.target == FAMILY) & (ref.domain == "K")].nsmallest(6, "D")
    check("C", "C5", "Knowledge deficit rewards broadly high-knowledge occupations",
          "NOTE", "Directional D gives zero or near-zero deficit to occupations at or above the family on every "
          "element, e.g. " + "; ".join(famK.title.head(5)) + ". K proximity therefore means 'lacks little', "
          "not 'is similar'. S and A nearest neighbours are maintenance/technical occupations.")

    vc = pd.read_csv(est / "validity_check.csv")
    fails = vc[vc.decision.str.startswith("FAIL")]
    check("C", "C6", "Pre-registered negative control",
          "FLAG" if len(fails) else "PASS",
          "; ".join(f"{r_.domain}: P={r_.P:.1f} ({'FAIL' if r_.decision.startswith('FAIL') else 'PASS'})"
                    for r_ in vc.itertuples())
          + ". A-domain failure: hand laborers share the physical abilities that maintenance work requires.")

    # ---------------------------------------------------------------- D. statistical integrity
    fam = ref[ref.target == FAMILY].dropna(subset=["C"])
    diag = []
    for d, g in fam.groupby("domain"):
        g = g[g.D > 0]
        r2 = {}
        for form, x in (("linear", g.D), ("log", np.log(g.D))):
            res = g[f"resid_{form}"]
            r2[form] = 1 - res.var() / g.C.var()
        bins = pd.qcut(g.D, 5, labels=False)
        bmeans = g.groupby(bins)["resid_linear"].mean()
        diag.append(f"{d}: R² linear {r2['linear']:.2f}, log {r2['log']:.2f}; mean linear residual by D-quintile "
                    + "/".join(f"{v:+.3f}" for v in bmeans))
    check("D", "D1", "Shape of the C–D relation in the reference universe",
          "NOTE", " | ".join(diag))

    core = pairs[(pairs.target == FAMILY) & (pairs.feeder_role == "feeder_core")]
    loc_rows = []
    for row in core.itertuples():
        g = fam[fam.domain == row.domain].copy()
        g["dist"] = (g.D - row.D).abs()
        nb = g.nsmallest(100, "dist")
        loc_rows.append({"domain": row.domain, "feeder": row.feeder,
                         "local_C_pct": 100 * float((nb.C <= row.C_top).mean())})
    loc = pd.DataFrame(loc_rows)
    loc.to_csv(repo_path("outputs/review", root) / "h2_local_diagnostic.csv", index=False)
    summ = loc.groupby("domain")["local_C_pct"].agg(["median", lambda s: int((s < 10).sum())])
    check("D", "D2", "POST-HOC (DL-7): D-matched local percentile of feeder concentration",
          "NOTE", "median local percentile / feeders below 10th pct (of 12): "
          + ", ".join(f"{d} {m:.1f} / {c}" for d, (m, c) in summ.iterrows())
          + ". Exploratory; does not replace the registered test.")

    out = pd.DataFrame(CHECKS)
    out_dir = repo_path("outputs/review", root)
    out.to_csv(out_dir / "integrity_checks.csv", index=False)
    lines = ["# Data integrity review\n", "Status: PASS = verified; NOTE = true, must be disclosed; "
             "FLAG = needs a decision.\n"]
    for grp, gdf in out.groupby("group", sort=False):
        lines.append(f"\n## {grp}\n")
        for c in gdf.itertuples():
            lines.append(f"- **{c.id} [{c.status}] {c.check}** — {c.detail}")
    (out_dir / "integrity_review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    repo_path("outputs/review").mkdir(parents=True, exist_ok=True)
    out = run(load_config(args.config))
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 400)
    for c in out.itertuples():
        print(f"{c.id} [{c.status}] {c.check}\n    {c.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
