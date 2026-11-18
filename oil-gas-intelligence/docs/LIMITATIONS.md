# Limitations — Oil & Gas

## Measurement
1. **Oil and gas are never combined.** No barrel-of-oil-equivalent is computed, so there is no "total hydrocarbons" KPI.
2. **bbl/d is a unit conversion** (1 m³ = 6.28981 bbl), validated against the Anuário's thousand-barrel tables. It is not an independent measurement.
3. **"Available gas" is ANP's accounting balance item.** It can be negative at state level, where volumes are allocated between states, so UF-level gas rates are *allocation-sensitive*.

## Coverage
4. **State × location monthly data only.** There is no field, well, operator or pre-salt split in the monthly series (pre-salt exists only in the annual Anuário tables, which were used for reconciliation, not analysis).
5. Gas-use flows start in **2000**; oil, gas and NGL start in 1997.
6. **2026 is provisional** (ANP revises recent months). The last month is **Sep 2026**; the oil file's Oct–Dec 2026 zeros were removed.
7. 183 state × location × month cells were never published. They are `not_reported` (NULL), not zero, and aggregates expose `n_not_reported`.

## Methods
8. **Anomalies are statistical**, not confirmed incidents; the data contains no operations log.
9. **Structural breaks** come from a piecewise-linear model chosen by BIC. Two segments end at the 36-month minimum, so those dates are approximate. Gains beyond about 4 segments are small (published BIC table).
10. **Seasonality is exploratory:** the effect is significant but small (≤ 3.6 %), and its cause is not identified.
11. **No forecast.** This was deliberate: no business question needs one, and the regime changes would make it unreliable.

## Data quality (see [DATA_QUALITY_REPORT.md](DATA_QUALITY_REPORT.md))
12. The national gas balance has a −28 % gap in Jul 2005, and Dec 2024 has unpublished flows (−0.5 %). 307 of 321 months close within 0.5 %.
13. ES onshore gas in 2020 differs from the Anuário by +67.8 % (revision between publications; small cell).
14. The dataset licence is not stated explicitly by ANP.

## Reproducibility
15. Results are tied to the 2026-11-18 snapshot (`data/raw/MANIFEST.csv`). Tests pinned to snapshot counts fail by design after a republication.
16. The dashboard is specified, not built. Verify a future build against the checklist in the build guide.
