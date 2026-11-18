# Industrial Data Analytics Portfolio

Two independent, reproducible analytics projects on **official Brazilian open data** for extractive industries. Each one has
its own pipeline, tests and documentation, and both share one visual identity (Stephany Alves Design System).

| Project | Core skill | Data | Questions | Status |
|---|---|---|---|---|
| [**Brazilian Mining Performance & Market Concentration**](mining-intelligence/README.md) | **SQL** (DuckDB): staging → marts, window functions, HHI | ANM AMB (2010–2025) + CFEM royalties (2.43 M rows, 2004–2026) | Price vs volume, commodity and state mix, geographic vs company concentration | Pipeline, analysis, 117 tests ✅ · dashboard specified |
| [**Brazilian Oil & Gas Production Analytics**](oil-gas-intelligence/README.md) | **Python** (pandas, NumPy): modular CLI pipeline, statistics | ANP monthly production by state and location (1997–2026) + Anuário 2026 | Growth regimes, regional concentration, stability, gas utilisation | Pipeline, analysis, 90 tests ✅ · dashboard specified |

> The Tableau Public dashboards are **fully specified** (build guides with calculated fields, layouts and verification
> checklists) but have **not been built or published yet**. Links will be added here once they are.

## Principles applied
- Real public data only, raw files preserved byte-for-byte with SHA-256 manifests.
- Nothing invented: every number in the docs comes from an executed query or test.
- Missing is never zero; units are never mixed; oil and gas are never summed; CFEM is never called revenue.
- Data-quality problems are documented, and either corrected by a stated rule or flagged.
- Only free tools: Python 3.12, DuckDB, pandas, pytest, Tableau Public.

## Repository structure

```
industrial-data-analytics/
├── mining-intelligence/      data/ (raw|interim|processed, raw not versioned) · sql/ · src/ · seeds/ · tests/ · tableau/ · docs/
├── oil-gas-intelligence/     data/ · src/oilgas/ · tests/ · notebooks/ · tableau/ · assets/ · docs/
├── shared/
│   ├── design-system/        SA_DESIGN_SYSTEM_TABLEAU.md · Preferences.tps
│   ├── documentation-templates/
│   ├── phase1_profiling/     Phase 1 profiling scripts
│   └── render_dictionary.py
├── SOURCE_SELECTION_REPORT.md
└── PHASE_LOG.md              objective · inputs · actions · files · tests · result · pending, per phase
```

## Quick start (Windows)

```powershell
cd C:\Tableau\industrial-data-analytics
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r mining-intelligence\requirements.txt -r oil-gas-intelligence\requirements.txt
```

Then follow the *Run it* section of each project README. Each one is a single command plus `pytest`.

## Environment used
Windows 11 · Python 3.12.10 · duckdb 2.0.0 · pandas 3.1.1 · numpy 2.5.5 · matplotlib 3.11.2 · pytest 9.2.0 · notebook 7.6.5.
