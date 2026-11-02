"""Checks on the REAL pinned data (skipped when data/raw is empty, e.g. in a fresh clone).

These lock in the audited facts the pre-registration relies on, so a silent
change in an input file is caught before any estimand is computed.
"""
from __future__ import annotations

import copy

import duckdb
import pytest

from src.config import REPO_ROOT, load_config, repo_path

CFG = load_config()
RAW_PRESENT = all((repo_path(CFG["paths"]["raw_onet"]) / s["file"]).exists()
                  for s in CFG["data_versions"]["onet"]["files"].values())
pytestmark = pytest.mark.skipif(not RAW_PRESENT, reason="raw data not downloaded")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """Run the full ingest into a temporary DuckDB so the project DB is untouched."""
    from src.audit import run_audit
    from src.ingest_ep import ingest as ingest_ep
    from src.ingest_oews import ingest as ingest_oews
    from src.ingest_onet import ingest as ingest_onet

    tmp = tmp_path_factory.mktemp("real")
    cfg = copy.deepcopy(CFG)
    for key in ("raw_onet", "raw_oews", "raw_ep"):
        cfg["paths"][key] = str(repo_path(CFG["paths"][key]))
    cfg["paths"]["duckdb"] = str(tmp / "test.duckdb")
    cfg["paths"]["audit_out"] = str(tmp / "audit")
    cfg["paths"]["validation_out"] = str(tmp / "validation")
    ingest_onet(cfg, root=REPO_ROOT, strict=True)
    audit = run_audit(cfg, root=REPO_ROOT)
    oews = ingest_oews(cfg, root=REPO_ROOT, strict=True)
    ep = ingest_ep(cfg, root=REPO_ROOT, strict=True)
    return {"cfg": cfg, "audit": audit, "oews": oews, "ep": ep}


def test_no_unresolved_codes(built):
    assert built["audit"]["unresolved_primary"].empty


def test_stop_rule_values(built):
    sr = built["audit"]["stop_rule"].set_index("domain")
    assert (sr["decision"] == "PASS").all()
    assert (sr.loc["K", "suppress_Y"], sr.loc["K", "rows_flag_known"]) == (189, 1188)


def test_missing_se_cases(built):
    ms = built["audit"]["missing_se"]
    assert set(zip(ms["onet_code"], ms["domain"])) == {("49-9044.00", "K"), ("17-3024.01", "K")}
    uni = built["audit"]["universe"].set_index("domain")
    assert uni.loc["K", "occupations_with_missing_se"] == 257
    assert uni.loc["S", "occupations_with_missing_se"] == 0 and uni.loc["A", "occupations_with_missing_se"] == 0


def test_frame_rules_hold(built):
    v = built["oews"]["validation"].set_index("soc6")
    core = CFG["frame"]["targets_core"] + CFG["frame"]["feeders_core"]
    assert v.loc[core, "rule_pass"].all()
    assert built["oews"]["problems"] == []


def test_ep_crosswalk_ok(built):
    assert (built["ep"]["xw_check"]["status"] == "OK").all()


def test_duckdb_tables(built):
    with duckdb.connect(built["cfg"]["paths"]["duckdb"], read_only=True) as con:
        tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    assert {"onet_ratings", "onet_file_meta", "oews_3363", "ep_separations",
            "ep_education", "ep_onet_nem_crosswalk"} <= tables
