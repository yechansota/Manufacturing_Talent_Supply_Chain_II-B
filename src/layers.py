"""Descriptive layers (prereg estimands.descriptive_layers) and the poster decision table.

Layers are reported next to the KSA results and are never combined into an index.
  1. Wage    — OEWS May 2025, NAICS 336300, national median hourly wage.
  2. Demand  — BLS EP 2025–35 (all industries, national): openings, separation rates, training category.
  3. Gates   — federal training requirements that sit outside any KSA rating (29 CFR 1910.147,
               1910.332, 1910.399). Applicability coding is the analyst's reading of each occupation's
               function and must be validated against plant job descriptions.

Outputs (outputs/layers/): wage_layer.csv, ep_layer.csv, regulatory_gates.csv,
                           decision_table.csv, layers_summary.md
Usage:   python -m src.layers
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from .config import REPO_ROOT, load_config, repo_path
from .frame import frame_table, resolve_codes

# Verified 2026-10-18 against osha.gov (see docs/Technical Documentation.md for quotations).
GATES = {
    "LOTO_authorized": {
        "citation": "29 CFR 1910.147(b) definitions; (c)(7)(i)(A)",
        "requirement": "Authorized employees (who lock/tag out equipment to perform servicing or maintenance) must be "
                       "trained in recognizing hazardous energy sources, their type and magnitude, and isolation methods. "
                       "Affected employees (who operate the equipment) need only instruction in the procedure's purpose and use.",
    },
    "electrical_qualified": {
        "citation": "29 CFR 1910.332(b)(3); 1910.399 'Qualified person' Note 2",
        "requirement": "Persons permitted to work on or near exposed energized parts must be trained to distinguish exposed "
                       "live parts, determine nominal voltage, and know clearance distances. A trainee who has shown safe "
                       "performance at his or her level and works under direct supervision of a qualified person is "
                       "considered qualified for those duties.",
    },
}
# Analyst coding by occupational function (NOT plant-validated).
TARGET_GATES = {
    "49-9041": ("Applies — servicing/repair of machinery is the core function", "Conditional — when assigned work on or near exposed energized parts"),
    "49-9071": ("Applies — servicing/repair of machinery is the core function", "Conditional — when assigned work on or near exposed energized parts"),
    "47-2111": ("Applies — installs/services electrical systems", "Applies — work on or near exposed energized parts is core"),
    "49-9043": ("Applies — machinery maintenance is the core function", "Conditional — when assigned work on or near exposed energized parts"),
    "49-9044": ("Applies — installs/dismantles/repairs machinery", "Conditional — when assigned work on or near exposed energized parts"),
}
FEEDER_LOTO = "Typically 'affected' (operates equipment); becomes 'authorized' only if assigned servicing"
# DL-24: setting up, adjusting and tool changes are 'servicing' under 1910.147(b); routine minor servicing with
# alternative protection is exempt ((a)(2)(ii) Note). Where O*NET rates servicing skills as Important (>= 3.0),
# the occupation may already hold authorized status for the equipment it sets up or services.
FEEDER_LOTO_SERVICE = ("Affected when operating; may already be 'authorized' for the equipment it sets up or services "
                       "(setting up, adjusting and tool changes are servicing, 1910.147(b); routine minor servicing with "
                       "alternative protection is exempt, (a)(2)(ii) Note)")
SERVICE_SKILLS = ("Repairing", "Equipment Maintenance")
SERVICE_THRESHOLD = 3.0          # O*NET Importance 3 = "Important"


def run(cfg: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, pd.DataFrame]:
    with duckdb.connect(str(repo_path(cfg["paths"]["duckdb"], root)), read_only=True) as con:
        oews = con.execute("SELECT * FROM oews_3363").df().set_index("OCC_CODE")
        sep = con.execute("SELECT * FROM ep_separations WHERE occupation_type = 'Line item'").df().set_index("nem_code")
        edu = con.execute("SELECT * FROM ep_education").df().set_index("nem_code")
        svc = con.execute("SELECT onet_code, element_name, data_value FROM onet_ratings WHERE domain = 'S' AND scale_id = 'IM' "
                          "AND element_name IN ('Repairing', 'Equipment Maintenance')").df()
    svc = svc.pivot(index="onet_code", columns="element_name", values="data_value")
    frame = frame_table(cfg)
    targets = cfg["frame"]["targets_core"]
    pi = oews.loc[targets, "TOT_EMP"] / oews.loc[targets, "TOT_EMP"].sum()
    fam_wage = float((pi * oews.loc[targets, "H_MEDIAN"]).sum())

    wage = frame.assign(title=lambda x: x.soc6.map(oews["OCC_TITLE"]),
                        emp_3363=lambda x: x.soc6.map(oews["TOT_EMP"]),
                        emp_rse=lambda x: x.soc6.map(oews["EMP_PRSE"]),
                        h_median=lambda x: x.soc6.map(oews["H_MEDIAN"]),
                        a_median=lambda x: x.soc6.map(oews["A_MEDIAN"]),
                        mean_wage_rse=lambda x: x.soc6.map(oews["MEAN_PRSE"]))
    wage["gap_to_49_9041"] = oews.loc["49-9041", "H_MEDIAN"] - wage["h_median"]
    wage["gap_to_family_approx"] = fam_wage - wage["h_median"]
    wage["gap_to_family_pct"] = 100 * wage["gap_to_family_approx"] / wage["h_median"]

    ep = frame.join(sep[["emp_2025_k", "emp_change_pct", "openings_k", "separations_rate_pct", "lf_exit_rate_pct",
                         "transfer_rate_pct"]], on="soc6").join(edu[["entry_education", "related_work_experience", "ojt"]], on="soc6")

    gates = []
    for rec in frame.itertuples(index=False):
        codes = [c for c, mtype in resolve_codes(rec.soc6, cfg) if mtype == "primary"]
        im = svc.reindex(codes).mean()           # equal-weight mean over the occupation's O*NET codes
        imp_rep, imp_eqm = float(im.get("Repairing")), float(im.get("Equipment Maintenance"))
        services = max(imp_rep, imp_eqm) >= SERVICE_THRESHOLD
        if rec.role == "target_core":
            loto, elec = TARGET_GATES[rec.soc6]
        elif rec.role.startswith("feeder") or rec.role in {"sensitivity", "negative_control"}:
            loto = FEEDER_LOTO_SERVICE if services else FEEDER_LOTO
            elec = "Not part of typical duties (unqualified-person training only, if exposed)"
        else:
            continue
        gates.append({"soc6": rec.soc6, "role": rec.role, "LOTO_authorized": loto, "electrical_qualified": elec,
                      "onet_importance_repairing": round(imp_rep, 2), "onet_importance_equipment_maintenance": round(imp_eqm, 2),
                      "coding_basis": "analyst reading of occupational function, grounded in O*NET Importance of Repairing / "
                                      "Equipment Maintenance (>= 3.0 = servicing is part of the job; DL-24) — validate "
                                      "against plant job descriptions"})
    gates = pd.DataFrame(gates)

    # Decision table: core feeders -> family, S as the interpretable primary domain.
    est = repo_path("outputs/estimates", root)
    h1 = pd.read_csv(est / "h1_decisions.csv")
    ne = pd.read_csv(est / "neff_exploratory.csv")
    mvh = pd.read_csv(repo_path("outputs/multiverse", root) / "multiverse_h1.csv")
    s = h1[(h1.domain == "S") & (h1.feeder_role == "feeder_core")].set_index("feeder")
    k = h1[(h1.domain == "K") & (h1.feeder_role == "feeder_core")].set_index("feeder")
    nS = ne[(ne.domain == "S")].set_index("feeder")
    mS = mvh[mvh.domain == "S"].set_index("feeder")
    top = pd.read_csv(est / "top_elements.csv")
    topS = (top[(top.domain == "S") & (top.target == "FAMILY") & (top["rank"] <= 3)]
            .groupby("feeder")["element_name"].apply(lambda x: ", ".join(x)))
    dt = pd.DataFrame(index=cfg["frame"]["feeders_core"])
    dt.index.name = "feeder"
    dt["title"] = dt.index.map(oews["OCC_TITLE"])
    dt["emp_3363"] = dt.index.map(oews["TOT_EMP"])
    dt["S_P"] = s["P_point"]; dt["S_P_hi"] = s["P_hi"]; dt["S_close_H1"] = s["close_rule"]
    dt["S_multiverse_share_P_le_25"] = mS["share_P_le_25"]
    dt["K_P"] = k["P_point"]; dt["K_P_hi"] = k["P_hi"]
    dt["S_neff (exploratory)"] = nS["neff_point"]
    dt["S_neff_local_pct (exploratory)"] = nS["neff_pct_local"]
    dt["S_top3_deficit_elements"] = topS
    dt["h_median"] = dt.index.map(oews["H_MEDIAN"])
    dt["wage_gap_to_family_approx"] = fam_wage - dt["h_median"]
    dt["ojt_feeder"] = dt.index.map(edu["ojt"])
    dt = dt.reset_index().sort_values("S_P")

    out = repo_path("outputs/layers", root)
    out.mkdir(parents=True, exist_ok=True)
    wage.to_csv(out / "wage_layer.csv", index=False)
    ep.to_csv(out / "ep_layer.csv", index=False)
    gates.to_csv(out / "regulatory_gates.csv", index=False)
    dt.to_csv(out / "decision_table.csv", index=False)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    tgt_ep = ep[ep.role == "target_core"][["soc6", "openings_k", "separations_rate_pct", "emp_change_pct", "entry_education", "ojt"]]
    md = [f"# Descriptive layers and decision table\n\nGenerated: {ts}\n",
          f"Family wage (employment-weighted mean of target medians, an approximation — not a median): ${fam_wage:.2f}/h. "
          f"π: " + ", ".join(f"{c} {v:.3f}" for c, v in pi.items()) + "\n",
          "## Decision table (core feeders → maintenance family; S = interpretable primary domain)\n",
          dt.round(2).to_markdown(index=False),
          "\n\n## Targets — EP 2025–35 (all industries, national)\n", tgt_ep.to_markdown(index=False),
          "\n\n## Regulatory gates (citations verified; applicability = analyst coding)\n",
          "\n".join(f"- **{k}** ({v['citation']}): {v['requirement']}" for k, v in GATES.items()),
          "\n\n", gates.to_markdown(index=False)]
    (out / "layers_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"wage": wage, "ep": ep, "gates": gates, "decision": dt, "fam_wage": fam_wage}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    res = run(load_config(args.config))
    pd.set_option("display.width", 260); pd.set_option("display.max_colwidth", 60)
    print(f"family wage approx ${res['fam_wage']:.2f}")
    print(res["decision"].round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
