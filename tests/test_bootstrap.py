"""Bootstrap mechanics on toy data."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.bootstrap import (H1_GROUPS, Spec, evaluate, exact_permutation_p, group_diff,
                           impute_missing_se, sample_truncnorm)


def _toy(n=60, e=7, seed=0):
    rng = np.random.default_rng(seed)
    L = rng.uniform(0, 7, size=(n, e))
    I = rng.uniform(1, 5, size=(n, e))
    spec = Spec(target_names=["FAMILY", "t1"], target_members=[np.array([0, 1]), np.array([0])],
                target_mix=[np.array([0.7, 0.3]), np.ones(1)], feeder_names=["f1", "f2", "f3"],
                feeder_roles=["feeder_core", "feeder_core", "negative_control"],
                feeder_members=[np.array([5]), np.array([6, 7]), np.array([9])], family_index=0)
    return L, I, spec


def test_zero_se_reproduces_point():
    L, I, spec = _toy()
    rng = np.random.default_rng(1)
    Ls = sample_truncnorm(L, np.zeros_like(L), 0, 7, rng)
    a, b = evaluate(L, I, spec, 3), evaluate(Ls, I, spec, 3)
    for k in a:
        assert np.allclose(a[k], b[k], equal_nan=True)


def test_truncation_bounds_and_seed():
    L, _, _ = _toy()
    se = np.full_like(L, 2.0)
    x1 = sample_truncnorm(L, se, 0, 7, np.random.default_rng(5))
    x2 = sample_truncnorm(L, se, 0, 7, np.random.default_rng(5))
    assert (x1 >= 0).all() and (x1 <= 7).all()
    assert np.array_equal(x1, x2)


def test_point_outputs_in_range():
    L, I, spec = _toy()
    out = evaluate(L, I, spec, 3)
    assert ((out["P"] >= 0) & (out["P"] <= 100)).all()
    assert (out["D"] >= 0).all()
    assert ((out["neff"] >= 1) & (out["neff"] <= L.shape[1])).all()


def test_imputation_fills_only_missing_with_incumbent_median():
    se = pd.DataFrame({"e1": [0.1, 0.3, np.nan], "e2": [0.2, 0.4, np.nan]}, index=["a", "b", "c"])
    src = pd.Series({"a": "Incumbent", "b": "Incumbent", "c": "Occupational Expert"})
    filled, n = impute_missing_se(se, src)
    assert n == 2
    assert filled.loc["c"].tolist() == [0.2, 0.30000000000000004] or np.allclose(filled.loc["c"], [0.2, 0.3])
    assert filled.loc[["a", "b"]].equals(se.loc[["a", "b"]])


def test_exact_permutation():
    codes = sum(H1_GROUPS.values(), [])
    # Machining/welding strictly closest -> observed diff is the minimum -> p = 1/120
    P = pd.Series({c: (i + 1.0) for i, c in enumerate(codes)})
    obs, p, n = exact_permutation_p(P)
    assert n == 120 and obs == group_diff(P) and abs(p - 1 / 120) < 1e-12
