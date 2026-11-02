"""Unit checks for the CPS additions of II-B (DL-43, DL-45): origin groups and annualization."""
from __future__ import annotations

import pandas as pd
import pytest

from src import cps_moves as cm

SOC = {8030: "51-4041", 8950: "51-9198", 7340: "49-9071", 7610: "49-9098", 6355: "47-2111", 6260: "47-2061",
       9130: "53-3032", 1545: "17-3026", 5000: "43-1011"}
MFG = {3570, 3580}


def test_origin_group_order_and_exclusivity():
    occ = pd.Series([8030, 8030, 7610, 6260, 9130, 1545, 5000])
    ind = pd.Series([3570, 8000, 3570, 3570, 3570, 3570, 3570])
    assert list(cm.origin_group(occ, ind, SOC, MFG)) == cm.ORIGINS      # one code per origin, in the logged order


def test_annualize():
    assert cm.annualize(0.0) == pytest.approx(0.0)
    assert cm.annualize(1.0) == pytest.approx(100 * (1 - 0.99 ** 12))
