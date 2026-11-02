"""Sensitivity analyses requested in expert review (deviation log DL-15 – DL-20).

  copula     DL-15a  Gaussian-copula errors, R = cross-occupation correlation of ratings (seed 20261004)
  comonotone DL-15b  rho = 1 errors within occupation x domain x scale (seed 20261005)
  mi_se      DL-19   multiple-imputation SEs for Knowledge, + DL-18 breadth alternatives (seed 20261006)
  distances  DL-16   continuous distances (directional D, weighted Euclidean, Ledoit-Wolf Mahalanobis)
  abilities  DL-17   Abilities subgroups (cognitive / psychomotor / physical / sensory) + classical MDS map
  vintage    DL-20   drop occupations rated before 2018

Bootstrap variants share everything with src.bootstrap except the error model. The registered
bootstrap is not re-run here; its results are read from outputs/estimates/bootstrap_pairs.csv.

Outputs: outputs/sensitivity/*.csv, sensitivity_summary.md
Usage:   python -m src.sensitivity --part bootstrap_copula|bootstrap_comonotone|bootstrap_mi|point|summary|all
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr, truncnorm
from sklearn.covariance import LedoitWolf

from .bootstrap import Spec, build_spec, evaluate, load_arrays
from .config import REPO_ROOT, load_config, repo_path
from .deficit import contributions, importance_weights, ols_fit, total_deficit, zscore
from .profiles import FAMILY

SEEDS = {"copula": 20261004, "comonotone": 20261005, "mi_se": 20261006}
TIE_TOL = 1e-12   # D values are O(0.1–2); a feeder's own row in the reference set must count as a tie (DL-22)


def pct(ref: np.ndarray, x: float) -> float:
    """Percentile with a floating-point tie tolerance: 100 * share of ref <= x."""
    ref = np.asarray(ref, float)
    return 100.0 * float(np.mean(ref <= x + TIE_TOL))
A_GROUPS = {"cognitive": "1.A.1", "psychomotor": "1.A.2", "physical": "1.A.3", "sensory": "1.A.4"}


def out_dir(root: Path) -> Path:
    p = repo_path("outputs/sensitivity", root)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ----------------------------------------------------------------------------- data
def load_all(cfg: dict[str, Any], root: Path):
    with duckdb.connect(str(repo_path(cfg["paths"]["duckdb"], root)), read_only=True) as con:
        emp = con.execute("SELECT OCC_CODE, TOT_EMP FROM oews_3363").df().set_index("OCC_CODE")["TOT_EMP"]
        arrays = {d: load_arrays(con, d, cfg) for d in ("A", "K", "S")}
        raw = con.execute("SELECT domain, onet_code, element_id, scale_id, se, domain_source, date_year "
                          "FROM onet_ratings").df()
    specs = {d: build_spec(a, cfg, emp) for d, a in arrays.items()}
    return arrays, specs, raw, emp


# ----------------------------------------------------------------------------- samplers
def corr_matrix(X: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):   # zero-variance columns -> NaN -> 0
        R = np.corrcoef(X, rowvar=False)
    R = np.nan_to_num(R, nan=0.0)
    np.fill_diagonal(R, 1.0)
    w, V = np.linalg.eigh(R)                       # nearest PSD, then re-normalize
    R = (V * np.clip(w, 1e-8, None)) @ V.T
    d = np.sqrt(np.diag(R))
    return R / np.outer(d, d)


def draw_truncnorm(values, se, lo, hi, z):
    """Truncated-normal marginals from standard-normal scores z (copula draw)."""
    out = values.astype(float).copy()
    m = se > 0
    a, b = (lo - values[m]) / se[m], (hi - values[m]) / se[m]
    u = np.clip(norm.cdf(z[m]), 1e-12, 1 - 1e-12)
    out[m] = truncnorm.ppf(u, a, b, loc=values[m], scale=se[m])
    return out


def impute_pools(raw: pd.DataFrame, arr, cfg) -> dict[str, Any]:
    """Missing-SE mask and per-element pools of incumbent SEs (Knowledge only)."""
    lv = cfg["measurement"]["scales"]["level"]["id"]; im = cfg["measurement"]["scales"]["importance"]["id"]
    k = raw[raw.domain == "K"]
    out = {}
    for sc, key in ((lv, "L"), (im, "I")):
        piv = k[k.scale_id == sc].pivot(index="onet_code", columns="element_id", values="se").loc[arr.codes, arr.elements]
        src = k.drop_duplicates("onet_code").set_index("onet_code").domain_source.reindex(arr.codes)
        pools = [piv.loc[(src == "Incumbent").to_numpy(), e].dropna().to_numpy() for e in arr.elements]
        out[key] = (piv.isna().to_numpy(), pools)
    return out


# ----------------------------------------------------------------------------- breadth (DL-18)
def breadth(L: np.ndarray, I: np.ndarray, spec: Spec) -> tuple[np.ndarray, np.ndarray]:
    Z, _, _ = zscore(L)
    W = importance_weights(I)
    fam = spec.family_index
    z_t = spec.target_mix[fam] @ Z[spec.target_members[fam]]
    w_t = spec.target_mix[fam] @ W[spec.target_members[fam]]
    Zf = np.stack([Z[idx].mean(axis=0) for idx in spec.feeder_members])
    c = contributions(z_t, w_t, Zf)
    s = c / c.sum(axis=1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        expH = np.exp(-np.nansum(np.where(s > 0, s * np.log(s), 0.0), axis=1))
    cs = np.cumsum(-np.sort(-s, axis=1), axis=1)
    k80 = (cs < 0.8).sum(axis=1) + 1
    return expH, k80.astype(float)


# ----------------------------------------------------------------------------- bootstrap variants
def run_bootstrap_variant(cfg, root, variant: str, B: int | None = None, suffix: str = "") -> pd.DataFrame:
    arrays, specs, raw, _ = load_all(cfg, root)
    lv, im = cfg["measurement"]["scales"]["level"], cfg["measurement"]["scales"]["importance"]
    B = int(B or cfg["uncertainty"]["bootstrap"]["B"])
    m = cfg["estimands"]["primary"]["top_m"]
    rng = np.random.default_rng(SEEDS[variant])
    chol = {}
    if variant == "copula":
        for d, a in arrays.items():
            chol[d] = (np.linalg.cholesky(corr_matrix(a.L)), np.linalg.cholesky(corr_matrix(a.I)))
    pools = impute_pools(raw, arrays["K"], cfg) if variant == "mi_se" else None
    store = {d: {"P": [], "exceed_linear": [], "expH": [], "k80": [], "neff": []} for d in arrays}
    t0 = time.time()
    for _ in range(B):
        for d, a in arrays.items():
            n, E = a.L.shape
            seL, seI = a.seL, a.seI
            if variant == "mi_se" and d == "K":
                seL, seI = seL.copy(), seI.copy()
                for key, se in (("L", seL), ("I", seI)):
                    miss, pl = pools[key]
                    for j in range(E):
                        rows = np.where(miss[:, j])[0]
                        if len(rows):
                            se[rows, j] = rng.choice(pl[j], size=len(rows), replace=True)
            if variant == "copula":
                zL = rng.standard_normal((n, E)) @ chol[d][0].T
                zI = rng.standard_normal((n, E)) @ chol[d][1].T
            elif variant == "comonotone":
                zL = np.repeat(rng.standard_normal((n, 1)), E, axis=1)
                zI = np.repeat(rng.standard_normal((n, 1)), E, axis=1)
            else:
                zL, zI = rng.standard_normal((n, E)), rng.standard_normal((n, E))
            Ls = draw_truncnorm(a.L, seL, lv["min"], lv["max"], zL)
            Is = draw_truncnorm(a.I, seI, im["min"], im["max"], zI)
            res = evaluate(Ls, Is, specs[d], m)
            fam = specs[d].family_index
            store[d]["P"].append(res["P"][fam]); store[d]["exceed_linear"].append(res["exceed_linear"][fam])
            store[d]["neff"].append(res["neff"])
            if variant == "mi_se":
                eh, k8 = breadth(Ls, Is, specs[d])
                store[d]["expH"].append(eh); store[d]["k80"].append(k8)
    rows = []
    for d, st in store.items():
        sp = specs[d]
        P = np.stack(st["P"]); EX = np.stack(st["exceed_linear"]); NE = np.stack(st["neff"])
        for fi, f in enumerate(sp.feeder_names):
            r = {"variant": variant, "domain": d, "feeder": f, "role": sp.feeder_roles[fi], "B": B, "seed": SEEDS[variant],
                 "P_lo": np.quantile(P[:, fi], .025), "P_hi": np.quantile(P[:, fi], .975),
                 "exceed_linear_share": float(EX[:, fi].mean()),
                 "neff_lo": np.nanquantile(NE[:, fi], .025), "neff_hi": np.nanquantile(NE[:, fi], .975)}
            if variant == "mi_se":
                EH, K8 = np.stack(st["expH"]), np.stack(st["k80"])
                r.update({"expH_lo": np.nanquantile(EH[:, fi], .025), "expH_hi": np.nanquantile(EH[:, fi], .975),
                          "k80_lo": np.nanquantile(K8[:, fi], .025), "k80_hi": np.nanquantile(K8[:, fi], .975)})
            rows.append(r)
    df = pd.DataFrame(rows).assign(seconds=round(time.time() - t0, 1))
    df.to_csv(out_dir(root) / f"bootstrap_{variant}{suffix}.csv", index=False)
    return df


# ----------------------------------------------------------------------------- point analyses
def distances(cfg, root) -> pd.DataFrame:
    arrays, specs, _, _ = load_all(cfg, root)
    pp = pd.read_csv(repo_path("outputs/estimates/point_pairs.csv", root))
    rows = []
    for d, a in arrays.items():
        sp = specs[d]
        Z, _, _ = zscore(a.L); W = importance_weights(a.I)
        fam = sp.family_index
        z_t = sp.target_mix[fam] @ Z[sp.target_members[fam]]; w_t = sp.target_mix[fam] @ W[sp.target_members[fam]]
        ref = np.ones(len(a.codes), bool); ref[sp.target_members[fam]] = False
        Zr = Z[ref]
        Zf = np.stack([Z[idx].mean(axis=0) for idx in sp.feeder_members])
        gap_r, gap_f = z_t[None, :] - Zr, z_t[None, :] - Zf
        metrics = {
            "D (registered)": (total_deficit(contributions(z_t, w_t, Zr), w_t), total_deficit(contributions(z_t, w_t, Zf), w_t)),
            "weighted Euclidean (non-directional)": (np.sqrt((w_t * gap_r ** 2).sum(1) / w_t.sum()),
                                                     np.sqrt((w_t * gap_f ** 2).sum(1) / w_t.sum())),
        }
        Sinv = np.linalg.inv(LedoitWolf().fit(Zr).covariance_)
        mah = lambda G: np.sqrt(np.einsum("ij,jk,ik->i", G, Sinv, G))
        metrics["Mahalanobis, Ledoit-Wolf (non-directional)"] = (mah(gap_r), mah(gap_f))
        Dref_f = metrics["D (registered)"][1]
        for name, (vr, vf) in metrics.items():
            for fi, f in enumerate(sp.feeder_names):
                rows.append({"domain": d, "metric": name, "feeder": f, "role": sp.feeder_roles[fi],
                             "value": vf[fi], "percentile": pct(vr, vf[fi])})
        sub = pd.DataFrame([r for r in rows if r["domain"] == d])
        core = [i for i, rr in enumerate(sp.feeder_roles) if rr == "feeder_core"]
        for name, (vr, vf) in metrics.items():
            rho = spearmanr(vf[core], Dref_f[core]).statistic
            rows.append({"domain": d, "metric": name, "feeder": "__spearman_vs_D_core__", "role": "summary",
                         "value": float(rho), "percentile": np.nan})
    df = pd.DataFrame(rows)
    # registered D path must match point_pairs
    chk = df[(df.metric == "D (registered)") & (df.role != "summary")].merge(
        pp[pp.target == FAMILY][["domain", "feeder", "P"]], on=["domain", "feeder"])
    assert np.allclose(chk.percentile, chk.P), "distance module does not reproduce registered P"
    df.to_csv(out_dir(root) / "distances.csv", index=False)
    return df


def abilities_groups(cfg, root) -> tuple[pd.DataFrame, pd.DataFrame]:
    arrays, specs, _, _ = load_all(cfg, root)
    a, sp = arrays["A"], specs["A"]
    Z, _, _ = zscore(a.L); W = importance_weights(a.I)
    fam = sp.family_index
    ref = np.ones(len(a.codes), bool); ref[sp.target_members[fam]] = False
    rows = []
    # family profile on the full element set first, then sliced, so the 'all' row reproduces the registered path
    z_full = sp.target_mix[fam] @ Z[sp.target_members[fam]]
    w_full = sp.target_mix[fam] @ W[sp.target_members[fam]]
    Zf_full = np.stack([Z[idx].mean(axis=0) for idx in sp.feeder_members])
    for g, pre in {"all": "1.A", **A_GROUPS}.items():
        cols = np.array([e.startswith(pre + ".") or (g == "all") for e in a.elements])
        z_t, w_t = z_full[cols], w_full[cols]
        Dr = total_deficit(contributions(z_t, w_t, Z[ref][:, cols]), w_t)
        Df = total_deficit(contributions(z_t, w_t, Zf_full[:, cols]), w_t)
        for fi, f in enumerate(sp.feeder_names):
            rows.append({"group": g, "n_elements": int(cols.sum()), "feeder": f, "role": sp.feeder_roles[fi],
                         "D": float(Df[fi]), "P": pct(Dr, float(Df[fi]))})
    df = pd.DataFrame(rows)
    pp = pd.read_csv(repo_path("outputs/estimates/point_pairs.csv", root))
    chk = df[df.group == "all"].merge(pp[(pp.target == FAMILY) & (pp.domain == "A")][["feeder", "P"]], on="feeder")
    assert np.allclose(chk.P_x, chk.P_y), "abilities 'all' path does not reproduce registered P"
    # classical MDS of Abilities z-profiles = PCA of centered z
    Zc = Z - Z.mean(axis=0)
    U, s, _ = np.linalg.svd(Zc, full_matrices=False)
    coords = U[:, :2] * s[:2]
    role = np.array(["other"] * len(a.codes), dtype=object)
    role[sp.target_members[fam]] = "maintenance target"
    for fi, idx in enumerate(sp.feeder_members):
        role[idx] = sp.feeder_roles[fi]
    mds = pd.DataFrame({"onet_code": a.codes, "dim1": coords[:, 0], "dim2": coords[:, 1], "role": role,
                        "var_explained_dim1": s[0] ** 2 / (s ** 2).sum(), "var_explained_dim2": s[1] ** 2 / (s ** 2).sum()})
    df.to_csv(out_dir(root) / "abilities_subgroups.csv", index=False)
    mds.to_csv(out_dir(root) / "abilities_mds.csv", index=False)
    return df, mds


def vintage(cfg, root, min_year: int = 2018) -> pd.DataFrame:
    arrays, specs, raw, emp = load_all(cfg, root)
    years = raw.groupby("onet_code").date_year.min()
    m = cfg["estimands"]["primary"]["top_m"]
    rows = []
    for d, a in arrays.items():
        keep = np.array([years.get(c, 0) >= min_year for c in a.codes])
        codes = a.codes[keep]; pos = {c: i for i, c in enumerate(codes)}
        sp0 = specs[d]
        tm = [np.array([pos[a.codes[i]] for i in mem]) for mem in sp0.target_members]
        fm, fn, fr = [], [], []
        for idx, nme, rl in zip(sp0.feeder_members, sp0.feeder_names, sp0.feeder_roles):
            kept = [pos[a.codes[i]] for i in idx if keep[i]]
            if kept:
                fm.append(np.array(kept)); fn.append(nme); fr.append(rl)
        sp = Spec(sp0.target_names, tm, sp0.target_mix, fn, fr, fm, sp0.family_index)
        res = evaluate(a.L[keep], a.I[keep], sp, m)
        for fi, f in enumerate(fn):
            rows.append({"domain": d, "feeder": f, "role": fr[fi], "n_universe": int(keep.sum()),
                         "P_vintage": res["P"][sp.family_index, fi], "rpct_linear_vintage": res["rpct_linear"][sp.family_index, fi],
                         "exceed_linear_vintage": bool(res["exceed_linear"][sp.family_index, fi])})
    df = pd.DataFrame(rows)
    pp = pd.read_csv(repo_path("outputs/estimates/point_pairs.csv", root))
    df = df.merge(pp[pp.target == FAMILY][["domain", "feeder", "P", "h2_resid_pct_linear"]], on=["domain", "feeder"], how="left")
    if min_year <= 0:   # self-check: no exclusion must reproduce the registered point estimates
        assert np.allclose(df.P_vintage, df.P), "vintage path does not reproduce registered P"
        return df
    df.to_csv(out_dir(root) / "vintage.csv", index=False)
    return df


# ----------------------------------------------------------------------------- summary
def summary(cfg, root) -> str:
    od = out_dir(root)
    reg = pd.read_csv(repo_path("outputs/estimates/bootstrap_pairs.csv", root))
    reg = reg[reg.target == FAMILY][["domain", "feeder", "feeder_role", "P_lo", "P_hi", "exceed_linear_share"]]
    reg = reg.rename(columns={"feeder_role": "role"}).assign(variant="registered (independent, median SE)")
    vs = [pd.read_csv(od / f"bootstrap_{v}.csv") for v in ("copula", "comonotone", "mi_se") if (od / f"bootstrap_{v}.csv").exists()]
    allv = pd.concat([reg] + [v[reg.columns] for v in vs], ignore_index=True)
    allv["P_width"] = allv.P_hi - allv.P_lo
    allv["close_rule"] = allv.P_hi <= 25
    core = allv[allv.role == "feeder_core"]
    s = (core.groupby(["variant", "domain"])
         .agg(n_close=("close_rule", "sum"), median_P_width=("P_width", "median"),
              max_exceed_share=("exceed_linear_share", "max")).reset_index())
    base = core[core.variant.str.startswith("registered")].set_index(["domain", "feeder"]).close_rule
    flips = []
    for v, g in core[~core.variant.str.startswith("registered")].groupby("variant"):
        gg = g.set_index(["domain", "feeder"]).close_rule
        diff = gg[gg != base.reindex(gg.index)]
        flips += [f"{v}: {d} {f} {'→ close' if c else '→ not close'}" for (d, f), c in diff.items()]
    allv.to_csv(od / "uncertainty_models.csv", index=False)
    s.to_csv(od / "uncertainty_summary.csv", index=False)
    md = ["# Sensitivity analyses (DL-15 – DL-20)\n", "## Uncertainty models — core feeders → family\n",
          s.round(3).to_markdown(index=False),
          "\n\nH1 decision changes vs registered: " + ("; ".join(flips) if flips else "none") + "\n"]
    for name in ("distances", "abilities_subgroups", "vintage"):
        p = od / f"{name}.csv"
        if p.exists():
            md += [f"\n## {name}\n", pd.read_csv(p).round(3).to_markdown(index=False)]
    if (od / "bootstrap_mi_se.csv").exists():
        b = pd.read_csv(od / "bootstrap_mi_se.csv")
        md += ["\n## Breadth alternatives (DL-18, inside the DL-19 bootstrap)\n",
               b[b.role == "feeder_core"][["domain", "feeder", "neff_lo", "neff_hi", "expH_lo", "expH_hi", "k80_lo", "k80_hi"]]
               .round(1).to_markdown(index=False)]
    text = "\n".join(md) + "\n"
    (od / "sensitivity_summary.md").write_text(text, encoding="utf-8")
    return text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    ap.add_argument("--part", default="all")
    ap.add_argument("--draws", type=int, default=None, help="override B (smoke tests only)")
    ap.add_argument("--suffix", default="", help="output file suffix (re-execution checks)")
    args = ap.parse_args(argv)
    cfg, root = load_config(args.config), REPO_ROOT
    parts = ["bootstrap_copula", "bootstrap_comonotone", "bootstrap_mi", "point", "summary"] if args.part == "all" else [args.part]
    for p in parts:
        t0 = time.time()
        if p.startswith("bootstrap_"):
            v = {"bootstrap_copula": "copula", "bootstrap_comonotone": "comonotone", "bootstrap_mi": "mi_se"}[p]
            run_bootstrap_variant(cfg, root, v, args.draws, args.suffix)
        elif p == "point":
            distances(cfg, root); abilities_groups(cfg, root); vintage(cfg, root, 0); vintage(cfg, root)
        elif p == "summary":
            print(summary(cfg, root)[:4000])
        print(f"[{p}] {time.time() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
