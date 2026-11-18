"""Phase 8 - Tableau extracts (pipeline step 8).

Writes slim, documented CSVs to tableau/data/:
  production_monthly.csv      level x entity x product (oil, gas, LGN) x month, with features
  gas_utilization_monthly.csv gas balance flows and rates
  annual_summary.csv          complete years, national
  regional_hhi.csv            geographic concentration by year
  structural_breaks.csv       BIC-selected growth regimes
  anomalies.csv               statistical anomalies (not incidents)
  seasonality.csv             seasonal index by calendar month
  dim_uf.csv, metadata.csv

Format: UTF-8 (no BOM), ',' delimiter, '.' decimal, ISO dates, empty = NULL.
Columns are described in tableau/data_dictionary.csv (a test enforces the match).

CLI:  python -m oilgas.tableau_export
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from oilgas.config import BBL_PER_M3, PROCESSED_DIR, PROJECT_ROOT, UF_REFERENCE

A = PROCESSED_DIR / "analysis"
OUT = PROJECT_ROOT / "tableau" / "data"

PRODUCT_LABEL = {"oil": "Oil", "gas": "Natural gas", "lgn": "NGL (LGN)"}
UNIT_DAILY = {"oil": "m3/d", "gas": "1000 m3/d", "lgn": "m3/d"}

PRODUCTION_COLS = [
    "level", "uf", "uf_name", "region", "location", "product", "unit", "unit_daily", "period_date", "year", "month",
    "days_in_month", "is_provisional", "n_not_reported", "volume", "daily_avg", "oil_daily_avg_bbl",
    "mom", "daily_avg_mom", "yoy", "rolling_3m_daily_avg", "rolling_12m_daily_avg", "ytd_volume",
    "share_of_national", "historical_peak_daily_avg", "pct_of_historical_peak", "is_new_peak", "volatility_12m",
    "baseline_12m_prior_daily_avg", "deviation_from_baseline_pct", "zscore_vs_prior_12m", "is_statistical_anomaly",
]


def _round(df: pd.DataFrame, digits: int = 6) -> pd.DataFrame:
    num = df.select_dtypes("float").columns
    df[num] = df[num].round(digits)
    return df


def _write(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT / name, index=False, encoding="utf-8", date_format="%Y-%m-%d", lineterminator="\n")


def production(f: pd.DataFrame, anomalies: pd.DataFrame) -> pd.DataFrame:
    p = f[f.series.isin(["oil", "gas", "lgn"])].copy()
    p["product"] = p.series.map(PRODUCT_LABEL)
    p["unit_daily"] = p.series.map(UNIT_DAILY)
    p = p.rename(columns={"value": "volume"})
    flags = set(zip(anomalies.series, anomalies.level, anomalies.location, anomalies.period))
    p["is_statistical_anomaly"] = [
        (s, l, loc, d.strftime("%Y-%m")) in flags for s, l, loc, d in zip(p.series, p.level, p.location, p.period_date)]
    p["is_new_peak"] = p.is_new_peak.astype(bool)
    return _round(p[PRODUCTION_COLS].sort_values(["product", "level", "uf", "location", "period_date"]))


def utilization(u: pd.DataFrame) -> pd.DataFrame:
    cols = ["level", "uf", "uf_name", "region", "location", "period_date", "year", "month", "days_in_month",
            "is_provisional", "gas_production_1000m3", "reinjection_1000m3", "flaring_loss_1000m3", "own_use_1000m3",
            "available_1000m3", "reinjection_rate", "flaring_loss_rate", "own_use_rate", "available_rate",
            "balance_gap_1000m3", "balance_gap_pct", "flaring_daily_avg_1000m3", "allocation_sensitive"]
    u = u[u.year >= 2000][cols].copy()
    return _round(u.sort_values(["level", "uf", "location", "period_date"]))


def annual(at: pd.DataFrame) -> pd.DataFrame:
    at = at.copy()
    at["product"] = at.series.map(PRODUCT_LABEL)
    at["unit_daily"] = at.series.map(UNIT_DAILY)
    at["oil_daily_avg_bbl"] = np.where(at.series == "oil", at.daily_avg * BBL_PER_M3, np.nan)
    at = at.rename(columns={"volume": "annual_volume", "daily_avg": "annual_daily_avg"})
    return _round(at[["year", "product", "unit_daily", "annual_volume", "annual_daily_avg", "oil_daily_avg_bbl",
                      "yoy", "offshore_share"]].sort_values(["product", "year"]))


def dim_uf() -> pd.DataFrame:
    return pd.DataFrame([{"uf": c, "uf_name": n, "region": r, "iso_3166_2": f"BR-{c}", "anp_name": k}
                         for k, (c, n, r) in UF_REFERENCE.items()]).sort_values("uf")


def metadata(f: pd.DataFrame) -> pd.DataFrame:
    last = f.period_date.max().strftime("%Y-%m")
    return pd.DataFrame([
        {"source_key": "ANP monthly", "source_name": "ANP - Produção de petróleo e gás natural por estado e localização",
         "url": "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/producao-de-petroleo-e-gas-natural-por-estado-e-localizacao",
         "coverage": f"1997-01 to {last} (gas uses from 2000-01)", "note": "Volumes: oil/NGL m3, gas 1000 m3; 2026 provisional"},
        {"source_key": "ANP Anuário 2026", "source_name": "Anuário Estatístico 2026 - tables 2.14, 2.19, 2.21, 2.22",
         "url": "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/anuario/anuario-estatistico-2026-dados-abertos",
         "coverage": "2016-2025 (annual)", "note": "Used for reconciliation only (<= 0.04 % national deviation)"},
        {"source_key": "Conversion", "source_name": "1 m3 = 6.28981 bbl", "url": "",
         "coverage": "", "note": "Applied only in oil_daily_avg_bbl; oil and gas are never summed"},
        {"source_key": "Snapshot", "source_name": "Raw files downloaded", "url": "data/raw/MANIFEST.csv",
         "coverage": "2026-11-18", "note": "SHA-256 of every raw file recorded"},
    ])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    f = pd.read_csv(PROCESSED_DIR / "features_production_monthly.csv", parse_dates=["period_date"])
    u = pd.read_csv(PROCESSED_DIR / "gas_utilization_monthly.csv", parse_dates=["period_date"])
    an = pd.read_csv(A / "stats_anomalies.csv")
    tables = {
        "production_monthly.csv": production(f, an),
        "gas_utilization_monthly.csv": utilization(u),
        "annual_summary.csv": annual(pd.read_csv(A / "eda_annual.csv")),
        "regional_hhi.csv": _round(pd.read_csv(A / "eda_regional_hhi.csv").assign(
            product=lambda d: d.series.map(PRODUCT_LABEL))[["year", "product", "hhi", "top_uf", "top_share"]]),
        "structural_breaks.csv": _round(pd.read_csv(A / "stats_structural_breaks.csv").assign(
            product=lambda d: d.series.map(PRODUCT_LABEL))[["product", "start", "end", "n_months", "annualised_growth",
                                                             "mean_daily_avg", "metric"]]),
        "anomalies.csv": _round(pd.read_csv(A / "stats_anomalies.csv").assign(
            product=lambda d: d.series.map(PRODUCT_LABEL))[["product", "level", "location", "period", "daily_avg",
                                                             "daily_avg_mom", "robust_z_mom", "zscore_vs_prior_12m",
                                                             "direction", "classification"]]),
        "seasonality.csv": _round(pd.read_csv(A / "eda_seasonality.csv").assign(
            product=lambda d: d.series.map(PRODUCT_LABEL))[["product", "month", "seasonal_index", "std", "n", "eta2",
                                                             "perm_p_value", "window"]]),
        "dim_uf.csv": dim_uf(),
        "metadata.csv": metadata(f),
    }
    for name, df in tables.items():
        _write(df, name)
        print(f"{name:<30} {len(df):>7,} rows  {(OUT / name).stat().st_size / 1e6:6.2f} MB")


if __name__ == "__main__":
    main()
