"""Data tests on the raw files and the pipeline outputs."""
from __future__ import annotations

import csv
import hashlib

import numpy as np
import pandas as pd
import pytest

from conftest import BUILD_MONTH
from oilgas.config import RAW_DIR, SOURCES
from oilgas.readers import read_raw, read_tidy

KEY = ["series", "period_date", "uf", "location"]


def _manifest():
    with (RAW_DIR / "MANIFEST.csv").open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@pytest.mark.parametrize("row", _manifest(), ids=lambda r: r["file"])
def test_raw_file_matches_manifest(row):
    p = RAW_DIR / row["file"]
    assert p.stat().st_size == int(row["bytes"])
    assert hashlib.sha256(p.read_bytes()).hexdigest() == row["sha256"]


@pytest.mark.parametrize("key", list(SOURCES))
def test_raw_schema(key):
    cols = list(read_raw(key).columns)
    base = ["ANO", "MÊS", "GRANDE REGIÃO", "UNIDADE DA FEDERAÇÃO", "PRODUTO"]
    expected = base + ([] if key == "lgn" else ["LOCALIZAÇÃO"]) + [SOURCES[key][3]]
    assert cols == expected


@pytest.mark.parametrize("key", list(SOURCES))
def test_raw_values_parse_and_nonnegative_except_available(key):
    t = read_tidy(key)
    assert t.value.notna().all()
    if key != "available":
        assert (t.value >= 0).all()


def test_clean_keys_unique(long_clean):
    assert not long_clean.duplicated(KEY).any()


def test_no_future_periods(long_clean, features):
    assert long_clean.period_date.max() < BUILD_MONTH
    assert features.period_date.max() == long_clean.period_date.max() == pd.Timestamp("2026-09-01")


def test_placeholder_zeros_removed(long_clean):
    oil = long_clean[long_clean.series == "oil"]
    assert oil.period_date.max() == pd.Timestamp("2026-09-01")
    assert oil.groupby("period_date").value.sum().gt(0).all()


@pytest.mark.parametrize("key", list(SOURCES))
def test_reported_rows_equal_raw_minus_cutoff(long_clean, key):
    raw = read_tidy(key)
    raw_p = pd.PeriodIndex.from_fields(year=raw.year, month=raw.month, freq="M")
    expected = int((raw_p <= pd.Period("2026-09", "M")).sum())
    got = int(((long_clean.series == key) & (long_clean.status == "reported")).sum())
    assert got == expected


def test_not_reported_is_nan_never_zero(long_clean):
    nr = long_clean[long_clean.status == "not_reported"]
    assert len(nr) == 183 and nr.value.isna().all()
    assert long_clean[long_clean.status == "reported"].value.notna().all()


def test_negative_values_only_flagged_available(long_clean):
    neg = long_clean[long_clean.value < 0]
    assert (neg.series == "available").all() and neg.is_negative_balance.all() and len(neg) == 681


@pytest.mark.parametrize("series", ["oil", "gas", "reinjection", "flaring", "own_use", "available", "lgn"])
def test_grid_dense_per_entity(long_clean, series):
    s = long_clean[long_clean.series == series]
    for _, g in s.groupby(["uf", "location"]):
        p = g.period_date.sort_values().dt.to_period("M")
        assert (p.diff().iloc[1:].map(lambda x: x.n) == 1).all()


def test_days_in_month(long_clean):
    d = long_clean.drop_duplicates("period_date").set_index("period_date").days_in_month
    assert d[pd.Timestamp("2024-02-01")] == 29 and d[pd.Timestamp("2025-02-01")] == 28 and d[pd.Timestamp("2025-07-01")] == 31


def test_units_consistent(long_clean):
    u = long_clean.groupby("series").unit.unique().map(list).to_dict()
    assert u["oil"] == ["m3"] and u["lgn"] == ["m3"]
    assert all(u[k] == ["1000 m3"] for k in ("gas", "reinjection", "flaring", "own_use", "available"))


def test_oil_and_gas_never_summed(features):
    """No feature row mixes products: every row has exactly one series and its own unit."""
    assert features.groupby(["level", "uf", "location", "period_date"]).series.nunique().max() <= 7
    assert not any(c for c in features.columns if "boe" in c.lower())


def test_national_equals_sum_of_ufs(features):
    f = features[features.series.isin(["oil", "gas"])]
    nat = f[f.level == "national"].set_index(["series", "period_date"]).value
    ufs = f[f.level == "uf"].groupby(["series", "period_date"]).value.sum(min_count=1)
    loc = f[f.level == "location"].groupby(["series", "period_date"]).value.sum(min_count=1)
    assert np.allclose(nat, ufs.reindex(nat.index), rtol=1e-12)
    assert np.allclose(nat, loc.reindex(nat.index), rtol=1e-12)


def test_shares_between_zero_and_one_and_sum_to_one(features):
    f = features[(features.level == "location") & features.series.isin(["oil", "gas"])]
    assert f.share_of_national.between(0, 1).all()
    s = f.groupby(["series", "period_date"]).share_of_national.sum()
    assert np.allclose(s, 1.0)


def test_no_infinite_values(features, utilization):
    for df in (features, utilization):
        num = df.select_dtypes("number")
        assert not np.isinf(num.to_numpy(dtype=float)).any()


def test_mom_and_yoy_match_manual(features):
    n = features[(features.level == "national") & (features.series == "oil")].set_index("period_date")
    t, prev, ly = pd.Timestamp("2025-09-01"), pd.Timestamp("2025-08-01"), pd.Timestamp("2024-09-01")
    assert n.loc[t, "mom"] == pytest.approx(n.loc[t, "value"] / n.loc[prev, "value"] - 1)
    assert n.loc[t, "yoy"] == pytest.approx(n.loc[t, "value"] / n.loc[ly, "value"] - 1)
    assert n.loc[t, "oil_daily_avg_bbl"] == pytest.approx(n.loc[t, "value"] / 30 * 6.28981)


def test_annual_totals_reconcile_with_anuario():
    rec = pd.read_csv(RAW_DIR.parent / "interim" / "profile_anuario_reconciliation.csv")
    scale = {"oil": 1000 / 6.28981, "gas": 1000, "reinjection": 1000, "flaring": 1000}
    nat = rec.groupby(["file", "year"])[["value_anuario", "value_monthly"]].sum()
    dev = (nat.value_monthly / nat.value_anuario / nat.index.get_level_values(0).map(scale) - 1).abs()
    assert dev.max() < 0.0005          # within 0.05 % for every series and year 2016-2025


def test_gas_balance_closes_nationally(utilization):
    n = utilization[(utilization.level == "national") & utilization.gas_production_1000m3.gt(0)]
    # 1997-1999: production exists but the use flows start in 2000 -> gap must be NaN, not a fake 100 %
    assert n.loc[n.year < 2000, "balance_gap_pct"].isna().all()
    n = n.dropna(subset=["balance_gap_pct"])
    assert len(n) == 321
    ok = n.balance_gap_pct.abs() <= 0.005
    # 307, not the 308 of Phase 2 profiling: profiling dropped UF-months with an unpublished flow; here each flow is
    # summed nationally, so Dec 2024 (reinjection/own use unpublished in several UFs) closes at -0.503 %.
    assert ok.mean() >= 0.95 and int(ok.sum()) == 307
    assert set(n.loc[n.balance_gap_pct.abs() > 0.1, "period_date"].dt.strftime("%Y-%m")) == {"2005-07"}


def test_utilization_rates_valid(utilization):
    n = utilization[utilization.level.isin(["national", "location"])]
    for c in ("reinjection_rate", "flaring_loss_rate", "own_use_rate"):
        assert n[c].dropna().between(0, 1.5).all(), c
    assert utilization.loc[utilization.level.isin(["uf", "uf_location"]), "allocation_sensitive"].all()
