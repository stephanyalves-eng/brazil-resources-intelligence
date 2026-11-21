# Changelog — Oil & Gas Intelligence

All dates 2026-11-18 (single build session). Commits are in the repository history.

| Version | Phase | Change |
|---|---|---|
| 0.1.0 | 1 | ANP sources evaluated; monthly state/location series selected; oil Oct–Dec 2026 placeholder zeros detected |
| 0.2.0 | 2 | Profiling module; gas balance check; Anuário 2026 reconciliation (≤ 0.04 % nationally; Anuário oil unit found to be thousand bbl) |
| 0.3.0 | 3–4 | Package scaffold, venv, `acquisition` with SHA-256 manifest |
| 0.4.0 | 5 | `cleaning` (R1–R5, corrections log) and `features` (4 levels, guarded time-series features, gas rates). Fixed: a `pivot_table` that tried to allocate 66.7 GiB |
| 0.5.0 | 6 | `eda`, `stats_analysis`, `charts`. Fixed: break detection moved from smoothed to raw series (BIC overfit) |
| 0.6.0 | 7 | pytest (68). Found: national gas balance is 307 (not 308) of 321 months because of unpublished Dec 2024 flows |
| 0.7.0 | 8 | `tableau_export` (9 CSVs), dictionary, data model, export tests (90 total). Fixed: `is_new_peak` flagged the first month of every series |
| 0.8.0 | 9 | KPI definitions and Tableau build guide in the SA Design System |
| 1.0.0 | 10 | README, data sources, limitations, portfolio kit, executed walkthrough notebook. A clean rebuild reproduced all extracts and charts byte for byte; 90/90 tests |
| 1.1.0 | Tableau build | Tableau workbook built from the guide (`tableau/build_workbook.py` → `.twbx`), all §7 values verified in Tableau Public 2026.3. Fixed: April oil seasonal value is −2.4 % (index 0.9765), not −2.3 % |
| 1.2.0 | Tableau interactivity | Dashboards made interactive: new STATE filter (regional and gas pages; UF rows sum exactly to the national totals), clicks on years, states and products set the filters (parameter actions). Header with filters and page buttons aligned in the dark band; regular grid layout; worksheet tabs hidden. §7 values unchanged at the defaults |
| 1.3.0 | Tableau cross-filtering | Cards and page-1 charts follow YEAR, PRODUCT and STATE (KPIs recomputed from state rows for the last month of the selected year; default year = 2026); every time-series chart sets the year on click |
