# Data Dictionary — oil-gas-intelligence

Generated from `tableau/data_dictionary.csv` by `shared/render_dictionary.py`; do not edit by hand.
Every exported column is listed (enforced by `tests/test_tableau_exports.py`). Files: `tableau/data/<table>.csv`.

## `production_monthly` — 29,631 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `level` | String |  | Aggregation level: national / location / uf / uf_location (always filter to ONE level) |
| `uf` | String |  | State code; All at national and location level |
| `uf_name` | String |  | State name; All when not applicable |
| `region` | String |  | Macro-region; All when not applicable |
| `location` | String |  | Onshore / Offshore / All (Total for NGL at UF level) |
| `product` | String |  | Oil / Natural gas / NGL (LGN) - never add products together |
| `unit` | String |  | Unit of volume: m3 (oil and NGL) or 1000 m3 (gas) |
| `unit_daily` | String |  | Unit of daily averages: m3/d or 1000 m3/d |
| `period_date` | Date |  | First day of the production month |
| `year` | Number (whole) |  | Calendar year |
| `month` | Number (whole) |  | Calendar month 1-12 |
| `days_in_month` | Number (whole) | days | Calendar days of the month (leap years included) |
| `is_provisional` | Boolean |  | True for 2026 months (subject to ANP revision) |
| `n_not_reported` | Number (whole) | count | Components of the aggregate that ANP did not publish (0 = complete) |
| `volume` | Number (decimal) | see unit | Monthly production volume; NULL = not reported (never 0) |
| `daily_avg` | Number (decimal) | see unit_daily | volume / days_in_month |
| `oil_daily_avg_bbl` | Number (decimal) | bbl/d | Oil only: daily_avg x 6.28981 (labelled conversion) |
| `mom` | Number (decimal) | ratio | Month-on-month change of volume; NULL if previous month is 0 or missing |
| `daily_avg_mom` | Number (decimal) | ratio | Month-on-month change of daily average (removes 28-31 day effect) |
| `yoy` | Number (decimal) | ratio | Change vs same month previous year; NULL in first 12 months or zero base |
| `rolling_3m_daily_avg` | Number (decimal) | see unit_daily | Volume-weighted 3-month daily average; NULL until 3 months exist |
| `rolling_12m_daily_avg` | Number (decimal) | see unit_daily | Volume-weighted 12-month daily average; NULL until 12 months exist |
| `ytd_volume` | Number (decimal) | see unit | Cumulative volume from January; NULL once a month in the year is missing |
| `share_of_national` | Number (decimal) | ratio | Share of the national volume of the same product and month; NULL at national level |
| `historical_peak_daily_avg` | Number (decimal) | see unit_daily | Highest daily average up to this month |
| `pct_of_historical_peak` | Number (decimal) | ratio | daily_avg / historical peak (1 = at peak) |
| `is_new_peak` | Boolean |  | True when the month beats every previous month (first month never flagged) |
| `volatility_12m` | Number (decimal) | ratio | Rolling 12-month std of daily_avg_mom |
| `baseline_12m_prior_daily_avg` | Number (decimal) | see unit_daily | Mean daily average of the previous 12 months (current excluded) |
| `deviation_from_baseline_pct` | Number (decimal) | ratio | daily_avg / baseline - 1 |
| `zscore_vs_prior_12m` | Number (decimal) | z | (daily_avg - baseline) / std of previous 12 months; NULL when std = 0 |
| `is_statistical_anomaly` | Boolean |  | Robust z of daily_avg_mom > 3.5 (national and location levels; oil and gas) - statistical not an incident |

## `gas_utilization_monthly` — 11,556 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `level` | String |  | national / location / uf / uf_location |
| `uf` | String |  | State code or All |
| `uf_name` | String |  | State name or All |
| `region` | String |  | Macro-region or All |
| `location` | String |  | Onshore / Offshore / All |
| `period_date` | Date |  | First day of the month (2000-01 onward) |
| `year` | Number (whole) |  | Calendar year |
| `month` | Number (whole) |  | Calendar month |
| `days_in_month` | Number (whole) | days | Calendar days |
| `is_provisional` | Boolean |  | True for 2026 |
| `gas_production_1000m3` | Number (decimal) | 1000 m3 | Gross natural gas production |
| `reinjection_1000m3` | Number (decimal) | 1000 m3 | Gas reinjected into reservoirs |
| `flaring_loss_1000m3` | Number (decimal) | 1000 m3 | Gas flared or lost |
| `own_use_1000m3` | Number (decimal) | 1000 m3 | Gas consumed in E&P operations |
| `available_1000m3` | Number (decimal) | 1000 m3 | Gas available (ANP 'disponível'); can be negative at UF level (allocation) |
| `reinjection_rate` | Number (decimal) | ratio | reinjection / production; NULL if production <= 0 |
| `flaring_loss_rate` | Number (decimal) | ratio | flaring & losses / production |
| `own_use_rate` | Number (decimal) | ratio | own use / production |
| `available_rate` | Number (decimal) | ratio | available / production |
| `balance_gap_1000m3` | Number (decimal) | 1000 m3 | production - (reinjection + flaring + own use + available); NULL if a flow is missing |
| `balance_gap_pct` | Number (decimal) | ratio | balance gap / production |
| `flaring_daily_avg_1000m3` | Number (decimal) | 1000 m3/d | Flaring & losses per calendar day |
| `allocation_sensitive` | Boolean |  | True at UF levels: ANP allocates volumes between states |

## `annual_summary` — 87 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `year` | Number (whole) |  | Complete calendar year |
| `product` | String |  | Oil / Natural gas / NGL (LGN) |
| `unit_daily` | String |  | Unit of annual_daily_avg |
| `annual_volume` | Number (decimal) | m3 or 1000 m3 | Annual national volume |
| `annual_daily_avg` | Number (decimal) | see unit_daily | annual_volume / days in year |
| `oil_daily_avg_bbl` | Number (decimal) | bbl/d | Oil only: annual_daily_avg x 6.28981 |
| `yoy` | Number (decimal) | ratio | Change of annual volume vs previous year |
| `offshore_share` | Number (decimal) | ratio | Offshore share of the annual volume (NULL for NGL) |

## `regional_hhi` — 58 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `year` | Number (whole) |  | Complete calendar year |
| `product` | String |  | Oil / Natural gas |
| `hhi` | Number (decimal) | index 0-10000 | HHI of state shares of annual volume |
| `top_uf` | String |  | Largest producing state |
| `top_share` | Number (decimal) | ratio | Share of the largest state |

## `structural_breaks` — 13 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `product` | String |  | Oil / Natural gas |
| `start` | String |  | First month of the regime (YYYY-MM) |
| `end` | String |  | Last month of the regime (YYYY-MM) |
| `n_months` | Number (whole) | months | Length of the regime |
| `annualised_growth` | Number (decimal) | ratio per year | Growth rate within the regime (piecewise-linear fit of ln daily average) |
| `mean_daily_avg` | Number (decimal) | m3/d or 1000 m3/d | Average daily production within the regime |
| `metric` | String |  | Series that was segmented |

## `anomalies` — 60 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `product` | String |  | Oil / Natural gas |
| `level` | String |  | national / location |
| `location` | String |  | All / Onshore / Offshore |
| `period` | String |  | Month flagged (YYYY-MM) |
| `daily_avg` | Number (decimal) | m3/d or 1000 m3/d | Daily average in the month |
| `daily_avg_mom` | Number (decimal) | ratio | Month-on-month change of the daily average |
| `robust_z_mom` | Number (decimal) | z | Robust z-score (median/MAD); flagged when |z| > 3.5 |
| `zscore_vs_prior_12m` | Number (decimal) | z | Local z-score vs previous 12 months |
| `direction` | String |  | rise / drop |
| `classification` | String |  | Always 'statistical anomaly (not verified as an operational incident)' |

## `seasonality` — 24 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `product` | String |  | Oil / Natural gas |
| `month` | Number (whole) |  | Calendar month 1-12 |
| `seasonal_index` | Number (decimal) | ratio | Mean ratio of daily average to its centred 12-month average (1 = no effect) |
| `std` | Number (decimal) | ratio | Standard deviation of the ratio across years |
| `n` | Number (whole) | count | Years in the average |
| `eta2` | Number (decimal) | ratio | Share of detrended variance explained by calendar month |
| `perm_p_value` | Number (decimal) | p | Permutation test p-value (5000 shuffles) |
| `window` | String |  | Period used |

## `dim_uf` — 11 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `uf` | String |  | State code; geographic role State/Province |
| `uf_name` | String |  | State name |
| `region` | String |  | Macro-region |
| `iso_3166_2` | String |  | ISO 3166-2 code (BR-XX) |
| `anp_name` | String |  | State name as published by ANP |

## `metadata` — 4 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `source_key` | String |  | Short source identifier |
| `source_name` | String |  | Source name |
| `url` | String |  | Official URL or local file |
| `coverage` | String |  | Period covered |
| `note` | String |  | Definition and caveats |
