"""Pre-analysis data audit (no estimands are computed here).

Outputs (outputs/audit/):
  audit_universe.csv   per-domain size of the reference universe and SE coverage
  audit_crosswalk.csv  SOC-6 -> O*NET-SOC resolution for every frame occupation
  audit_frame.csv      coverage / precision / source / date audit per (occupation, code, domain)
  audit_stop_rule.csv  pre-registered stop rule per domain
  audit_missing_se.csv frame codes x domains that need SE imputation (prereg measurement.missing_se)
  audit_summary.md     human-readable summary for the review log

Usage:
    python -m src.audit [--config config/prereg.yaml]
Exit codes: 0 = pass, 1 = database missing, 2 = unresolved primary O*NET code.
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
from .frame import CORE_ROLES, aggregation_rule, frame_table, resolve_codes


def expected_elements_by_domain(cfg: dict[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for spec in cfg["data_versions"]["onet"]["files"].values():
        out[spec["domain"]] = out.get(spec["domain"], 0) + spec["expected_elements"]
    return out


def _rate(numer: int, denom: int) -> float:
    return float(numer) / denom if denom else float("nan")


def audit_code_domain(sub: pd.DataFrame, level_id: str, expected_el: int) -> dict[str, Any]:
    """Coverage, precision, source and date metrics for one O*NET code in one domain."""
    lv = sub[sub["scale_id"] == level_id]
    flag_known = sub["suppress"].notna()
    nr_known = lv["not_relevant"].notna()
    has_n = sub["n"].notna().any()
    has_year = sub["date_year"].notna().any()
    return {
        "n_rows": len(sub),
        "n_elements_lv": lv["element_id"].nunique(),
        "expected_elements": expected_el,
        "coverage": _rate(lv["element_id"].nunique(), expected_el),
        "suppress_Y": int((sub["suppress"] == "Y").sum()),
        "suppress_rate": _rate(int((sub["suppress"] == "Y").sum()), int(flag_known.sum())),
        "suppress_flag_missing": int((~flag_known).sum()),
        "not_relevant_rate_lv": _rate(int((lv["not_relevant"] == "Y").sum()), int(nr_known.sum())),
        "se_missing_rate": float(sub["se"].isna().mean()) if len(sub) else float("nan"),
        "n_median": float(sub["n"].median()) if has_n else float("nan"),
        "n_min": float(sub["n"].min()) if has_n else float("nan"),
        "year_min": int(sub["date_year"].min()) if has_year else pd.NA,
        "year_max": int(sub["date_year"].max()) if has_year else pd.NA,
        "domain_sources": ";".join(sorted(sub["domain_source"].dropna().unique())),
    }


def run_audit(cfg: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    db_path = repo_path(cfg["paths"]["duckdb"], root)
    if not db_path.exists():
        raise FileNotFoundError(f"{db_path} not found — run `python -m src.ingest_onet` first.")
    with duckdb.connect(str(db_path), read_only=True) as con:
        ratings = con.execute("SELECT * FROM onet_ratings").df()
        file_meta = con.execute("SELECT * FROM onet_file_meta").df()

    level_id = cfg["measurement"]["scales"]["level"]["id"]
    exp_el = expected_elements_by_domain(cfg)
    domains = sorted(ratings["domain"].unique())
    out_dir = repo_path(cfg["paths"]["audit_out"], root)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Reference universe per domain (incl. how many occupations lack SE)
    occ_se = (ratings.assign(se_missing=ratings["se"].isna())
              .groupby(["domain", "onet_code"])["se_missing"].any().reset_index())
    universe = (
        ratings.groupby("domain")
        .agg(occupations=("onet_code", "nunique"), elements=("element_id", "nunique"), rows=("onet_code", "size"))
        .reset_index()
        .merge(occ_se.groupby("domain")["se_missing"].sum().rename("occupations_with_missing_se").reset_index(),
               on="domain")
    )
    universe["expected_elements"] = universe["domain"].map(exp_el)
    sources = (ratings.groupby(["domain", "domain_source"])["onet_code"].nunique()
               .rename("occupations").reset_index())

    # 2) Crosswalk resolution
    frame = frame_table(cfg)
    codes_by_domain = {d: set(ratings.loc[ratings["domain"] == d, "onet_code"]) for d in domains}
    all_codes = set(ratings["onet_code"])
    titles = ratings.drop_duplicates("onet_code").set_index("onet_code")["title"]
    xw_rows = []
    for rec in frame.itertuples(index=False):
        children = sorted(c for c in all_codes if c.startswith(rec.soc6 + "."))
        for code, mtype in resolve_codes(rec.soc6, cfg):
            row = {"soc6": rec.soc6, "role": rec.role, "onet_code": code, "mapping_type": mtype,
                   "aggregation": aggregation_rule(rec.soc6, cfg),
                   "title": titles.get(code, ""), "found_any_domain": code in all_codes,
                   "candidate_codes_with_soc6_prefix": ";".join(children)}
            for d in domains:
                row[f"has_{d}"] = code in codes_by_domain[d]
            xw_rows.append(row)
    crosswalk = pd.DataFrame(xw_rows)

    # 3) Per (occupation, code, domain) audit
    fa_rows = []
    for rec in crosswalk.itertuples(index=False):
        for d in domains:
            sub = ratings[(ratings["onet_code"] == rec.onet_code) & (ratings["domain"] == d)]
            fa_rows.append({"soc6": rec.soc6, "role": rec.role, "onet_code": rec.onet_code,
                            "mapping_type": rec.mapping_type, "domain": d,
                            **audit_code_domain(sub, level_id, exp_el.get(d, 0))})
    frame_audit = pd.DataFrame(fa_rows)

    # 4) Pre-registered stop rule (primary codes of core roles only)
    sr_cfg = cfg["decision_rules"]["stop_rule"]
    core_codes = set(crosswalk.loc[(crosswalk["mapping_type"] == "primary")
                                   & crosswalk["role"].isin(CORE_ROLES), "onet_code"])
    sr_rows = []
    for d in domains:
        sub = ratings[(ratings["domain"] == d) & ratings["onet_code"].isin(core_codes)]
        known = int(sub["suppress"].notna().sum())
        n_y = int((sub["suppress"] == "Y").sum())
        rate = _rate(n_y, known)
        if np.isnan(rate):
            decision = "CHECK: no flags"
        elif rate > sr_cfg["max_rate"]:
            decision = "EXCLUDE from primary"
        else:
            decision = "PASS"
        sr_rows.append({"domain": d, "codes_in_scope": len(core_codes), "rows_in_scope": len(sub),
                        "rows_flag_known": known, "rows_flag_missing": len(sub) - known,
                        "suppress_Y": n_y, "suppress_rate": rate, "max_rate": sr_cfg["max_rate"],
                        "decision": decision})
    stop_rule = pd.DataFrame(sr_rows)

    # 5) Codes needing SE imputation (prereg measurement.missing_se)
    missing_se = frame_audit[(frame_audit["se_missing_rate"] > 0)][
        ["soc6", "role", "onet_code", "mapping_type", "domain", "se_missing_rate", "domain_sources", "n_median"]]
    missing_se = missing_se.assign(
        primary_handling=cfg["measurement"]["missing_se"]["primary"],
        sensitivity_handling=cfg["measurement"]["missing_se"]["sensitivity"])

    # 6) Write outputs
    universe.to_csv(out_dir / "audit_universe.csv", index=False)
    crosswalk.to_csv(out_dir / "audit_crosswalk.csv", index=False)
    frame_audit.to_csv(out_dir / "audit_frame.csv", index=False)
    stop_rule.to_csv(out_dir / "audit_stop_rule.csv", index=False)
    missing_se.to_csv(out_dir / "audit_missing_se.csv", index=False)
    summary = render_summary(cfg, file_meta, universe, sources, crosswalk, frame_audit, stop_rule, missing_se)
    (out_dir / "audit_summary.md").write_text(summary, encoding="utf-8")

    unresolved = crosswalk[(crosswalk["mapping_type"] == "primary") & ~crosswalk["found_any_domain"]]
    return {"out_dir": out_dir, "unresolved_primary": unresolved, "stop_rule": stop_rule,
            "frame_audit": frame_audit, "crosswalk": crosswalk, "universe": universe,
            "missing_se": missing_se}


def _md_table(df: pd.DataFrame, floatfmt: str = "{:.3f}") -> str:
    """Minimal markdown table renderer (avoids optional tabulate dependency)."""
    def fmt(v: Any) -> str:
        if v is None or v is pd.NA:
            return ""
        if isinstance(v, (float, np.floating)):
            return "" if np.isnan(v) else floatfmt.format(v)
        return str(v)
    head = "| " + " | ".join(df.columns) + " |"
    sep = "|" + "|".join(["---"] * len(df.columns)) + "|"
    body = ["| " + " | ".join(fmt(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([head, sep, *body])


def render_summary(cfg, file_meta, universe, sources, crosswalk, frame_audit, stop_rule, missing_se) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    unresolved = crosswalk[~crosswalk["found_any_domain"]]
    primary_view = frame_audit[frame_audit["mapping_type"] == "primary"][
        ["soc6", "role", "onet_code", "domain", "coverage", "suppress_rate", "se_missing_rate",
         "n_median", "year_min", "domain_sources"]]
    years = frame_audit[(frame_audit["mapping_type"] == "primary") & frame_audit["year_min"].notna()]
    meta = file_meta.assign(sha256=file_meta["sha256"].str.slice(0, 16) + "…")
    parts = [
        f"# Data audit summary\n\nGenerated: {ts}  \nPre-registration: v{cfg['meta']['prereg_version']} "
        f"({cfg['meta']['status']})  \nO*NET release: {cfg['data_versions']['onet']['release']}\n",
        "## 1. Ingested files\n", _md_table(meta),
        "\n## 2. Reference universe\n", _md_table(universe),
        "\n\nRating sources by domain (number of occupations):\n\n", _md_table(sources),
        "\n## 3. Crosswalk issues\n",
        ("None — every frame code was found." if unresolved.empty
         else _md_table(unresolved[["soc6", "role", "onet_code", "mapping_type", "candidate_codes_with_soc6_prefix"]])),
        "\n\nMulti-code mappings:\n\n",
        _md_table(crosswalk[crosswalk["aggregation"] != "single"][["soc6", "onet_code", "title", "aggregation"]])
        if (crosswalk["aggregation"] != "single").any() else "None.",
        "\n## 4. Stop rule (pre-registered)\n", _md_table(stop_rule),
        "\n## 5. Codes needing SE imputation\n",
        _md_table(missing_se) if not missing_se.empty else "None.",
        "\n## 6. Rating collection years (primary mappings)\n",
        f"Range across frame codes: {int(years['year_min'].min())}–{int(years['year_max'].max())}.\n"
        if not years.empty else "No dated rows.\n",
        "\n## 7. Frame audit (primary mappings)\n", _md_table(primary_view),
        "\n## 8. Reviewer checklist\n",
        "- [ ] All primary codes resolved (Section 3 first table empty)\n"
        "- [ ] Coverage = 1.000 for every primary code x domain\n"
        "- [ ] Stop rule decision recorded for each domain\n"
        "- [ ] SE-imputation cases match prereg measurement.missing_se\n"
        "- [ ] Collection-year spread noted for the limitations section\n"
        "- [ ] Any deviation logged in outputs/deviation_log.md before analysis begins\n",
    ]
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    try:
        res = run_audit(cfg)
    except FileNotFoundError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    out = Path(res["out_dir"])
    try:
        out = out.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        pass
    print(f"Audit written to {out.as_posix()}")
    print(res["stop_rule"].to_string(index=False))
    if not res["unresolved_primary"].empty:
        print("\nUNRESOLVED primary O*NET codes (fix crosswalk before analysis):", file=sys.stderr)
        print(res["unresolved_primary"][["soc6", "onet_code", "candidate_codes_with_soc6_prefix"]]
              .to_string(index=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
