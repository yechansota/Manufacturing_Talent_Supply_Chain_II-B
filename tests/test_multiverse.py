"""Multiverse helpers reduce to the primary estimator when no cell is missing."""
from __future__ import annotations

import numpy as np

from src.deficit import concentration, contributions, total_deficit, zscore
from src.multiverse import k_star, masked_metrics, transform, weighted_profile


def test_k_star():
    assert k_star(12) == 3 and k_star(14) == 3


def test_masked_equals_primary_without_missing():
    rng = np.random.default_rng(3)
    L = rng.uniform(0, 7, size=(40, 6))
    I = rng.uniform(1, 5, size=(40, 6))
    avail = np.ones_like(L, dtype=bool)
    X = transform(L, avail, "z")
    Z, _, _ = zscore(L)
    assert np.allclose(X, Z)
    W = np.clip(I - 1, 0, 4)
    mix = np.array([0.6, 0.4])
    z_t = weighted_profile(X, np.array([0, 1]), mix)
    w_t = weighted_profile(W, np.array([0, 1]), mix)
    assert np.allclose(z_t, mix @ Z[[0, 1]]) and np.allclose(w_t, mix @ W[[0, 1]])
    D, C, _ = masked_metrics(z_t, w_t, X[2:], 3)
    c = contributions(z_t, w_t, Z[2:])
    assert np.allclose(D, total_deficit(c, w_t))
    assert np.allclose(C, concentration(c, 3), equal_nan=True)


def test_pairwise_deletion_drops_element_from_both_sides():
    z_t = np.array([1.0, 1.0]); w_t = np.array([1.0, 3.0])
    X = np.array([[0.0, np.nan]])
    D, C, neff = masked_metrics(z_t, w_t, X, 1)
    assert D[0] == 1.0 and C[0] == 1.0 and neff[0] == 1.0     # only element 1 counts, weight 1
