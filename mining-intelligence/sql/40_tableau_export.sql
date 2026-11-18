-- =====================================================================================
-- Phase 8 - Tableau extracts. One CSV per analytical grain, written to tableau/data/.
-- Format: UTF-8, ',' delimiter, '.' decimal, ISO dates, header row, empty string = NULL.
-- Column names are English snake_case; every column is described in tableau/data_dictionary.csv
-- (a test enforces the match). Values: nominal R$.
-- =====================================================================================

CREATE OR REPLACE TABLE seed_company_names AS
SELECT cnpj_root, legal_name FROM read_csv('seeds/company_names.csv', header = true, all_varchar = true);

-- name: export_dim_uf
COPY (
  SELECT uf, uf_name, region, ibge_uf_code, 'BR-' || uf AS iso_3166_2
  FROM dim_uf ORDER BY uf
) TO 'tableau/data/dim_uf.csv' (HEADER, DELIMITER ',');

-- name: export_dim_substance
COPY (
  SELECT substance_group, substance_class_en, has_amb_equivalent
  FROM dim_substance_group ORDER BY substance_group
) TO 'tableau/data/dim_substance.csv' (HEADER, DELIMITER ',');

-- name: export_amb_uf_substance_year
-- Grain: year x UF x substance group. Main table of Regional & Commodity Analysis.
COPY (
  SELECT base_year AS year, uf, substance_group, substance_class_en,
         round(sale_value_brl, 2) AS sale_value_brl,
         round(production_qty, 3) AS production_qty, unit,
         round(value_yoy, 6) AS value_yoy, round(qty_yoy, 6) AS qty_yoy,
         round(uf_share_of_substance, 6) AS uf_share_of_substance,
         round(share_of_national, 6) AS share_of_national,
         (uf = 'ES' AND substance_group = 'Iron ore') AS dq_flag_intermittent_series
  FROM mart_amb_uf_substance_year ORDER BY year, uf, substance_group
) TO 'tableau/data/amb_uf_substance_year.csv' (HEADER, DELIMITER ',');

-- name: export_amb_uf_year
COPY (
  SELECT base_year AS year, uf, uf_name, region, round(sale_value_brl, 2) AS sale_value_brl, n_substance_groups,
         round(share_of_national, 6) AS share_of_national, rank_in_year, round(cumulative_share, 6) AS cumulative_share,
         round(value_yoy, 6) AS value_yoy, rank_change
  FROM mart_amb_uf_year ORDER BY year, rank_in_year, uf
) TO 'tableau/data/amb_uf_year.csv' (HEADER, DELIMITER ',');

-- name: export_amb_substance_year
COPY (
  SELECT base_year AS year, substance_group, substance_class_en, round(sale_value_brl, 2) AS sale_value_brl,
         round(production_qty, 3) AS production_qty, unit, n_producing_ufs,
         round(share_of_national, 6) AS share_of_national, rank_in_year, round(cumulative_share, 6) AS cumulative_share,
         round(value_yoy, 6) AS value_yoy, round(qty_yoy, 6) AS qty_yoy
  FROM mart_amb_substance_year ORDER BY year, rank_in_year, substance_group
) TO 'tableau/data/amb_substance_year.csv' (HEADER, DELIMITER ',');

-- name: export_amb_national_year
COPY (
  SELECT base_year AS year, round(sale_value_brl, 2) AS sale_value_brl, round(value_yoy, 6) AS value_yoy,
         n_ufs, n_substance_groups
  FROM mart_amb_national_year ORDER BY year
) TO 'tableau/data/amb_national_year.csv' (HEADER, DELIMITER ',');

-- name: export_amb_price_volume
-- Grain: year x substance group (single-unit groups only). Log-point decomposition of value change.
COPY (
  WITH b AS (
    SELECT base_year, substance_group, any_value(unit) AS unit, sum(sale_value_brl) AS v, sum(sale_qty) AS q
    FROM fct_amb_beneficiada GROUP BY ALL HAVING count(DISTINCT unit) = 1
  ),
  c AS (
    SELECT *, lag(v) OVER w AS v0, lag(q) OVER w AS q0, lag(base_year) OVER w AS y0
    FROM b WINDOW w AS (PARTITION BY substance_group ORDER BY base_year)
  )
  SELECT base_year AS year, substance_group, unit, round(v, 2) AS sale_value_brl, round(q, 3) AS sale_qty,
         round(v / NULLIF(q, 0), 4) AS unit_value_brl,
         CASE WHEN y0 = base_year - 1 AND v0 > 0 AND q0 > 0 AND q > 0 AND v > 0
              THEN round(100 * ln(q / q0), 3) END AS volume_effect_logpts,
         CASE WHEN y0 = base_year - 1 AND v0 > 0 AND q0 > 0 AND q > 0 AND v > 0
              THEN round(100 * ln((v / q) / (v0 / q0)), 3) END AS unit_value_effect_logpts
  FROM c ORDER BY substance_group, year
) TO 'tableau/data/amb_price_volume.csv' (HEADER, DELIMITER ',');

-- name: export_cfem_uf_substance_year
-- Grain: year x UF x substance group (usable months; 2026 = YTD Jan-Jun provisional). 'N/A' = no UF reported.
COPY (
  SELECT year, cfem_year_status(year) AS year_status, coalesce(uf, 'N/A') AS uf, substance_group,
         round(sum(cfem_brl), 2) AS cfem_brl, count(DISTINCT holder_key) AS n_holders,
         count(DISTINCT period_month) AS n_months
  FROM v_cfem_usable GROUP BY ALL ORDER BY year, uf, substance_group
) TO 'tableau/data/cfem_uf_substance_year.csv' (HEADER, DELIMITER ',');

-- name: export_cfem_municipality_year
COPY (
  SELECT year, year_status, ibge_municipality_code, municipality_name, uf, main_substance_group,
         round(cfem_brl, 2) AS cfem_brl, rank_in_year
  FROM mart_cfem_municipality_year ORDER BY year, rank_in_year, ibge_municipality_code
) TO 'tableau/data/cfem_municipality_year.csv' (HEADER, DELIMITER ',');

-- name: export_cfem_monthly
COPY (
  SELECT period_month, month_status, substance_group, round(cfem_brl, 2) AS cfem_brl,
         round(cfem_brl_rolling_12m, 2) AS cfem_brl_rolling_12m, round(cfem_brl_same_month_ly, 2) AS cfem_brl_same_month_ly
  FROM mart_cfem_monthly ORDER BY substance_group, period_month
) TO 'tableau/data/cfem_monthly.csv' (HEADER, DELIMITER ',');

-- name: export_cfem_company_substance_year
-- Grain: year x substance group x company (top 10 per group-year) + one 'All other holders' row.
-- Company = legal entity (CNPJ root). Names: Receita Federal via BrasilAPI for the 25 largest; else the CNPJ root.
COPY (
  WITH h AS (SELECT * FROM mart_cfem_holder_substance_year),
  top AS (
    SELECT h.year, h.year_status, h.substance_group, h.rank_in_substance AS rank, h.holder_key AS company_key, h.holder_type,
           CASE WHEN h.holder_type = 'PJ' THEN coalesce(n.legal_name, 'CNPJ root ' || h.holder_key) ELSE h.holder_key END AS company_name,
           h.cfem_brl, h.share_in_substance, h.cumulative_share
    FROM h LEFT JOIN seed_company_names n ON n.cnpj_root = h.holder_key
    WHERE h.rank_in_substance <= 10
  ),
  rest AS (
    SELECT year, any_value(year_status) AS year_status, substance_group, 11 AS rank, 'OTHERS' AS company_key, 'MIXED' AS holder_type,
           'All other holders (' || count(*) || ')' AS company_name, sum(cfem_brl) AS cfem_brl,
           sum(share_in_substance) AS share_in_substance, 1.0 AS cumulative_share
    FROM h WHERE rank_in_substance > 10 GROUP BY year, substance_group
  )
  SELECT year, year_status, substance_group, rank, company_key, holder_type, company_name,
         round(cfem_brl, 2) AS cfem_brl, round(share_in_substance, 6) AS share_in_substance,
         round(cumulative_share, 6) AS cumulative_share
  FROM (SELECT * FROM top UNION ALL SELECT * FROM rest)
  ORDER BY year, substance_group, rank
) TO 'tableau/data/cfem_company_substance_year.csv' (HEADER, DELIMITER ',');

-- name: export_concentration
COPY (
  SELECT year, concentration_type, scope, n_participants, hhi, cr1_pct, cr4_pct,
         CASE WHEN concentration_type LIKE 'business%' THEN coalesce(n.legal_name, 'CNPJ root ' || top_participant)
              WHEN concentration_type LIKE 'geographic%' THEN u.uf_name ELSE top_participant END AS top_participant,
         round(total_value_brl, 2) AS total_value_brl, hhi_band
  FROM mart_concentration c
  LEFT JOIN seed_company_names n ON n.cnpj_root = c.top_participant
  LEFT JOIN dim_uf u ON u.uf = c.top_participant
  ORDER BY concentration_type, scope, year
) TO 'tableau/data/concentration.csv' (HEADER, DELIMITER ',');

-- name: export_amb_cfem_uf_substance_year
COPY (
  SELECT year, uf, substance_group, round(amb_sale_value_brl, 2) AS amb_sale_value_brl, round(cfem_brl, 2) AS cfem_brl,
         round(cfem_to_amb_sales_ratio, 6) AS cfem_to_amb_sales_ratio, match_status
  FROM mart_amb_cfem_uf_substance_year ORDER BY year, uf, substance_group
) TO 'tableau/data/amb_cfem_uf_substance_year.csv' (HEADER, DELIMITER ',');

-- name: export_metadata
COPY (
  SELECT * FROM (VALUES
    ('AMB', 'ANM - Anuário Mineral Brasileiro, Produção Beneficiada', 'https://dadosabertos.anm.gov.br/AMB/Producao_Beneficiada.csv',
     '2010-2025 (base years)', 'Value of beneficiated sales reported in the RAL; nominal R$'),
    ('CFEM', 'ANM - CFEM Arrecadação', 'https://dadosabertos.anm.gov.br/CFEM/CFEM_Arrecadacao.csv',
     '2004-01 to 2026-06 (usable months)', 'Royalty collected (not revenue); nominal R$; Feb 2024 duplicate export removed'),
    ('Company names', 'Receita Federal CNPJ registry via BrasilAPI', 'https://brasilapi.com.br',
     'retrieved 2026-11-18', 'Legal entity names for the 25 largest CFEM payers (2021-2025)'),
    ('Snapshot', 'Raw files downloaded', 'data/raw/MANIFEST.csv', '2026-11-18', 'SHA-256 of every raw file recorded')
  ) t(source_key, source_name, url, coverage, note)
) TO 'tableau/data/metadata.csv' (HEADER, DELIMITER ',');
