"""Standardization step: domain matrices, z-scores, and target/feeder profiles.

Primary specification only (prereg measurement.*_primary):
  * Level values as published (Not Relevant as published, Recommend Suppress kept)
  * z over all O*NET occupations rated in the domain (sample SD)
  * weights w = Importance - 1 of the target
Multiverse variants are added in a later step.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from .deficit import importance_weights, zscore
from .frame import aggregation_rule, frame_table, resolve_codes

FAMILY = "FAMILY"


@dataclass
class DomainData:
    domain: str
    codes: pd.Index                 # O*NET-SOC codes (rows)
    elements: pd.Index              # element IDs (columns)
    element_names: pd.Series        # element_id -> name
    titles: pd.Series               # onet_code -> title
    L: pd.DataFrame                 # Level
    I: pd.DataFrame                 # Importance
    Z: pd.DataFrame                 # standardized Level
    mu: pd.Series = field(default=None)
    sd: pd.Series = field(default=None)


@dataclass
class Profile:
    name: str                       # SOC-6 code or FAMILY
    role: str
    z: np.ndarray
    w: np.ndarray
    member_codes: list[str]         # O*NET codes that make up the profile
    weights_note: str = ""


def load_domain(con: duckdb.DuckDBPyConnection, domain: str, cfg: dict[str, Any]) -> DomainData:
    lv = cfg["measurement"]["scales"]["level"]["id"]
    im = cfg["measurement"]["scales"]["importance"]["id"]
    r = con.execute(
        "SELECT onet_code, title, element_id, element_name, scale_id, data_value "
        "FROM onet_ratings WHERE domain = ?", [domain]).df()
    L = r[r.scale_id == lv].pivot(index="onet_code", columns="element_id", values="data_value").sort_index()
    I = r[r.scale_id == im].pivot(index="onet_code", columns="element_id", values="data_value")
    I = I.loc[L.index, L.columns]
    if L.isna().any().any() or I.isna().any().any():
        raise ValueError(f"domain {domain}: incomplete occupation x element matrix")
    Z, mu, sd = zscore(L.to_numpy())
    names = r.drop_duplicates("element_id").set_index("element_id")["element_name"]
    titles = r.drop_duplicates("onet_code").set_index("onet_code")["title"]
    return DomainData(domain, L.index, L.columns, names, titles, L, I,
                      pd.DataFrame(Z, index=L.index, columns=L.columns),
                      pd.Series(mu, index=L.columns), pd.Series(sd, index=L.columns))


def _code_profile(dd: DomainData, codes: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Equal-weight mean of z and of Importance over the given O*NET codes."""
    z = dd.Z.loc[codes].to_numpy().mean(axis=0)
    imp = dd.I.loc[codes].to_numpy().mean(axis=0)
    return z, importance_weights(imp)


def soc_profile(dd: DomainData, soc6: str, role: str, cfg: dict[str, Any]) -> Profile:
    codes = [c for c, mtype in resolve_codes(soc6, cfg) if mtype == "primary"]
    rule = aggregation_rule(soc6, cfg)
    if len(codes) > 1 and rule != "equal_weight_profile_mean":
        raise ValueError(f"{soc6}: multiple primary codes but aggregation={rule}")
    z, w = _code_profile(dd, codes)
    return Profile(soc6, role, z, w, codes, rule)


def family_profile(dd: DomainData, cfg: dict[str, Any], employment: pd.Series) -> Profile:
    """Employment-share weighted mean of the core target profiles (prereg family_target)."""
    targets = cfg["frame"]["targets_core"]
    emp = employment.reindex(targets)
    if emp.isna().any():
        raise ValueError(f"missing OEWS employment for {emp[emp.isna()].index.tolist()}")
    pi = (emp / emp.sum()).to_numpy()
    profs = [soc_profile(dd, t, "target_core", cfg) for t in targets]
    z = sum(p * pr.z for p, pr in zip(pi, profs))
    w = sum(p * pr.w for p, pr in zip(pi, profs))
    members = [c for pr in profs for c in pr.member_codes]
    note = "; ".join(f"{t}={p:.4f}" for t, p in zip(targets, pi))
    return Profile(FAMILY, "family_target", z, w, members, note)


def build_profiles(dd: DomainData, cfg: dict[str, Any], employment: pd.Series
                   ) -> tuple[dict[str, Profile], dict[str, Profile]]:
    """Return (targets, feeders). Targets: core + sensitivity + FAMILY. Feeders: every other frame role."""
    frame = frame_table(cfg)
    targets = {FAMILY: family_profile(dd, cfg, employment)}
    feeders = {}
    for rec in frame.itertuples(index=False):
        prof = soc_profile(dd, rec.soc6, rec.role, cfg)
        (targets if rec.role.startswith("target") else feeders)[rec.soc6] = prof
    return targets, feeders
