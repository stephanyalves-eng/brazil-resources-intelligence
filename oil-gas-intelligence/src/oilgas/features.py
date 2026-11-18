"""Phase 5 - Feature engineering.

Input : data/interim/ppgn_long_clean.csv (from oilgas.cleaning)
Output: data/processed/features_production_monthly.csv  (one row per level x entity x series x month)
        data/processed/gas_utilization_monthly.csv      (gas balance ratios)

Aggregation levels: national, location (Onshore/Offshore), uf (all locations), uf_location.
'not_reported' cells contribute nothing to an aggregate; how many were missing is kept in
n_not_reported so a reader can see when a total is incomplete (an aggregate is NaN only when
*every* component is missing).

Guard rails:
  - All ratios return NaN when the denominator is 0 or missing (no inf, no fake +100 %).
  - MoM uses the previous calendar month, YoY the same month one year earlier; the grid is dense,
    so shift(1) / shift(12) are calendar-exact (asserted).
  - Rolling windows require a complete window (first 2 / 11 observations are NaN).
  - Rolling daily averages are volume-weighted: sum(volume) / sum(days), not a mean of monthly means.
  - Oil and gas are never added together.

CLI:  python -m oilgas.features
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from oilgas.config import BBL_PER_M3, INTERIM_DIR, PROCESSED_DIR

ALL = "All"


def safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    return num / den.where(den > 0)


def aggregate_levels(long: pd.DataFrame) -> pd.DataFrame:
    long = long.assign(missing=long.value.isna().astype(int))
    base = ["series", "unit", "period_date", "year", "month", "days_in_month", "is_provisional"]
    specs = {
        "national": [],
        "location": ["location"],
        "uf": ["uf", "uf_name", "region"],
        "uf_location": ["uf", "uf_name", "region", "location"],
    }
    parts = []
    for level, dims in specs.items():
        src = long
        if level in ("location", "uf_location"):
            src = long[long.series != "lgn"]  # LGN has no onshore/offshore split
        g = (src.groupby(base + dims, dropna=False)
             .agg(value=("value", lambda s: s.sum(min_count=1)), n_not_reported=("missing", "sum"))
             .reset_index())
        g["level"] = level
        for d in ("uf", "uf_name", "region", "location"):
            if d not in g:
                g[d] = ALL
        parts.append(g)
    out = pd.concat(parts, ignore_index=True)
    return out.sort_values(["level", "series", "uf", "location", "period_date"]).reset_index(drop=True)


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    keys = ["level", "series", "uf", "location"]
    df = df.copy()
    df["daily_avg"] = df.value / df.days_in_month
    out = []
    for _, g in df.groupby(keys, sort=False):
        g = g.sort_values("period_date").copy()
        p = g.period_date.dt.to_period("M")
        assert (p.diff().iloc[1:].map(lambda x: x.n) == 1).all(), "grid is not dense"
        v, days, d = g.value, g.days_in_month, g.daily_avg

        g["mom"] = safe_ratio(v, v.shift(1)) - 1
        g["yoy"] = safe_ratio(v, v.shift(12)) - 1
        g["daily_avg_mom"] = safe_ratio(d, d.shift(1)) - 1          # removes calendar-length effect
        g["rolling_3m_daily_avg"] = v.rolling(3, min_periods=3).sum() / days.rolling(3, min_periods=3).sum()
        g["rolling_12m_daily_avg"] = v.rolling(12, min_periods=12).sum() / days.rolling(12, min_periods=12).sum()

        ytd = v.groupby(g.year).cumsum()
        ytd_missing = v.isna().astype(int).groupby(g.year).cumsum() > 0
        g["ytd_volume"] = ytd.mask(ytd_missing)

        peak = d.cummax()
        g["historical_peak_daily_avg"] = peak
        g["pct_of_historical_peak"] = safe_ratio(d, peak)
        g["is_new_peak"] = (d >= peak) & d.notna() & (d > 0) & (d > d.shift(1).cummax().fillna(-np.inf))

        g["volatility_12m"] = g["daily_avg_mom"].rolling(12, min_periods=12).std()

        prev_mean = d.shift(1).rolling(12, min_periods=12).mean()
        prev_std = d.shift(1).rolling(12, min_periods=12).std()
        g["baseline_12m_prior_daily_avg"] = prev_mean
        g["deviation_from_baseline_pct"] = safe_ratio(d, prev_mean) - 1
        g["zscore_vs_prior_12m"] = (d - prev_mean) / prev_std.where(prev_std > 0)
        out.append(g)
    return pd.concat(out, ignore_index=True)


def add_shares(df: pd.DataFrame) -> pd.DataFrame:
    nat = df[df.level == "national"][["series", "period_date", "value"]].rename(columns={"value": "national_value"})
    df = df.merge(nat, on=["series", "period_date"], how="left", validate="many_to_one")
    df["share_of_national"] = safe_ratio(df.value, df.national_value)
    df.loc[df.level == "national", "share_of_national"] = np.nan
    return df.drop(columns="national_value")


def gas_utilization(levels: pd.DataFrame) -> pd.DataFrame:
    flows = ["gas", "reinjection", "flaring", "own_use", "available"]
    sub = levels[levels.series.isin(flows) & (levels.level != "uf")]   # uf_location carries UF detail
    sub = pd.concat([sub, levels[levels.series.isin(flows) & (levels.level == "uf")]])
    key = ["level", "uf", "uf_name", "region", "location", "period_date", "year", "month", "days_in_month", "is_provisional"]
    w = sub.set_index(key + ["series"])["value"].unstack("series").reset_index()
    w.columns.name = None
    w = w.rename(columns={"gas": "gas_production_1000m3", "reinjection": "reinjection_1000m3",
                          "flaring": "flaring_loss_1000m3", "own_use": "own_use_1000m3", "available": "available_1000m3"})
    prod = w.gas_production_1000m3
    w["reinjection_rate"] = safe_ratio(w.reinjection_1000m3, prod)
    w["flaring_loss_rate"] = safe_ratio(w.flaring_loss_1000m3, prod)
    w["own_use_rate"] = safe_ratio(w.own_use_1000m3, prod)
    w["available_rate"] = safe_ratio(w.available_1000m3, prod)
    uses = w[["reinjection_1000m3", "flaring_loss_1000m3", "own_use_1000m3", "available_1000m3"]].sum(axis=1, min_count=4)
    w["balance_gap_1000m3"] = prod - uses
    w["balance_gap_pct"] = safe_ratio(w.balance_gap_1000m3, prod)
    w["flaring_daily_avg_1000m3"] = w.flaring_loss_1000m3 / w.days_in_month
    # UF-level shares depend on ANP's allocation of volumes between states (see DATA_PROFILE §1 finding 4)
    w["allocation_sensitive"] = w.level.isin(["uf", "uf_location"])
    return w.sort_values(["level", "uf", "location", "period_date"]).reset_index(drop=True)


def build() -> tuple[pd.DataFrame, pd.DataFrame]:
    long = pd.read_csv(INTERIM_DIR / "ppgn_long_clean.csv", parse_dates=["period_date"])
    levels = aggregate_levels(long)
    feats = add_shares(add_time_features(levels))
    feats["oil_daily_avg_bbl"] = np.where(feats.series == "oil", feats.daily_avg * BBL_PER_M3, np.nan)
    return feats, gas_utilization(levels)


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    feats, util = build()
    feats.to_csv(PROCESSED_DIR / "features_production_monthly.csv", index=False, encoding="utf-8")
    util.to_csv(PROCESSED_DIR / "gas_utilization_monthly.csv", index=False, encoding="utf-8")
    print(f"features: {len(feats):,} rows x {feats.shape[1]} cols | gas utilization: {len(util):,} rows")
    print(feats.groupby(["level", "series"]).size().unstack(fill_value=0))
    nat = feats[(feats.level == "national") & feats.series.isin(["oil", "gas"])]
    last = nat[nat.period_date == nat.period_date.max()]
    print(last[["series", "period_date", "value", "daily_avg", "oil_daily_avg_bbl", "mom", "yoy",
                "rolling_12m_daily_avg", "pct_of_historical_peak", "zscore_vs_prior_12m"]].to_string(index=False))


if __name__ == "__main__":
    main()
