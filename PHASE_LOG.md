# Phase Log

## Phase 1 — Source discovery and validation (2026-11-18) ✅
See [SOURCE_SELECTION_REPORT.md](SOURCE_SELECTION_REPORT.md).

## Phase 2 — Data profiling and selection (2026-11-18) ✅

| Item | Content |
|---|---|
| Objective | Full profiling of the selected files, and confirmation of the selection |
| Inputs | Raw files in each project's `data/raw/` (see MANIFEST.csv) |
| Actions | DuckDB SQL profiling of CFEM (2.43 M rows) and AMB. pandas profiling of the 7 ANP files. Gas mass balance. Reconciliation with the ANP Anuário 2026 |
| Files created | `mining-intelligence/sql/00_profile_raw.sql`, `01_profile_followups.sql`, `src/run_sql.py`, `docs/DATA_PROFILE.md`; `oil-gas-intelligence/src/oilgas/{readers,profiling}.py`, `_inspect_*.py`, `docs/DATA_PROFILE.md` |
| Tests | Profiling queries were executed. **No automated pytest suite yet** (Phase 7) |
| Result | Selection confirmed. ANP monthly totals match the Anuário within 0.04 % per year. Staging rules defined (see DATA_PROFILE.md in each project) |
| Issues found | ANP oil Oct–Dec 2026 placeholder zeros. 681 negative available-gas rows (valid). CFEM: 143,751 identical rows (0.44 % of value), incomplete Jul–Nov 2026, FERRO / MINÉRIO DE FERRO synonyms, mixed units. AMB: double-counted Columbita-Tantalita rows, AC absent |
| Pending | `substance_map.csv` seed (manual mapping, Phase 5). Licence still not explicit |
| Next | Phase 5 — staging/marts SQL (mining) and the cleaning module (oil & gas) |

## Phase 3 — Project scaffolding and environment (2026-11-18) ✅

| Item | Content |
|---|---|
| Objective | Reproducible structure and environment on Windows with free tools |
| Actions | Created the directory tree from the master prompt. `git init -b main` (nothing committed). `.gitignore` excludes `.venv`, raw/interim data and `*.duckdb`. Created a Python 3.12 venv, because the system Python 3.15 cannot build the `pyyaml` wheel that Jupyter needs |
| Environment | Python 3.12.10 · duckdb 2.0.0 · pandas 3.1.1 · numpy 2.5.5 · pyarrow 26.0.1 · pytest 9.2.0 · matplotlib 3.11.2 · notebook 7.6.5 |
| Files created | `.gitignore`, `mining-intelligence/requirements.txt` (duckdb, pytest), `oil-gas-intelligence/requirements.txt` (pandas, numpy, matplotlib, pytest, notebook) |
| Reproduce | `py -3.12 -m venv .venv` then `.venv\Scripts\python.exe -m pip install -r <project>\requirements.txt` |
| Pending | pyarrow is installed but not used yet. It will be added to the mining requirements only if Parquet export is implemented. scipy/statsmodels are not installed (not needed so far) |

## Phase 4 — Raw data acquisition (2026-11-18) ✅

| Item | Content |
|---|---|
| Mining | `mining-intelligence/src/acquire_raw.ps1`: 5 files, 326.9 MB, SHA-256 manifest. Uses PowerShell because the ANM TLS chain is incomplete. Certificate validation stays on |
| Oil & gas | `python -m oilgas.acquisition`: 7 data files + 4 Anuário benchmark tables + 4 metadata PDFs, SHA-256 manifest. Python urllib works with gov.br TLS |
| Raw-data policy | Files are stored byte-for-byte as downloaded and never modified. They are not committed. Each project's `data/raw/MANIFEST.csv` is the record of version |

## Phase 5 — Data cleaning and transformation (2026-11-18) ✅

| Item | Content |
|---|---|
| Objective | Typed, standardised, analysis-ready layers for both projects |
| Inputs | Raw files (Phase 4) and the decisions in each DATA_PROFILE.md |
| Mining actions | Seeds: `uf.csv`, `amb_substance.csv` (57 AMB substances → English groups), `substance_map.csv` (148 CFEM names → 48 groups, each with a mapping basis). `sql/10_staging.sql` (3 staging tables + month status), `sql/20_marts.sql` (2 dims, 3 facts, 1 view, 10 marts including HHI/CR4 and the AMB×CFEM integration), `src/run_pipeline.ps1` |
| Oil & gas actions | `oilgas/cleaning.py` (rules R1–R5, corrections log), `oilgas/features.py` (4 aggregation levels, 20+ guarded features, gas-utilisation rates), `oilgas/pipeline.py` CLI. Shared parser moved to `readers.read_tidy` |
| Bugs found and fixed during the phase | (1) `PARTITION BY COLUMNS(*)` did not expand in DuckDB, so the repeat flag marked 2.43 M rows. Columns are now listed explicitly, giving 143,751 (= profiling count). (2) 5 AMB Bruta substances were missing from the seed. (3) A pandas `pivot_table(dropna=False)` tried to allocate 66.7 GiB and was replaced with a keyed `unstack` |
| Checks executed | AMB value staging = fact = marts (R$ 2.388 tn). CFEM staging = fact (R$ 74.537 bn), usable view = every CFEM mart (R$ 74.305 bn). One unit per AMB fact key. Seed completeness and label consistency (0 issues). Oil & gas reported rows = raw rows − R1 removals. Dense-grid assertion inside features |
| Tests | Inspection queries and in-code assertions only. **The pytest suite has not been written or run yet** (Phase 7) |
| Result | Mining pipeline ~7 s, oil & gas pipeline ~5 s, both reproducible from raw with one command |
| Pending | Company names for CNPJ roots are not in CFEM (only the ID). Mapping rows tagged `judgment` should be reviewed by a domain expert. pyarrow is not used |
| Next | Phase 6 — exploratory and statistical analysis |

## Phase 6 — Exploratory and statistical analysis (2026-11-18) ✅

| Item | Content |
|---|---|
| Objective | Answer the business questions with verifiable numbers and interpretable methods |
| Mining actions | `sql/30_analysis.sql` (Q1–Q14), `31_analysis_followups.sql`, `32_repeat_month_scan.sql`, `33_state_drivers.sql`, `src/lookup_company_names.py` → `seeds/company_names.csv` (25 largest CFEM legal entities, BrasilAPI / Receita Federal, all resolved) |
| Oil & gas actions | `oilgas/eda.py` (annual, descriptive, log-linear trend, regional HHI, onshore/offshore, seasonality with permutation test, gas utilisation), `oilgas/stats_analysis.py` (robust-z anomalies, volatility regimes, DP piecewise-linear structural breaks with BIC), `oilgas/charts.py` (5 PNGs in `assets/`), `_check_breaks.py` (robustness) |
| Corrections made during the phase | **New rule T13** (mining): Feb 2024 CFEM holds a systematic duplicate export (32.4 % of that month's value). Repeats are excluded only in months above 5 %, removing R$ 296.3 M, and 2024 CFEM growth goes from +12.8 % (gross) to +8.4 % (net). **Break detection** switched from the smoothed to the raw monthly series, because BIC overfit on the smoothed input. **Wording corrections** after re-checking: iron-share "lowest since" and the CFEM ratio step-up |
| Findings | `mining-intelligence/docs/ANALYSIS_FINDINGS.md` (F1–F10, DQ1–DQ3), `oil-gas-intelligence/docs/ANALYSIS_FINDINGS.md` (F1–F9) |
| Methodology | `docs/ANALYSIS_METHODOLOGY.md` in each project |
| Tests | Analysis outputs were re-derived and spot-checked against source queries. **The pytest suite has not been written yet** (Phase 7) |
| Decisions | No forecast (no business question needs one, and the regime changes make it unreliable). Company = legal entity, not group. ES iron ore treated as a reporting inconsistency |
| Next | Phase 7 — automated QA test suite and TEST_REPORT |

## Phase 7 — Data quality validation (2026-11-18) ✅

| Item | Content |
|---|---|
| Objective | Automated, executed tests for every QA requirement in §5 of the brief |
| Files created | `mining-intelligence/tests/{conftest,test_raw_and_schema,test_staging_quality,test_marts_integrity}.py`, `oil-gas-intelligence/tests/{conftest,test_units,test_data_quality}.py`, `tests/results/{pytest_output.txt,junit.xml}`, `docs/TEST_REPORT.md` and `docs/DATA_QUALITY_REPORT.md` in each project, `src/oilgas/_check_balance_diff.py` |
| Tests executed | Mining **56 / 56 passed**. Oil & gas **68 / 68 passed** (2026-11-18 16:05). 0 skipped, 0 xfail |
| Failures found and resolved | Harness: DuckDB 2.0 API change and an invalid nested window (test code). Test scope: pre-2000 gas balance NaN. **Real findings:** T13 also fires in Aug 2002 (docs said "only Feb 2024"); 2002–03 spine gaps; national gas balance is 307 (not 308) of 321 months because of unpublished Dec 2024 cells. Docs corrected |
| Not covered | Tableau export files (they do not exist yet; tests come in Phase 8) |
| Next | Phase 8 — Tableau-ready datasets (+ export tests) |
