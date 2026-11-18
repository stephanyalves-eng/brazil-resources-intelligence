# KPI Definitions — Mining

All money is **nominal R$**. The "Reference value" column is the 2025 result from the 2026-11-18 build. Use it to check the Tableau build (§7 of the build guide).

| # | KPI | Definition | Source table · field | Tableau formula | Reference value | Caveat |
|---|---|---|---|---|---|---|
| K1 | Value of beneficiated sales | Σ value of beneficiated mineral sales reported in the RAL | `amb_national_year.sale_value_brl` | `SUM([sale_value_brl])` | R$ 281.69 bn (2025) | Sales value, not total production value; transfers and own use are excluded |
| K2 | Value YoY | K1(t) / K1(t−1) − 1 | `amb_national_year.value_yoy` | `[KPI Value YoY]` (guide §3) | +15.2 % | NULL for 2010 |
| K3 | 15-year CAGR | (K1₂₀₂₅ / K1₂₀₁₀)^(1/15) − 1 | `amb_national_year` | `[KPI CAGR]` | +10.7 % | Nominal |
| K4 | Iron ore share | Iron ore value / K1 | `amb_substance_year` | `[KPI Iron Share]` | 56.7 % | — |
| K5 | Top-3 commodity share | Σ value of the 3 largest groups / K1 | `amb_substance_year.cumulative_share` at rank 3 | `[KPI Top3 Share]` | 82.1 % | — |
| K6 | State share | State value / K1 | `amb_uf_year.share_of_national` | recompute `SUM/TOTAL(SUM)` | MG 37.8 %, PA 36.9 % | ES 2021/2025 carries the DQ2 caveat |
| K7 | State ranking | Rank of K6 within the year | `amb_uf_year.rank_in_year` | `RANK(SUM([sale_value_brl]))` | 1 MG · 2 PA · 3 BA | — |
| K8 | Volume by substance | Σ beneficiated production in the group's unit | `amb_substance_year.production_qty` | `SUM([production_qty])` **with one group selected** | Iron ore 484.9 Mt | Never summed across groups |
| K9 | Unit value | Value / quantity sold | `amb_price_volume.unit_value_brl` | `SUM([sale_value_brl]) / SUM([sale_qty])` | Iron ore R$ 368/t; gold R$ 579,297/kg | Implied, not a market price |
| K10 | Volume vs unit-value effect | 100·ln(Q₁/Q₀) and 100·ln(P₁/P₀); they add to the total log change | `amb_price_volume` | as stored | Iron ore 2025: +9.4 / −2.2 | Arithmetic split only, not causality |
| K11 | Geographic HHI | Σ (UF share %)², 0–10,000 | `concentration` (type geographic, scope All substances) | `MAX([hhi])` | 2,862 | Concentration of *where* value is reported |
| K12 | Commodity-mix HHI | Σ (group share %)² | `concentration` (commodity mix) | `MAX([hhi])` | 3,591 | — |
| K13 | Business HHI (per commodity) | Σ (company share %)² within one substance group, PJ only, CFEM-based | `concentration` (business, scope = group) | `MAX([hhi])` | Iron ore 5,104; gold 1,166 | Company = legal entity (CNPJ root) |
| K14 | CR1 / CR4 | Share of the largest 1 / 4 participants | `concentration.cr1_pct / cr4_pct` | `MAX([cr4_pct])` | Iron ore CR1 70.6 % (VALE S.A.), CR4 87.6 % | Same caveat as K13 |
| K15 | CFEM collected | Σ CFEM royalty collected | `cfem_uf_substance_year.cfem_brl` | `SUM([cfem_brl])` | R$ 7.91 bn (2025) | **Not revenue.** 2026 = YTD Jan–Jun, provisional. Feb 2024 duplicates removed |
| K16 | CFEM by state / municipality | K15 by UF / IBGE municipality | `cfem_uf_substance_year`, `cfem_municipality_year` | `SUM([cfem_brl])` | Canaã dos Carajás 15.8 %, Parauapebas 13.9 % | — |
| K17 | Municipal top-10 share | Σ top-10 municipalities / K15 | `cfem_municipality_year` | `[KPI Top10 Municipal Share]` | 61.6 % | Lines without a valid IBGE code are excluded |
| K18 | CFEM per R$ of AMB sales | Σ CFEM / Σ AMB value, matched year × UF × group | `amb_cfem_uf_substance_year` (match_status = both) | `SUM([cfem_brl]) / SUM([amb_sale_value_brl])` | All mapped 2.70 %, iron ore 3.42 % | Indicator: different base and timing |
| K19 | Pareto (cumulative share) | Running Σ share by rank | `cumulative_share` columns | `RUNNING_SUM(SUM(v)) / TOTAL(SUM(v))` | — | — |

**HHI bands** (reference only, US DOJ/FTC 2010): < 1,500 unconcentrated · 1,500–2,500 moderately · > 2,500 highly concentrated.
