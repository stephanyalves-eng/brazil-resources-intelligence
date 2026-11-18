-- =====================================================================================
-- Phase 6 - Analytical queries. Each answers one business question (Q#) and feeds
-- docs/ANALYSIS_FINDINGS.md. All values are nominal R$. AMB = value of beneficiated sales;
-- CFEM = royalty collected (not revenue).
-- =====================================================================================

-- name: q01_national_value_trend
-- Q1. How did the value of beneficiated mineral sales evolve, and how volatile was it?
WITH y AS (SELECT base_year, sale_value_brl FROM mart_amb_national_year)
SELECT base_year, round(sale_value_brl / 1e9, 2) AS value_bn,
       round(100 * (sale_value_brl / lag(sale_value_brl) OVER (ORDER BY base_year) - 1), 1) AS yoy_pct,
       round(100 * (power(sale_value_brl / first_value(sale_value_brl) OVER (ORDER BY base_year),
                          1.0 / NULLIF(base_year - 2010, 0)) - 1), 1) AS cagr_since_2010_pct,
       sale_value_brl = max(sale_value_brl) OVER () AS is_peak
FROM y ORDER BY base_year;

-- name: q02_commodity_mix
-- Q2. How dependent is the sector on iron ore, and is the mix diversifying?
SELECT base_year,
       round(100 * max(share_of_national) FILTER (substance_group = 'Iron ore'), 1) AS iron_share_pct,
       round(100 * max(cumulative_share) FILTER (rank_in_year = 3), 1)            AS top3_share_pct,
       round(100 * max(cumulative_share) FILTER (rank_in_year = 5), 1)            AS top5_share_pct,
       string_agg(substance_group, ' > ' ORDER BY rank_in_year) FILTER (rank_in_year <= 5) AS top5
FROM mart_amb_substance_year GROUP BY base_year ORDER BY base_year;

-- name: q03_substance_growth_2015_2025
-- Q3. Which commodities grew fastest in value over the last decade (min R$ 1 bn in 2025)?
WITH a AS (
  SELECT substance_group,
         max(sale_value_brl) FILTER (base_year = 2015) AS v2015,
         max(sale_value_brl) FILTER (base_year = 2025) AS v2025
  FROM mart_amb_substance_year GROUP BY 1
)
SELECT substance_group, round(v2015 / 1e9, 2) AS bn_2015, round(v2025 / 1e9, 2) AS bn_2025,
       round(100 * (power(v2025 / v2015, 0.1) - 1), 1) AS cagr_pct,
       round(v2025 / v2015, 1) AS multiple
FROM a WHERE v2025 >= 1e9 AND v2015 > 0 ORDER BY cagr_pct DESC;

-- name: q04_price_volume_iron_gold_copper
-- Q4. Was value growth driven by volume or by unit value? (single unit per substance, so valid)
-- Log decomposition: ln(V1/V0) = ln(Q1/Q0) + ln(P1/P0), P = value / quantity sold.
WITH b AS (
  SELECT base_year, substance_group, unit,
         sum(sale_value_brl) AS v, sum(sale_qty) AS q
  FROM fct_amb_beneficiada
  WHERE substance_group IN ('Iron ore', 'Gold', 'Copper', 'Bauxite (aluminium)', 'Niobium')
  GROUP BY ALL
),
c AS (
  SELECT *, v / NULLIF(q, 0) AS unit_value,
         lag(v) OVER w AS v0, lag(q) OVER w AS q0, lag(base_year) OVER w AS y0
  FROM b WINDOW w AS (PARTITION BY substance_group ORDER BY base_year)
)
SELECT substance_group, base_year, unit, round(q / 1e6, 3) AS qty_sold_mn_units, round(unit_value, 2) AS brl_per_unit,
       round(100 * (v / v0 - 1), 1) AS value_yoy_pct,
       round(100 * ln(q / q0), 1)   AS volume_effect_logpts,
       round(100 * ln((v / q) / (v0 / q0)), 1) AS unit_value_effect_logpts
FROM c WHERE y0 = base_year - 1 AND q > 0 AND q0 > 0 AND v > 0 AND v0 > 0
ORDER BY substance_group, base_year;

-- name: q05_state_ranking_shift
-- Q5. Which states gained or lost share between 2010 and 2025?
WITH s AS (
  SELECT uf, uf_name,
         max(share_of_national) FILTER (base_year = 2010) AS s2010,
         max(share_of_national) FILTER (base_year = 2025) AS s2025,
         max(rank_in_year) FILTER (base_year = 2010) AS r2010,
         max(rank_in_year) FILTER (base_year = 2025) AS r2025
  FROM mart_amb_uf_year GROUP BY ALL
)
SELECT uf, uf_name, round(100 * s2010, 2) AS share_2010_pct, round(100 * s2025, 2) AS share_2025_pct,
       round(100 * (s2025 - s2010), 2) AS change_pp, r2010, r2025
FROM s ORDER BY s2025 DESC NULLS LAST LIMIT 12;

-- name: q06_mg_vs_pa
-- Q6. The two mining poles over time.
SELECT base_year,
       round(100 * max(share_of_national) FILTER (uf = 'MG'), 1) AS mg_share_pct,
       round(100 * max(share_of_national) FILTER (uf = 'PA'), 1) AS pa_share_pct,
       round(100 * sum(share_of_national) FILTER (uf IN ('MG', 'PA')), 1) AS mg_pa_combined_pct
FROM mart_amb_uf_year GROUP BY base_year ORDER BY base_year;

-- name: q07_concentration_trends
-- Q7. Is the sector becoming more or less concentrated (geography, commodity mix, companies)?
SELECT year, concentration_type, scope, n_participants, hhi, cr1_pct, cr4_pct, top_participant, hhi_band
FROM mart_concentration
WHERE (scope IN ('All substances', 'Brazil'))
   OR (concentration_type LIKE 'business%' AND scope IN ('Iron ore', 'Gold', 'Copper', 'Bauxite (aluminium)', 'Niobium', 'Limestone'))
ORDER BY concentration_type, scope, year;

-- name: q08_business_concentration_summary
-- Q8. Company concentration within commodities, first vs last complete year (CFEM-based proxy).
WITH c AS (
  SELECT scope, year, n_participants, hhi, cr1_pct, cr4_pct, top_participant
  FROM mart_concentration WHERE concentration_type LIKE 'business%'
),
s AS (
  SELECT scope,
         max(hhi) FILTER (year = 2010) AS hhi_2010, max(hhi) FILTER (year = 2025) AS hhi_2025,
         max(n_participants) FILTER (year = 2010) AS n_2010, max(n_participants) FILTER (year = 2025) AS n_2025,
         max(cr4_pct) FILTER (year = 2025) AS cr4_2025, max(top_participant) FILTER (year = 2025) AS top_2025,
         max(cr1_pct) FILTER (year = 2025) AS cr1_2025
  FROM c GROUP BY scope
)
SELECT s.*, round(g.cfem_brl / 1e6, 1) AS cfem_2025_mn
FROM s JOIN mart_cfem_substance_year g ON g.substance_group = s.scope AND g.year = 2025
WHERE g.cfem_brl >= 50e6 ORDER BY g.cfem_brl DESC;

-- name: q09_top_companies_iron_2025
-- Q9. Who leads iron ore (CNPJ roots), and how cumulative is it?
SELECT rank_in_substance AS rk, holder_key AS cnpj_root, round(cfem_brl / 1e6, 1) AS cfem_mn,
       round(100 * share_in_substance, 2) AS share_pct, round(100 * cumulative_share, 2) AS cum_pct
FROM mart_cfem_holder_substance_year
WHERE year = 2025 AND substance_group = 'Iron ore' AND rank_in_substance <= 10 ORDER BY rk;

-- name: q10_top_companies_all_2025
-- Q10. Largest CFEM payers overall in 2025 (all substances), with their main commodity.
WITH h AS (
  SELECT holder_key, sum(cfem_brl) AS cfem, arg_max(substance_group, cfem_brl) AS main_group
  FROM mart_cfem_holder_substance_year WHERE year = 2025 AND holder_type = 'PJ' GROUP BY 1
)
SELECT row_number() OVER (ORDER BY cfem DESC) AS rk, holder_key AS cnpj_root, main_group,
       round(cfem / 1e6, 1) AS cfem_mn, round(100 * cfem / sum(cfem) OVER (), 2) AS share_pct,
       round(100 * sum(cfem) OVER (ORDER BY cfem DESC ROWS UNBOUNDED PRECEDING) / sum(cfem) OVER (), 2) AS cum_pct
FROM h QUALIFY rk <= 10 ORDER BY rk;

-- name: q11_municipal_concentration_2025
-- Q11. How concentrated is CFEM collection across municipalities?
WITH m AS (
  SELECT municipality_name, uf, main_substance_group, cfem_brl, rank_in_year
  FROM mart_cfem_municipality_year WHERE year = 2025
)
SELECT rank_in_year AS rk, municipality_name, uf, main_substance_group, round(cfem_brl / 1e6, 1) AS cfem_mn,
       round(100 * cfem_brl / sum(cfem_brl) OVER (), 2) AS share_pct,
       round(100 * sum(cfem_brl) OVER (ORDER BY cfem_brl DESC ROWS UNBOUNDED PRECEDING) / sum(cfem_brl) OVER (), 2) AS cum_pct,
       (SELECT count(*) FROM m) AS n_municipalities_with_cfem
FROM m QUALIFY rk <= 10 ORDER BY rk;

-- name: q12_cfem_to_sales_ratio
-- Q12. CFEM collected per R$ of AMB beneficiated sales (indicative effective rate), national and iron ore.
-- Bases differ (CFEM base = gross revenue per Lei 13.540/2017; timing = cash); read as an indicator only.
WITH n AS (
  SELECT year, sum(amb_sale_value_brl) AS amb, sum(cfem_brl) AS cfem
  FROM mart_amb_cfem_uf_substance_year GROUP BY year
),
i AS (
  SELECT year, sum(amb_sale_value_brl) AS amb, sum(cfem_brl) AS cfem
  FROM mart_amb_cfem_uf_substance_year WHERE substance_group = 'Iron ore' GROUP BY year
)
SELECT n.year, round(100 * n.cfem / n.amb, 2) AS all_mapped_ratio_pct, round(100 * i.cfem / i.amb, 2) AS iron_ratio_pct
FROM n JOIN i USING (year) ORDER BY year;

-- name: q13_cfem_identical_repeat_sensitivity
-- Q13. Sensitivity: gross (all lines), net (rule T13, used in marts), and net minus every remaining repeat.
SELECT year, round(sum(cfem_brl_gross) / 1e9, 3) AS gross_bn, round(sum(cfem_brl) / 1e9, 3) AS net_bn,
       round((sum(cfem_brl) - coalesce(sum(cfem_brl_identical_repeats_kept), 0)) / 1e9, 3) AS net_without_any_repeat_bn,
       round(100 * coalesce(sum(cfem_brl_identical_repeats_kept), 0) / sum(cfem_brl), 3) AS kept_repeats_pct_of_net
FROM v_cfem_usable GROUP BY year ORDER BY year;

-- name: q14_value_volatility_by_substance
-- Q14. Which commodities have the most volatile value (std of YoY, 2011-2025, min R$ 1 bn avg)?
SELECT substance_group, count(value_yoy) AS n_years, round(100 * avg(value_yoy), 1) AS mean_yoy_pct,
       round(100 * stddev_samp(value_yoy), 1) AS sd_yoy_pct, round(avg(sale_value_brl) / 1e9, 2) AS avg_value_bn
FROM mart_amb_substance_year GROUP BY 1 HAVING avg(sale_value_brl) >= 1e9 ORDER BY sd_yoy_pct DESC;
