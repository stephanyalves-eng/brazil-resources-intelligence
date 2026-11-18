# Data Sources — Mining

| # | Dataset | Publisher | Direct URL | Format | Coverage used | Snapshot (server Last-Modified) | Role |
|---|---|---|---|---|---|---|---|
| 1 | AMB – Produção Beneficiada | ANM | https://dadosabertos.anm.gov.br/AMB/Producao_Beneficiada.csv | CSV, CP-1252, `,` | Base years 2010–2025, UF × substance | 2026-11-18 09:05 GMT | **Primary** (value, volume) |
| 2 | AMB – Produção Bruta | ANM | https://dadosabertos.anm.gov.br/AMB/Producao_Bruta.csv | same | 2010–2025 | 2026-11-18 09:05 GMT | Sibling fact (ROM tonnage) |
| 3 | AMB metadata | ANM | https://dadosabertos.anm.gov.br/AMB/metadados-amb.ods | ODS | — | 2026-02-04 | Field definitions |
| 4 | CFEM – Arrecadação | ANM | https://dadosabertos.anm.gov.br/CFEM/CFEM_Arrecadacao.csv | CSV, CP-1252, `,` | 2004-01 → 2026-06 usable (2002-08 → 2026-11 published) | 2026-11-18 09:04 GMT | **Complementary** (royalty, municipality, company) |
| 5 | CFEM metadata | ANM | https://dadosabertos.anm.gov.br/CFEM/metadados-cfem.ods | ODS | — | 2026-02-04 | Field definitions |
| 6 | CNPJ registry (legal names) | Receita Federal, via BrasilAPI | https://brasilapi.com.br/api/cnpj/v1/{cnpj} | JSON | 25 largest CFEM payers (2021–2025) | retrieved 2026-11-18 | Company names (`seeds/company_names.csv`) |

Catalogue pages: https://dadosabertos.anm.gov.br/AMB · https://dadosabertos.anm.gov.br/CFEM ·
https://www.gov.br/anm/pt-br/acesso-a-informacao/dados-abertos/bases-de-dados/bases-de-dados/

**Exact file versions:** `data/raw/MANIFEST.csv` (bytes, SHA-256, Last-Modified, download time). ANM updates these files
**daily in place**, so a later download can differ. The tests detect a changed file.

**Licence and attribution:** the ANM metadata states no dataset licence. The data is published under Brazil's federal open-data
policy (Decreto 8.777/2016). Cite it as: *"Fonte: Agência Nacional de Mineração (ANM), Dados Abertos — AMB e CFEM, acesso em
2026-11-18."* CNPJ registration data is public information from Receita Federal.

**Access note:** `dadosabertos.anm.gov.br` serves an incomplete TLS certificate chain. Downloads use the Windows TLS stack
(`acquire_raw.ps1`), and certificate verification is never disabled.

**Candidates evaluated and not used:** AMB Água Mineral, CFEM Distribuição (317 MB, fiscal distribution) and CFEM Autuação
(enforcement). See [data_source_evaluation.md](data_source_evaluation.md).
