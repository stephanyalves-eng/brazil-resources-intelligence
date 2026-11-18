# Data Quality Report — Oil & Gas Intelligence

Snapshot: ANP files downloaded 2026-11-18 (see `data/raw/MANIFEST.csv`). Automated checks: **68/68 passed** ([TEST_REPORT.md](TEST_REPORT.md)).

## Quality indicators

| Indicator | Value |
|---|---|
| Raw rows (7 series) | 47,409 |
| Parse failures / duplicate keys | 0 / 0 |
| Rows removed (future placeholder zeros, oil Oct–Dec 2026) | 66 |
| UF × location × month cells not published (densified as NaN) | 183 (0.39 %) |
| Negative values | 681, all in available gas, all flagged |
| National annual reconciliation with Anuário 2026 (2016–2025) | ≤ 0.039 % deviation (oil ≤ 0.000 %) |
| National monthly gas balance within 0.5 % | 307 of 321 months (95.6 %) |
| Coverage | oil, gas, LGN Jan 1997 – Sep 2026; gas uses Jan 2000 – Sep 2026 |

## Issue register

| ID | Issue | Severity | Detection | Correction | Residual risk |
|---|---|---|---|---|---|
| G-01 | Oil Oct–Dec 2026 published as zeros | High | Phase 1 | R1 common cut-off (2026-09) | A future snapshot may publish zeros again. The test catches it |
| G-02 | Unpublished UF × location × month cells | Medium | Phase 2 | R2: NaN / `not_reported`, never 0 | Aggregates treat them as contributing nothing; `n_not_reported` is exposed |
| G-03 | Negative available gas | Medium | Phase 2 | R4: kept and flagged | UF-level availability is allocation-sensitive |
| G-04 | Jul 2005 gas balance −28 % nationally | Medium | Phase 2 | None (as published), documented | 2005 annual rates do not sum to 100 % |
| G-05 | Dec 2024 reinjection/own use unpublished in several UFs (balance −0.503 %) | Low | Phase 7 test | Documented. Profiling count corrected (308 → 307) | — |
| G-06 | Metadata column name `QUEIMA E PERDA` vs CSV `QUEIMADO` | Low | Phase 1 | `config.SOURCES` uses the CSV name | Schema test |
| G-07 | ES onshore gas 2020: monthly sum +67.8 % vs Anuário | Low | Phase 2 | None. Revision between publications | Small cell (< 50 million m³) |
| G-08 | Anuário header typo (`UNIDDES`) in t2.21 | Low | Phase 5 | Columns renamed positionally | — |
| G-09 | Recent months provisional (ANP revises) | Medium | Phase 5 | `is_provisional` for 2026 | Figures may change on the next download |
| G-10 | Dataset licence not stated | Low | Phase 1 | Attribution to ANP | Recorded in LIMITATIONS |
