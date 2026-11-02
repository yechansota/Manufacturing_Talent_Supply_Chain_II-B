"""Pure estimator functions (no I/O). Notation follows the pre-registration.

For target j, feeder i and element k in one domain:

    c_ijk = w_jk * max(0, z_jk - z_ik)            contribution (directional: no offsetting)
    D(i -> j) = sum_k c_ijk / sum_k w_jk          total deficit, in SD units
    C^(m)(i -> j) = sum of the m largest c_ijk / sum_k c_ijk     deficit concentration

with z standardized over the reference universe and w_jk = I_jk - 1.
"""
from __future__ import annotations

import numpy as np


def importance_weights(importance: np.ndarray) -> np.ndarray:
    """w = I - 1, clipped to [0, 4] (Importance is published on 1-5)."""
    return np.clip(np.asarray(importance, dtype=float) - 1.0, 0.0, 4.0)


def zscore(levels: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Column-wise z over the reference universe (rows = occupations). Sample SD (ddof=1)."""
    L = np.asarray(levels, dtype=float)
    mu = L.mean(axis=0)
    sd = L.std(axis=0, ddof=1)
    if np.any(sd <= 0):
        raise ValueError("an element has zero variance across the reference universe")
    return (L - mu) / sd, mu, sd


def contributions(z_target: np.ndarray, w_target: np.ndarray, Z: np.ndarray) -> np.ndarray:
    """c_ik for every row of Z (occupations x elements) against one target profile."""
    gap = np.asarray(z_target, dtype=float)[None, :] - np.atleast_2d(Z)
    return np.asarray(w_target, dtype=float)[None, :] * np.maximum(gap, 0.0)


def total_deficit(contrib: np.ndarray, w_target: np.ndarray) -> np.ndarray:
    wsum = float(np.sum(w_target))
    if wsum <= 0:
        raise ValueError("target importance weights sum to zero")
    return np.atleast_2d(contrib).sum(axis=1) / wsum


def concentration(contrib: np.ndarray, m: int) -> np.ndarray:
    """Share of the total deficit carried by the m largest contributions; NaN when total is 0."""
    c = np.atleast_2d(contrib)
    total = c.sum(axis=1)
    top = -np.sort(-c, axis=1)[:, :m].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(total > 0, top / np.where(total > 0, total, 1.0), np.nan)
    return out


def proximity_percentile(d_feeder: float, d_reference: np.ndarray) -> float:
    """P = 100 * share of reference occupations with D <= D(feeder) (lower = closer)."""
    ref = np.asarray(d_reference, dtype=float)
    return 100.0 * float(np.mean(ref <= d_feeder))


def ols_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Intercept and slope of y = a + b x."""
    X = np.column_stack([np.ones_like(x), x])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float(coef[0]), float(coef[1])
