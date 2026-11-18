# Source Selection Report — Phase 1

**Date:** 2026-11-18 · **Status:** Phase 1 complete. Source decision recorded. No pipeline built yet.
Detailed matrices: [`mining-intelligence/docs/data_source_evaluation.md`](mining-intelligence/docs/data_source_evaluation.md) ·
[`oil-gas-intelligence/docs/data_source_evaluation.md`](oil-gas-intelligence/docs/data_source_evaluation.md).
Profiling scripts: `shared/phase1_profiling/`.

## Phase log

| Item | Content |
|---|---|
| Objective | Find, validate and choose official public sources for both projects |
| Inputs | The ANM and ANP URLs in the master prompt |
| Actions | Fetched the ANM directory listings and the 3 ANP pages. Read HTTP headers (size, Last-Modified). Downloaded all small files in full plus a 3 MB sample of CFEM. Profiled encoding, separator, rows, columns, blanks, duplicates, keys, units and periods. Read the official metadata (ODS/PDF). Checked the gas mass balance and future-month zeros |
| Files created | This report, two `data_source_evaluation.md`, 4 profiling scripts |
| Tests | Exploratory profiling only. **No automated tests have been written or run yet** (Phase 7) |
| Result | One primary and one complementary source chosen per project (below) |
| Pending | Licences not stated explicitly. Substance mapping AMB↔CFEM. CFEM full-file profiling. DuckDB not installed |
| Next | Phase 2 (full profiling of the chosen files) → Phase 3 (scaffolding, environment) |

## 1. Project 01 — Mining

| | Primary | Complementary |
|---|---|---|
| Dataset | ANM **AMB – Produção Beneficiada** (+ AMB Produção Bruta as a sibling fact) | ANM **CFEM – Arrecadação** |
| URL | https://dadosabertos.anm.gov.br/AMB/Producao_Beneficiada.csv | https://dadosabertos.anm.gov.br/CFEM/CFEM_Arrecadacao.csv (or the 5 five-year splits) |
| Grain | Base year × UF × substance (× contained indicator) | Payment slip: year-month × mining process × holder (CNPJ/masked CPF) × substance × municipality |
| Dimensions | Year, UF (26–27), substance class (4), substance (52–56), contained element | Year, month, UF, IBGE municipality code, substance (156), PF/PJ, CNPJ, process |
| Measures | Production qty (t / kg / ct, one unit per substance), sale qty, **sale value R$**, consumption and transfer qty/value | Quantity sold (7 units), **CFEM collected R$** |
| Coverage | 2010–2025 (16 base years) | 2002 – Nov 2026, monthly |
| Size | 0.68 MB (+0.99 MB Bruta), ~10k rows | 325 MB, ≈2.4 M rows (*estimate* from sample density) |
| Complexity | Low | Medium (size, mixed units, masked CPF, substance vocabulary) |
| Analytical potential | Value and volume by state and commodity, YoY, geographic concentration | Company concentration (HHI/CR4 within substance), municipal map, monthly trend |

**Integration incompatibilities:** (1) production base year vs royalty cash date; (2) 56 grouped vs 156 commodity
substance names, so a versioned mapping seed is required; (3) CFEM rates differ by substance, so CFEM is a fiscal proxy and
never "revenue"; (4) AMB has no company field, so **business concentration can only come from CFEM**, and **geographic
concentration** comes from AMB; (5) joins happen only after both sides are aggregated to (year, uf, substance_group).

**KPIs feasible with the verified fields**

| KPI | Source | Note |
|---|---|---|
| Total value of beneficiated sales (R$, nominal) | AMB | "Valor Venda" is sales value, not total production value. Label it that way |
| Volume by substance | AMB | Only within one substance and unit. Never summed across substances |
| YoY % (value, volume) | AMB | Null when the prior year is 0 or missing |
| State share %, state ranking | AMB | |
| Substance share % of sales value | AMB | |
| Geographic HHI (by UF), overall and per substance | AMB | Measures geographic concentration |
| CR1/CR4 and cumulative share (Pareto) of substances/states | AMB | |
| CFEM collected by UF, municipality, month | CFEM | |
| Company HHI / CR4 within a substance (e.g. Ferro) | CFEM, PJ only | Proxy for share of taxable sales. Masked-CPF payers grouped as "individuals" |
| Real (inflation-adjusted) values | — | **Not possible with ANM data alone.** IPCA would be a third source and needs a separate decision |

## 2. Project 02 — Oil & Gas

| | Primary | Complementary |
|---|---|---|
| Dataset | ANP **Production by state and location**: oil (m³), natural gas, reinjection, flaring and loss, own consumption, available gas (1000 m³) | ANP LGN by state. **Anuário 2026** tables 2.14/2.19/2.21/2.22 (annual reconciliation, pre-salt split) |
| URL base | https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/ppgn-el/ | Anuário page (see evaluation doc) |
| Grain | Month × UF × location (TERRA/MAR) | Month × UF (LGN). Year × location × UF (Anuário) |
| Coverage | Oil and gas Jan 1997 – Sep 2026. Gas uses Jan 2000 – Sep 2026 | LGN 1997–2026. Anuário 2016–2025 |
| Size | 7 files, 2.83 MB, ~48k rows total | < 1 MB |
| Complexity | Low–medium (densifying sparse rows, future zeros, provisional months) | Low |
| Analytical potential | Monthly and daily average production, MoM/YoY, rolling 3M/12M, volatility, anomalies, regional share, gas utilisation balance | Validation, pre-salt context |

**Incompatibilities:** oil is in m³ and gas in 1000 m³, so they are **never summed**. A boe conversion is out of scope unless a
documented ANP factor is adopted. LGN has no onshore/offshore split. Well-level files (deferred) report gas in Mm³ and use
inconsistent file naming across years.

**KPIs feasible**

| KPI | Note |
|---|---|
| Monthly production (oil m³, gas 1000 m³) | |
| Daily average = monthly / calendar days of the month | Uses actual days, including leap Februaries |
| MoM %, YoY % | Null when the denominator is 0 or missing |
| Rolling 3M / 12M averages | Null until a full window exists |
| YTD cumulative production | |
| Regional share (UF, offshore vs onshore) | |
| Volatility (rolling 12M std of MoM %), historical peak, deviation from the 12M baseline (z-score) | Statistical anomalies only, not confirmed incidents |
| **Gas reinjection rate, flaring rate, own-use rate, availability rate** (% of production) | Valid: the balance identity is verified (median gap 0%) |
| Oil bbl/d | Only as a labelled conversion (1 m³ = 6.2898 bbl) |

## 3. Size and compute estimate (measured)

| Item | Download | Rows | Engine | Expected cost |
|---|---|---|---|---|
| AMB (3 files) | 1.74 MB | ~10.7k | DuckDB | Seconds |
| CFEM Arrecadação | 325 MB | ≈2.4 M (*estimate*) | DuckDB (columnar, out-of-core) | Seconds to under a minute. Store only the Parquet output, never the raw file, in Git |
| ANP state/location (7 files) | 2.83 MB | ~48k | pandas | Seconds |
| Final Tableau extracts | target < 10 MB each | — | — | Fits Tableau Public limits |

No paid service is needed. Everything runs locally.

## 4. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| ANM TLS chain is incomplete | curl/OpenSSL downloads fail | Download through PowerShell/.NET. **Never disable certificate checks** |
| Both portals update **daily/monthly in place** | Results change between runs | Record SHA-256 + timestamp of each raw file in a manifest |
| Zeros for future months (ANP oil) | Fake collapse in production | QA rule to cut the series at the last fully reported month |
| Provisional recent months | Revisions | `is_provisional` flag for the current year |
| Metadata disagrees with files (separator, column names) | Silent parse errors | Schema assertions in tests |
| AMB↔CFEM substance mapping | Mis-joins | Explicit seed table, with unmapped share reported |
| CFEM ≠ revenue, rates vary | Misinterpretation | Labelled as "royalty collected" on every chart |
| Licence not explicit | Reuse uncertainty | Attribute ANM/ANP. Recorded in LIMITATIONS |
| Nominal R$ only | Value growth includes inflation | State "nominal" on every chart. IPCA only if approved |

## 5. Design system

No official SA Design System token file was found under `C:\Tableau`. The existing dashboard
`FAB/FAB Supplier Concentration.html` contains a complete CSS token set (forest/sage palette, light and dark mode;
Newsreader / IBM Plex Sans / IBM Plex Mono). Before Phase 9 you need to confirm whether these are the official
SA tokens. If no official files exist, `DESIGN_SYSTEM_REQUIRED.md` will be created, as the prompt requires.

## 6. Commands to proceed (Windows, free tools)

DuckDB is **not installed**. pandas 3.1.1 and numpy 2.5.5 are present under `C:\Python315`.

```powershell
python -m pip install duckdb pytest matplotlib jupyter
```

```powershell
python -c "import duckdb, pandas, pytest; print(duckdb.__version__, pandas.__version__, pytest.__version__)"
```

```powershell
cd C:\Tableau\industrial-data-analytics; git init
```
