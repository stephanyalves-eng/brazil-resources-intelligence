# Tableau Build Guide — Brazilian Oil & Gas Production Analytics

> **Status (2026-11-18):** built. `tableau/Brazilian_Oil_Gas_Production.twbx` was generated from this guide by
> `tableau/build_workbook.py`, opened in Tableau Public 2026.3, checked against §7 (all values match) and saved locally. It is
> not published. The manual procedure below remains the reference.
> There is no reliable free way to generate a Tableau Public workbook automatically. Build it by hand in Tableau Public from
> `tableau/data/`, then check the numbers against §7.

Design: [SA Design System for Tableau](../../shared/design-system/SA_DESIGN_SYSTEM_TABLEAU.md), the same visual language as the
mining dashboard. The difference is functional: oil & gas pages are **time-series-first** (lines, bands and markers), while mining
pages are composition and ranking (bars, maps, Pareto charts). Data model: [TABLEAU_DATA_MODEL.md](TABLEAU_DATA_MODEL.md).
KPIs: [KPI_DEFINITIONS.md](KPI_DEFINITIONS.md).

## 0. Prerequisites
Tableau Public (free) and a Tableau Public account (your step). `Preferences.tps` from `shared/design-system/` goes into
`Documents\My Tableau Repository\`. Rebuild the data with `..\..\.venv\Scripts\python.exe -m oilgas.pipeline` from `oil-gas-intelligence/src`.

## 1. Connect the data
1. Add each CSV in `tableau/data/` as its own data source. Relate `dim_uf` to `production_monthly` and `gas_utilization_monthly` on `uf`.
2. Field settings: `period_date` → Date; `year`, `month` → discrete dimensions; `uf` → geographic role *State/Province*
   (Country = Brazil). In `structural_breaks`, convert `start` and `end` with `DATEPARSE("yyyy-MM", [start])`.
3. **Data-source filters**, which prevent double counting. Duplicate `production_monthly` four times and set one filter on each copy:

| Source copy | Data-source filter |
|---|---|
| `prod · national` | `level = national` |
| `prod · location` | `level = location` |
| `prod · uf` | `level = uf` |
| `prod · uf_location` | `level = uf_location` |

Do the same for `gas_utilization_monthly` (`util · national`, `util · location`, `util · uf`).

## 2. Parameters

| Name | Type | Values | Default |
|---|---|---|---|
| `p Product` | String | Oil / Natural gas / NGL (LGN) | Oil |
| `p Unit Oil` | String | m3/d / bbl/d | bbl/d |
| `p Window` | String | Since 2000 / Last 10 years / Last 36 months | Since 2000 |
| `p Year` | Integer | 2000–2025 | 2025 (for regional, annual views) |

## 3. Calculated fields

```text
// all prod · * sources
Is Product            = [product] = [p Product]
Daily Avg             = SUM([volume]) / SUM([days_in_month])                     // recomputed: valid at any time grain
Daily Avg Display     = IF [p Product] = "Oil" AND [p Unit Oil] = "bbl/d" THEN [Daily Avg] * 6.28981 ELSE [Daily Avg] END
Display Unit          = IF [p Product] = "Oil" AND [p Unit Oil] = "bbl/d" THEN "bbl/d"
                        ELSEIF [p Product] = "Natural gas" THEN "thousand m³/d" ELSE "m³/d" END
Latest Month          = { FIXED : MAX([period_date]) }
Is Latest             = [period_date] = [Latest Month]
In Window             = CASE [p Window]
                          WHEN "Since 2000" THEN [period_date] >= #2000-01-01#
                          WHEN "Last 10 years" THEN [period_date] > DATEADD('year', -10, [Latest Month])
                          WHEN "Last 36 months" THEN [period_date] > DATEADD('month', -36, [Latest Month]) END
KPI Latest Daily      = SUM(IF [Is Latest] THEN [volume] END) / SUM(IF [Is Latest] THEN [days_in_month] END)
KPI Daily MoM         = MAX(IF [Is Latest] THEN [daily_avg_mom] END)            // stored, national row
KPI YoY               = MAX(IF [Is Latest] THEN [yoy] END)
KPI % of Peak         = MAX(IF [Is Latest] THEN [pct_of_historical_peak] END)
Rolling 12M Display   = IF [p Product] = "Oil" AND [p Unit Oil] = "bbl/d" THEN AVG([rolling_12m_daily_avg]) * 6.28981
                        ELSE AVG([rolling_12m_daily_avg]) END                    // one row per month at this level -> AVG = value
Baseline Band Low     = AVG([baseline_12m_prior_daily_avg]) * 0.95
Baseline Band High    = AVG([baseline_12m_prior_daily_avg]) * 1.05
Anomaly Marker        = IF MAX([is_statistical_anomaly]) THEN [Daily Avg] END
Provisional Label     = IF MAX([is_provisional]) THEN "PROVISIONAL" END
Share (recomputed)    = SUM([volume]) / TOTAL(SUM([volume]))                     // compute along uf or location
Change Arrow          = IF [KPI YoY] >= 0 THEN "▲" ELSE "▼" END

// util · * sources
Reinjection Rate      = SUM([reinjection_1000m3]) / SUM([gas_production_1000m3])
Flaring Rate          = SUM([flaring_loss_1000m3]) / SUM([gas_production_1000m3])
Own Use Rate          = SUM([own_use_1000m3]) / SUM([gas_production_1000m3])
Available Rate        = SUM([available_1000m3]) / SUM([gas_production_1000m3])
Balance Gap %         = (SUM([gas_production_1000m3]) - SUM([reinjection_1000m3]) - SUM([flaring_loss_1000m3])
                         - SUM([own_use_1000m3]) - SUM([available_1000m3])) / SUM([gas_production_1000m3])
Flaring per Day       = SUM([flaring_loss_1000m3]) / SUM([days_in_month])
```

Formats: daily averages `#,##0`; `0.0%` for rates and shares; MoM/YoY `+0.0%;-0.0%`; HHI `#,##0`.

## 4. Sheets

| ID | Sheet | Source | Build | Colour | Tooltip |
|---|---|---|---|---|---|
| P1 | KPI · Latest daily avg | prod · national | Text: eyebrow "LATEST MONTH · " + `MAX(period_date)`, `KPI Latest Daily` (×6.28981 if bbl/d), `Display Unit`, `Provisional Label` | Inverse tile; tag `--warn` | none |
| P2 | KPI · MoM (daily) | prod · national | `Change Arrow` + `KPI Daily MoM`, sub "volume MoM " + `MAX(mom)` | ▲ `--signal` / ▼ `--err` | none |
| P3 | KPI · YoY | prod · national | `KPI YoY` | same | none |
| P4 | KPI · % of peak | prod · national | `KPI % of Peak`, sub "new peak" when `is_new_peak` | `--forest-700` | none |
| P5 | Monthly production (volume) | prod · national | Columns `MONTH(period_date)`, Rows `SUM(volume)`; bars | `--context`; `Is Latest` → `--forest-700`; provisional months bordered `--warn` | "<month>: <volume> <unit> · <days> days · daily <Daily Avg>" |
| P6 | Historical daily average | prod · national | Line `Daily Avg Display` (1 pt `--context`) + `Rolling 12M Display` (2 pt `--forest-700`), dual axis synchronised | Filters `Is Product`, `In Window` | "<month>: <daily> · 12M <rolling>" |
| P7 | Annual summary | annual_summary | Bars `annual_daily_avg` by `year`, label `yoy` | `--forest-600`; 2025 `--forest-700` | "<year>: <daily> <unit_daily> · <yoy> · offshore <offshore_share>" |
| G1 | State share map | prod · uf | Filled map `uf`, colour `Share (recomputed)` | SA sequential | "<uf_name>: <share> of national <product> in <year>" |
| G2 | State ranking | prod · uf | Bars `SUM(volume)` by `uf_name` for `year = [p Year]` | Focus + context (top `--forest-700`) | "<uf_name>: <volume> · <share>" |
| G3 | Onshore vs offshore | prod · location | Area `Daily Avg` by month, colour `location` | Offshore `--forest-700`, onshore `--sage` | "<location> <month>: <daily> (<share>)" |
| G4 | State trends | prod · uf | Lines `rolling_12m_daily_avg` by month, colour = top 4 UFs (set) else `--context` | Focus + context | "<uf_name> <month>: <rolling12>" |
| G5 | Geographic HHI | regional_hhi | Line `hhi` by `year` + reference lines 1,500 / 2,500 (`--warn` dashed) | `--forest-700` | "<year>: HHI <hhi>, top <top_uf> <top_share>" |
| S1 | Baseline band + anomalies | prod · national | `Daily Avg` line; reference band `Baseline Band Low`–`High` (fill `--sage-100`); circles from `Anomaly Marker` | Line `--forest-700`, anomalies `--err` | "<month>: daily <d>, vs prior-12M baseline <deviation_from_baseline_pct>, z = <zscore_vs_prior_12m>. Statistical anomaly, not a verified incident." |
| S2 | Volatility | prod · national + prod · location | Line `AVG(volatility_12m)` by month, colour `location` | National `--forest-700`, onshore `--sage`, offshore `--forest-600` | "<month>: 12M volatility <v>" |
| S3 | Growth regimes | structural_breaks | Gantt: `start`→`end` by `product`, label `annualised_growth` | Bars `--forest-600`; regimes > +5 %/yr `--forest-700` | "<product> <start>–<end>: <growth>/yr over <n_months> months" |
| S4 | Seasonality | seasonality | Bars `seasonal_index − 1` by `month`, columns `product` | Positive `--signal`, negative `--err` | "<month>: <index−1> vs centred 12M average (η² <eta2>, p <perm_p_value>)" |
| S5 | Anomaly log | anomalies | Text table: period, product, location, MoM, robust z, direction | Table style; `classification` in the footnote | none |
| U1 | Gas balance (stacked 100 %) | util · national | Area: `Reinjection Rate`, `Available Rate`, `Own Use Rate`, `Flaring Rate` by `YEAR(period_date)` | `--forest-700`, `--sage`, `--context`, `--warn` | "<year>: reinjected <r>, available <a>, own use <o>, flared <f>" |
| U2 | Gas production vs reinjection | util · national | Dual line `SUM(gas_production_1000m3)/SUM(days_in_month)` and reinjection per day | `--forest-600` / `--forest-700` | "<month>: produced <p>, reinjected <r> (thousand m³/d)" |
| U3 | Flaring rate trend | util · national | Line `Flaring Rate` by year + `Flaring per Day` on the tooltip | `--warn` | "<year>: <flaring rate> · <per day> thousand m³/d" |
| U4 | Offshore vs onshore rates | util · location | Side-by-side bars: the 4 rates for `year = [p Year]`, by `location` | categorical SA | "<location> <year>: <rate>" |
| U5 | Balance quality | util · national | Bar `Balance Gap %` by month, reference band ±0.5 % | Within band `--context`, outside `--err` | "<month>: gap <gap>" |
| D1 | Sources | metadata | Text table | Table style | none |

## 5. Dashboards (desktop 1200 × 900 fixed, one per page, navigation in the header band)

Header band (`--forest`): eyebrow "BRAZILIAN OIL & GAS · ANP MONTHLY", page title (Georgia), chips `p Product`, `p Unit Oil`, `p Window`.
Footer: "Source: ANP — production by state and location, snapshot 2026-11-18 · last month Sep 2026 (provisional) · oil and gas are never summed".

**1 · Production Overview**
```
┌ header band ──────────────────────────────────── p Product ▾  p Unit ▾  p Window ▾ ┐
├ P1 (inverse) ─┬ P2 ─────────┬ P3 ─────────┬ P4 ─────────┤  KPI row h 110
├ P6 Historical daily average with 12M rolling (12/12) ───────────────────────────────┤  h 360
├ P5 Monthly volume, last 36 months (7/12) ────────┬ P7 Annual summary (5/12) ───────┤  h 260
└ footer ─────────────────────────────────────────────────────────────────────────────┘
```
Caption (F1/F3): "Record month in Sep 2026; growth has accelerated since mid-2022 after a 2016–2022 plateau."

**2 · Regional Analysis.** Row 1: G1 map (5/12) + G2 ranking (7/12), h 360. Row 2: G3 (6/12) + G4 (6/12), h 280. G5 as a slim
strip under G2. Caption (F4/F5): "97.6 % of oil is offshore; Rio de Janeiro's share is back to 87.8 %."

**3 · Production Stability.** Row 1: S1 (12/12), h 340. Row 2: S2 (4/12) + S3 (4/12) + S4 (4/12), h 260. S5 is shown as a
viz-in-tooltip of S1 or on a toggled panel. A note in `--warn`: "Anomalies are statistical; causes are not in the data."

**4 · Natural Gas Utilization.** KPI row: reinjection rate, flaring rate, own-use rate and available rate for `p Year`
(`util · national`). Row 1: U1 (7/12) + U4 (5/12). Row 2: U2 (6/12) + U3 (3/12) + U5 (3/12). Caption (F6): "Reinjection took
54.4 % of gas in 2025 (19.1 % in 2010); flaring fell to 2.8 %."

**5 · Methodology.** D1 plus text blocks on `--paper` covering units (m³, thousand m³, the bbl conversion), definitions (K2, K4, K14,
K15, K17–K20), the cleaning rules R1–R5, the limitations (provisional data, allocation-sensitive UF rates, no field data, no
forecast) and the update procedure.

### Phone layout (375 px, fit width)
Header (title plus `p Product` only) → P1 → P3 (combine P2 into P3's sub-line) → P6 with `p Window` fixed to "Last 10 years" →
G2 (top 5) → U1 → footer. Hide G1 (the map is too small), S2, S3 and U5. Each tile is full width, values at 20 pt.

## 6. Interactions

| Action | Type | Effect |
|---|---|---|
| Click a year in P7 or U1 | Parameter action → `p Year` | Updates G2, U4 and the gas KPI row |
| Click a state in G1 or G2 | Filter action → G4 | Shows that state's trend; others fade |
| Hover S1 anomaly | Viz-in-tooltip (S5 filtered to that month) | Shows the anomaly record |
| Product chip | Parameter `p Product` | All production sheets (via `Is Product` filter) |
| Navigation | Buttons in the header band | Pages 1–5 |

Rules: no sheet mixes two products on one axis. Gas production and oil appear together only as **separate panes or separate
axes**, each with its own unit label.

## 7. Verification checklist (2026-11-18 build)

| Check | Expected |
|---|---|
| P1 Oil, m³/d | 748,985 m³/d (Sep 2026, PROVISIONAL tag) |
| P1 Oil, bbl/d | ≈ 4.71 million bbl/d |
| P1 Natural gas | 223,878 thousand m³/d |
| P2 Oil | ▲ +2.1 % daily (volume MoM −1.2 %) |
| P3 Oil / gas | +20.3 % / +17.5 % |
| P4 | 100 % (new peak) for both |
| P7 2025 | oil 599,389 m³/d (+12.0 %); gas 179,237 thousand m³/d (+16.7 %) |
| G1/G2 oil 2025 | RJ 87.8 %; offshore (G3) 97.6 % |
| G5 2025 | oil HHI 7,760; gas 6,033 |
| U1 2025 | reinjection 54.4 %, available 33.4 %, own use 9.8 %, flaring 2.8 % |
| S3 | Oil Jul 2022 → Sep 2026 +8.7 %/yr; gas Oct 2023 → Sep 2026 +15.9 %/yr |
| S4 April | oil −2.4 % (index 0.9765), gas −3.6 % |
| S5 | 7 national rows (6 oil, 1 gas) when filtered to level = national |

## 8. Publish
*File → Save to Tableau Public As…* → "Brazilian Oil & Gas Production Analytics". The workbook becomes **public**. Publishing is
your decision and your action. Then add the URL to `README.md`.
