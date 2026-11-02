"""Invariants of the pure estimator functions (toy data, hand-checkable)."""
from __future__ import annotations

import numpy as np
import pytest

from src.deficit import (concentration, contributions, importance_weights, ols_fit,
                         proximity_percentile, total_deficit, zscore)


def test_hand_example():
    z_t = np.array([1.0, 0.0, 2.0])
    w_t = importance_weights(np.array([3.0, 1.0, 5.0]))          # -> [2, 0, 4]
    z_i = np.array([[0.0, -1.0, 2.5]])
    c = contributions(z_t, w_t, z_i)
    assert c.tolist() == [[2.0, 0.0, 0.0]]                        # surplus on element 3 does not offset
    assert total_deficit(c, w_t)[0] == pytest.approx(2.0 / 6.0)
    assert concentration(c, 1)[0] == pytest.approx(1.0)


def test_self_deficit_zero_and_nonnegative():
    rng = np.random.default_rng(1)
    Z = rng.normal(size=(50, 8))
    w = rng.uniform(0, 4, size=8)
    c = contributions(Z[3], w, Z)
    D = total_deficit(c, w)
    assert D[3] == 0.0
    assert (D >= 0).all()
    C = concentration(c, 3)
    assert np.isnan(C[3])                                        # undefined when total deficit is 0
    assert ((C[~np.isnan(C)] >= 0) & (C[~np.isnan(C)] <= 1 + 1e-12)).all()


def test_scale_invariance_of_P_and_C():
    rng = np.random.default_rng(2)
    Z = rng.normal(size=(40, 6))
    w = rng.uniform(0, 4, size=6)
    c1 = contributions(Z[0], w, Z)
    c2 = contributions(2.5 * Z[0], w, 2.5 * Z)
    D1, D2 = total_deficit(c1, w), total_deficit(c2, w)
    assert np.allclose(D2, 2.5 * D1)
    assert np.allclose(concentration(c1, 2), concentration(c2, 2), equal_nan=True)
    assert proximity_percentile(D1[5], D1[1:]) == proximity_percentile(D2[5], D2[1:])


def test_zero_weight_elements_never_contribute():
    c = contributions(np.array([5.0, 5.0]), np.array([0.0, 1.0]), np.array([[0.0, 0.0]]))
    assert c[0, 0] == 0.0 and c[0, 1] == 5.0


def test_zscore_and_percentile_and_ols():
    L = np.array([[1.0, 2.0], [3.0, 2.5], [5.0, 3.0]])
    Z, mu, sd = zscore(L)
    assert np.allclose(Z.mean(axis=0), 0) and np.allclose(Z.std(axis=0, ddof=1), 1)
    assert proximity_percentile(2.0, np.array([1.0, 2.0, 3.0, 4.0])) == 50.0
    a, b = ols_fit(np.array([0.0, 1.0, 2.0]), np.array([1.0, 3.0, 5.0]))
    assert (a, b) == pytest.approx((1.0, 2.0))
    with pytest.raises(ValueError):
        zscore(np.array([[1.0], [1.0]]))
