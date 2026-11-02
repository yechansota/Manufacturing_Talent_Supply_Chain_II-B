"""Deficit and reference-distribution step (point estimates, primary specification).

For every domain and every target profile (5 core targets, 2 sensitivity targets,
and the maintenance family J):
  1. compute D and C for every O*NET occupation in the reference universe
     (excluding the target, or all five family members for J — deviation log DL-1);
  2. fit C on D over reference occupations with D > 0: OLS linear (primary) and
     OLS on log D (sensitivity) — DL-3;
  3. for every frame feeder: D, proximity percentile P, C, H2 residual and its
     percentile in the reference residual distribution (DL-4), and the top-m elements.
Negative-control validity check per domain against J (DL-5).

Bootstrap intervals are NOT computed here; H1 decisions need them and are deferred.

Outputs (outputs/estimates/):
  point_pairs.csv          feeder x target x domain estimates
  top_elements.csv         top-m contributing elements per feeder x target x domain
  reference_distribution.csv  D, C, residuals for every reference occupation x target x domain
  validity_check.csv       negative-control rule per domain
  h2_summary.csv           headline H2 count per domain (feeder -> FAMILY)
  estimates_summary.md

Usage:
    python -m src.reference [--config config/prereg.yaml]
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from .config import REPO_ROOT, load_config, repo_path
from .deficit import concentration, contributions, ols_fit, proximity_percentile, total_deficit
from .profiles import FAMILY, build_profiles, load_domain


def _fit_residuals(D: np.ndarray, C: np.ndarray, form: str) -> tuple[float, float, np.ndarray]:
    ok = D > 0
    x = D[ok] if form == "linear" else np.log(D[ok])
    a, b = ols_fit(x, C[ok])
    res = np.full_like(D, np.nan)
    res[ok] = C[ok] - (a + b * x)
    return a, b, res


def _predict_residual(d: float, c: float, a: float, b: float, form: str) -> float:
    if not d > 0:
        return float("nan")
    x = d if form == "linear" else np.log(d)
    return float(c - (a + b * x))


def run(cfg: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, pd.DataFrame]:
    m = cfg["estimands"]["primary"]["top_m"]
    db_path = repo_path(cfg["paths"]["duckdb"], root)
    with duckdb.connect(str(db_path), read_only=True) as con:
        employment = con.execute("SELECT OCC_CODE, TOT_EMP FROM oews_3363").df().set_index("OCC_CODE")["TOT_EMP"]
        domains = [r[0] for r in con.execute("SELECT DISTINCT domain FROM onet_ratings ORDER BY 1").fetchall()]
        data = {d: load_domain(con, d, cfg) for d in domains}

    pair_rows, top_rows, ref_rows = [], [], []
    for d, dd in data.items():
        targets, feeders = build_profiles(dd, cfg, employment)
        Zall = dd.Z.to_numpy()
        for tname, tp in targets.items():
            exclude = set(tp.member_codes)
            ref_mask = ~dd.codes.isin(exclude)
            c_ref = contributions(tp.z, tp.w, Zall[ref_mask])
            D_ref = total_deficit(c_ref, tp.w)
            C_ref = concentration(c_ref, m)
            fits = {form: _fit_residuals(D_ref, C_ref, form) for form in ("linear", "log")}
            q95 = {form: float(np.nanquantile(fits[form][2], 0.95)) for form in fits}
            n_zero = int(np.sum(D_ref == 0))

            ref_rows.append(pd.DataFrame({
                "domain": d, "target": tname, "onet_code": dd.codes[ref_mask],
                "title": dd.titles.reindex(dd.codes[ref_mask]).to_numpy(),
                "D": D_ref, "C": C_ref,
                "resid_linear": fits["linear"][2], "resid_log": fits["log"][2]}))

            for fname, fp in feeders.items():
                c_f = contributions(tp.z, tp.w, fp.z[None, :])
                D_f = float(total_deficit(c_f, tp.w)[0])
                C_f = float(concentration(c_f, m)[0])
                row = {"domain": d, "target": tname, "feeder": fname, "feeder_role": fp.role,
                       "feeder_codes": ";".join(fp.member_codes), "n_reference": int(ref_mask.sum()),
                       "n_reference_D_zero": n_zero, "D": D_f,
                       "P": proximity_percentile(D_f, D_ref), "C_top": C_f}
                for form, (a, b, res) in fits.items():
                    r_f = _predict_residual(D_f, C_f, a, b, form)
                    row[f"h2_resid_{form}"] = r_f
                    valid = ~np.isnan(res)          # D = 0 occupations have no residual (DL-3/DL-4)
                    row[f"h2_resid_pct_{form}"] = (100.0 * float(np.mean(res[valid] <= r_f))
                                                   if np.isfinite(r_f) else np.nan)
                    row[f"h2_q95_{form}"] = q95[form]
                    row[f"h2_exceeds_q95_{form}"] = bool(np.isfinite(r_f) and r_f > q95[form])
                    row[f"fit_{form}_a"], row[f"fit_{form}_b"] = a, b
                pair_rows.append(row)

                order = np.argsort(-c_f[0])[:m]
                total = c_f[0].sum()
                for rank, k in enumerate(order, start=1):
                    el = dd.elements[k]
                    top_rows.append({"domain": d, "target": tname, "feeder": fname, "rank": rank,
                                     "element_id": el, "element_name": dd.element_names[el],
                                     "contribution": float(c_f[0, k]),
                                     "share_of_total": float(c_f[0, k] / total) if total > 0 else np.nan,
                                     "target_z": float(tp.z[k]), "feeder_z": float(fp.z[k]),
                                     "target_weight": float(tp.w[k])})

    pairs = pd.DataFrame(pair_rows)
    top = pd.DataFrame(top_rows)
    reference = pd.concat(ref_rows, ignore_index=True)

    vc = cfg["decision_rules"]["validity_check"]
    neg = pairs[(pairs["target"] == FAMILY) & (pairs["feeder_role"] == "negative_control")]
    validity = neg[["domain", "feeder", "D", "P"]].assign(
        min_percentile=vc["negative_control_min_percentile"],
        decision=lambda x: np.where(x["P"] >= vc["negative_control_min_percentile"],
                                    "PASS — H1 interpretable", "FAIL — measure failure; H1 not interpreted"))

    core = pairs[(pairs["target"] == FAMILY) & (pairs["feeder_role"] == "feeder_core")]
    h2 = (core.groupby("domain")
          .agg(n_feeders=("feeder", "size"),
               n_exceed_linear=("h2_exceeds_q95_linear", "sum"),
               n_exceed_log=("h2_exceeds_q95_log", "sum"),
               median_resid_pct_linear=("h2_resid_pct_linear", "median"),
               median_resid_pct_log=("h2_resid_pct_log", "median"),
               median_C=("C_top", "median"), median_D=("D", "median"))
          .reset_index())
    h2["expected_under_null"] = h2["n_feeders"] * 0.05

    out_dir = repo_path(cfg["paths"].get("estimates_out", "outputs/estimates"), root)
    out_dir.mkdir(parents=True, exist_ok=True)
    pairs.to_csv(out_dir / "point_pairs.csv", index=False)
    top.to_csv(out_dir / "top_elements.csv", index=False)
    reference.to_csv(out_dir / "reference_distribution.csv", index=False)
    validity.to_csv(out_dir / "validity_check.csv", index=False)
    h2.to_csv(out_dir / "h2_summary.csv", index=False)
    (out_dir / "estimates_summary.md").write_text(render(cfg, pairs, top, validity, h2), encoding="utf-8")
    return {"pairs": pairs, "top": top, "reference": reference, "validity": validity, "h2": h2}


def render(cfg, pairs, top, validity, h2) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fam = pairs[pairs["target"] == FAMILY].copy()
    cols = ["domain", "feeder", "feeder_role", "D", "P", "C_top", "h2_resid_pct_linear", "h2_resid_pct_log"]
    tbl = fam[cols].sort_values(["domain", "P"])
    lines = [f"# Point estimates (primary specification, no bootstrap)\n\nGenerated: {ts}  \n"
             f"Pre-registration v{cfg['meta']['prereg_version']} ({cfg['meta']['status']}); "
             "implementation clarifications DL-1..DL-6 in outputs/deviation_log.md.\n",
             "## Validity check (negative control vs family target)\n", validity.round(2).to_markdown(index=False),
             "\n\n## H2 headline (core feeders -> family target)\n", h2.round(3).to_markdown(index=False),
             "\n\n## Feeder -> family target, by domain (sorted by P; lower P = closer)\n",
             tbl.round(3).to_markdown(index=False)]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    try:
        res = run(cfg)
    except Exception as exc:  # surface any data problem with a non-zero exit
        print(f"FAILED: {exc}", file=sys.stderr)
        raise
    print(res["validity"].to_string(index=False))
    print(res["h2"].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
