# Portfolio Kit — Brazilian Oil & Gas Production Analytics

Numbers come from the 2026-11-18 build ([ANALYSIS_FINDINGS.md](ANALYSIS_FINDINGS.md)). There are no invented impact metrics.
Replace `[GitHub link]` and `[Tableau Public link]` when available; the dashboard is built locally, not yet published.

---

## 1. Case study

**Executive summary.** I built a modular Python pipeline over ANP's official monthly production statistics. It covers oil, gas,
NGL and four gas-use flows, by state and onshore/offshore, from 1997 to Sep 2026. It cleans the data with explicit rules, engineers
guarded time-series features, runs interpretable statistics and exports Tableau-ready tables. A five-page Tableau dashboard presents the results.

**Business problem.** "Brazil produces record oil" is a headline, not an analysis. An operations or market analyst needs to know:
- whether growth is steady or comes in phases;
- how dependent output is on one state and on offshore fields;
- how stable it is month to month;
- what share of the gas produced actually reaches the market.

**Analytical approach.**
1. **Validation first.** Monthly totals reconcile with ANP's annual Anuário within 0.04 %. This also proved that the Anuário reports oil in thousand barrels.
2. **Cleaning rules:**
   - a common cut-off that removes placeholder zeros for future months;
   - a dense monthly grid where unpublished cells are NULL, never 0;
   - negative "available gas" kept and flagged.
3. **Feature engineering:** daily averages on real month lengths, MoM/YoY, volume-weighted rolling windows, peaks, baselines and z-scores. Every ratio is guarded against zero or missing denominators.
4. **Statistics:**
   - log-linear trends;
   - exact piecewise-linear segmentation with BIC;
   - seasonality with a permutation test;
   - robust-z anomalies;
   - volatility regimes.
5. **QA.** 90 pytest checks, including unit tests on synthetic data for every guard rail.

**Architecture.** `acquisition → profiling → cleaning → features → eda → stats_analysis → charts → tableau_export`. Each step is a
module in `src/oilgas/` that runs on its own, orchestrated by `python -m oilgas.pipeline`.

**Key findings.**
- Record month in Sep 2026: 748,985 m³/d of oil (≈ 4.71 M bbl/d) and 223.9 M m³/d of gas, both provisional.
- Long-run growth from 2000 to 2025: oil +4.1 %/yr, gas +6.6 %/yr. There was a 2016–2022 plateau, and growth has run at +8.7 %/yr since mid-2022.
- 97.6 % of oil is offshore. Rio de Janeiro's share dipped to 67 % in 2015 and was back at 88 % in 2025.
- 54.4 % of the gas produced is reinjected (19.1 % in 2010). Flaring and losses fell from 17.9 % to 2.8 %.
- A small, significant March–May dip, and volatility rising onshore.

**Dashboard walkthrough (built; screenshots in `assets/tableau_*.png`, [build guide](TABLEAU_BUILD_GUIDE.md)).**
1. *Production Overview:* KPI tiles (latest daily average, daily MoM, YoY, % of peak) and the history with a 12-month line.
2. *Regional:* map, ranking, onshore vs offshore, HHI.
3. *Stability:* baseline band with anomaly markers, volatility, growth regimes, seasonality.
4. *Gas Utilization:* the 100 % balance, reinjection vs production, flaring, and a balance-quality check.
5. *Methodology.*

**Technical challenges.**
- The oil file publishes Oct–Dec 2026 as zeros. A naive chart shows a production collapse.
- BIC selected the maximum number of breaks on a smoothed series. A robustness check showed why: autocorrelation. The fix was to segment the raw series.
- A pandas `pivot_table(dropna=False)` tried to allocate 66.7 GiB. It was replaced by a keyed `unstack`.
- Tests caught a first-month "new peak" bug and a profiling count (308 vs 307) that hid unpublished Dec 2024 data.

**Limitations.**
- No field, operator or pre-salt split in the monthly data.
- Gas rates at state level depend on ANP's allocation between states.
- Anomalies are statistical, not incidents. No forecast was made, deliberately.
- See [LIMITATIONS.md](LIMITATIONS.md).

**Skills demonstrated.**
- **Python:** modular package design, CLI pipelines, pandas/NumPy time series, matplotlib.
- **Statistics:** robust statistics, dynamic-programming segmentation, permutation tests.
- **Quality and delivery:** data-quality rules, pytest (unit and data tests), Tableau data modelling, documentation.

---

## 2. Channel texts

### GitHub — repository description
Modular Python pipeline on ANP monthly oil & gas data (1997–2026): validated against the official yearbook, missing ≠ zero cleaning, guarded time-series features, BIC structural breaks, seasonality and anomaly statistics, gas-utilisation balance, 90 pytest checks, Tableau-ready extracts.

**Topics:** `python` `pandas` `time-series` `data-quality` `oil-and-gas` `brazil` `open-data` `statistics` `pytest` `tableau`

### LinkedIn post
Brazil produced 748,985 m³ of oil per day in September 2026 (≈ 4.7 million barrels), a record. Here is what the monthly data from ANP shows behind it:

→ Growth isn't a straight line. Output was flat from mid-2016 to mid-2022, and since then it has grown at 8.7 % a year.
→ 97.6 % of the oil comes from offshore fields, and Rio de Janeiro's share is back to 88 %.
→ More than half of the natural gas produced (54.4 %) goes back into the reservoirs. In 2010 that was 19 %. Flaring fell from 18 % in 2000 to under 3 %.
→ There's a small but statistically significant dip every March–May. The data doesn't say why, and I don't guess.

Two lessons from building it in Python:
1. The official file publishes future months as zeros. Without a cut-off rule, every chart shows a collapse.
2. Missing is not zero. Unpublished cells stay empty and are counted, never filled in.

Everything is validated against ANP's yearbook (within 0.04 %) and covered by 90 automated tests. Repo: [GitHub link]

#DataAnalytics #Python #OilAndGas #TimeSeries #DataQuality

### Medium — article plan
**Title:** *Missing Is Not Zero: Lessons from Analysing 30 Years of Brazilian Oil & Gas Data in Python*
1. Hook: the placeholder zeros that make a record look like a collapse.
2. Validating against the official yearbook, and discovering its unit.
3. Feature engineering with guard rails: daily averages, rolling windows, ratios that refuse to divide by zero.
4. Growth regimes with piecewise-linear segmentation, and why BIC overfits smoothed data.
5. Where the gas goes: the balance identity and the reinjection shift.
6. Statistical anomalies vs incidents: what the data can and cannot say.

### DEV Community — post outline
**Title:** *A testable pandas pipeline for public time-series data: 11 modules, 90 tests, zero notebooks required*
Sections: package layout and CLI → reading Brazilian CSVs safely (BOM, `;`, decimal comma, fail on `.`) → dense grids and `not_reported`
→ guarded features + their unit tests → exact DP segmentation in NumPy → exporting for Tableau with a dictionary that tests enforce.
Tags: `#python #pandas #datascience #testing`

### Peerlist — project card
**Brazilian Oil & Gas Production Analytics.** Python pipeline over ANP monthly data (1997–2026): yearbook-validated cleaning, time-series
features, structural breaks, seasonality, anomalies and gas-utilisation balance. 90 tests, Tableau-ready. Stack: Python, pandas, NumPy,
matplotlib, pytest, Tableau Public. [GitHub link]

### Personal portfolio — card
**Oil & Gas Intelligence · Python**. *Is Brazil's record production steady growth, a new phase, or a data artefact?* A modular,
tested pipeline over 30 years of official ANP data.
`Python` `pandas` `Statistics` `Tableau` → [GitHub link] · [Tableau Public link]
