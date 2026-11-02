"""Element and target robustness of the proximity and concentration results (deviation log DL-27).

No predictive model is fitted in this project, so the overfitting-like risks are (i) a result that holds only
for a particular subset of KSA elements, (ii) one that is carried by one maintenance occupation in the family,
and (iii) an H2 conclusion that depends on the functional form of the C-on-D fit. Four checks, point estimates:

  splits   500 random half-splits of the elements per domain (seed 20261007): P of every frame feeder in each half
  loeo     leave one element out: P of every feeder
  loto     leave one target out of the family (mixing weights renormalized; the removed target rejoins the reference set)
  h2form   polynomial fits of degree 1-3 and a local 95th percentile among the 50/100/200 reference occupations nearest in D

A fifth check applies the registered false-discovery setting (decision_rules.fdr_q) to the H1 decisions (DL-32):
  fdr      Benjamini-Hochberg over the bootstrap p-values of the core feeders, p = (#draws with P > 25 + 1) / (B + 1)
           from src.bootstrap; primary family = the 24 core-feeder tests of the two interpretable domains (S, K),
           with all 36 (S, K, A) and each domain alone as alternatives. A feeder stays close only if the registered
           rule and BH both hold.

z is standardized over the full universe and the family profile is built on the full element set before slicing
(DL-22), so the full element set reproduces the registered P exactly (asserted).

A sixth check adds 49-1011 (first-line supervisors of mechanics, installers and repairers) to the family at its
3363 employment weight (DL-35): it meets the target rule's size and precision thresholds but is not a registered
target, and the registration records no reason. Point P of every frame feeder in Skills and Knowledge.

Outputs: outputs/robustness/element_splits.csv, leave_one_out.csv, h2_forms.csv, domain_summary.csv, fdr_h1.csv,
         family_plus_49_1011.csv
Usage:   python -m src.robustness
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .config import REPO_ROOT, load_config, repo_path
from .deficit import concentration, contributions, importance_weights, total_deficit, zscore
from .profiles import FAMILY
from .sensitivity import load_all, pct

SEED = 20261007
N_SPLITS = 500
LOCAL_K = (50, 100, 200)
FDR_FAMILIES = {"SK": ("S", "K"), "SKA": ("S", "K", "A")}     # SK = interpretable domains (primary family)


def out_dir(root: Path) -> Path:
    p = repo_path("outputs/robustness", root)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _setup(a, sp):
    """z, weights, family profile and reference mask for one domain (registered construction)."""
    Z, _, _ = zscore(a.L)
    W = importance_weights(a.I)
    fam = sp.family_index
    mem, mix = sp.target_members[fam], sp.target_mix[fam]
    Zf = np.stack([Z[idx].mean(axis=0) for idx in sp.feeder_members])
    return Z, W, mem, mix, Zf


def _family(Z, W, mem, mix):
    return mix @ Z[mem], mix @ W[mem]


def _p(z_t, w_t, Zr, Zf, cols) -> np.ndarray:
    Dr = total_deficit(contributions(z_t[cols], w_t[cols], Zr[:, cols]), w_t[cols])
    Df = total_deficit(contributions(z_t[cols], w_t[cols], Zf[:, cols]), w_t[cols])
    return np.array([pct(Dr, x) for x in Df])


def _top3(names: np.ndarray, p: np.ndarray) -> frozenset:
    return frozenset(names[np.argsort(p, kind="stable")[:3]])


def bh_adjust(p) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values (step-up); reject where adjusted p <= q."""
    p = np.asarray(p, dtype=float)
    n = len(p)
    o = np.argsort(p, kind="stable")
    adj = np.minimum.accumulate((p[o] * n / np.arange(1, n + 1))[::-1])[::-1]
    out = np.empty(n)
    out[o] = np.minimum(adj, 1.0)
    return out


def fdr_h1(cfg: dict[str, Any], root: Path = REPO_ROOT, write: bool = True) -> pd.DataFrame:
    """Apply decision_rules.fdr_q (Benjamini-Hochberg) to the H1 core-feeder decisions (DL-32)."""
    q = float(cfg["decision_rules"]["fdr_q"])
    h1 = pd.read_csv(repo_path("outputs/estimates/h1_decisions.csv", root))
    if "p_one_sided" not in h1.columns:
        raise RuntimeError("h1_decisions.csv has no p_one_sided column; re-run python -m src.bootstrap")
    t = h1[h1.feeder_role == "feeder_core"].reset_index(drop=True)
    for name, doms in FDR_FAMILIES.items():
        m = t.domain.isin(doms).to_numpy()
        t.loc[m, f"bh_adj_p_{name}"] = bh_adjust(t.loc[m, "p_one_sided"])
        t[f"n_tests_{name}"] = int(m.sum())
    t["bh_adj_p_domain"] = t.groupby("domain").p_one_sided.transform(lambda s: bh_adjust(s.to_numpy()))
    for name in (*FDR_FAMILIES, "domain"):
        t[f"bh_reject_{name}"] = t[f"bh_adj_p_{name}"] <= q
    t["bonferroni_reject_SK"] = np.where(t.domain.isin(FDR_FAMILIES["SK"]), t.p_one_sided <= q / t.n_tests_SK, False)
    t["close_after_fdr"] = t.close_rule & t.bh_reject_SK & t.domain.isin(FDR_FAMILIES["SK"])
    t["decision_changed_by_fdr"] = t.domain.isin(FDR_FAMILIES["SK"]) & (t.close_rule != t.close_after_fdr)
    t["fdr_q"] = q
    if write:
        t.to_csv(out_dir(root) / "fdr_h1.csv", index=False)
    return t


EXTRA_TARGET = ("49-1011", "49-1011.00")


def family_plus_supervisors(cfg: dict[str, Any], root: Path = REPO_ROOT, write: bool = True) -> pd.DataFrame:
    """Point P of every frame feeder against the family with 49-1011 added at its 3363 employment weight (DL-35)."""
    from .bootstrap import Spec, build_spec, evaluate, load_arrays
    soc, code = EXTRA_TARGET
    m = cfg["estimands"]["primary"]["top_m"]
    with duckdb.connect(str(repo_path(cfg["paths"]["duckdb"], root)), read_only=True) as con:
        emp = con.execute("SELECT OCC_CODE, TOT_EMP FROM oews_3363").df().set_index("OCC_CODE")["TOT_EMP"]
        arrays = {d: load_arrays(con, d, cfg) for d in ("S", "K")}
    core = list(cfg["frame"]["targets_core"])
    w = np.append(emp.reindex(core).to_numpy(dtype=float), float(emp[soc]))
    w = w / w.sum()
    rows = []
    for d, a in arrays.items():
        sp = build_spec(a, cfg, emp)
        base = evaluate(a.L, a.I, sp, m)["P"][sp.family_index]
        pos = {c: i for i, c in enumerate(a.codes)}
        mem = np.append(sp.target_members[sp.family_index], pos[code])
        sp2 = Spec(["FAMILY_PLUS_49_1011"], [mem], [w], sp.feeder_names, sp.feeder_roles, sp.feeder_members, 0)
        alt = evaluate(a.L, a.I, sp2, m)["P"][0]
        for j, f in enumerate(sp.feeder_names):
            rows.append({"domain": d, "feeder": f, "role": sp.feeder_roles[j], "P_registered": base[j],
                         "P_with_49_1011": alt[j], "weight_49_1011": w[-1]})
    t = pd.DataFrame(rows)
    if write:
        t.to_csv(out_dir(root) / "family_plus_49_1011.csv", index=False)
    return t


def run(cfg: dict[str, Any], root: Path = REPO_ROOT, write: bool = True) -> dict[str, pd.DataFrame]:
    arrays, specs, _, _ = load_all(cfg, root)
    with duckdb.connect(str(repo_path(cfg["paths"]["duckdb"], root)), read_only=True) as con:
        en = con.execute("SELECT DISTINCT element_id, element_name FROM onet_ratings").df().set_index("element_id")["element_name"]
    pp = pd.read_csv(repo_path("outputs/estimates/point_pairs.csv", root))
    thr = cfg["estimands"]["secondary"][0]["threshold_upper_ci_percentile"]
    m = cfg["estimands"]["primary"]["top_m"]
    rng = np.random.default_rng(SEED)
    splits, loo, h2, summ = [], [], [], []
    for d in ("S", "K", "A"):
        a, sp = arrays[d], specs[d]
        Z, W, mem, mix, Zf = _setup(a, sp)
        z_t, w_t = _family(Z, W, mem, mix)
        ref = np.ones(len(a.codes), bool); ref[mem] = False
        names = np.array(sp.feeder_names); roles = np.array(sp.feeder_roles)
        core = roles == "feeder_core"
        E = Z.shape[1]
        P0 = _p(z_t, w_t, Z[ref], Zf, np.ones(E, bool))
        reg = pp[(pp.target == FAMILY) & (pp.domain == d)].set_index("feeder").loc[names, "P"].to_numpy()
        assert np.allclose(P0, reg), f"{d}: full element set does not reproduce the registered P"
        top_full = _top3(names[core], P0[core])

        # (a) element split-half
        PH, rho, same = [], [], 0
        for _ in range(N_SPLITS):
            h = np.zeros(E, bool); h[rng.permutation(E)[: E // 2]] = True
            p1, p2 = _p(z_t, w_t, Z[ref], Zf, h), _p(z_t, w_t, Z[ref], Zf, ~h)
            PH += [p1, p2]
            rho.append(spearmanr(p1[core], p2[core]).statistic)
            same += _top3(names[core], p1[core]) == top_full and _top3(names[core], p2[core]) == top_full
        PH, rho = np.array(PH), np.array(rho)
        for j, f in enumerate(names):
            splits.append({"domain": d, "feeder": f, "role": roles[j], "P_registered": P0[j],
                           "share_half_sets_P_le_thr": float((PH[:, j] <= thr).mean()),
                           "P_q05": np.quantile(PH[:, j], .05), "P_q50": np.quantile(PH[:, j], .5),
                           "P_q95": np.quantile(PH[:, j], .95), "n_half_sets": len(PH), "seed": SEED})

        # (b) leave one element out
        loeo = []
        for k in range(E):
            cols = np.arange(E) != k
            p = _p(z_t, w_t, Z[ref], Zf, cols)
            loeo.append(p)
            for j, f in enumerate(names):
                loo.append({"domain": d, "kind": "element", "dropped": a.elements[k], "dropped_name": en.get(a.elements[k], ""),
                            "feeder": f, "role": roles[j], "P": p[j], "P_registered": P0[j]})
        loeo = np.array(loeo)

        # (c) leave one target out
        loto_same = []
        for t in range(len(mem)):
            keep = np.arange(len(mem)) != t
            zt2, wt2 = _family(Z, W, mem[keep], mix[keep] / mix[keep].sum())
            ref2 = np.ones(len(a.codes), bool); ref2[mem[keep]] = False
            p = _p(zt2, wt2, Z[ref2], Zf, np.ones(E, bool))
            loto_same.append(_top3(names[core], p[core]) == top_full)
            for j, f in enumerate(names):
                loo.append({"domain": d, "kind": "target", "dropped": a.codes[mem[t]], "dropped_name": "",
                            "feeder": f, "role": roles[j], "P": p[j], "P_registered": P0[j]})

        # (d) H2 functional form
        cr, cf = contributions(z_t, w_t, Z[ref]), contributions(z_t, w_t, Zf)
        Dr, Df = total_deficit(cr, w_t), total_deficit(cf, w_t)
        Cr, Cf = concentration(cr, m), concentration(cf, m)
        ok = Dr > 0
        Dr, Cr = Dr[ok], Cr[ok]
        ci = np.where(core)[0]
        for deg in (1, 2, 3):
            co = np.polyfit(Dr, Cr, deg)
            q = np.quantile(Cr - np.polyval(co, Dr), .95)
            h2.append({"domain": d, "form": f"polynomial degree {deg}", "n_core_above": int((Cf[ci] - np.polyval(co, Df[ci]) > q).sum()),
                       "n_core": len(ci)})
        for K in LOCAL_K:
            nb = [np.argsort(np.abs(Dr - Df[j]))[:K] for j in ci]
            h2.append({"domain": d, "form": f"local q95, {K} nearest in D",
                       "n_core_above": int(sum(Cf[j] > np.quantile(Cr[n], .95) for j, n in zip(ci, nb))),
                       "n_core_below_local_median": int(sum(Cf[j] < np.median(Cr[n]) for j, n in zip(ci, nb))),
                       "n_core": len(ci)})

        t3 = [list(names).index(f) for f in sorted(top_full)]
        summ.append({"domain": d, "n_elements": E, "top3_full": ", ".join(sorted(top_full)),
                     "split_rho_median": float(np.median(rho)), "split_rho_p05": float(np.quantile(rho, .05)),
                     "spearman_brown_of_median": float(2 * np.median(rho) / (1 + np.median(rho))),
                     "share_splits_both_halves_same_top3": same / N_SPLITS,
                     "loeo_share_same_top3": float(np.mean([_top3(names[core], r[core]) == top_full for r in loeo])),
                     "loeo_max_P_of_top3": float(loeo[:, t3].max()),
                     "loeo_min_spearman": float(min(spearmanr(r[core], P0[core]).statistic for r in loeo)),
                     "loto_share_same_top3": float(np.mean(loto_same)),
                     # Abilities: the registered validity check failed, so its H1 results are not interpreted (DL-5)
                     "h1_interpretable": d != "A", "seed": SEED, "n_splits": N_SPLITS})
    res = {"element_splits": pd.DataFrame(splits), "leave_one_out": pd.DataFrame(loo),
           "h2_forms": pd.DataFrame(h2), "domain_summary": pd.DataFrame(summ)}
    if write:                                    # write=False: the output audit re-executes and compares (E18)
        od = out_dir(root)
        for k, v in res.items():
            v.to_csv(od / f"{k}.csv", index=False)
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    res = run(cfg)
    fdr = fdr_h1(cfg)
    sup = family_plus_supervisors(cfg)
    pd.set_option("display.width", 250)
    print(res["domain_summary"].round(3).to_string(index=False))
    s = res["element_splits"]
    print(s[s.role == "feeder_core"].pivot(index="feeder", columns="domain", values="share_half_sets_P_le_thr").round(3).to_string())
    print(res["h2_forms"].to_string(index=False))
    print(f"\nH1 with Benjamini-Hochberg, q = {fdr.fdr_q.iloc[0]} (DL-32)")
    print(fdr[["domain", "feeder", "P_point", "P_hi", "close_rule", "p_one_sided", "bh_adj_p_SK", "bh_reject_SK",
               "bh_reject_SKA", "bh_reject_domain", "bonferroni_reject_SK", "close_after_fdr",
               "decision_changed_by_fdr"]].round(4).to_string(index=False))
    print("\nFamily with 49-1011 added (DL-35), core feeders")
    print(sup[sup.role == "feeder_core"].round(1).sort_values(["domain", "P_registered"]).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
