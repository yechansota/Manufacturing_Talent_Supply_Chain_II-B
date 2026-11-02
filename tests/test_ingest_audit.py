"""O*NET ingest + audit tests on SYNTHETIC files shaped like O*NET 31.0 CSVs.

Values are random and carry no meaning; they only exercise the code paths
(schema check, cleaning, crosswalk resolution, audit metrics, stop rule, SE gaps).
"""
from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.audit import run_audit
from src.config import load_config
from src.frame import aggregation_rule, resolve_codes
from src.ingest_onet import IngestError, ingest, read_rating_file

ELEMENTS = {"knowledge": 3, "abilities": 4, "essential_skills": 2, "transferable_skills": 3}
MISSING_CODE = "49-2094.00"   # deliberately absent -> must be reported as unresolved
NO_SE_CODE = "49-9044.00"     # K rows without SE (mimics Occupational Expert rows)
SUPPRESSED_CODE = "51-4031.00"


def _codes(cfg) -> list[str]:
    codes = set()
    for key in ("targets_core", "targets_sensitivity", "feeders_core",
                "sensitivity_occupations", "negative_controls"):
        for soc6 in cfg["frame"][key]:
            for code, _ in resolve_codes(soc6, cfg):
                codes.add(code)
    codes |= {"11-1011.00", "29-1141.00", "15-1252.00"}   # extra reference-universe occupations
    codes.discard(MISSING_CODE)
    return sorted(codes)


def _write_synthetic(raw_dir: Path, cfg, rng: np.random.Generator) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    cols = cfg["data_versions"]["onet"]["expected_columns"]
    for key, spec in cfg["data_versions"]["onet"]["files"].items():
        rows = []
        for code in _codes(cfg):
            no_se = code == NO_SE_CODE and key == "knowledge"
            for e in range(ELEMENTS[key]):
                for scale, lo, hi in (("IM", 1, 5), ("LV", 0, 7)):
                    rows.append({
                        "O*NET-SOC Code": code, "Title": f"Synthetic {code}",
                        "Element ID": f"{key[:2]}.{e}", "Element Name": f"{key} element {e}",
                        "Scale ID": scale, "Scale Name": "Importance" if scale == "IM" else "Level",
                        "Data Value": f"{rng.uniform(lo, hi):.2f}", "N": "22",
                        "Standard Error": "" if no_se else f"{rng.uniform(0.05, 0.4):.4f}",
                        "Lower CI Bound": "", "Upper CI Bound": "",
                        "Recommend Suppress": "" if no_se else
                        ("Y" if (code == SUPPRESSED_CODE and key == "knowledge") else "N"),
                        "Not Relevant": ("N" if scale == "LV" else "n/a"),
                        "Date": "08/2025",
                        "Domain Source": "Occupational Expert" if no_se else "Analyst",
                    })
        pd.DataFrame(rows, columns=cols).to_csv(raw_dir / spec["file"], index=False)


@pytest.fixture()
def synthetic_repo(tmp_path: Path):
    cfg = copy.deepcopy(load_config())
    n_occ = len(_codes(cfg))
    cfg["data_versions"]["onet"]["expected_occupations"] = n_occ
    for key, spec in cfg["data_versions"]["onet"]["files"].items():
        spec["expected_elements"] = ELEMENTS[key]
        spec["expected_rows"] = n_occ * ELEMENTS[key] * 2
    _write_synthetic(tmp_path / cfg["paths"]["raw_onet"], cfg, np.random.default_rng(0))
    return cfg, tmp_path


def test_header_mismatch_raises(tmp_path: Path):
    cfg = load_config()
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"wrong": [1]}).to_csv(bad, index=False)
    with pytest.raises(IngestError):
        read_rating_file(bad, cfg["data_versions"]["onet"]["expected_columns"])


def test_strict_row_count_mismatch_raises(synthetic_repo):
    cfg, root = synthetic_repo
    cfg["data_versions"]["onet"]["files"]["knowledge"]["expected_rows"] += 1
    with pytest.raises(IngestError):
        ingest(cfg, root=root, strict=True)


def test_crosswalk_overrides():
    cfg = load_config()
    assert resolve_codes("51-2090", cfg) == [("51-2092.00", "primary")]
    assert resolve_codes("51-2028", cfg) == [("51-2022.00", "primary"), ("51-2023.00", "primary")]
    assert aggregation_rule("51-2028", cfg) == "equal_weight_profile_mean"
    assert resolve_codes("17-3024", cfg) == [("17-3024.00", "primary"), ("17-3024.01", "sensitivity")]
    assert resolve_codes("53-7062", cfg) == [("53-7062.00", "primary")]
    assert resolve_codes("49-9041", cfg) == [("49-9041.00", "primary")]


def test_end_to_end_audit(synthetic_repo):
    cfg, root = synthetic_repo
    assert ingest(cfg, root=root, strict=True)["problems"] == []
    res = run_audit(cfg, root=root)
    for name in ("audit_universe.csv", "audit_crosswalk.csv", "audit_frame.csv",
                 "audit_stop_rule.csv", "audit_missing_se.csv", "audit_summary.md"):
        assert (res["out_dir"] / name).exists()

    # Missing code is reported, not silently dropped.
    assert MISSING_CODE in set(res["unresolved_primary"]["onet_code"])

    # Coverage is complete for resolved primary codes.
    fa = res["frame_audit"]
    resolved = fa[(fa["mapping_type"] == "primary") & (fa["onet_code"] != MISSING_CODE)]
    assert (resolved["coverage"] == 1.0).all()

    # Stop rule: one suppressed core code in K; the no-SE code has missing flags (excluded from denominator).
    xw = res["crosswalk"]
    n_core = xw[(xw["mapping_type"] == "primary")
                & xw["role"].isin({"target_core", "feeder_core", "negative_control"})
                & xw["found_any_domain"]]["onet_code"].nunique()
    sr = res["stop_rule"].set_index("domain")
    assert sr.loc["K", "suppress_rate"] == pytest.approx(1 / (n_core - 1))
    assert sr.loc["K", "rows_flag_missing"] == ELEMENTS["knowledge"] * 2
    assert sr.loc["A", "suppress_rate"] == 0.0

    # SE gap is surfaced for imputation, only where it exists.
    ms = res["missing_se"]
    assert set(zip(ms["onet_code"], ms["domain"])) == {(NO_SE_CODE, "K")}

    # IM rows carry "n/a" for Not Relevant -> treated as missing, LV rate defined.
    assert resolved["not_relevant_rate_lv"].eq(0.0).all()
