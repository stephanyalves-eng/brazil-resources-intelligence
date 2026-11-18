"""Integrity of the Tableau extracts (tableau/data/*.csv) against the dictionary and the pipeline outputs."""
from __future__ import annotations

import csv
from collections import defaultdict

import numpy as np
import pandas as pd
import pytest

from oilgas.config import PROJECT_ROOT

DATA = PROJECT_ROOT / "tableau" / "data"
FILES = sorted(DATA.glob("*.csv"))


@pytest.fixture(scope="module")
def prod() -> pd.DataFrame:
    return pd.read_csv(DATA / "production_monthly.csv", parse_dates=["period_date"])


@pytest.fixture(scope="module")
def util() -> pd.DataFrame:
    return pd.read_csv(DATA / "gas_utilization_monthly.csv", parse_dates=["period_date"])


def dictionary() -> dict[str, list[str]]:
    d = defaultdict(list)
    with (PROJECT_ROOT / "tableau" / "data_dictionary.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            d[r["table"]].append(r["column"])
    return d


def test_exports_exist():
    assert len(FILES) == 9


def test_dictionary_covers_every_file_and_column():
    d = dictionary()
    assert set(d) == {f.stem for f in FILES}
    for f in FILES:
        with f.open(encoding="utf-8") as fh:
            assert next(csv.reader(fh)) == d[f.stem], f.name


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_encoding_and_no_sentinel_strings(path):
    raw = path.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8")
    for bad in (",nan,", ",NaN,", ",None,", ",inf,", ",-inf,"):
        assert bad not in text, f"{bad} in {path.name}"
    assert path.stat().st_size < 15_000_000


def test_production_keys_unique(prod):
    assert not prod.duplicated(["level", "uf", "location", "product", "period_date"]).any()


def test_production_matches_features(prod, features):
    f = features[features.series.isin(["oil", "gas", "lgn"])]
    assert len(prod) == len(f)
    for product, series in (("Oil", "oil"), ("Natural gas", "gas"), ("NGL (LGN)", "lgn")):
        a = prod[(prod["product"] == product) & (prod.level == "national")].volume.sum()
        b = f[(f.series == series) & (f.level == "national")].value.sum()
        assert a == pytest.approx(b, rel=1e-9)


def test_each_level_sums_to_national(prod):
    for product in ("Oil", "Natural gas"):
        p = prod[prod["product"] == product]
        nat = p[p.level == "national"].groupby("period_date").volume.sum()
        for lvl in ("location", "uf", "uf_location"):
            s = p[p.level == lvl].groupby("period_date").volume.sum(min_count=1)
            assert np.allclose(nat, s.reindex(nat.index), rtol=1e-6), (product, lvl)


def test_daily_avg_recomputable(prod):
    ok = prod.dropna(subset=["volume"])
    # exports are rounded to 6 decimals, so tiny volumes need an absolute tolerance
    assert np.allclose(ok.volume / ok.days_in_month, ok.daily_avg, rtol=1e-6, atol=1e-6)


def test_no_future_periods_and_cutoff(prod, util):
    assert prod.period_date.max() == util.period_date.max() == pd.Timestamp("2026-09-01")


def test_units_by_product(prod):
    u = prod.groupby("product").unit.unique().map(list).to_dict()
    assert u == {"NGL (LGN)": ["m3"], "Natural gas": ["1000 m3"], "Oil": ["m3"]}
    assert prod.loc[prod["product"] != "Oil", "oil_daily_avg_bbl"].isna().all()


def test_anomaly_flags_match_anomaly_table(prod):
    an = pd.read_csv(DATA / "anomalies.csv")
    assert int(prod.is_statistical_anomaly.sum()) == len(an) == 60


def test_utilization_flows_and_rates(util):
    nat = util[util.level == "national"]
    assert np.allclose(nat.reinjection_rate.dropna(),
                       (nat.reinjection_1000m3 / nat.gas_production_1000m3)[nat.reinjection_rate.notna()], rtol=1e-5)
    assert util.period_date.min() == pd.Timestamp("2000-01-01")


def test_annual_summary_matches_production(prod):
    a = pd.read_csv(DATA / "annual_summary.csv")
    p = prod[(prod.level == "national") & (prod["product"] == "Oil") & (prod.year == 2025)]
    row = a[(a["product"] == "Oil") & (a.year == 2025)].iloc[0]
    assert row.annual_volume == pytest.approx(p.volume.sum(), rel=1e-6)
    assert row.annual_daily_avg == pytest.approx(p.volume.sum() / 365, rel=1e-6)


def test_dim_uf_covers_all_states(prod):
    d = pd.read_csv(DATA / "dim_uf.csv")
    assert set(prod.loc[prod.uf != "All", "uf"]) <= set(d.uf)
    assert d.iso_3166_2.str.match(r"^BR-[A-Z]{2}$").all()
