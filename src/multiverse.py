"""Multiverse (prereg `multiverse`, implementation and summary rules in deviation log DL-11).

3 standardizations x 2 weightings x 2 suppress rules x 2 not-relevant rules x 2 feeder
thresholds x 2 family weightings = 96 specifications per domain, point estimates only,
family target J only. Cells removed by the 'drop' branch are handled with pairwise element
deletion; with no removed cells every formula reduces to the primary-specification code.

Outputs (outputs/multiverse/):
  multiverse_specs.csv     one row per domain x specification
  multiverse_feeders.csv   one row per domain x specification x feeder
  multiverse_summary.csv   DL-11 shares per domain
  multiverse_h1.csv        share of specs with P <= 25 per feeder (validity-passing specs only)
  multiverse_summary.md

Usage:
    python -m src.multiverse
"""
from __future__ import annotations

import argparse
import itertools
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
from scipy.stats import binom

from .config import REPO_ROOT, load_config, repo_path
from .deficit import ols_fit
from .frame import resolve_codes

LOCAL_K = 100


def k_star(n: int, alpha: float = 0.05, p: float = 0.05) -> int:
    """Smallest k with P(X >= k) < alpha for X ~ Binomial(n, p)."""
    return next(k for k in range(n + 1) if binom.sf(k - 1, n, p) < alpha)


def load_domain(con, domain: str, cfg: dict[str, Any]) -> dict[str, Any]:
    lv = cfg["measurement"]["scales"]["level"]["id"]
    im = cfg["measurement"]["scales"]["importance"]["id"]
    r = con.execute("SELECT onet_code, element_id, scale_id, data_value, suppress, not_relevant "
                    "FROM onet_ratings WHERE domain = ?", [domain]).df()
    piv = lambda s, v: r[r.scale_id == s].pivot(index="onet_code", columns="element_id", values=v)
    L = piv(lv, "data_value").sort_index()
    align = lambda x: x.loc[L.index, L.columns]
    I = align(piv(im, "data_value"))
    supL = align(piv(lv, "suppress")).eq("Y").to_numpy()
    supI = align(piv(im, "suppress")).eq("Y").to_numpy()
    nr = align(piv(lv, "not_relevant")).eq("Y").to_numpy()
    return {"codes": L.index.to_numpy(), "elements": L.columns.to_numpy(), "L": L.to_numpy(float),
            "I": I.to_numpy(float), "supL": supL, "supI": supI, "nr": nr}


def transform(L: np.ndarray, avail: np.ndarray, how: str) -> np.ndarray:
    X = np.where(avail, L, np.nan)
    if how == "raw":
        return X
    if how == "z":
        mu = np.nanmean(X, axis=0)
        sd = np.nanstd(X, axis=0, ddof=1)
        return (X - mu) / sd
    if how == "percentile":
        return pd.DataFrame(X).rank(pct=True, method="average").to_numpy()
    raise ValueError(how)


def weighted_profile(X: np.ndarray, idx: np.ndarray, mix: np.ndarray) -> np.ndarray:
    """Mixture over member rows ignoring missing cells (weights renormalized per element)."""
    sub = X[idx]
    w = np.where(np.isnan(sub), 0.0, mix[:, None])
    tot = w.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(tot > 0, np.nansum(np.where(np.isnan(sub), 0.0, sub) * w, axis=0) / tot, np.nan)


def masked_metrics(z_t: np.ndarray, w_t: np.ndarray, X: np.ndarray, m: int):
    valid = ~np.isnan(X) & ~np.isnan(z_t)[None, :] & ~np.isnan(w_t)[None, :]
    gap = np.where(valid, z_t[None, :] - np.where(valid, X, 0.0), 0.0)
    c = np.where(valid, np.nan_to_num(w_t)[None, :] * np.maximum(gap, 0.0), 0.0)
    denom = np.where(valid, np.nan_to_num(w_t)[None, :], 0.0).sum(axis=1)
    tot = c.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        D = np.where(denom > 0, tot / denom, np.nan)
        top = -np.sort(-c, axis=1)[:, :m].sum(axis=1)
        C = np.where(tot > 0, top / tot, np.nan)
        s = c / tot[:, None]
        neff = np.where(tot > 0, 1.0 / np.sum(s ** 2, axis=1), np.nan)
    return D, C, neff


def run(cfg: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, pd.DataFrame]:
    mv = cfg["multiverse"]
    m = cfg["estimands"]["primary"]["top_m"]
    vc_min = cfg["decision_rules"]["validity_check"]["negative_control_min_percentile"]
    h1_thr = next(s["threshold_upper_ci_percentile"] for s in cfg["estimands"]["secondary"] if s["id"] == "H1")
    with duckdb.connect(str(repo_path(cfg["paths"]["duckdb"], root)), read_only=True) as con:
        emp = con.execute("SELECT OCC_CODE, TOT_EMP FROM oews_3363").df().set_index("OCC_CODE")["TOT_EMP"]
        domains = [r[0] for r in con.execute("SELECT DISTINCT domain FROM onet_ratings ORDER BY 1").fetchall()]
        data = {d: load_domain(con, d, cfg) for d in domains}
    alt = pd.read_csv(repo_path(cfg["paths"]["validation_out"], root) / "oews_feeders_threshold_alt.csv", dtype=str)
    feeders_by_thr = {int(t): g["OCC_CODE"].tolist() for t, g in alt.groupby("threshold")}
    if set(feeders_by_thr[max(feeders_by_thr)]) != set(cfg["frame"]["feeders_core"]):
        raise RuntimeError("threshold-4000 feeder set differs from frame.feeders_core")
    neg = cfg["frame"]["negative_controls"][0]
    targets = cfg["frame"]["targets_core"]

    grid = list(itertools.product(mv["standardization"], mv["weights"], mv["suppress"], mv["not_relevant"],
                                  mv["feeder_employment_threshold"], mv["family_weights"]))
    primary = ("z", "importance_minus_one", "keep", "as_published",
               cfg["frame"]["selection_rules"]["feeder"]["min_employment"], "employment_share")
    spec_rows, feeder_rows = [], []
    for d, dd in data.items():
        pos = {c: i for i, c in enumerate(dd["codes"])}
        prim = lambda soc: np.array([pos[c] for c, t in resolve_codes(soc, cfg) if t == "primary"])
        fam_idx = [prim(t) for t in targets]
        fam_rows = np.concatenate(fam_idx)
        ref_mask = np.ones(len(dd["codes"]), dtype=bool); ref_mask[fam_rows] = False
        for spec in grid:
            std, wts, sup, nrr, thr, fw = spec
            L = np.where(dd["nr"], 0.0, dd["L"]) if nrr == "zero" else dd["L"]
            avail = ~(dd["supL"] | dd["supI"]) if sup == "drop" else np.ones_like(L, dtype=bool)
            X = transform(L, avail, std)
            W = np.where(avail, np.clip(dd["I"] - 1.0, 0, 4) if wts == "importance_minus_one" else 1.0, np.nan)
            e = emp.reindex(targets).to_numpy(float)
            pi = e / e.sum() if fw == "employment_share" else np.full(len(targets), 1 / len(targets))
            # family = pi-mixture of target profiles; each target is its single primary code
            mix = np.concatenate([np.full(len(ix), p / len(ix)) for ix, p in zip(fam_idx, pi)])
            z_t = weighted_profile(X, fam_rows, mix)
            w_t = weighted_profile(W, fam_rows, mix)
            D_ref, C_ref, N_ref = masked_metrics(z_t, w_t, X[ref_mask], m)
            ok = (D_ref > 0) & ~np.isnan(C_ref)
            fits = {}
            for form in ("linear", "log"):
                x = D_ref[ok] if form == "linear" else np.log(D_ref[ok])
                a, b = ols_fit(x, C_ref[ok])
                res = C_ref[ok] - (a + b * x)
                fits[form] = (a, b, res, np.quantile(res, 0.95))
            feeders = feeders_by_thr[thr] + [neg]
            rows = []
            for f in feeders:
                idx = prim(f)
                with warnings.catch_warnings():   # all-missing element in the drop branch -> NaN (pairwise deletion)
                    warnings.simplefilter("ignore", RuntimeWarning)
                    zf = np.nanmean(X[idx], axis=0) if len(idx) > 1 else X[idx[0]]
                D_f, C_f, N_f = (v[0] for v in masked_metrics(z_t, w_t, zf[None, :], m))
                P_f = 100.0 * float(np.mean(D_ref[~np.isnan(D_ref)] <= D_f))
                r = {"domain": d, "standardization": std, "weights": wts, "suppress": sup, "not_relevant": nrr,
                     "feeder_threshold": thr, "family_weights": fw, "feeder": f,
                     "role": "negative_control" if f == neg else "feeder", "D": D_f, "P": P_f, "C": C_f, "neff": N_f}
                for form, (a, b, res, q95) in fits.items():
                    x_f = D_f if form == "linear" else np.log(D_f) if D_f > 0 else np.nan
                    r_f = C_f - (a + b * x_f) if D_f > 0 else np.nan
                    r[f"rpct_{form}"] = 100.0 * float(np.mean(res <= r_f)) if np.isfinite(r_f) else np.nan
                    r[f"exceed_{form}"] = bool(np.isfinite(r_f) and r_f > q95)
                nb = np.argsort(np.abs(np.nan_to_num(D_ref, nan=np.inf) - D_f))[:LOCAL_K]
                nb = nb[~np.isnan(N_ref[nb])]
                r["neff_local_pct"] = 100.0 * float(np.mean(N_ref[nb] <= N_f))
                rows.append(r)
            fr = pd.DataFrame(rows)
            feeder_rows.append(fr)
            core = fr[fr.role == "feeder"]
            n = len(core); ks = k_star(n)
            negP = float(fr.loc[fr.role == "negative_control", "P"].iloc[0])
            spec_rows.append({
                "domain": d, "standardization": std, "weights": wts, "suppress": sup, "not_relevant": nrr,
                "feeder_threshold": thr, "family_weights": fw, "is_primary": spec == primary,
                "n_feeders": n, "k_star": ks,
                "n_exceed_linear": int(core.exceed_linear.sum()), "n_exceed_log": int(core.exceed_log.sum()),
                "h2_supported_linear": bool(core.exceed_linear.sum() >= ks),
                "h2_supported_log": bool(core.exceed_log.sum() >= ks),
                "median_rpct_linear": float(core.rpct_linear.median()),
                "direction_lower_tail": bool(core.rpct_linear.median() < 50),
                "negative_control_P": negP, "validity_pass": bool(negP >= vc_min),
                "median_neff_local_pct": float(core.neff_local_pct.median()),
                "breadth_wide": bool(core.neff_local_pct.median() > 50)})
    specs = pd.DataFrame(spec_rows)
    feeders = pd.concat(feeder_rows, ignore_index=True)

    # Primary spec must reproduce the point-estimate module (DL-11).
    pp = pd.read_csv(repo_path("outputs/estimates/point_pairs.csv", root))
    pp = pp[pp.target == "FAMILY"].set_index(["domain", "feeder"])
    prim_f = feeders.merge(specs[specs.is_primary][["domain", "standardization", "weights", "suppress",
                                                    "not_relevant", "feeder_threshold", "family_weights"]])
    prim_f = prim_f.set_index(["domain", "feeder"])
    common = prim_f.index.intersection(pp.index)
    dev = max((prim_f.loc[common, "D"] - pp.loc[common, "D"]).abs().max(),
              (prim_f.loc[common, "P"] - pp.loc[common, "P"]).abs().max(),
              (prim_f.loc[common, "rpct_linear"] - pp.loc[common, "h2_resid_pct_linear"]).abs().max())
    if dev > 1e-8 or len(common) != 13 * len(domains):
        raise RuntimeError(f"primary multiverse spec does not reproduce point_pairs.csv (max dev {dev}, n {len(common)})")

    prim_dec = specs[specs.is_primary].set_index("domain")
    summ = []
    for d, g in specs.groupby("domain"):
        p = prim_dec.loc[d]
        summ.append({"domain": d, "n_specs": len(g),
                     "share_h2_supported_linear": g.h2_supported_linear.mean(),
                     "share_h2_supported_log": g.h2_supported_log.mean(),
                     "share_direction_lower_tail (exploratory)": g.direction_lower_tail.mean(),
                     "share_validity_pass": g.validity_pass.mean(),
                     "share_breadth_wide (exploratory)": g.breadth_wide.mean(),
                     "agreement_h2_linear_with_primary": (g.h2_supported_linear == p.h2_supported_linear).mean(),
                     "agreement_validity_with_primary": (g.validity_pass == p.validity_pass).mean(),
                     "median_n_exceed_linear": g.n_exceed_linear.median(),
                     "max_n_exceed_linear": g.n_exceed_linear.max(),
                     "median_of_median_rpct_linear": g.median_rpct_linear.median()})
    summary = pd.DataFrame(summ)
    key = ["domain", "standardization", "weights", "suppress", "not_relevant", "feeder_threshold", "family_weights"]
    fv = feeders.merge(specs[key + ["validity_pass"]], on=key)
    h1 = (fv[(fv.role == "feeder") & fv.validity_pass]
          .assign(close=lambda x: x.P <= h1_thr)
          .groupby(["domain", "feeder"]).agg(n_valid_specs=("close", "size"), share_P_le_25=("close", "mean"),
                                             median_P=("P", "median"), min_P=("P", "min"), max_P=("P", "max"))
          .reset_index())

    out = repo_path("outputs/multiverse", root)
    out.mkdir(parents=True, exist_ok=True)
    specs.to_csv(out / "multiverse_specs.csv", index=False)
    feeders.to_csv(out / "multiverse_feeders.csv", index=False)
    summary.to_csv(out / "multiverse_summary.csv", index=False)
    h1.to_csv(out / "multiverse_h1.csv", index=False)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    md = [f"# Multiverse summary (DL-11)\n\nGenerated: {ts}. {len(grid)} specs per domain, family target, point estimates. "
          f"Primary spec reproduces point_pairs.csv (max dev {dev:.1e}).\n",
          "## Shares across specifications\n", summary.round(3).to_markdown(index=False),
          "\n\n## H1 point rule (P <= 25) — validity-passing specs only\n",
          h1.sort_values(["domain", "median_P"]).round(3).to_markdown(index=False)]
    (out / "multiverse_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"specs": specs, "feeders": feeders, "summary": summary, "h1": h1}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    res = run(load_config(args.config))
    pd.set_option("display.width", 250)
    print(res["summary"].round(3).T.to_string(header=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
