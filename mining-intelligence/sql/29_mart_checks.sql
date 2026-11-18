-- Post-mart reconciliation checks (read-only). Formal pass/fail assertions are in tests/ (Phase 7).

-- name: chk_row_counts
SELECT 'fct_amb_beneficiada' AS t, count(*) AS n FROM fct_amb_beneficiada UNION ALL
SELECT 'fct_amb_bruta', count(*) FROM fct_amb_bruta UNION ALL
SELECT 'fct_cfem_monthly', count(*) FROM fct_cfem_monthly UNION ALL
SELECT 'mart_amb_uf_substance_year', count(*) FROM mart_amb_uf_substance_year UNION ALL
SELECT 'mart_amb_uf_year', count(*) FROM mart_amb_uf_year UNION ALL
SELECT 'mart_amb_substance_year', count(*) FROM mart_amb_substance_year UNION ALL
SELECT 'mart_cfem_uf_year', count(*) FROM mart_cfem_uf_year UNION ALL
SELECT 'mart_cfem_substance_year', count(*) FROM mart_cfem_substance_year UNION ALL
SELECT 'mart_cfem_municipality_year', count(*) FROM mart_cfem_municipality_year UNION ALL
SELECT 'mart_cfem_monthly', count(*) FROM mart_cfem_monthly UNION ALL
SELECT 'mart_cfem_holder_substance_year', count(*) FROM mart_cfem_holder_substance_year UNION ALL
SELECT 'mart_concentration', count(*) FROM mart_concentration UNION ALL
SELECT 'mart_amb_cfem_uf_substance_year', count(*) FROM mart_amb_cfem_uf_substance_year;

-- name: chk_amb_value_reconciliation
-- staging total minus the value removed by the collapse rule must equal the fact total
SELECT (SELECT round(sum(sale_value_brl), 2) FROM stg_amb_beneficiada) AS staging_brl,
       (SELECT round(sum(sale_value_brl), 2) FROM fct_amb_beneficiada) AS fact_brl,
       (SELECT round(sum(sale_value_brl), 2) FROM mart_amb_uf_year)    AS mart_uf_brl,
       (SELECT round(sum(sale_value_brl), 2) FROM mart_amb_substance_year) AS mart_substance_brl,
       (SELECT max(n_units) FROM fct_amb_beneficiada) AS max_units_per_key;

-- name: chk_cfem_value_reconciliation
SELECT (SELECT round(sum(cfem_brl), 2) FROM stg_cfem)         AS staging_brl,
       (SELECT round(sum(cfem_brl), 2) FROM fct_cfem_monthly) AS fact_brl,
       (SELECT round(sum(cfem_brl), 2) FROM v_cfem_usable)    AS usable_brl,
       (SELECT round(sum(cfem_brl), 2) FROM mart_cfem_uf_year) AS mart_uf_brl,
       (SELECT round(sum(cfem_brl), 2) FROM mart_cfem_monthly) AS mart_monthly_brl,
       (SELECT round(sum(cfem_brl), 2) FROM mart_cfem_holder_substance_year) AS mart_holder_brl;

-- name: chk_group_label_consistency
-- a CFEM name mapped to an AMB substance must carry the same group label as that AMB substance
SELECT m.cfem_substance, m.substance_group AS map_group, a.substance_group AS amb_group
FROM seed_substance_map m JOIN seed_amb_substance a USING (amb_substance)
WHERE m.substance_group <> a.substance_group;

-- name: chk_national_headline
SELECT * FROM mart_amb_national_year ORDER BY base_year;

-- name: chk_cfem_national_by_year
SELECT year, any_value(year_status) AS status, round(sum(cfem_brl) / 1e9, 3) AS cfem_bn
FROM mart_cfem_uf_year GROUP BY year ORDER BY year;

-- name: chk_concentration_sample
SELECT * FROM mart_concentration
WHERE year IN (2010, 2025) AND (scope IN ('All substances', 'Brazil', 'Iron ore', 'Gold', 'Copper'))
ORDER BY concentration_type, scope, year;

-- name: chk_integration_match
SELECT match_status, count(*) AS rows, round(sum(amb_sale_value_brl) / 1e9, 2) AS amb_bn, round(sum(cfem_brl) / 1e9, 2) AS cfem_bn
FROM mart_amb_cfem_uf_substance_year GROUP BY 1;
