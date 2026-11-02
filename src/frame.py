"""Analysis frame helpers shared by audit and parsers.

The frame (which SOC codes play which role) and the SOC-6 -> O*NET-SOC mapping
are defined only in config/prereg.yaml; this module just reads them.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

ROLE_KEYS = {
    "targets_core": "target_core",
    "targets_sensitivity": "target_sensitivity",
    "feeders_core": "feeder_core",
    "sensitivity_occupations": "sensitivity",
    "negative_controls": "negative_control",
}
CORE_ROLES = {"target_core", "feeder_core", "negative_control"}


def frame_table(cfg: dict[str, Any]) -> pd.DataFrame:
    """One row per SOC-6 code with its pre-registered role."""
    rows = [{"soc6": soc6, "role": role}
            for key, role in ROLE_KEYS.items()
            for soc6 in cfg["frame"].get(key, [])]
    df = pd.DataFrame(rows)
    dup = df["soc6"].duplicated()
    if dup.any():
        raise ValueError(f"SOC codes assigned to more than one role: {df.loc[dup, 'soc6'].tolist()}")
    return df


def resolve_codes(soc6: str, cfg: dict[str, Any]) -> list[tuple[str, str]]:
    """Return [(onet_code, mapping_type)], mapping_type in {'primary', 'sensitivity'}."""
    xw = cfg["onet_crosswalk"]
    ov = xw.get("overrides", {}).get(soc6)
    if ov:
        out = [(c, "primary") for c in ov.get("primary", [])]
        out += [(c, "sensitivity") for c in ov.get("sensitivity_codes", [])]
        return out
    return [(soc6 + xw["default_suffix"], "primary")]


def aggregation_rule(soc6: str, cfg: dict[str, Any]) -> str:
    """How multiple primary O*NET codes are combined for one SOC-6 code."""
    ov = cfg["onet_crosswalk"].get("overrides", {}).get(soc6)
    return ov.get("aggregation", "single") if ov else "single"
