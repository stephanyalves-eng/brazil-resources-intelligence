"""Phase 6 - Exploratory data analysis (descriptive, trend, regional, seasonality).

Input : data/processed/features_production_monthly.csv, gas_utilization_monthly.csv
Output: data/processed/analysis/eda_*.csv

Only complete calendar years enter annual comparisons (2026 is partial and provisional).
CLI:  python -m oilgas.eda
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from oilgas.config import PROCESSED_DIR

OUT = PROCESSED_DIR / "analysis"
LAST_FULL_YEAR = 2025
RNG = np.random.default_rng(20261118)  # fixed seed: permutation tests are reproducible


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    f = pd.read_csv(PROCESSED_DIR / "features_production_monthly.csv", parse_dates=["period_date"])
    u = pd.read_csv(PROCESSED_DIR / "gas_utilization_monthly.csv", parse_dates=["period_date"])
    return f, u


def national(f: pd.DataFrame, series: str) -> pd.DataFrame:
    return f[(f.level == "national") & (f.series == series)].sort_values("period_date").reset_index(drop=True)


def annual_table(f: pd.DataFrame) -> pd.DataFrame:
    """Annual volume and daily average (volume / days in year), oil & gas, national + offshore share."""
    rows = []
    for s in ("oil", "gas", "lgn"):
        n = national(f, s)
        a = n.groupby("year").agg(volume=("value", "sum"), days=("days_in_month", "sum"), months=("value", "count"))
        a = a[a.months == 12]
        a["daily_avg"] = a.volume / a.days
        a["yoy"] = a.volume.pct_change(fill_method=None)
        a.loc[a.index.to_series().diff() != 1, "yoy"] = np.nan
        if s != "lgn":
            off = f[(f.level == "location") & (f.series == s) & (f.location == "Offshore")].groupby("year").value.sum()
            a["offshore_share"] = off.reindex(a.index) / a.volume
        a["series"] = s
        rows.append(a.reset_index())
    return pd.concat(rows, ignore_index=True)


def descriptive(f: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for s, unit in (("oil", "m3/d"), ("gas", "1000 m3/d"), ("lgn", "m3/d")):
        n = national(f, s).dropna(subset=["daily_avg"])
        full = n[n.year <= LAST_FULL_YEAR]
        a = full.groupby("year").apply(lambda g: g.value.sum() / g.days_in_month.sum(), include_groups=False)
        def cagr(y0, y1):
            return (a[y1] / a[y0]) ** (1 / (y1 - y0)) - 1 if y0 in a and y1 in a and a[y0] > 0 else np.nan
        peak = n.loc[n.daily_avg.idxmax()]
        rows.append({
            "series": s, "unit": unit, "first_month": n.period_date.min().date(), "last_month": n.period_date.max().date(),
            "n_months": len(n), "mean_daily": n.daily_avg.mean(), "median_daily": n.daily_avg.median(),
            "std_daily": n.daily_avg.std(), "min_daily": n.daily_avg.min(), "max_daily": n.daily_avg.max(),
            "peak_month": peak.period_date.date(), "last_daily": n.daily_avg.iloc[-1],
            "cagr_2000_2025": cagr(2000, 2025), "cagr_2015_2025": cagr(2015, 2025), "cagr_2020_2025": cagr(2020, 2025),
        })
    return pd.DataFrame(rows)


def log_linear_trend(f: pd.DataFrame, windows=((2000, 2009), (2010, 2016), (2017, 2025), (2000, 2025))) -> pd.DataFrame:
    """OLS of ln(annual daily average) on year -> constant annual growth rate and R^2 per window."""
    at = annual_table(f)
    rows = []
    for s in ("oil", "gas"):
        a = at[at.series == s].set_index("year").daily_avg
        for y0, y1 in windows:
            w = a.loc[y0:y1]
            x, y = w.index.values.astype(float), np.log(w.values)
            b, c = np.polyfit(x, y, 1)
            yhat = b * x + c
            r2 = 1 - ((y - yhat) ** 2).sum() / ((y - y.mean()) ** 2).sum()
            rows.append({"series": s, "window": f"{y0}-{y1}", "n_years": len(w),
                         "annual_growth": np.exp(b) - 1, "r2": r2})
    return pd.DataFrame(rows)


def regional(f: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """UF shares at reference years and the HHI of UF shares over time (geographic concentration)."""
    uf = f[(f.level == "uf") & f.series.isin(["oil", "gas"]) & (f.year <= LAST_FULL_YEAR)]
    ann = uf.groupby(["series", "year", "uf", "uf_name"]).value.sum().reset_index()
    ann["share"] = ann.value / ann.groupby(["series", "year"]).value.transform("sum")
    ref = ann[ann.year.isin([2000, 2010, 2015, 2020, 2025])].pivot_table(
        index=["series", "uf", "uf_name"], columns="year", values="share").reset_index()
    ref.columns = [str(c) for c in ref.columns]
    ref["change_2000_2025_pp"] = (ref["2025"] - ref["2000"]) * 100
    hhi = (ann.assign(sq=(ann.share * 100) ** 2).groupby(["series", "year"])
           .agg(hhi=("sq", "sum"), top_uf=("share", lambda s: ann.loc[s.idxmax(), "uf"]),
                top_share=("share", "max")).reset_index())
    return ref.sort_values(["series", "2025"], ascending=[True, False]), hhi


def onshore_offshore(f: pd.DataFrame) -> pd.DataFrame:
    loc = f[(f.level == "location") & f.series.isin(["oil", "gas"]) & (f.year <= LAST_FULL_YEAR)]
    a = loc.groupby(["series", "location", "year"]).agg(v=("value", "sum"), d=("days_in_month", "sum")).reset_index()
    a["daily_avg"] = a.v / a.d
    p = a.pivot_table(index=["series", "year"], columns="location", values="daily_avg").reset_index()
    p.columns.name = None
    return p.rename(columns={"Offshore": "offshore_daily_avg", "Onshore": "onshore_daily_avg"})


def seasonality(f: pd.DataFrame, start_year: int = 2011) -> pd.DataFrame:
    """Ratio to a centred 12-month moving average of the daily average (classical decomposition),
    averaged by calendar month. Significance by permutation test of eta^2 (share of variance
    explained by calendar month), 5,000 shuffles."""
    rows = []
    for s in ("oil", "gas"):
        n = national(f, s).set_index("period_date")
        d = n.daily_avg
        cma = d.rolling(12, center=True).mean().rolling(2).mean().shift(-1)   # 2x12 centred MA
        ratio = (d / cma).dropna()
        ratio = ratio[ratio.index.year >= start_year]
        m = ratio.index.month.values
        x = ratio.values

        def eta2(lbl):
            grand = x.mean()
            ssb = sum(((x[lbl == k].mean() - grand) ** 2) * (lbl == k).sum() for k in range(1, 13))
            return ssb / ((x - grand) ** 2).sum()

        obs = eta2(m)
        perm = np.array([eta2(RNG.permutation(m)) for _ in range(5000)])
        p = (1 + (perm >= obs).sum()) / (1 + len(perm))
        by_m = pd.Series(x).groupby(m).agg(["mean", "std", "count"])
        for k, r in by_m.iterrows():
            rows.append({"series": s, "month": k, "seasonal_index": r["mean"], "std": r["std"], "n": int(r["count"]),
                         "eta2": obs, "perm_p_value": p, "window": f"{start_year}-{ratio.index.max():%Y-%m}"})
    return pd.DataFrame(rows)


def gas_utilization_annual(u: pd.DataFrame) -> pd.DataFrame:
    nat = u[u.level.isin(["national", "location"]) & (u.year <= LAST_FULL_YEAR)]
    cols = ["gas_production_1000m3", "reinjection_1000m3", "flaring_loss_1000m3", "own_use_1000m3", "available_1000m3"]
    a = nat.groupby(["level", "location", "year"])[cols].sum(min_count=1).reset_index()
    g = a.gas_production_1000m3.where(a.gas_production_1000m3 > 0)
    a["reinjection_rate"] = a.reinjection_1000m3 / g
    a["flaring_loss_rate"] = a.flaring_loss_1000m3 / g
    a["own_use_rate"] = a.own_use_1000m3 / g
    a["available_rate"] = a.available_1000m3 / g
    a["balance_gap_pct"] = (a.gas_production_1000m3 - a[cols[1:]].sum(axis=1)) / g
    return a


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    f, u = load()
    outputs = {
        "eda_annual": annual_table(f),
        "eda_descriptive": descriptive(f),
        "eda_trend_loglinear": log_linear_trend(f),
        "eda_onshore_offshore": onshore_offshore(f),
        "eda_seasonality": seasonality(f),
        "eda_gas_utilization_annual": gas_utilization_annual(u),
    }
    ref, hhi = regional(f)
    outputs["eda_regional_shares"] = ref
    outputs["eda_regional_hhi"] = hhi
    for name, df in outputs.items():
        df.to_csv(OUT / f"{name}.csv", index=False)
    with pd.option_context("display.width", 220, "display.max_columns", 30, "display.float_format", "{:,.4f}".format):
        for name in ("eda_descriptive", "eda_trend_loglinear"):
            print(f"\n== {name}\n", outputs[name].to_string(index=False))
        s = outputs["eda_seasonality"]
        print("\n== seasonality (eta2, permutation p)\n", s.groupby("series")[["eta2", "perm_p_value"]].first())
        print(s.pivot_table(index="month", columns="series", values="seasonal_index").round(4).T.to_string())
        at = outputs["eda_annual"]
        print("\n== annual oil & gas (2015+)\n", at[(at.year >= 2015) & (at.series != "lgn")]
              [["series", "year", "volume", "daily_avg", "yoy", "offshore_share"]].to_string(index=False))
        print("\n== regional shares\n", ref.to_string(index=False))
        print("\n== HHI (every 5 years)\n", hhi[hhi.year % 5 == 0].to_string(index=False))
        g = outputs["eda_gas_utilization_annual"]
        print("\n== gas utilization national\n", g[(g.level == "national") & (g.year % 5 == 0) | (g.level == "national") & (g.year >= 2021)]
              [["year", "reinjection_rate", "flaring_loss_rate", "own_use_rate", "available_rate", "balance_gap_pct"]].to_string(index=False))
        print("\n== gas utilization by location 2025\n", g[(g.level == "location") & (g.year.isin([2010, 2025]))]
              [["location", "year", "reinjection_rate", "flaring_loss_rate", "own_use_rate", "available_rate"]].to_string(index=False))


if __name__ == "__main__":
    main()
