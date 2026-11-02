"""OEWS and EP parser tests on SYNTHETIC workbooks (values carry no meaning)."""
from __future__ import annotations

import copy
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from src.config import load_config
from src.frame import frame_table
from src.ingest_ep import EpError, crosswalk_check, ingest as ingest_ep
from src.ingest_oews import OewsError, ingest as ingest_oews


# ----------------------------------------------------------------------------- OEWS
def _oews_rows(cfg) -> list[dict]:
    rows = [{"OCC_CODE": "00-0000", "OCC_TITLE": "All Occupations", "O_GROUP": "total", "TOT_EMP": "100000"}]
    for rec in frame_table(cfg).itertuples(index=False):
        emp = "500" if rec.role == "target_sensitivity" else "5000"   # sensitivity targets fail the rule
        rows.append({"OCC_CODE": rec.soc6, "OCC_TITLE": f"Occ {rec.soc6}", "O_GROUP": "detailed", "TOT_EMP": emp})
    # OEWS publishes 51-2090 twice (broad + detailed) with identical values.
    rows.append({"OCC_CODE": "51-2090", "OCC_TITLE": "Occ 51-2090", "O_GROUP": "broad", "TOT_EMP": "5000"})
    rows.append({"OCC_CODE": "51-9199", "OCC_TITLE": "Production Workers, All Other", "O_GROUP": "detailed", "TOT_EMP": "9000"})
    out = []
    for r in rows:
        out.append({"AREA": "99", "NAICS": "336300", "NAICS_TITLE": "Motor Vehicle Parts Manufacturing",
                    "EMP_PRSE": "2.0", "PCT_TOTAL": "1", "H_MEAN": "25", "MEAN_PRSE": "0.5",
                    "H_MEDIAN": "*" if r["OCC_CODE"] == "49-9041" else "24", "A_MEDIAN": "50000", **r})
    return out


def _write_oews(cfg, root: Path, rows: list[dict]) -> None:
    ocfg = cfg["data_versions"]["oews"]
    folder = root / cfg["paths"]["raw_oews"]
    folder.mkdir(parents=True, exist_ok=True)
    xlsx = root / "tmp_nat4d.xlsx"
    pd.DataFrame(rows).to_excel(xlsx, index=False)
    with zipfile.ZipFile(folder / ocfg["file"], "w") as zf:
        zf.write(xlsx, ocfg["member"])


@pytest.fixture()
def oews_cfg():
    cfg = copy.deepcopy(load_config())
    cfg["data_versions"]["oews"]["expected_total_employment"] = 100000
    return cfg


def test_oews_pass_dedupe_and_tokens(oews_cfg, tmp_path):
    _write_oews(oews_cfg, tmp_path, _oews_rows(oews_cfg))
    res = ingest_oews(oews_cfg, root=tmp_path, strict=True)
    assert res["dup_log"]["OCC_CODE"].tolist() == ["51-2090"]
    v = res["validation"].set_index("soc6")
    assert v.loc["49-9041", "rule_pass"] and not v.loc["49-2094", "rule_pass"]
    assert (tmp_path / "outputs/validation/oews_frame_validation.csv").exists()


def test_oews_unexpected_qualifying_feeder_fails(oews_cfg, tmp_path):
    rows = _oews_rows(oews_cfg)
    rows.append({**rows[-1], "OCC_CODE": "51-9999", "OCC_TITLE": "New Production Occ", "TOT_EMP": "8000"})
    _write_oews(oews_cfg, tmp_path, rows)
    with pytest.raises(OewsError, match="51-9999"):
        ingest_oews(oews_cfg, root=tmp_path, strict=True)


def test_oews_conflicting_duplicates_fail(oews_cfg, tmp_path):
    rows = _oews_rows(oews_cfg)
    rows[-2] = {**rows[-2], "TOT_EMP": "4999"}   # broad 51-2090 row now disagrees
    _write_oews(oews_cfg, tmp_path, rows)
    with pytest.raises(OewsError, match="51-2090"):
        ingest_oews(oews_cfg, root=tmp_path, strict=True)


# ----------------------------------------------------------------------------- EP
def _write_ep(cfg, root: Path, title_period: str = "2025–35") -> None:
    ecfg = cfg["data_versions"]["ep"]
    folder = root / cfg["paths"]["raw_ep"]
    folder.mkdir(parents=True, exist_ok=True)
    socs = frame_table(cfg)["soc6"].tolist()

    sep_cols = ["2025 National Employment Matrix title", "2025 National Employment Matrix code", "Occupation type",
                "Employment, 2025", "Employment, 2035", "Employment change, numeric, 2025–35",
                "Employment change, percent, 2025–35", "Labor force exit rate, 2025–35 annual average",
                "Occupational transfer rate, 2025–35 annual average",
                "Total occupational separations rate, 2025–35 annual average",
                "Labor force exits, 2025–35 annual average", "Occupational transfers, 2025–35 annual average",
                "Total occupational separations, 2025–35 annual average",
                "Occupational openings, 2025–35 annual average"]
    sep = [[f"Table 1.10 Occupational separations and openings, projected {title_period}"] + [""] * 13, sep_cols]
    sep += [[f"Occ {s}", s, "Line item", "10", "11", "1", "10", "3", "5", "8", "0.3", "0.5", "0.8", "0.9"] for s in socs]
    sep += [["Source: U.S. Bureau of Labor Statistics."] + [""] * 13]
    edu_cols = ["2025 National Employment Matrix title", "2025 National Employment Matrix code",
                "Typical education needed for entry", "Work experience in a related occupation",
                "Typical on-the-job training needed to attain competency in the occupation",
                "Related Occupational Outlook Handbook (OOH) content"]
    edu = [["Table 5.4 Education and training assignments by detailed occupation, 2025"] + [""] * 5, edu_cols]
    edu += [[f"Occ {s}", s, "High school diploma or equivalent", "None", "Apprenticeship", "OOH Content"] for s in socs]

    xw_rows = [["BLS crosswalk"] + [""] * 3, [f"As of {ecfg['crosswalk_file']['as_of']}"] + [""] * 3,
               ["O*NET-SOC code", "O*NET-SOC title", "NEM Code", "NEM title"]]
    from src.frame import resolve_codes
    overrides = cfg["onet_crosswalk"]["overrides"]
    for s in socs:
        codes = [c for c, _ in resolve_codes(s, cfg)] + list((overrides.get(s, {}) or {}).get("excluded_codes", {}) or {})
        xw_rows += [[c, f"Title {c}", s, f"NEM {s}"] for c in codes]

    for key, rows, sheet in (("occupation_file", sep, "Table 1.10"), ("education_file", edu, "Table 5.4"),
                             ("crosswalk_file", xw_rows, "Crosswalk")):
        with pd.ExcelWriter(folder / ecfg[key]["file"]) as xw:
            pd.DataFrame(rows).to_excel(xw, sheet_name=sheet, header=False, index=False)


def test_ep_pass_and_none_is_text(tmp_path):
    cfg = load_config()
    _write_ep(cfg, tmp_path)
    res = ingest_ep(cfg, root=tmp_path, strict=True)
    assert (res["education"]["related_work_experience"] == "None").all()
    assert (res["xw_check"]["status"] == "OK").all()
    assert res["separations"]["openings_k"].notna().all()


def test_ep_wrong_projection_period_fails(tmp_path):
    cfg = load_config()
    _write_ep(cfg, tmp_path, title_period="2024–34")
    with pytest.raises(EpError, match="2025–35"):
        ingest_ep(cfg, root=tmp_path, strict=True)


def test_crosswalk_check_flags_unmapped_code():
    cfg = load_config()
    xw = pd.DataFrame({"onet_code": ["49-9041.00", "49-9041.99"], "nem_code": ["49-9041", "49-9041"],
                       "onet_title": ["a", "b"], "nem_title": ["x", "x"]})
    _, problems = crosswalk_check(cfg, xw)
    assert any("49-9041.99" in p for p in problems)
