# KPI Definitions — Oil & Gas

Units: oil and NGL in m³, gas in thousand m³ (`1000 m3`). Oil and gas are **never added together**. "Latest" = Sep 2026 (provisional).
Reference values come from the 2026-11-18 build. Use them to verify the Tableau build (§7 of the build guide).

| # | KPI | Definition | Source · field | Tableau formula | Reference value | Caveat |
|---|---|---|---|---|---|---|
| K1 | Monthly production | Σ monthly volume | `production_monthly.volume` (level national) | `SUM([volume])` | Oil Sep 2026: 22.47 million m³ | One level, one product |
| K2 | Daily average production | volume / calendar days of the month | `volume`, `days_in_month` | `SUM([volume]) / SUM([days_in_month])` | Oil 748,985 m³/d · gas 223,878 thousand m³/d | Recompute; never average `daily_avg` |
| K3 | Oil in barrels per day | K2 × 6.28981 | `oil_daily_avg_bbl` | `[Daily Avg] * 6.28981` | 4.71 million bbl/d | Labelled unit conversion |
| K4 | MoM (daily-average basis) | K2(t) / K2(t−1) − 1 | `daily_avg_mom` | as stored (national row) | Oil +2.1 % (volume MoM −1.2 %) | Daily basis removes the month-length effect |
| K5 | YoY | volume(t) / volume(t−12) − 1 | `yoy` | as stored | Oil +20.3 %, gas +17.5 % | NULL in the first 12 months |
| K6 | Rolling 3M / 12M daily average | Σ volume / Σ days over the window | `rolling_3m_daily_avg`, `rolling_12m_daily_avg` | as stored | Oil 12M: 676,074 m³/d | NULL until the window is full |
| K7 | YTD cumulative production | Σ volume Jan → month | `ytd_volume` | as stored | — | NULL once a month in the year is missing |
| K8 | Annual production and daily average | Σ volume of a complete year; ÷ days in year | `annual_summary` | `SUM([annual_volume])` | Oil 2025: 599,389 m³/d (+12.0 %); gas 179,237 (+16.7 %) | Complete years only |
| K9 | Regional share | UF (or location) volume / national | `share_of_national` | `SUM([volume]) / TOTAL(SUM([volume]))` | RJ 87.8 % of oil (2025); offshore 97.6 % | Gas UF shares are allocation-sensitive |
| K10 | Geographic HHI | Σ (UF share %)² of annual volume | `regional_hhi.hhi` | `MAX([hhi])` | Oil 7,760; gas 6,033 (2025) | — |
| K11 | Historical peak / % of peak | Max daily average to date; K2 / peak | `historical_peak_daily_avg`, `pct_of_historical_peak` | as stored | Sep 2026 = 100 % (new peak) | — |
| K12 | Volatility | Rolling 12-month std of K4 | `volatility_12m` | as stored | — | By era: `stats` table in the findings |
| K13 | Deviation from baseline | K2 / mean of the previous 12 months − 1; z-score vs the same window | `deviation_from_baseline_pct`, `zscore_vs_prior_12m` | as stored | — | Current month excluded from the baseline |
| K14 | Statistical anomaly | robust z of K4 > 3.5 | `is_statistical_anomaly`, `anomalies` | as stored | 60 flagged months (7 at national level) | **Not** an operational incident |
| K15 | Structural regime growth | Annualised growth within a BIC-selected segment | `structural_breaks.annualised_growth` | as stored | Oil since Jul 2022 +8.7 %/yr; gas since Oct 2023 +15.9 %/yr | Two segment ends sit at the 36-month minimum |
| K16 | Seasonal index | Mean ratio to a centred 12-month average, by calendar month | `seasonality.seasonal_index` | as stored | April: oil 0.977, gas 0.964 | Exploratory; cause unknown |
| K17 | Reinjection rate | reinjection / gas production | `gas_utilization_monthly` | `SUM([reinjection_1000m3]) / SUM([gas_production_1000m3])` | 54.4 % (2025) | — |
| K18 | Flaring & losses rate | flaring and losses / production | same | `SUM([flaring_loss_1000m3]) / SUM([gas_production_1000m3])` | 2.83 % (2025) | — |
| K19 | Own-use rate / available rate | own use (or available) / production | same | `SUM(x) / SUM([gas_production_1000m3])` | 9.8 % / 33.4 % | Available can be negative at UF level |
| K20 | Balance gap | production − Σ uses, ÷ production | `balance_gap_pct` | `(SUM(prod) − SUM(uses)) / SUM(prod)` | 307 of 321 months within 0.5 % | Quality indicator |
