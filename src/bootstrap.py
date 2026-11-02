"""Parametric bootstrap of the primary specification (prereg uncertainty.bootstrap; DL-10).

Each draw perturbs every Level and Importance rating with a truncated normal centred on the
published value with its published SE (K rows without SE: imputed, prereg D2), then recomputes
z, all profiles, the reference distribution, both C–D fits and q95. pi (OEWS employment) is fixed.

Outputs (outputs/estimates/):
  bootstrap_pairs.csv     point + 95% intervals for D, P, C, H2 residual percentiles; H2 exceedance shares
  h1_decisions.csv        H1 rule (97.5th pct of P <= 25) for feeder -> FAMILY, with interpretability flag and the
                          bootstrap p-value p = (#draws with P > 25 + 1) / (B + 1) used by the FDR check (DL-32)
  h1_group_test.csv       exact permutation test (DL-8) + bootstrap share of draws with diff < 0
  neff_exploratory.csv    EXPLORATORY N_eff (DL-9) with intervals and reference percentiles
  bootstrap_meta.csv      B, seed, imputation counts, Monte Carlo error, centering diagnostics
  bootstrap_summary.md

Usage:
    python -m src.bootstrap [--config config/prereg.yaml] [--draws N]   # --draws overrides B for smoke tests only
"""
from __future__ import annotations

import argparse
import itertools
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
from scipy.stats import truncnorm

from .config import REPO_ROOT, load_config, repo_path
from .deficit import concentration, contributions, importance_weights, ols_fit, total_deficit, zscore
from .frame import frame_table, resolve_codes
from .profiles import FAMILY

LOCAL_K = 100


# ----------------------------------------------------------------------------- data
@dataclass
class DomainArrays:
    domain: str
    codes: np.ndarray
    elements: np.ndarray
    L: np.ndarray
    I: np.ndarray
    seL: np.ndarray
    seI: np.ndarray
    n_imputed: int


def impute_missing_se(se: pd.DataFrame, source: pd.Series, reference_source: str = "Incumbent") -> tuple[pd.DataFrame, int]:
    """Fill missing SE with the median SE of `reference_source`-rated occupations, per element (one scale)."""
    missing = se.isna()
    n = int(missing.to_numpy().sum())
    if n == 0:
        return se, 0
    ref_rows = source.reindex(se.index) == reference_source
    med = se.loc[ref_rows].median(axis=0)
    if med.isna().any():
        raise ValueError(f"no {reference_source} SE available for elements {med[med.isna()].index.tolist()}")
    return se.fillna(med), n


def load_arrays(con: duckdb.DuckDBPyConnection, domain: str, cfg: dict[str, Any]) -> DomainArrays:
    lv = cfg["measurement"]["scales"]["level"]["id"]
    im = cfg["measurement"]["scales"]["importance"]["id"]
    r = con.execute("SELECT onet_code, element_id, scale_id, data_value, se, domain_source "
                    "FROM onet_ratings WHERE domain = ?", [domain]).df()
    piv = lambda s, v: r[r.scale_id == s].pivot(index="onet_code", columns="element_id", values=v)
    L = piv(lv, "data_value").sort_index()
    I = piv(im, "data_value").loc[L.index, L.columns]
    seL = piv(lv, "se").loc[L.index, L.columns]
    seI = piv(im, "se").loc[L.index, L.columns]
    source = r.drop_duplicates("onet_code").set_index("onet_code")["domain_source"]
    if domain == "K":
        seL, nL = impute_missing_se(seL, source)
        seI, nI = impute_missing_se(seI, source)
    else:
        nL = nI = 0
    if seL.isna().any().any() or seI.isna().any().any():
        raise ValueError(f"domain {domain}: missing SE outside the pre-registered imputation scope")
    return DomainArrays(domain, L.index.to_numpy(), L.columns.to_numpy(), L.to_numpy(), I.to_numpy(),
                        seL.to_numpy(), seI.to_numpy(), nL + nI)


# ----------------------------------------------------------------------------- spec
@dataclass
class Spec:
    target_names: list[str]
    target_members: list[np.ndarray]     # row indices
    target_mix: list[np.ndarray]         # mixing weights over members (sum to 1)
    feeder_names: list[str]
    feeder_roles: list[str]
    feeder_members: list[np.ndarray]
    family_index: int


def build_spec(arr: DomainArrays, cfg: dict[str, Any], employment: pd.Series) -> Spec:
    pos = {c: i for i, c in enumerate(arr.codes)}
    frame = frame_table(cfg)
    prim = lambda soc: np.array([pos[c] for c, t in resolve_codes(soc, cfg) if t == "primary"])
    t_names, t_mem, t_mix = [], [], []
    core = cfg["frame"]["targets_core"]
    emp = employment.reindex(core).to_numpy(dtype=float)
    pi = emp / emp.sum()
    fam_mem = np.concatenate([prim(t) for t in core])
    t_names.append(FAMILY); t_mem.append(fam_mem); t_mix.append(pi)
    f_names, f_roles, f_mem = [], [], []
    for rec in frame.itertuples(index=False):
        idx = prim(rec.soc6)
        if rec.role.startswith("target"):
            if len(idx) != 1:
                raise ValueError(f"target {rec.soc6} must map to exactly one primary code")
            t_names.append(rec.soc6); t_mem.append(idx); t_mix.append(np.ones(1))
        else:
            f_names.append(rec.soc6); f_roles.append(rec.role); f_mem.append(idx)
    return Spec(t_names, t_mem, t_mix, f_names, f_roles, f_mem, 0)


# ----------------------------------------------------------------------------- evaluation
def _neff(c: np.ndarray) -> np.ndarray:
    tot = c.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        s = c / tot[:, None]
        out = 1.0 / np.sum(s ** 2, axis=1)
    return np.where(tot > 0, out, np.nan)


def evaluate(L: np.ndarray, I: np.ndarray, spec: Spec, m: int) -> dict[str, np.ndarray]:
    Z, _, _ = zscore(L)
    W = importance_weights(I)
    n = Z.shape[0]
    T, F = len(spec.target_names), len(spec.feeder_names)
    Zf = np.stack([Z[idx].mean(axis=0) for idx in spec.feeder_members])
    out = {k: np.full((T, F), np.nan) for k in
           ("D", "P", "C", "rpct_linear", "rpct_log", "exceed_linear", "exceed_log")}
    for t in range(T):
        mem, mix = spec.target_members[t], spec.target_mix[t]
        z_t = mix @ Z[mem]
        w_t = mix @ W[mem]
        ref = np.ones(n, dtype=bool); ref[mem] = False
        c_ref = contributions(z_t, w_t, Z[ref])
        D_ref = total_deficit(c_ref, w_t)
        C_ref = concentration(c_ref, m)
        c_f = contributions(z_t, w_t, Zf)
        D_f = total_deficit(c_f, w_t)
        C_f = concentration(c_f, m)
        out["D"][t], out["C"][t] = D_f, C_f
        out["P"][t] = 100.0 * (D_ref[None, :] <= D_f[:, None]).mean(axis=1)
        ok = D_ref > 0
        for form in ("linear", "log"):
            x_ref = D_ref[ok] if form == "linear" else np.log(D_ref[ok])
            a, b = ols_fit(x_ref, C_ref[ok])
            res_ref = C_ref[ok] - (a + b * x_ref)
            with np.errstate(divide="ignore"):
                x_f = D_f if form == "linear" else np.log(D_f)
            res_f = np.where(D_f > 0, C_f - (a + b * x_f), np.nan)
            out[f"rpct_{form}"][t] = 100.0 * (res_ref[None, :] <= res_f[:, None]).mean(axis=1)
            out[f"exceed_{form}"][t] = res_f > np.quantile(res_ref, 0.95)
        if t == spec.family_index:
            ne_ref, ne_f = _neff(c_ref), _neff(c_f)
            valid = ~np.isnan(ne_ref)
            out["neff"] = ne_f
            out["neff_pct"] = 100.0 * (ne_ref[valid][None, :] <= ne_f[:, None]).mean(axis=1)
            loc = np.empty(F)
            for j in range(F):
                nb = np.argsort(np.abs(D_ref - D_f[j]))[:LOCAL_K]
                nb = nb[valid[nb]]
                loc[j] = 100.0 * float(np.mean(ne_ref[nb] <= ne_f[j]))
            out["neff_local_pct"] = loc
    return out


def sample_truncnorm(values: np.ndarray, se: np.ndarray, lo: float, hi: float,
                     rng: np.random.Generator) -> np.ndarray:
    out = values.astype(float).copy()
    mask = se > 0
    loc, sc = values[mask], se[mask]
    out[mask] = truncnorm.rvs((lo - loc) / sc, (hi - loc) / sc, loc=loc, scale=sc, random_state=rng)
    return out


# ----------------------------------------------------------------------------- permutation (DL-8)
H1_GROUPS = {
    "machining_setup": ["51-4031", "51-4041", "51-4081", "51-9161", "51-4072"],
    "welding": ["51-4121", "51-4122"],
    "assembly": ["51-2090", "51-2031", "51-2028"],
}


def group_diff(P: pd.Series) -> float:
    mw = H1_GROUPS["machining_setup"] + H1_GROUPS["welding"]
    return float(P[mw].mean() - P[H1_GROUPS["assembly"]].mean())


def exact_permutation_p(P: pd.Series) -> tuple[float, float, int]:
    """One-sided p for 'machining/welding closer' (diff <= observed) over all C(10,3) relabelings."""
    pool = H1_GROUPS["machining_setup"] + H1_GROUPS["welding"] + H1_GROUPS["assembly"]
    obs = group_diff(P)
    vals = P[pool].to_numpy()
    k = len(H1_GROUPS["assembly"])
    diffs = []
    for asm in itertools.combinations(range(len(pool)), k):
        mask = np.zeros(len(pool), dtype=bool); mask[list(asm)] = True
        diffs.append(vals[~mask].mean() - vals[mask].mean())
    diffs = np.array(diffs)
    return obs, float(np.mean(diffs <= obs + 1e-12)), len(diffs)


# ----------------------------------------------------------------------------- run
def run(cfg: dict[str, Any], root: Path = REPO_ROOT, draws: int | None = None) -> dict[str, Any]:
    bcfg = cfg["uncertainty"]["bootstrap"]
    B = int(draws or bcfg["B"])
    m = cfg["estimands"]["primary"]["top_m"]
    lv, im = cfg["measurement"]["scales"]["level"], cfg["measurement"]["scales"]["importance"]
    with duckdb.connect(str(repo_path(cfg["paths"]["duckdb"], root)), read_only=True) as con:
        employment = con.execute("SELECT OCC_CODE, TOT_EMP FROM oews_3363").df().set_index("OCC_CODE")["TOT_EMP"]
        domains = [r[0] for r in con.execute("SELECT DISTINCT domain FROM onet_ratings ORDER BY 1").fetchall()]
        arrays = {d: load_arrays(con, d, cfg) for d in domains}
    specs = {d: build_spec(a, cfg, employment) for d, a in arrays.items()}
    point = {d: evaluate(a.L, a.I, specs[d], m) for d, a in arrays.items()}

    # Consistency with the point-estimate module (same data, independent code path).
    pp = pd.read_csv(repo_path("outputs/estimates/point_pairs.csv", root))
    max_dev = 0.0
    for d, sp in specs.items():
        for ti, t in enumerate(sp.target_names):
            for fi, f in enumerate(sp.feeder_names):
                row = pp[(pp.domain == d) & (pp.target == t) & (pp.feeder == f)].iloc[0]
                max_dev = max(max_dev, abs(row.D - point[d]["D"][ti, fi]), abs(row.P - point[d]["P"][ti, fi]),
                              abs(row.h2_resid_pct_linear - point[d]["rpct_linear"][ti, fi]))
    if max_dev > 1e-8:
        raise RuntimeError(f"bootstrap point evaluation disagrees with point_pairs.csv (max dev {max_dev})")

    rng = np.random.default_rng(bcfg["seed"])
    store = {d: {k: [] for k in point[d]} for d in domains}
    t0 = time.time()
    for b in range(B):
        for d in domains:
            a = arrays[d]
            Ls = sample_truncnorm(a.L, a.seL, lv["min"], lv["max"], rng)
            Is = sample_truncnorm(a.I, a.seI, im["min"], im["max"], rng)
            res = evaluate(Ls, Is, specs[d], m)
            for k, v in res.items():
                store[d][k].append(v)
    elapsed = time.time() - t0
    store = {d: {k: np.stack(v) for k, v in s.items()} for d, s in store.items()}

    half = B // 2
    q = lambda x, p: np.nanquantile(x, p, axis=0)
    rows, h1_rows, neff_rows, grp_rows, cent = [], [], [], [], []
    vc_min = cfg["decision_rules"]["validity_check"]["negative_control_min_percentile"]
    h1_thr = next(s["threshold_upper_ci_percentile"] for s in cfg["estimands"]["secondary"] if s["id"] == "H1")
    for d in domains:
        sp, pt, bs = specs[d], point[d], store[d]
        for ti, t in enumerate(sp.target_names):
            for fi, f in enumerate(sp.feeder_names):
                r = {"domain": d, "target": t, "feeder": f, "feeder_role": sp.feeder_roles[fi]}
                for k in ("D", "P", "C", "rpct_linear", "rpct_log"):
                    x = bs[k][:, ti, fi]
                    r[f"{k}_point"] = pt[k][ti, fi]
                    r[f"{k}_lo"], r[f"{k}_hi"] = np.nanquantile(x, 0.025), np.nanquantile(x, 0.975)
                r["D_boot_mean"] = float(np.nanmean(bs["D"][:, ti, fi]))
                r["P_hi_mc_se"] = abs(np.nanquantile(bs["P"][:half, ti, fi], .975)
                                      - np.nanquantile(bs["P"][half:, ti, fi], .975)) / 2
                for form in ("linear", "log"):
                    r[f"exceed_{form}_point"] = bool(pt[f"exceed_{form}"][ti, fi])
                    sh = float(np.mean(bs[f"exceed_{form}"][:, ti, fi]))
                    r[f"exceed_{form}_share"] = sh
                    r[f"exceed_{form}_share_mc_se"] = float(np.sqrt(sh * (1 - sh) / B))
                rows.append(r)
        fam = sp.family_index
        negP = pt["P"][fam, sp.feeder_roles.index("negative_control")]
        interpretable = negP >= vc_min
        for fi, f in enumerate(sp.feeder_names):
            n_above = int(np.sum(bs["P"][:, fam, fi] > h1_thr))
            h1_rows.append({"domain": d, "feeder": f, "feeder_role": sp.feeder_roles[fi],
                            "P_point": pt["P"][fam, fi], "P_hi": np.nanquantile(bs["P"][:, fam, fi], .975),
                            "close_rule": bool(np.nanquantile(bs["P"][:, fam, fi], .975) <= h1_thr),
                            "domain_interpretable": bool(interpretable),
                            # bootstrap p-value of 'not close' (P > threshold); input to the FDR check (DL-32)
                            "n_draws_P_above_thr": n_above, "p_one_sided": (n_above + 1) / (B + 1)})
            neff_rows.append({"domain": d, "feeder": f, "feeder_role": sp.feeder_roles[fi],
                              "neff_point": pt["neff"][fi], "neff_lo": np.nanquantile(bs["neff"][:, fi], .025),
                              "neff_hi": np.nanquantile(bs["neff"][:, fi], .975),
                              "n_elements_in_domain": len(arrays[d].elements),
                              "neff_pct_reference": pt["neff_pct"][fi],
                              "neff_pct_reference_lo": np.nanquantile(bs["neff_pct"][:, fi], .025),
                              "neff_pct_reference_hi": np.nanquantile(bs["neff_pct"][:, fi], .975),
                              "neff_pct_local": pt["neff_local_pct"][fi],
                              "neff_pct_local_lo": np.nanquantile(bs["neff_local_pct"][:, fi], .025),
                              "neff_pct_local_hi": np.nanquantile(bs["neff_local_pct"][:, fi], .975),
                              "label": "EXPLORATORY (DL-9)"})
        Pser = pd.Series(pt["P"][fam], index=sp.feeder_names)
        obs, pval, nperm = exact_permutation_p(Pser)
        boot_d = np.array([group_diff(pd.Series(bs["P"][b, fam], index=sp.feeder_names)) for b in range(B)])
        sub = {g: float(Pser[c].mean()) for g, c in H1_GROUPS.items()}
        grp_rows.append({"domain": d, "diff_mean_P_mw_minus_asm": obs, "exact_p_one_sided": pval,
                         "n_permutations": nperm, "boot_share_diff_lt_0": float(np.mean(boot_d < 0)),
                         "diff_lo": np.quantile(boot_d, .025), "diff_hi": np.quantile(boot_d, .975),
                         **{f"mean_P_{g}": v for g, v in sub.items()},
                         "domain_interpretable": bool(interpretable), "label": "not blind (DL-8)"})
        Dp, Db = pt["D"][fam], bs["D"][:, fam].mean(axis=0)
        cent.append(f"{d}: median (boot mean D − point D) = {np.median(Db - Dp):+.4f}, max |.| = {np.max(np.abs(Db - Dp)):.4f}")

    pairs, h1, neff, grp = map(pd.DataFrame, (rows, h1_rows, neff_rows, grp_rows))
    meta = pd.DataFrame([{"B": B, "seed": bcfg["seed"], "seconds": round(elapsed, 1),
                          "se_imputed_K_cells": arrays["K"].n_imputed if "K" in arrays else 0,
                          "point_consistency_max_dev": max_dev, "centering": " | ".join(cent),
                          "max_P_hi_mc_se": float(pairs["P_hi_mc_se"].max())}])
    out = repo_path("outputs/estimates", root)
    pairs.to_csv(out / "bootstrap_pairs.csv", index=False)
    h1.to_csv(out / "h1_decisions.csv", index=False)
    grp.to_csv(out / "h1_group_test.csv", index=False)
    neff.to_csv(out / "neff_exploratory.csv", index=False)
    meta.to_csv(out / "bootstrap_meta.csv", index=False)
    (out / "bootstrap_summary.md").write_text(render(pairs, h1, grp, neff, meta), encoding="utf-8")
    return {"pairs": pairs, "h1": h1, "grp": grp, "neff": neff, "meta": meta}


def render(pairs, h1, grp, neff, meta) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fam = pairs[(pairs.target == FAMILY) & (pairs.feeder_role == "feeder_core")]
    h2 = fam.groupby("domain").agg(n_exceed_point_linear=("exceed_linear_point", "sum"),
                                   n_exceed_point_log=("exceed_log_point", "sum"),
                                   mean_share_exceed_linear=("exceed_linear_share", "mean"),
                                   mean_share_exceed_log=("exceed_log_share", "mean"),
                                   max_share_exceed_linear=("exceed_linear_share", "max")).reset_index()
    core_h1 = h1[h1.feeder_role.isin(["feeder_core", "negative_control"])].sort_values(["domain", "P_point"])
    parts = [f"# Bootstrap results (primary specification)\n\nGenerated: {ts}  \n"
             f"B = {int(meta.B[0])}, seed = {int(meta.seed[0])}, {meta.seconds[0]} s; "
             f"SE imputed for {int(meta.se_imputed_K_cells[0])} K cells (prereg D2).  \n"
             f"Point-path consistency max deviation: {meta.point_consistency_max_dev[0]:.2e}.  \n"
             f"Centering: {meta.centering[0]}  \nMax Monte Carlo SE of P upper bound: {meta.max_P_hi_mc_se[0]:.2f}\n",
             "## H2 (registered: point rule; bootstrap share = uncertainty)\n", h2.round(3).to_markdown(index=False),
             "\n\n## H1: feeder -> family, 97.5th percentile of P (close if <= 25)\n",
             core_h1.round(2).to_markdown(index=False),
             "\n\n## H1-group (DL-8, not blind)\n", grp.round(4).to_markdown(index=False),
             "\n\n## N_eff — EXPLORATORY (DL-9)\n",
             neff[neff.feeder_role == "feeder_core"].round(2).to_markdown(index=False)]
    return "\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    ap.add_argument("--draws", type=int, default=None, help="override B (smoke tests only)")
    args = ap.parse_args(argv)
    res = run(load_config(args.config), draws=args.draws)
    print(res["meta"].T.to_string(header=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
