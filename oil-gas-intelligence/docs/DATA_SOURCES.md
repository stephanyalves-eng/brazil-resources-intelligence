# Data Sources — Oil & Gas

Base URL of the monthly series: `https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/ppgn-el/`
Catalogue page: https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/producao-de-petroleo-e-gas-natural-por-estado-e-localizacao
(says "updated 29/10/2026", monthly cadence).

| # | File | Measure | Unit | Coverage used | Role |
|---|---|---|---|---|---|
| 1 | `producao-petroleo-m3.csv` | Oil production | m³ | 1997-01 → 2026-09 | **Primary** |
| 2 | `producao-gas-natural-1000m3.csv` | Gas production | 1000 m³ | 1997-01 → 2026-09 | **Primary** |
| 3 | `producao-lgn-m3.csv` | NGL production | m³ | 1997-01 → 2026-09 | Complementary (no onshore/offshore split) |
| 4 | `reinjecao-gn-1000m3` (no extension) | Gas reinjection | 1000 m³ | 2000-01 → 2026-09 | Gas utilisation |
| 5 | `queima-e-perda-gn-1000m3.csv` | Flaring and losses | 1000 m³ | 2000-01 → 2026-09 | Gas utilisation |
| 6 | `consumo-proprio-gn1000m3.csv` | Own consumption in E&P | 1000 m³ | 2000-01 → 2026-09 | Gas utilisation |
| 7 | `gn-disponivel-1000m3.csv` | Available gas | 1000 m³ | 2000-01 → 2026-09 | Gas utilisation |
| 8 | Anuário Estatístico 2026, tables 2.14 / 2.19 / 2.21 / 2.22 (`…/anuario-estatistico-2026/secao-2/anuario-2026-dados_abertos-tabela2-XX.csv`) | Annual oil (thousand bbl), gas, reinjection, flaring (million m³) by UF × location | — | 2016–2025 | **Reconciliation only** |
| 9 | Metadata PDFs (`metadados-*.pdf`) | Field definitions | — | — | Documentation |

Grain of 1–7: month × UF × location (TERRA/MAR). Format: UTF-8 with BOM, `;` separator, decimal comma, Portuguese month
abbreviations. Source cited in the metadata: *ANP – Boletim Mensal de Produção (Decreto 2.705/1998)*, ANP/SDC.

**Exact versions:** `data/raw/MANIFEST.csv` (bytes, SHA-256, download time).

**Licence and attribution:** no dataset licence is stated on the pages or in the metadata. The gov.br footer licence (CC BY-ND 3.0)
covers *site content*. The data is published under Decreto 8.777/2016. Cite it as: *"Fonte: ANP — Produção de petróleo e gás
natural por estado e localização; Anuário Estatístico 2026, acesso em 2026-11-18."*

**Evaluated and deferred:** well-level production (`fase-de-desenvolvimento-e-producao`; offshore 2025 ≈ 2.0 MB per year, onshore
split by quarter or semester). It would add field and installation detail; it is listed as a future extension.
