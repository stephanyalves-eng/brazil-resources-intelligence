# Data Dictionary — mining-intelligence

Generated from `tableau/data_dictionary.csv` by `shared/render_dictionary.py`; do not edit by hand.
Every exported column is listed (enforced by `tests/test_tableau_exports.py`). Files: `tableau/data/<table>.csv`.

## `dim_uf` — 27 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `uf` | String |  | Two-letter state code (Brazilian UF); geographic role State/Province |
| `uf_name` | String |  | State name |
| `region` | String |  | Macro-region (North / Northeast / Central-West / Southeast / South) |
| `ibge_uf_code` | Number (whole) |  | IBGE two-digit state code |
| `iso_3166_2` | String |  | ISO 3166-2 code (BR-XX); alternative geocoding key |

## `dim_substance` — 58 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `substance_group` | String |  | Analytical commodity group shared by AMB and CFEM (seeds/substance_map.csv) |
| `substance_class_en` | String |  | Metallic / Non-metallic / Energy / Gems & diamonds / Unclassified |
| `has_amb_equivalent` | Boolean |  | True if the group exists in AMB production data |

## `amb_national_year` — 16 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `year` | Number (whole) |  | AMB base year (2010-2025) |
| `sale_value_brl` | Number (decimal) | R$ nominal | Value of beneficiated mineral sales (AMB) - Brazil total |
| `value_yoy` | Number (decimal) | ratio | Year-on-year change of sale_value_brl (0.10 = +10 %); NULL for 2010 |
| `n_ufs` | Number (whole) | count | States with any reported value |
| `n_substance_groups` | Number (whole) | count | Substance groups with any reported value |

## `amb_uf_year` — 416 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `year` | Number (whole) |  | AMB base year |
| `uf` | String |  | State code (joins dim_uf) |
| `uf_name` | String |  | State name |
| `region` | String |  | Macro-region |
| `sale_value_brl` | Number (decimal) | R$ nominal | Value of beneficiated sales in the state (all substances) |
| `n_substance_groups` | Number (whole) | count | Substance groups reported in the state |
| `share_of_national` | Number (decimal) | ratio | State share of national value in the year |
| `rank_in_year` | Number (whole) | rank | 1 = largest state in the year |
| `cumulative_share` | Number (decimal) | ratio | Running share by rank (Pareto) |
| `value_yoy` | Number (decimal) | ratio | YoY change; NULL when the previous calendar year is missing or zero |
| `rank_change` | Number (whole) | rank | Rank this year minus rank previous year (negative = moved up) |

## `amb_substance_year` — 754 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `year` | Number (whole) |  | AMB base year |
| `substance_group` | String |  | Commodity group (joins dim_substance) |
| `substance_class_en` | String |  | Commodity class |
| `sale_value_brl` | Number (decimal) | R$ nominal | Value of beneficiated sales of the group (Brazil) |
| `production_qty` | Number (decimal) | see unit | Beneficiated production; NULL when the group mixes units |
| `unit` | String |  | Unit of production_qty (t / kg / ct) |
| `n_producing_ufs` | Number (whole) | count | States reporting the group |
| `share_of_national` | Number (decimal) | ratio | Group share of national value |
| `rank_in_year` | Number (whole) | rank | 1 = largest group in the year |
| `cumulative_share` | Number (decimal) | ratio | Running share by rank (Pareto) |
| `value_yoy` | Number (decimal) | ratio | YoY change of value; NULL across gaps or zero base |
| `qty_yoy` | Number (decimal) | ratio | YoY change of production quantity; same guard |

## `amb_uf_substance_year` — 3,929 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `year` | Number (whole) |  | AMB base year |
| `uf` | String |  | State code |
| `substance_group` | String |  | Commodity group |
| `substance_class_en` | String |  | Commodity class |
| `sale_value_brl` | Number (decimal) | R$ nominal | Value of beneficiated sales |
| `production_qty` | Number (decimal) | see unit | Beneficiated production; NULL when units are mixed |
| `unit` | String |  | Unit of production_qty |
| `value_yoy` | Number (decimal) | ratio | YoY change of value; NULL across gaps or zero base |
| `qty_yoy` | Number (decimal) | ratio | YoY change of quantity; same guard |
| `uf_share_of_substance` | Number (decimal) | ratio | State share of the group's national value (geographic concentration input) |
| `share_of_national` | Number (decimal) | ratio | Row share of total national value |
| `dq_flag_intermittent_series` | Boolean |  | True for ES iron ore - intermittent reporting (data-quality caveat DQ2) |

## `amb_price_volume` — 754 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `year` | Number (whole) |  | AMB base year |
| `substance_group` | String |  | Commodity group (single-unit groups only) |
| `unit` | String |  | Unit of sale_qty |
| `sale_value_brl` | Number (decimal) | R$ nominal | Value of beneficiated sales |
| `sale_qty` | Number (decimal) | see unit | Quantity sold |
| `unit_value_brl` | Number (decimal) | R$ per unit | Implied unit value = value / quantity sold |
| `volume_effect_logpts` | Number (decimal) | log-points | 100 x ln(Q / Q previous year); NULL when not computable |
| `unit_value_effect_logpts` | Number (decimal) | log-points | 100 x ln(P / P previous year); volume + unit value effects = total log change |

## `cfem_uf_substance_year` — 8,845 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `year` | Number (whole) |  | CFEM collection year (2004-2026) |
| `year_status` | String |  | complete / 2026 YTD Jan-Jun (provisional) |
| `uf` | String |  | State of the mining activity; N/A = not reported |
| `substance_group` | String |  | Commodity group |
| `cfem_brl` | Number (decimal) | R$ nominal | CFEM royalty collected (not revenue); Feb 2024 duplicates removed |
| `n_holders` | Number (whole) | count | Distinct paying holders (company = CNPJ root) |
| `n_months` | Number (whole) | count | Months with collections in the year |

## `cfem_municipality_year` — 54,123 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `year` | Number (whole) |  | CFEM collection year |
| `year_status` | String |  | complete / 2026 YTD Jan-Jun (provisional) |
| `ibge_municipality_code` | String |  | 7-digit IBGE municipality code (keep as String) |
| `municipality_name` | String |  | Municipality name (most frequent spelling in CFEM) |
| `uf` | String |  | State code |
| `main_substance_group` | String |  | Group with the largest single collection line in the year |
| `cfem_brl` | Number (decimal) | R$ nominal | CFEM collected in the municipality |
| `rank_in_year` | Number (whole) | rank | 1 = largest municipality in the year |

## `cfem_monthly` — 13,230 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `period_month` | Date |  | First day of the collection month (2004-01 to 2026-06) |
| `month_status` | String |  | complete / provisional |
| `substance_group` | String |  | Commodity group |
| `cfem_brl` | Number (decimal) | R$ nominal | CFEM collected in the month (0 = no collection that month) |
| `cfem_brl_rolling_12m` | Number (decimal) | R$ nominal | Sum of the last 12 months; NULL until 12 months exist |
| `cfem_brl_same_month_ly` | Number (decimal) | R$ nominal | Same month one year earlier; NULL in the first 12 months |

## `cfem_company_substance_year` — 8,117 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `year` | Number (whole) |  | CFEM collection year |
| `year_status` | String |  | complete / 2026 YTD Jan-Jun (provisional) |
| `substance_group` | String |  | Commodity group (shares are within the group) |
| `rank` | Number (whole) | rank | 1-10 = top payers; 11 = aggregated remainder |
| `company_key` | String |  | CNPJ root (8 digits; keep as String - leading zeros) or OTHERS / INDIVIDUALS / UNIDENTIFIED |
| `holder_type` | String |  | PJ (company) / PF (individuals; CPF masked) / UNKNOWN / MIXED (remainder row) |
| `company_name` | String |  | Registered legal name (Receita Federal via BrasilAPI) or 'CNPJ root ...' when not looked up |
| `cfem_brl` | Number (decimal) | R$ nominal | CFEM collected |
| `share_in_substance` | Number (decimal) | ratio | Share of the group's CFEM in the year |
| `cumulative_share` | Number (decimal) | ratio | Running share by rank |

## `concentration` — 1,789 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `year` | Number (whole) |  | Year |
| `concentration_type` | String |  | geographic (UF; AMB value) / commodity mix (AMB value) / business (CNPJ root; CFEM) |
| `scope` | String |  | Substance group; 'All substances' or 'Brazil' for totals |
| `n_participants` | Number (whole) | count | Number of states / groups / companies with value > 0 |
| `hhi` | Number (decimal) | index 0-10000 | Herfindahl-Hirschman Index = sum of squared % shares |
| `cr1_pct` | Number (decimal) | % | Share of the largest participant |
| `cr4_pct` | Number (decimal) | % | Share of the four largest participants |
| `top_participant` | String |  | Largest participant (state name / group / company legal name) |
| `total_value_brl` | Number (decimal) | R$ nominal | Total value over which shares are computed |
| `hhi_band` | String |  | unconcentrated (<1500) / moderately (1500-2500) / highly concentrated (>2500); US DOJ/FTC 2010 reference |

## `amb_cfem_uf_substance_year` — 5,596 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `year` | Number (whole) |  | Year (2010-2025) |
| `uf` | String |  | State code |
| `substance_group` | String |  | Commodity group with an AMB equivalent |
| `amb_sale_value_brl` | Number (decimal) | R$ nominal | AMB beneficiated sales value; NULL if CFEM-only |
| `cfem_brl` | Number (decimal) | R$ nominal | CFEM collected; NULL if AMB-only |
| `cfem_to_amb_sales_ratio` | Number (decimal) | ratio | CFEM / AMB value - indicator only (different base and timing) |
| `match_status` | String |  | both / amb_only / cfem_only |

## `metadata` — 4 rows

| Column | Tableau type | Unit | Description |
|---|---|---|---|
| `source_key` | String |  | Short source identifier |
| `source_name` | String |  | Source name |
| `url` | String |  | Official URL or local file |
| `coverage` | String |  | Period covered |
| `note` | String |  | Definition and caveats |
