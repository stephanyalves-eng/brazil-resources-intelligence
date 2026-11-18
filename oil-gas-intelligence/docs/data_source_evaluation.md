# Data Source Evaluation — Brazilian Oil & Gas Production Analytics

Phase 1 output. Files were downloaded and profiled on **2026-11-18** (scripts in `shared/phase1_profiling/`).

## 1. Sources checked

| Portal page | URL | What it offers |
|---|---|---|
| Production by state and location | https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/producao-de-petroleo-e-gas-natural-por-estado-e-localizacao | 7 monthly CSVs + PDF metadata. Page says data updated 29/10/2026, monthly cadence (published by the last day of the following month) |
| Development & production phase | https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/fase-de-desenvolvimento-e-producao | Well-level production, offshore (`pm/`, 1941–2026) and onshore (`pt/`, quarterly/semester files, 1992–2026). Metadata in DOCX |
| Anuário Estatístico 2026 | https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/anuario/anuario-estatistico-2026-dados-abertos | Annual tables 2016–2025 (Section 2: production by basin/location/state, concessionaire, operator, reinjection, flaring) |

## 2. Comparison matrix: production by state and location (base URL `…/dados-abertos/arquivos/ppgn-el/`)

| File | Bytes | Rows × cols | Period | Unit | Measure column | Dims | Key duplicates | Blanks |
|---|---|---|---|---|---|---|---|---|
| `producao-petroleo-m3.csv` | 463,261 | 7,920 × 7 | Jan 1997 – Dec 2026* | m³ | PRODUÇÃO | ANO, MÊS, GRANDE REGIÃO, UF, LOCALIZAÇÃO (TERRA/MAR) | 0 | 0% |
| `producao-gas-natural-1000m3.csv` | 480,850 | 7,775 × 7 | Jan 1997 – Sep 2026 | 1000 m³ | PRODUÇÃO | same | 0 | 0% |
| `producao-lgn-m3.csv` | 167,964 | 3,567 × 6 | 1997 – 2026 | m³ | PRODUÇÃO | **no LOCALIZAÇÃO** | 0 | 0% |
| `reinjecao-gn-1000m3` (no extension, served as text/csv) | 414,491 | 7,021 × 7 | 2000 – Sep 2026 | 1000 m³ | REINJETADO | same as gas | 0 | 0% |
| `queima-e-perda-gn-1000m3.csv` | 431,035 | 7,043 × 7 | 2000 – Sep 2026 | 1000 m³ | QUEIMADO | same | 0 | 0% |
| `consumo-proprio-gn1000m3.csv` | 431,686 | 7,034 × 7 | 2000 – Sep 2026 | 1000 m³ | CONSUMO | same | 0 | 0% |
| `gn-disponivel-1000m3.csv` | 439,803 | 7,049 × 7 | 2000 – Sep 2026 | 1000 m³ | DISPONÍVEL | same | 0 | 0% |

Common properties: UTF-8 with BOM, `;` separator, decimal comma, month as a Portuguese abbreviation (JAN…DEZ),
UF and region as upper-case full names (11 producing UFs, 4 regions; no Centro-Oeste rows, although the metadata lists it).
Source cited in the metadata: *ANP – Boletim Mensal de Produção (Decreto 2.705/1998)*, owner ANP/SDC.

### Issues found during profiling (these become QA rules)

1. **Future months are stored as zeros.** `producao-petroleo-m3.csv` has 264 rows for 2026, covering Jan–Dec. Oct, Nov and Dec 2026 sum to exactly **0 m³**, while every other 2026 month is around 18–23 million m³. The gas file stops at Sep 2026. Zero must not be read as "no production". Rule: drop any period after the last month that is non-zero nationally *and* present in every series, then flag it.
2. **Precision changes.** Values up to 2025 are integers. 2026 values carry 3 decimals (`19484791.358`). This is consistent with provisional vs consolidated data. The 2026 months are flagged `is_provisional`.
3. **Column name differs from metadata.** The metadata column is "QUEIMA E PERDA", but the CSV column is `QUEIMADO`.
4. **Rows are sparse, not complete.** There are 2,447 zero-valued oil rows, and different files have different row counts per year (e.g. reinjection 2024 has 256 rows vs 264). Missing UF × location × month combinations must be densified and labelled `not_reported`, kept separate from reported zeros.
5. **Gas balance identity holds.** For each UF × location × month, production ≈ reinjection + flaring/loss + own consumption + available gas. The median gap is 0.0% and the interquartile range is 0.0% (4,979 rows with prod > 0). Large relative gaps appear only in rows with tiny production. 69 keys are missing at least one component. Nationally for 2025 (bn m³): production 65.42; reinjection 35.59, flaring 1.85, own use 6.43, available 21.84 (sum 65.71). This **makes gas-utilisation ratios methodologically valid**.
6. **Sanity check against public figures:** 2025 oil = 218.78 million m³ ≈ 3.77 million bbl/d (× 6.2898 bbl/m³ ÷ 365). This matches the order of magnitude ANP reports publicly.

## 3. Other candidates

| Candidate | Grain | Measured size | Verdict |
|---|---|---|---|
| Well-level offshore (`pm/producao-mar-2025.csv`) | Month × state × basin × field × well × installation; 21 columns (oil, condensate, associated / non-associated gas, water, 8 injection types) | 1,996,681 bytes for 2025 (from Content-Range; a HEAD request returns 403, ranged GET works) | **Complementary, optional.** Adds field/basin/installation detail. Units differ (gas in Mm³ = thousand m³), and the onshore files are split by quarter/semester with renamed file patterns. Use only for a limited field-level drill-down after reconciling to state totals |
| Well-level onshore (`pt/<year>/…trim.csv`) | same | not measured (HEAD 403) | Same as above |
| Anuário 2026 Tabela 2.14 / 2.19 / 2.21 / 2.22 | Annual × location (incl. pre-salt/post-salt) × UF, 2016–2025 | not downloaded | **Reconciliation benchmark**: annual totals from the monthly files must match the Anuário within rounding. Also the only official source for the **pre-salt split** |
| Anuário 2026 Tabela 2.16 / 2.17 | 2025 by concessionaire / operator | not downloaded | Single year only, so not usable for trends. Optional context |

Licence: neither the data pages nor the metadata state a dataset licence. The gov.br site footer applies
CC BY-ND 3.0 to *site content*. The data itself is published under the federal open-data policy
(Decreto 8.777/2016). Treat it as reusable with attribution ("Fonte: ANP"). This is recorded as a residual
uncertainty, not as a confirmed licence.

## 4. Selection

- **Primary:** the 4 gas files (production, reinjection, flaring/loss, own consumption, available) + oil production, monthly × UF × location, 1997/2000 → Sep 2026.
- **Complementary:** LGN production (state-level only). Anuário 2026 tables 2.14/2.19/2.21/2.22 for annual reconciliation and the pre-salt split.
- **Deferred:** well-level data, to be brought in only for a field-level drill-down once the state-level product is complete.
