# Data Source Evaluation — Brazilian Mining Performance & Market Concentration

Phase 1 output. Every figure below comes from files downloaded and profiled on **2026-11-18**
(scripts in `shared/phase1_profiling/`). Figures marked *estimate* are extrapolated from a measured
sample and say how.

## 1. Sources checked

| Portal | URL | Status on 2026-11-18 |
|---|---|---|
| ANM open data, AMB | https://dadosabertos.anm.gov.br/AMB/ | Online. IIS directory listing, 4 files |
| ANM open data, CFEM | https://dadosabertos.anm.gov.br/CFEM/ | Online. IIS directory listing, 9 files |
| ANM catalogue on gov.br | https://www.gov.br/anm/pt-br/acesso-a-informacao/dados-abertos/bases-de-dados/bases-de-dados/ | Not opened in Phase 1. The two ANM folders above are the catalogue's source (`Catálogo origem` in the ODS metadata) |

**Access note:** `dadosabertos.anm.gov.br` sends an incomplete TLS certificate chain. Strict clients
(curl/OpenSSL, Node) fail with "unable to verify the first certificate". The Windows TLS stack
(PowerShell `Invoke-WebRequest`) can still build the chain and download normally. The pipeline
**must not** turn certificate checks off. It should download through PowerShell/.NET or another client
that completes the chain via AIA.

## 2. Comparison matrix

| Criterion | AMB Produção Bruta | AMB Produção Beneficiada | AMB Água Mineral | CFEM Arrecadação | CFEM Distribuição | CFEM Autuação |
|---|---|---|---|---|---|---|
| Direct URL | `/AMB/Producao_Bruta.csv` | `/AMB/Producao_Beneficiada.csv` | `/AMB/Agua_Mineral_Producao.csv` | `/CFEM/CFEM_Arrecadacao.csv` (+ 5 five-year splits) | `/CFEM/CFEM_Distribuicao.csv` | `/CFEM/CFEM_Autuacao.csv` |
| Size (bytes) | 991,623 | 678,757 | 71,974 | 325,179,278 (splits add up to 325.18 MB) | 317,276,257 | 3,031,566 |
| Last modified (server) | 2026-11-18 09:05 GMT | 2026-11-18 09:05 GMT | 2026-11-18 09:05 GMT | 2026-11-18 09:04 GMT | 2026-11-18 09:03 GMT | 2026-11-18 09:02 GMT |
| Update frequency (metadata) | Daily | Daily | Daily | Daily | Daily | Daily |
| Format / encoding | CSV, CP-1252 | CSV, CP-1252 | CSV, CP-1252 | CSV, CP-1252 | CSV, CP-1252 (metadata) | CSV, CP-1252 (metadata) |
| Separator (observed) | `,` with quoted decimal-comma numbers | same | same | `,` | not profiled | not profiled |
| Period | Base years 2010–2025 (16) | 2010–2025 (16) | 2010–2025 (16) | Collection years 2002–2026, monthly | Distribution year/month | Publication year/month |
| Grain | Year × UF × substance (× contained-element indicator) | Year × UF × substance (× contained indicator) | Year × UF | Payment slip line: year-month × mining process × holder × substance × municipality | Year-month × receiving entity × substance × distribution type | Enforcement case |
| Rows × cols | 6,307 × 14 | 3,982 × 18 | 432 × 17 | 22,284 × 14 in a 3 MB sample. Full file ≈ 2.4 M rows (*estimate*: sample density × file size) | not profiled | not profiled |
| Candidate key | (Ano, UF, Substância, Indicação Contido). (Ano, UF, Substância) alone has 74 duplicates | Same. 29 duplicates on the 3-column key | (Ano, UF) | None natural. 68 full-row duplicates in the sample (likely separate slips with the same values; must be checked against DataCriacao) | — | ProcessoCobrança |
| Blank values | 0% on all fields except `Indicação Contido` (71.7%, legitimately blank when no contained metal is reported) | 0% except `Indicação Contido` (67.6%) | 0% | 0% on all 14 fields in the sample. `UF` contains an empty-string category | — | — |
| Zeros | 40.1% of rows have Valor Venda = 0 (production that was transferred or consumed, not sold) | profiled in Phase 2 | — | No negative ValorRecolhido in the sample | — | — |
| Measures | ROM tonnage (t), contained qty, sale qty (t), sale value (R$), consumption and transfer qty/value | Beneficiated qty (unit varies by substance), contained qty, sale qty/value, plant consumption, transfers | Litres and R$ by package type | QuantidadeComercializada (units: t, m3, g, l, kg, m2, ct), **ValorRecolhido (R$)** | Valor (R$) distributed | Valor (R$) of the initial assessment |
| Units | ROM always t. Contained: t / kg / ct / "-" | Production: t (most), kg (Estanho, Ouro, Prata, Gemas), ct (Diamante). Exactly one unit per substance | l | 7 units, mixed **within** substances possible | R$ | R$ |
| Geography | UF (27) | UF (26) | UF (27) | UF + IBGE municipality code (7-digit, joinable to IBGE) | UF / municipality entity | Municipality / UF |
| Company / holder | **None** | **None** | None | CPF_CNPJ: full 14-digit CNPJ for companies (97.3% of sample rows). CPF masked for individuals | — | NomeTitular + CPF_CNPJ |
| Monetary fields | Nominal R$ | Nominal R$ | Nominal R$ | Nominal R$ | Nominal R$ | Nominal R$ |
| Licence | No dataset-level licence in the metadata ODS. Published under Brazil's federal open-data policy (Decreto 8.777/2016). Cite "ANM – Agência Nacional de Mineração" | same | same | same | same | same |
| Analytical fit | Mine-level output and sales | **Best value measure**: market value of sold beneficiated product | Niche | **Only source of company-level and municipal detail** | Fiscal federalism, not industry structure | Compliance, out of scope |
| Processing cost | Trivial | Trivial | Trivial | Moderate: 325 MB CSV. DuckDB scans it in seconds; pandas would need ~2–3 GB RAM | High, out of scope | Low |

### Metadata vs. file discrepancies found

1. The metadata says the separator is `;`. The files actually use `,` and quote decimal-comma numbers. Ingestion must say this explicitly.
2. Column names differ in case from the metadata (`Ano base` vs `Ano Base`, `Classe Substância Mineral` in Água Mineral). Staging has to normalise names.
3. Numbers have mixed precision and float artefacts (`87835,169999999998`, `,000000`). Parse as DECIMAL after replacing the comma, and round to 2 dp for R$.
4. The metadata changelog dates the ODS 04/02/2025, but the server shows 2026-02-04. Minor, but it means metadata timestamps should not be trusted as data-freshness evidence.

## 3. Selection

| Role | Dataset | Reason |
|---|---|---|
| **Primary** | **AMB Produção Beneficiada** (with Produção Bruta as a sibling fact) | Official annual production *and* sale value by UF × substance, 2010–2025, one consistent unit per substance, small and clean |
| **Complementary** | **CFEM Arrecadação** (monthly, 2002–2026) | Adds monthly frequency, municipality, and the **only identifiable company dimension** (CNPJ). Needed for business concentration (HHI) |
| Rejected | Água Mineral, CFEM Distribuição, CFEM Autuação | Out of scope for production and market structure, or too large for the value they add |

### Is integrating the two analytically valid?

Yes, but only at an aggregated grain and with three documented constraints:

- **Different events.** AMB records production and sales in a *base year* (declared in the RAL). CFEM records a *royalty payment* on its collection date (cash basis, possibly paying for an earlier period). Joined at year × UF they are comparable, but they are not the same transaction.
- **Different substance vocabularies.** AMB uses 56 grouped names ("Alumínio (Bauxita)", "Rochas (Britadas) e Cascalho"). CFEM uses 156 upper-case commodity names ("AREIA", "CASCALHO"). A hand-built, versioned `substance_map` seed table is required. Only mapped substances get joined, and unmapped CFEM value is reported, never dropped silently.
- **CFEM rates vary by substance** (Lei 13.540/2017). CFEM is therefore *not* proportional to production value across substances. Company HHI must be computed **within a substance**, using CFEM shares as a proxy for each company's share of taxable sales. It must never be presented as total industry revenue.

To avoid fan-out, both sides are pre-aggregated to (year, uf, substance_group) before any join.
