"""Unit tests of the reusable functions on synthetic data (no files needed)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from oilgas.features import add_time_features, safe_ratio
from oilgas.readers import parse_decimal_comma
from oilgas.stats_analysis import robust_z, segment


def test_parse_decimal_comma():
    s = pd.Series(["134835,0003", "0", "7974", " 12,5 "])
    assert parse_decimal_comma(s).tolist() == [134835.0003, 0.0, 7974.0, 12.5]


def test_parse_decimal_comma_rejects_thousand_separators():
    with pytest.raises(ValueError):
        parse_decimal_comma(pd.Series(["1.234,5"]))


def test_safe_ratio_zero_and_missing_denominator():
    r = safe_ratio(pd.Series([1.0, 1.0, 1.0, 0.0]), pd.Series([2.0, 0.0, np.nan, 5.0]))
    assert r.iloc[0] == 0.5 and np.isnan(r.iloc[1]) and np.isnan(r.iloc[2]) and r.iloc[3] == 0.0
    assert not np.isinf(r).any()


def _panel(values, start="2020-01-01"):
    p = pd.period_range(start, periods=len(values), freq="M")
    return pd.DataFrame({"level": "national", "series": "oil", "uf": "All", "location": "All",
                         "period_date": p.to_timestamp(), "year": p.year, "month": p.month,
                         "days_in_month": p.days_in_month, "value": values})


def test_time_features_guard_first_observations():
    f = add_time_features(_panel(np.arange(1, 25, dtype=float) * 100))
    assert f.mom.iloc[0] != f.mom.iloc[0]                       # NaN
    assert f.yoy.iloc[:12].isna().all() and f.yoy.iloc[12:].notna().all()
    assert f.rolling_3m_daily_avg.iloc[:2].isna().all() and f.rolling_3m_daily_avg.iloc[2:].notna().all()
    assert f.rolling_12m_daily_avg.iloc[:11].isna().all() and f.rolling_12m_daily_avg.iloc[11:].notna().all()


def test_daily_average_uses_real_month_length():
    f = add_time_features(_panel([2900.0, 3100.0], start="2024-02-01"))     # Feb 2024 = 29 days
    assert f.daily_avg.tolist() == [100.0, 100.0]
    assert f.daily_avg_mom.iloc[1] == pytest.approx(0.0)
    assert f.mom.iloc[1] == pytest.approx(3100 / 2900 - 1)


def test_rolling_daily_average_is_volume_weighted():
    f = add_time_features(_panel([3100.0, 2800.0, 3100.0], start="2023-01-01"))
    assert f.rolling_3m_daily_avg.iloc[2] == pytest.approx(9000 / 90)


def test_mom_nan_after_zero_and_missing():
    f = add_time_features(_panel([100.0, 0.0, 50.0, np.nan, 80.0]))
    assert f.mom.iloc[1] == pytest.approx(-1.0)      # 100 -> 0 is a real -100 %
    assert np.isnan(f.mom.iloc[2])                    # from 0: undefined
    assert np.isnan(f.mom.iloc[4])                    # from missing: undefined
    assert np.isnan(f.ytd_volume.iloc[3]) and np.isnan(f.ytd_volume.iloc[4])


def test_dense_grid_assertion():
    p = _panel([1.0, 2.0, 3.0]).drop(index=1)
    with pytest.raises(AssertionError):
        add_time_features(p)


def test_robust_z_flags_planted_outlier():
    x = pd.Series(np.r_[np.random.default_rng(1).normal(0, 1, 200), 15.0])
    z = robust_z(x)
    assert z.iloc[-1] > 3.5 and (z.iloc[:-1].abs() > 3.5).sum() <= 2


def test_segmentation_recovers_known_break():
    t = np.arange(120)
    y = np.where(t < 60, 0.01 * t, 0.6 - 0.005 * (t - 60)) + np.random.default_rng(7).normal(0, 0.002, 120)
    segs, _ = segment(y, k_max=4, min_len=24)
    assert len(segs) == 2 and abs(segs[0][1] - 60) <= 2
