"""Render the README figures of II-B from pipeline outputs (no computation of estimands here).

Figure numbers follow the README after the split into two repositories (DL-36): 1 H1 proximity, 2 CPS moves,
3 proximity vs pool, 4 skill-gap heatmap, 5 H2 concentration, 6 OSHA pathway, 7 multiverse, 8 error models,
S1 Abilities negative control.

    python scripts/make_figures.py      -> figures/*.png

Palette: single categorical slot (blue #2a78d6, validated) plus neutral ink/grid tokens;
context (reference occupations, non-qualifying feeders) is drawn in muted gray so identity
never depends on hue alone — every highlighted mark is also labelled or in the legend.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
EST, MV, OUT = ROOT / "outputs/estimates", ROOT / "outputs/multiverse", ROOT / "figures"
PR, SE, LY = ROOT / "outputs/practice", ROOT / "outputs/sensitivity", ROOT / "outputs/layers"

BLUE, INK, INK2, MUTED, GRID, BASE, SURF = "#2a78d6", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
CORE_FEEDERS = ["51-2090", "51-4031", "51-2031", "51-9061", "51-4121", "51-4081", "51-4041", "51-2028", "51-9161",
                "51-4072", "51-4122", "51-9124"]
LABELS = {
    "51-9161": "CNC tool operators", "51-4081": "Multiple machine tool setters", "51-4041": "Machinists",
    "51-2031": "Engine & machine assemblers", "51-9061": "Inspectors & testers", "51-2090": "Assemblers (team, proxy)",
    "51-4031": "Press setters & operators", "51-9124": "Coating & painting setters", "51-4072": "Molding & casting setters",
    "51-4122": "Welding machine setters", "51-2028": "Electrical/electromech. assemblers",
    "51-4121": "Welders & cutters", "53-7062": "Hand laborers (neg. control)",
    "51-1011": "Production supervisors", "51-4111": "Tool & die makers", "51-9162": "CNC programmers",
    "51-8021": "Stationary engineers", "49-9041": "Industrial machinery mechanics",
    "49-9071": "Maintenance & repair, general", "47-2111": "Electricians", "49-9043": "Machinery maintenance workers",
    "49-9044": "Millwrights",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": BASE, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.facecolor": SURF, "figure.facecolor": SURF,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.axisbelow": True, "savefig.facecolor": SURF,
})


def titles(fig, title: str, subtitle: str) -> None:
    fig.text(0.012, 0.975, title, ha="left", va="top", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.012, 0.925, subtitle, ha="left", va="top", fontsize=9.5, color=INK2)


def fig_h1() -> Path:
    h1 = pd.read_csv(EST / "h1_decisions.csv")
    bp = pd.read_csv(EST / "bootstrap_pairs.csv")
    s = h1[(h1.domain == "S") & h1.feeder_role.isin(["feeder_core", "negative_control"])].copy()
    lo = bp[(bp.domain == "S") & (bp.target == "FAMILY")].set_index("feeder")["P_lo"]
    s["P_lo"] = s.feeder.map(lo)
    s = s.sort_values("P_point", ascending=False).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    fig.subplots_adjust(left=0.30, right=0.97, top=0.84, bottom=0.11)
    for i, r in s.iterrows():
        neg = r.feeder_role == "negative_control"
        col = BLUE if r.close_rule else MUTED
        ax.plot([r.P_lo, r.P_hi], [i, i], color=col, lw=2, solid_capstyle="round")
        ax.plot(r.P_point, i, "o", ms=8, color=col, mfc=SURF if neg else col, mew=2,
                markeredgecolor=SURF if not neg else col, zorder=3)
    ax.set_yticks(range(len(s)))
    ax.set_yticklabels([LABELS[f] for f in s.feeder], color=INK)
    ax.axvline(25, color=INK2, lw=1, ls=(0, (4, 3)))
    ax.text(25.8, len(s) - 0.4, "H1 threshold:\nupper bound ≤ 25", fontsize=8.5, color=INK2, va="top")
    ax.set_xlim(0, 100); ax.set_xlabel("Proximity percentile among 905 occupations (lower = closer)")
    ax.grid(axis="y", visible=False)
    ax.legend(handles=[Line2D([], [], color=BLUE, marker="o", lw=2, ms=8, label="Meets H1 rule"),
                       Line2D([], [], color=MUTED, marker="o", lw=2, ms=8, label="Does not"),
                       Line2D([], [], color=MUTED, marker="o", lw=0, ms=8, mfc=SURF, mew=2, label="Negative control")],
              loc="upper right", frameon=False, fontsize=9)
    titles(fig, "Machining and setup occupations are the closest feeders on skills",
           "Skills (S) · production feeder → maintenance family · point and 95% bootstrap interval (B = 1,000)")
    p = OUT / "fig1_h1_proximity_skills.png"; fig.savefig(p, dpi=200); plt.close(fig); return p


def fig_h2() -> Path:
    ref = pd.read_csv(EST / "reference_distribution.csv")
    pp = pd.read_csv(EST / "point_pairs.csv")
    r = ref[(ref.domain == "S") & (ref.target == "FAMILY")].dropna(subset=["C"])
    f = pp[(pp.domain == "S") & (pp.target == "FAMILY") & (pp.feeder_role == "feeder_core")]
    a, b = f.fit_linear_a.iloc[0], f.fit_linear_b.iloc[0]
    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.84, bottom=0.11)
    ax.scatter(r.D, r.C, s=10, color=MUTED, alpha=0.45, lw=0, label="Other O*NET occupations (reference)")
    xs = np.linspace(r.D.min(), r.D.max(), 50)
    ax.plot(xs, a + b * xs, color=INK2, lw=2, label="Registered fit  C = a + b·D")
    ax.scatter(f.D, f.C_top, s=64, color=BLUE, edgecolor=SURF, linewidth=2, zorder=3, label="Production feeders")
    for code, dx, dy in (("51-9161", 0.03, 0.03), ("51-4041", 0.03, -0.045), ("51-4121", 0.03, 0.03), ("51-2090", 0.03, -0.065)):
        row = f[f.feeder == code].iloc[0]
        ax.annotate(LABELS[code], (row.D, row.C_top), (row.D + dx, row.C_top + dy), fontsize=8.5, color=INK)
    ax.set_xlabel("Total deficit D (SD units)"); ax.set_ylabel("Share of deficit in top 5 elements, C")
    ax.set_ylim(0, 1.02)
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    titles(fig, "Feeder deficits are spread wider than those of occupations with similar total deficit",
           "Skills (S) · deficit to the maintenance family · H2 (concentration above the fit) not supported: 0 of 12 feeders above q95")
    p = OUT / "fig5_h2_concentration_skills.png"; fig.savefig(p, dpi=200); plt.close(fig); return p


def fig_mv() -> Path:
    specs = pd.read_csv(MV / "multiverse_specs.csv")
    order = ["S", "K", "A"]
    names = {"S": "Skills (S)", "K": "Knowledge (K)", "A": "Abilities (A)"}
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots(figsize=(9.2, 4.2))
    fig.subplots_adjust(left=0.14, right=0.97, top=0.78, bottom=0.15)
    for i, d in enumerate(order):
        g = specs[specs.domain == d]
        y = i + rng.uniform(-0.18, 0.18, len(g))
        ax.scatter(g.median_rpct_linear, y, s=22, color=BLUE, alpha=0.75, lw=0)
        prim = g[g.is_primary].iloc[0]
        ax.scatter(prim.median_rpct_linear, i, s=90, facecolor=SURF, edgecolor=INK, linewidth=1.6, zorder=3)
        ax.text(g.median_rpct_linear.max() + 2.5, i,
                f"H2 supported in {int(g.h2_supported_linear.sum())} of {len(g)}", fontsize=8.5, color=INK2, va="center")
    ax.axvline(50, color=INK2, lw=1, ls=(0, (4, 3)))
    ax.text(51, 2.45, "50 = no difference from reference", fontsize=8.5, color=INK2)
    ax.set_yticks(range(len(order))); ax.set_yticklabels([names[d] for d in order], color=INK)
    ax.set_ylim(-0.6, 2.7); ax.set_xlim(0, 100); ax.grid(axis="y", visible=False)
    ax.set_xlabel("Median feeder residual percentile (lower = less concentrated than expected)")
    ax.legend(handles=[Line2D([], [], color=BLUE, marker="o", lw=0, ms=6, label="One analysis specification"),
                       Line2D([], [], color=INK, marker="o", lw=0, ms=9, mfc=SURF, label="Pre-registered primary")],
              loc="lower right", frameon=False, fontsize=9)
    titles(fig, "The pattern holds in all 96 analysis specifications per domain",
           "Multiverse: standardization × weights × suppression × not-relevant × feeder threshold × family weights")
    p = OUT / "fig7_multiverse.png"; fig.savefig(p, dpi=200); plt.close(fig); return p


def fig_pool() -> Path:
    """F4 — proximity and headcount side by side (not multiplied into an index)."""
    r = pd.read_csv(PR / "production_ranking_3363.csv")
    s = r[(r.domain == "S") & r.has_profile].copy()
    fig, ax = plt.subplots(figsize=(9.2, 5.8))
    fig.subplots_adjust(left=0.10, right=0.97, top=0.84, bottom=0.11)
    ax.axvspan(0, 25, color=GRID, alpha=0.55, lw=0)
    ax.text(1, 3.2e5, "close on skills (P ≤ 25)", fontsize=8.5, color=INK2, va="top")
    ok, small = s[~s.small_or_imprecise], s[s.small_or_imprecise]
    core = ok.soc6.isin(CORE_FEEDERS)
    excl = ok.soc6.isin(["51-1011", "51-4111"])
    other = ok[~core & ~excl]
    ax.scatter(small.P, small.emp_3363, s=26, facecolor=SURF, edgecolor=MUTED, lw=1, label="< 1,000 jobs or RSE ≥ 10% (imprecise)")
    ax.scatter(other.P, other.emp_3363, s=34, color=MUTED, lw=0, label="Other production occupations")
    ax.scatter(ok[excl].P, ok[excl].emp_3363, s=58, color=INK2, edgecolor=SURF, lw=1.5, zorder=3,
               label="Excluded from feeders by design")
    ax.scatter(ok[core].P, ok[core].emp_3363, s=58, color=BLUE, edgecolor=SURF, lw=1.5, zorder=3, label="Registered core feeders")
    # label position (x, y) in data coordinates; a thin leader line joins label and point
    pos = {"51-2090": (40, 1.6e5), "51-4031": (45, 4.6e4), "51-1011": (1.0, 4.6e4), "51-9061": (35.5, 1.3e4),
           "51-2031": (21.5, 3.0e4), "51-4121": (70, 2.6e4), "51-4081": (13.5, 1.5e4), "51-4041": (12, 6.0e3),
           "51-9161": (1.0, 3.3e3), "51-4111": (20.5, 1.07e4), "51-2028": (56, 7.0e3), "51-9162": (11.5, 1.9e3),
           "51-8021": (7.5, 190), "51-4072": (27, 5.0e3), "51-9124": (47.5, 3.6e3), "51-4122": (47.5, 2.4e3)}
    for code, (tx, ty) in pos.items():
        row = s[s.soc6 == code].iloc[0]
        ax.annotate(LABELS[code], (row.P, row.emp_3363), (tx, ty), fontsize=8, color=INK,
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6, shrinkA=0, shrinkB=4))
    ax.set_yscale("log"); ax.set_ylim(60, 3.5e5); ax.set_xlim(0, 100)
    ax.set_xlabel("Proximity percentile to the maintenance family, Skills (lower = closer)")
    ax.set_ylabel("Jobs in NAICS 3363, May 2025 (log scale)")
    ax.legend(loc="upper right", frameon=False, fontsize=8.5)
    n_wh = int(s.emp_3363.isna().sum())
    titles(fig, "The closest feeders are mid-sized; the largest pool sits mid-distance",
           f"{len(s) - n_wh} production occupations in motor vehicle parts mfg. with an O*NET profile and published employment"
           f" ({n_wh} withheld)\npoint estimates · employment from OEWS May 2025")
    p = OUT / "fig3_proximity_vs_pool.png"; fig.savefig(p, dpi=200); plt.close(fig); return p


def fig_gaps(n_elem: int = 12) -> Path:
    """F5 — where the Skills deficit sits, element by element."""
    g = pd.read_csv(PR / "gap_matrix.csv")
    g = g[(g.domain == "S") & (g.role == "feeder_core")]
    h1 = pd.read_csv(EST / "h1_decisions.csv")
    order = h1[(h1.domain == "S") & (h1.feeder_role == "feeder_core")].sort_values("P_point").feeder.tolist()
    cols = g.groupby("element_name").contribution.mean().sort_values(ascending=False).index[:n_elem].tolist()
    M = g.pivot(index="feeder", columns="element_name", values="contribution").loc[order, cols]
    tot = g.groupby("feeder").contribution.sum().loc[order]
    fig, ax = plt.subplots(figsize=(10.8, 6.8))
    fig.subplots_adjust(left=0.29, right=0.92, top=0.82, bottom=0.25)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("seq", [SURF, "#cfe1f6", "#7fb0e8", BLUE, "#123f78"])
    im = ax.imshow(M.to_numpy(), cmap=cmap, aspect="auto", vmin=0)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M.iat[i, j]
            if v >= 0.005:
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7, color=SURF if v > 0.09 else INK)
    ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, rotation=40, ha="right", fontsize=8.5, color=INK)
    ax.set_yticks(range(len(order))); ax.set_yticklabels([f"{LABELS[f]}  (D={tot[f]:.2f})" for f in order], fontsize=8.5, color=INK)
    ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02); cb.outline.set_visible(False); cb.ax.tick_params(labelsize=8)
    cb.set_label("Contribution to D (SD units)", color=INK2, fontsize=8.5)
    share = 100 * M.sum(axis=1) / tot
    fig.text(0.012, 0.02, f"The {n_elem} elements shown hold {share.min():.0f}–{share.max():.0f}% of each feeder's total deficit D; "
             "the rest is spread over the other 23 Skills elements.", fontsize=8.5, color=INK2)
    titles(fig, "Installation, repair and troubleshooting lead the gap, but it does not stop there",
           "Skills (S) · core feeders → maintenance family · cell = importance-weighted shortfall w·max(0, z_target − z_feeder) / Σw")
    p = OUT / "fig4_skill_gap_heatmap.png"; fig.savefig(p, dpi=200); plt.close(fig); return p


def fig_osha() -> Path:
    """F7 — the training-status change a line-to-maintenance move triggers (federal text only)."""
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
    import textwrap
    fig, ax = plt.subplots(figsize=(11.0, 4.9))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.86, bottom=0.02)
    ax.set_xlim(0, 100); ax.set_ylim(0, 52); ax.axis("off")
    boxes = [
        ("Operator or setter", "'Affected' or already 'authorized'",
         "Operators need instruction in the purpose and use of the procedure. Setting up, adjusting and tool changes "
         "count as servicing, so setters may already be authorized for their own machines.",
         "1910.147(b); (c)(7)(i)(B); (a)(2)(ii) Note", False),
        ("Assigned to maintenance", "status change",
         "Authorization extends to all equipment serviced; retraining is required whenever job assignments change. "
         "Electrical: a supervised trainee who has shown safe performance is treated as qualified for those duties.",
         "1910.147(c)(7)(iii)(A); 1910.399 Note 2", False),
        ("Maintenance (LOTO)", "'Authorized employee'",
         "Training in hazardous-energy sources, their type and magnitude, and isolation methods.", "1910.147(c)(7)(i)(A)", True),
        ("Maintenance (electrical)", "'Qualified person'",
         "Trained to identify exposed live parts, nominal voltage and clearance distances.", "1910.332(b)(3)", True),
    ]
    w, gap, x0 = 22.0, 3.2, 1.5
    for i, (head, status, req, cite, tgt) in enumerate(boxes):
        x = x0 + i * (w + gap)
        ax.add_patch(FancyBboxPatch((x, 17), w, 33, boxstyle="round,pad=0.3,rounding_size=1.2",
                                    facecolor="#e8f0fb" if tgt else SURF, edgecolor=BLUE if tgt else MUTED, lw=1.6))
        ax.text(x + 1.2, 47.5, head, fontsize=10.5, fontweight="bold", color=INK, va="top")
        ax.text(x + 1.2, 43.3, status, fontsize=8.6, color=BLUE if tgt else INK2, va="top", style="italic")
        ax.text(x + 1.2, 38.8, textwrap.fill(req, 31), fontsize=8.2, color=INK, va="top", linespacing=1.32)
        ax.text(x + 1.2, 19.0, textwrap.fill("29 CFR " + cite, 34), fontsize=7.8, color=INK2, va="bottom")
        if i < len(boxes) - 1:
            ax.add_patch(FancyArrowPatch((x + w + 0.5, 33.5), (x + w + gap - 0.4, 33.5), arrowstyle="-|>",
                                         mutation_scale=14, color=INK2, lw=1.4))
    ax.add_patch(FancyBboxPatch((x0, 1.5), 4 * w + 3 * gap, 11, boxstyle="round,pad=0.3,rounding_size=1.2",
                                facecolor=GRID, edgecolor="none"))
    ax.text(x0 + 1.2, 11.2, "Employer obligations throughout", fontsize=9, fontweight="bold", color=INK, va="top")
    ax.text(x0 + 1.2, 7.6, "• Certify that training is done and kept up to date, with each employee's name and dates — 1910.147(c)(7)(iv)\n"
            "• Inspect each energy-control procedure at least annually — 1910.147(c)(6)(i)", fontsize=8.3, color=INK, va="top",
            linespacing=1.5)
    titles(fig, "Moving from the line to maintenance changes or extends the worker's legal training status",
           "Federal OSHA text (29 CFR 1910) · which gate applies to which job is the analyst's reading and must be checked against plant job descriptions")
    p = OUT / "fig6_osha_pathway.png"; fig.savefig(p, dpi=200); plt.close(fig); return p


def fig_uncertainty() -> Path:
    """F8 — do the H1 upper bounds survive other error models?"""
    u = pd.read_csv(SE / "uncertainty_models.csv")
    u = u[u.role == "feeder_core"]
    names = {"registered (independent, median SE)": ("Registered: independent errors", BLUE, "o", "-"),
             "copula": ("Correlated errors (copula)", INK, "s", "-"),
             "comonotone": ("Fully correlated (ρ = 1)", INK2, "^", (0, (3, 2))),
             "mi_se": ("Imputed SE drawn, not median", MUTED, "D", "-")}
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 6.0), sharey=False)
    fig.subplots_adjust(left=0.20, right=0.98, top=0.80, bottom=0.17, wspace=0.62)
    for ax, d in zip(axes, ("S", "K")):
        g = u[u.domain == d]
        order = g[g.variant.str.startswith("registered")].sort_values("P_hi").feeder.tolist()[::-1]
        for k, (v, (lab, col, mk, ls)) in enumerate(names.items()):
            gv = g[g.variant == v].set_index("feeder").loc[order]
            yy = np.arange(len(order)) + (k - 1.5) * 0.18
            ax.hlines(yy, gv.P_lo, gv.P_hi, color=col, lw=1.8, linestyles=ls)
            ax.plot(gv.P_hi, yy, mk, color=col, ms=4.5, label=lab)
        ax.axvline(25, color=INK2, lw=1, ls=(0, (4, 3)))
        ax.set_yticks(range(len(order))); ax.set_yticklabels([LABELS[f] for f in order], fontsize=8.3, color=INK)
        ax.set_xlim(0, 100); ax.grid(axis="y", visible=False)
        ax.set_title({"S": "Skills (S)", "K": "Knowledge (K)"}[d], loc="left", fontsize=10, color=INK)
        ax.set_xlabel("95% interval of P (marker = upper bound)")
    axes[0].legend(loc="upper center", bbox_to_anchor=(1.12, -0.10), ncol=4, frameon=False, fontsize=8.3)
    titles(fig, "CNC operators and multi-machine setters stay close under every error model",
           "Core feeders → maintenance family · B = 1,000 per model · dashed line = H1 threshold (upper bound ≤ 25) · ρ = 1 is an extreme bound")
    p = OUT / "fig8_uncertainty_models.png"; fig.savefig(p, dpi=200); plt.close(fig); return p


def fig_abilities() -> Path:
    """S1 — why the Abilities negative control failed (DL-17)."""
    a = pd.read_csv(SE / "abilities_subgroups.csv")
    mds = pd.read_csv(SE / "abilities_mds.csv")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 5.2), gridspec_kw={"width_ratios": [1.05, 1]})
    fig.subplots_adjust(left=0.135, right=0.98, top=0.80, bottom=0.12, wspace=0.28)
    groups = ["all", "cognitive", "psychomotor", "sensory", "physical"]
    n = a.drop_duplicates("group").set_index("group").n_elements
    for i, gname in enumerate(groups):
        g = a[a.group == gname]
        core = g[g.role == "feeder_core"]
        ax1.scatter(core.P, np.full(len(core), i) + np.random.default_rng(i).uniform(-0.12, 0.12, len(core)),
                    s=22, color=MUTED, lw=0, label="Core feeders" if i == 0 else None)
        cnc = g[g.feeder == "51-9161"].iloc[0]
        ax1.plot(cnc.P, i, "o", color=BLUE, ms=7, label="CNC tool operators" if i == 0 else None)
        nc = g[g.role == "negative_control"].iloc[0]
        ax1.plot(nc.P, i, "o", ms=9, mfc=SURF, mec=INK, mew=1.6, label="Hand laborers (neg. control)" if i == 0 else None)
    ax1.set_yticks(range(len(groups))); ax1.set_yticklabels([f"{g} ({n[g]})" for g in groups], color=INK)
    ax1.invert_yaxis(); ax1.set_xlim(0, 100); ax1.grid(axis="y", visible=False)
    ax1.set_xlabel("Proximity percentile to maintenance family"); ax1.legend(loc="lower right", frameon=False, fontsize=8)
    ax1.set_title("Abilities subgroup (elements)", loc="left", fontsize=10, color=INK)
    other = mds[mds.role == "other"]
    ax2.scatter(other.dim1, other.dim2, s=8, color=MUTED, alpha=0.4, lw=0)
    for role, kw in (("feeder_core", dict(s=26, color=INK2)), ("maintenance target", dict(s=46, color=BLUE)),
                     ("negative_control", dict(s=70, facecolor=SURF, edgecolor=INK, linewidth=1.6))):
        m = mds[mds.role == role]
        ax2.scatter(m.dim1, m.dim2, zorder=3, **kw, label={"feeder_core": "Core feeders", "maintenance target": "Maintenance targets",
                                                         "negative_control": "Neg. control"}[role])
    v1, v2 = mds.var_explained_dim1.iloc[0], mds.var_explained_dim2.iloc[0]
    ax2.set_xlabel(f"MDS dimension 1 ({100 * v1:.0f}% of variance)"); ax2.set_ylabel(f"MDS dimension 2 ({100 * v2:.0f}%)")
    ax2.legend(loc="best", frameon=False, fontsize=8)
    ax2.set_title("Classical MDS of Abilities z-profiles (910 occupations)", loc="left", fontsize=10, color=INK)
    titles(fig, "The Abilities control fails on physical abilities, not on cognitive ones",
           "Supplement (DL-17, exploratory) · subgroup percentiles use z over the full universe · registered A decision unchanged")
    p = OUT / "figS1_abilities_negative_control.png"; fig.savefig(p, dpi=200); plt.close(fig); return p


CPS = ROOT / "outputs/cps_moves"


ORIGIN_LABELS = {"production_mfg": "Production job, manufacturing", "production_outside_mfg": "Production job, other industry",
                 "other_install_maint_repair": "Other installation / repair job", "construction_extraction": "Construction / extraction",
                 "transport_material_moving": "Transportation / material moving", "architecture_engineering": "Engineering technician / engineer",
                 "other": "All other occupations"}


def _interval_row(ax, y, r, col, open_marker=None, fmt="{:.1f}%", dx=0.0):
    ax.plot([r.lo, r.hi], [y, y], color=col, lw=2, solid_capstyle="round", zorder=3)
    ax.plot(r.pct, y, "o", ms=8, color=col, mec=SURF, mew=2, zorder=4)
    if open_marker is not None:
        ax.plot(open_marker, y, "D", ms=6, mfc=SURF, mec=INK2, mew=1.4, zorder=5)


def fig_cps() -> Path | None:
    """F14 — where new maintenance workers come from and how often production workers move (DL-37, 40, 42, 43, 45)."""
    if not (CPS / "q2_origin_composition.csv").exists():
        return None
    q1 = pd.read_csv(CPS / "q1_rates.csv"); qo = pd.read_csv(CPS / "q2_origin_composition.csv")
    H, R = "iv_no_allocation", "main"
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.2, 5.6), gridspec_kw={"width_ratios": [1.25, 1]})
    fig.subplots_adjust(left=0.205, right=0.955, top=0.76, bottom=0.16, wspace=0.62)
    order = list(ORIGIN_LABELS)
    for i, og in enumerate(order):
        h = qo[(qo.check == H) & (qo.event == "any_employer") & (qo.group == og)].iloc[0]
        g = qo[(qo.check == R) & (qo.event == "any_employer") & (qo.group == og)].iloc[0]
        y = len(order) - 1 - i
        col = BLUE if og == "production_mfg" else INK2
        _interval_row(a1, y, h, col, open_marker=g.pct)
        a1.text(max(h.hi, g.pct) + 1.2, y, f"{h.pct:.0f}%", va="center", fontsize=8.6, color=INK)
    a1.set_yticks(range(len(order))); a1.set_yticklabels([ORIGIN_LABELS[o] for o in order][::-1], fontsize=8.8)
    a1.set_xlim(0, 52); a1.set_xlabel("Share of new maintenance workers in manufacturing (%)")
    n_h = int(qo[(qo.check == H) & (qo.event == "any_employer")].n_den.iloc[0])
    a1.set_title(f"Last month's job of workers who moved into maintenance\n(manufacturing, n = {n_h} moves)",
                 fontsize=10, color=INK, loc="left")
    rows = [("any_employer", "Any employer"), ("same_employer", "Same employer")]
    for i, (ev, lab) in enumerate(rows):
        h = q1[(q1.check == H) & (q1.group == "all_P") & (q1.event == ev)].iloc[0]
        g = q1[(q1.check == R) & (q1.group == "all_P") & (q1.event == ev)].iloc[0]
        y = len(rows) - 1 - i
        hh = h.copy(); hh["pct"], hh["lo"], hh["hi"] = h.per_10000, h.per_10000_lo, h.per_10000_hi
        _interval_row(a2, y, hh, BLUE, open_marker=g.per_10000)
        a2.text(max(hh.hi, g.per_10000) + 1.6, y,
                f"{h.per_10000:.1f} per 10,000 a month\n\u2248 {h.annual_pct:.1f}% a year  ({int(h.n_num)} moves)",
                va="center", fontsize=8.5, color=INK)
    a2.set_yticks(range(len(rows))); a2.set_yticklabels([r[1] for r in rows][::-1], fontsize=9)
    a2.set_ylim(-0.6, 1.6); a2.set_xlim(0, 48)
    a2.set_xlabel("Per 10,000 production workers, per month")
    a2.set_title("How often production workers in manufacturing\nmove into maintenance", fontsize=10, color=INK, loc="left")
    fig.legend(handles=[Line2D([], [], color=BLUE, lw=2, marker="o", ms=7, mec=SURF, label="Without imputed codes, 95% interval (headline)"),
                        Line2D([], [], ls="", marker="D", ms=6, mfc=SURF, mec=INK2, mew=1.4, label="All records (registered primary)")],
               loc="lower left", bbox_to_anchor=(0.012, 0.0), ncol=2, frameon=False, fontsize=8.5)
    titles(fig, "Production jobs are the largest identified source of new maintenance workers in manufacturing",
           "Current Population Survey, same person in consecutive months, Jan 2020 \u2013 Sep 2026 \u00b7 manufacturing as a whole "
           "(NAICS 3363 alone not identifiable)\n95% intervals: household bootstrap \u00b7 exploratory (DL-37, 40, 42, 43, 45)")
    p = OUT / "fig2_cps_moves.png"; fig.savefig(p, dpi=200); plt.close(fig); return p


def main() -> int:
    OUT.mkdir(exist_ok=True)
    fns = [fig_h1, fig_h2, fig_mv, fig_pool, fig_gaps, fig_osha, fig_abilities]
    if (SE / "uncertainty_models.csv").exists():
        fns.append(fig_uncertainty)
    fns += [fig_cps]
    for fn in fns:
        p = fn()
        if p is not None:
            print("wrote", p.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
