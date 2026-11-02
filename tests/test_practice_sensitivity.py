"""Unit tests for the review-stage helpers (synthetic data; no download needed)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.deficit import contributions, total_deficit
from src.sensitivity import TIE_TOL, corr_matrix, draw_truncnorm, pct


def test_pct_counts_a_float_noise_self_tie():
    ref = np.array([0.1, 0.2, 0.3 + 1e-16, 0.4])
    assert pct(ref, 0.3) == 75.0                     # the 0.3 + 1e-16 row is the feeder itself
    assert 100.0 * np.mean(ref <= 0.3) == 50.0       # what a raw comparison would give
    assert TIE_TOL < 1e-9


def test_corr_matrix_is_valid_correlation():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(50, 8))
    X[:, 3] = X[:, 2]                                # exact collinearity -> PSD repair needed
    X[:, 5] = 1.0                                    # zero variance column -> NaN correlations
    R = corr_matrix(X)
    assert np.allclose(np.diag(R), 1.0)
    assert np.allclose(R, R.T)
    assert np.linalg.eigvalsh(R).min() > -1e-10
    np.linalg.cholesky(R)                            # must not raise


def test_draw_truncnorm_respects_bounds_and_zero_se():
    rng = np.random.default_rng(1)
    v = np.array([0.05, 3.5, 6.95, 2.0])
    se = np.array([0.5, 0.5, 0.5, 0.0])
    draws = np.stack([draw_truncnorm(v, se, 0.0, 7.0, rng.standard_normal(4)) for _ in range(2000)])
    assert draws.min() >= 0.0 and draws.max() <= 7.0
    assert np.all(draws[:, 3] == 2.0)                # SE = 0 -> value unchanged
    assert abs(np.median(draws[:, 1]) - 3.5) < 0.05  # symmetric when far from the bounds


def test_comonotone_scores_move_together():
    z = np.repeat(np.random.default_rng(2).standard_normal((5, 1)), 4, axis=1)
    out = draw_truncnorm(np.full((5, 4), 3.0), np.full((5, 4), 0.2), 0.0, 7.0, z)
    assert np.allclose(out, out[:, [0]])             # same quantile on every element of an occupation


def test_gap_contributions_sum_to_deficit():
    rng = np.random.default_rng(3)
    z_t, w_t, Z = rng.normal(size=6), rng.uniform(0.5, 3, 6), rng.normal(size=(4, 6))
    c = contributions(z_t, w_t, Z) / w_t.sum()
    assert np.allclose(c.sum(axis=1), total_deficit(contributions(z_t, w_t, Z), w_t))
    assert (c >= 0).all()


def test_training_share_over_one_year_logic():
    # category percentages for one occupation; categories >= 6 are 'over 1 year'
    dist = pd.Series([5, 10, 20, 15, 10, 25, 10, 5, 0], index=range(1, 10), dtype=float)
    share = dist[dist.index >= 6].sum() / dist.sum() * 100
    med = int(dist.index[np.searchsorted((dist / dist.sum() * 100).cumsum().to_numpy(), 50.0)])
    assert share == 40.0
    assert med == 4                                  # cumulative 5, 15, 35, 50 -> category 4 reaches 50%


def test_read_nem_parses_bls_export(tmp_path):
    from src.practice import read_nem
    csv = tmp_path / "nem.csv"
    csv.write_text(
        '"Occupation Title","Occupation Code","Occupation Type","2025 Employment","2025 Percent of Industry",'
        '"2025 Percent of Occupation","Projected 2035 Employment","Projected 2035 Percent of Industry",'
        '"Projected 2035 Percent of Occupation","Employment Change, 2025-2035","Employment Percent Change, 2025-2035",'
        '"Occupation Sort","Display Level"\n'
        '"Total, all occupations","=""00-0000""","Summary","524.7","100.0","0.3","451.5","100.0","0.3","-73.2","-13.9","","0"\n'
        '"Industrial machinery mechanics","=""49-9041""","Line Item","12.9","2.5","2.9","13.4","3.0","2.6","0.6","4.5","885","4"\n',
        encoding="utf-8")
    t = read_nem(csv).set_index("code")
    assert list(t.index) == ["00-0000", "49-9041"]
    assert t.loc["49-9041", "change_pct"] == 4.5 and t.loc["00-0000", "emp_2035_k"] == 451.5


def test_read_ces_fred_csv_and_bls_xlsx(tmp_path):
    from src.trend import read_monthly
    fred = tmp_path / "CEU3133630001.csv"
    fred.write_text("observation_date,CEU3133630001\n2024-01-01,540.1\n2024-02-01,541.3\n", encoding="utf-8")
    m = read_monthly(fred)
    assert list(m.emp_k) == [540.1, 541.3] and str(m.date.iloc[0].date()) == "2024-01-01"
    rows = [["Series Id:", "CEU3133630001"], [], ["Year"] + ["Jan", "Feb", "Mar"], [2024, 540.1, 541.3, 542.0]]
    x = pd.DataFrame(rows)
    path = tmp_path / "SeriesReport.xlsx"
    x.to_excel(path, header=False, index=False)
    m2 = read_monthly(path)
    assert list(m2.emp_k) == [540.1, 541.3, 542.0]


def test_nem_baseline_is_mode_and_adjustment_formula():
    from src.practice import bls_adjustment_pct, nem_baseline
    t = pd.DataFrame({"type": ["Summary", "Line item", "Line item", "Line item", "Line item"],
                      "change_pct": [-13.9, -12.9, -12.9, 4.5, -21.6], "emp_2025_k": [10.0, 3.0, 2.0, 1.0, 4.0]})
    b = nem_baseline(t)
    assert b["baseline_change_pct"] == -12.9 and b["n_at_baseline"] == 2 and b["n_line_items"] == 4
    assert b["emp_2025_k_at_baseline"] == 5.0
    adj = bls_adjustment_pct([4.5, -12.9, -21.6], -12.9)
    assert np.allclose(adj, [100 * (1.045 / 0.871 - 1), 0.0, 100 * (0.784 / 0.871 - 1)])


def test_robustness_top3_is_order_free_and_stable():
    from src.robustness import _top3
    names = np.array(["a", "b", "c", "d"])
    assert _top3(names, np.array([3.0, 1.0, 2.0, 9.0])) == frozenset({"a", "b", "c"})
    assert _top3(names, np.array([1.0, 1.0, 1.0, 1.0])) == frozenset({"a", "b", "c"})   # stable sort on ties


def test_history_read_year_parses_zip_member(tmp_path):
    import zipfile
    from src.history import read_year
    cols = ["AREA", "NAICS", "NAICS_TITLE", "OCC_CODE", "OCC_TITLE", "O_GROUP", "TOT_EMP", "EMP_PRSE", "PCT_TOTAL",
            "H_MEAN", "MEAN_PRSE", "H_MEDIAN", "A_MEDIAN"]
    rows = [["99", "336300", "Parts", "00-0000", "All", "total", "1,000", "0.0", "100", "20", "0.1", "19", "40000"],
            ["99", "336300", "Parts", "49-9041", "IMM", "detailed", "50", "2.0", "5", "30", "0.4", "29", "60000"],
            ["99", "336300", "Parts", "51-2090", "Misc", "broad", "300", "1.0", "30", "18", "0.2", "17", "**"],
            ["99", "336300", "Parts", "51-2090", "Misc", "detailed", "300", "1.0", "30", "18", "0.2", "17", "**"],
            ["99", "336100", "Vehicles", "49-9041", "IMM", "detailed", "70", "2.0", "5", "31", "0.4", "30", "61000"]]
    x = tmp_path / "nat4d_M2021_dl.xlsx"
    pd.DataFrame(rows, columns=[c.lower() for c in cols]).to_excel(x, index=False)    # 2021 files use lower case
    z = tmp_path / "oesm21in4.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.write(x, "oesm21in4/nat4d_M2021_dl.xlsx")
    d = read_year(z, 2021).set_index("OCC_CODE")
    assert list(d.index) == ["00-0000", "49-9041", "51-2090"]           # other industry dropped, duplicate resolved
    assert d.loc["00-0000", "TOT_EMP"] == 1000 and np.isnan(d.loc["51-2090", "A_MEDIAN"])






def test_bh_adjust_matches_hand_computation():
    from src.robustness import bh_adjust
    adj = bh_adjust([0.01, 0.04, 0.03, 0.2])
    # sorted 0.01, 0.03, 0.04, 0.2 -> 0.04, 0.06, 0.0533, 0.2 -> running minimum from the top
    assert np.allclose(adj, [0.04, 0.04 * 4 / 3, 0.04 * 4 / 3, 0.2])
    assert np.allclose(bh_adjust([0.001] * 24), 0.001)            # ties at the bootstrap floor all survive




def test_history_premium_z_on_log_ratio():
    from src.history import change_rows
    rows = []
    for y, (imm, mmw) in {2021: (30.0, 26.0), 2025: (33.0, 31.0)}.items():
        rows += [{"year": y, "soc6": "49-9041", "role": "maintenance target", "emp": 100.0, "emp_rse": 5.0,
                  "a_median": 60000.0, "h_mean": imm, "mean_prse": 1.0, "premium_mean_49_9041_over_pct": np.nan},
                 {"year": y, "soc6": "49-9043", "role": "maintenance target", "emp": 50.0, "emp_rse": 10.0,
                  "a_median": 50000.0, "h_mean": mmw, "mean_prse": 2.0,
                  "premium_mean_49_9041_over_pct": 100 * (imm / mmw - 1)}]
    mix = pd.DataFrame(rows).assign(title="")
    c = change_rows(mix, 2021, 2025).set_index("soc6")
    want = (np.log(33 / 31) - np.log(30 / 26)) / (np.sqrt(1 + 4 + 1 + 4) / 100)
    assert np.isclose(c.at["49-9043", "premium_mean_change_z"], want)
    assert np.isnan(c.at["49-9041", "premium_mean_change_z"])




