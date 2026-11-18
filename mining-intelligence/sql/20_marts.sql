-- =====================================================================================
-- MARTS layer: dimensions, facts and analytical marts. Grain is stated above each table.
-- Rules: quantities are never summed across substances/units; every join happens between
-- tables already aggregated to the same grain (no fan-out); YoY uses the *calendar* previous
-- year (a gap year gives NULL, not the last available year).
-- =====================================================================================

-- ---------- Dimensions ----------
-- Grain: one UF
CREATE OR REPLACE TABLE dim_uf AS
SELECT uf, uf_name, region, CAST(ibge_uf_code AS INTEGER) AS ibge_uf_code FROM seed_uf;

-- Grain: one substance group (the analytical commodity unit shared by AMB and CFEM)
CREATE OR REPLACE TABLE dim_substance_group AS
WITH g AS (
  SELECT substance_group, substance_class_en FROM seed_amb_substance
  UNION
  SELECT substance_group, NULL FROM seed_substance_map
  UNION
  SELECT 'Other (unmapped)', NULL
)
SELECT substance_group,
       coalesce(max(substance_class_en), 'Unclassified') AS substance_class_en,
       substance_group IN (SELECT substance_group FROM seed_amb_substance) AS has_amb_equivalent
FROM g GROUP BY substance_group;

-- ---------- Facts (AMB) ----------
-- Grain: base_year x UF x AMB substance.
-- Records repeating the same quantities and values inside one key (the Columbita-Tantalita AM case,
-- one row per contained oxide) are collapsed with DISTINCT before summing; different records are summed.
CREATE OR REPLACE TABLE fct_amb_beneficiada AS
WITH dedup AS (
  SELECT DISTINCT base_year, uf, amb_substance, production_qty, production_unit, sale_qty,
                  sale_value_brl, plant_use_value_brl, transfer_value_brl
  FROM stg_amb_beneficiada
),
src_counts AS (
  SELECT base_year, uf, amb_substance, count(*) AS n_source_records FROM stg_amb_beneficiada GROUP BY ALL
)
SELECT d.base_year, d.uf, d.amb_substance, s.substance_group, s.substance_class_en,
       any_value(d.production_unit)            AS unit,
       count(DISTINCT d.production_unit)       AS n_units,      -- must be 1 (tested)
       sum(d.production_qty)                   AS production_qty,
       sum(d.sale_qty)                         AS sale_qty,
       sum(d.sale_value_brl)                   AS sale_value_brl,
       sum(d.plant_use_value_brl)              AS plant_use_value_brl,
       sum(d.transfer_value_brl)               AS transfer_value_brl,
       count(*)                                AS n_records_after_collapse,
       any_value(c.n_source_records)           AS n_source_records
FROM dedup d
JOIN seed_amb_substance s USING (amb_substance)
JOIN src_counts c USING (base_year, uf, amb_substance)
GROUP BY d.base_year, d.uf, d.amb_substance, s.substance_group, s.substance_class_en;

-- Grain: base_year x UF x AMB substance (run-of-mine, always tonnes)
CREATE OR REPLACE TABLE fct_amb_bruta AS
WITH dedup AS (
  SELECT DISTINCT base_year, uf, amb_substance, rom_qty_t, sale_qty_t, sale_value_brl FROM stg_amb_bruta
)
SELECT d.base_year, d.uf, d.amb_substance, s.substance_group,
       sum(rom_qty_t) AS rom_qty_t, sum(sale_qty_t) AS sale_qty_t, sum(sale_value_brl) AS sale_value_brl,
       count(*) AS n_records_after_collapse
FROM dedup d JOIN seed_amb_substance s USING (amb_substance)
GROUP BY ALL;

-- ---------- Facts (CFEM) ----------
-- Grain: month x UF x IBGE municipality x substance group x holder key. Excludes nothing; carries month status.
CREATE OR REPLACE TABLE fct_cfem_monthly AS
SELECT c.period_month, year(c.period_month) AS year, c.uf, c.ibge_municipality_code, c.substance_group,
       c.holder_type, c.holder_key, s.month_status,
       sum(c.cfem_brl)                                         AS cfem_brl,
       sum(c.cfem_brl) FILTER (c.is_identical_repeat)          AS cfem_brl_identical_repeats,
       count(*)                                                AS n_lines
FROM stg_cfem c
JOIN stg_cfem_month_status s USING (period_month)
GROUP BY ALL;

-- Analysis-ready CFEM view: drops 'partial_history' (2002-03) and 'incomplete' months (Jul-Nov 2026).
CREATE OR REPLACE VIEW v_cfem_usable AS
SELECT * FROM fct_cfem_monthly WHERE month_status IN ('complete', 'provisional');

-- Year label used by every annual CFEM mart.
CREATE OR REPLACE MACRO cfem_year_status(y) AS CASE WHEN y = 2026 THEN '2026 YTD Jan-Jun (provisional)' ELSE 'complete' END;

-- =====================================================================================
-- Analytical marts
-- =====================================================================================

-- Grain: base_year x UF x substance group. Value KPIs; quantity only when one unit applies.
CREATE OR REPLACE TABLE mart_amb_uf_substance_year AS
WITH base AS (
  SELECT base_year, uf, substance_group, substance_class_en,
         sum(sale_value_brl) AS sale_value_brl,
         CASE WHEN count(DISTINCT unit) = 1 THEN sum(production_qty) END AS production_qty,
         CASE WHEN count(DISTINCT unit) = 1 THEN any_value(unit) END     AS unit
  FROM fct_amb_beneficiada GROUP BY ALL
),
lagged AS (
  SELECT *,
         lag(base_year)      OVER w AS prev_year,
         lag(sale_value_brl) OVER w AS prev_value,
         lag(production_qty) OVER w AS prev_qty
  FROM base WINDOW w AS (PARTITION BY uf, substance_group ORDER BY base_year)
)
SELECT base_year, uf, substance_group, substance_class_en, sale_value_brl, production_qty, unit,
       CASE WHEN prev_year = base_year - 1 AND prev_value > 0
            THEN sale_value_brl / prev_value - 1 END                                   AS value_yoy,
       CASE WHEN prev_year = base_year - 1 AND prev_qty > 0
            THEN production_qty / prev_qty - 1 END                                     AS qty_yoy,
       sale_value_brl / NULLIF(sum(sale_value_brl) OVER (PARTITION BY base_year, substance_group), 0) AS uf_share_of_substance,
       sale_value_brl / NULLIF(sum(sale_value_brl) OVER (PARTITION BY base_year), 0)                  AS share_of_national
FROM lagged;

-- Grain: base_year x UF (all substances, value only - quantities are not additive across substances)
CREATE OR REPLACE TABLE mart_amb_uf_year AS
WITH base AS (
  SELECT base_year, uf, sum(sale_value_brl) AS sale_value_brl, count(DISTINCT substance_group) AS n_substance_groups
  FROM fct_amb_beneficiada GROUP BY ALL
),
ranked AS (
  SELECT *,
         sale_value_brl / sum(sale_value_brl) OVER (PARTITION BY base_year)        AS share_of_national,
         rank() OVER (PARTITION BY base_year ORDER BY sale_value_brl DESC)          AS rank_in_year,
         lag(base_year) OVER (PARTITION BY uf ORDER BY base_year)                   AS prev_year,
         lag(sale_value_brl) OVER (PARTITION BY uf ORDER BY base_year)              AS prev_value
  FROM base
)
SELECT r.base_year, r.uf, u.uf_name, u.region, r.sale_value_brl, r.n_substance_groups, r.share_of_national, r.rank_in_year,
       sum(r.share_of_national) OVER (PARTITION BY r.base_year ORDER BY r.rank_in_year, r.uf
                                      ROWS UNBOUNDED PRECEDING)                    AS cumulative_share,
       CASE WHEN r.prev_year = r.base_year - 1 AND r.prev_value > 0 THEN r.sale_value_brl / r.prev_value - 1 END AS value_yoy,
       r.rank_in_year - lag(r.rank_in_year) OVER (PARTITION BY r.uf ORDER BY r.base_year) AS rank_change
FROM ranked r JOIN dim_uf u USING (uf);

-- Grain: base_year x substance group (national)
CREATE OR REPLACE TABLE mart_amb_substance_year AS
WITH base AS (
  SELECT base_year, substance_group, substance_class_en,
         sum(sale_value_brl) AS sale_value_brl,
         CASE WHEN count(DISTINCT unit) = 1 THEN sum(production_qty) END AS production_qty,
         CASE WHEN count(DISTINCT unit) = 1 THEN any_value(unit) END     AS unit,
         count(DISTINCT uf) AS n_producing_ufs
  FROM fct_amb_beneficiada GROUP BY ALL
),
ranked AS (
  SELECT *,
         sale_value_brl / sum(sale_value_brl) OVER (PARTITION BY base_year)        AS share_of_national,
         rank() OVER (PARTITION BY base_year ORDER BY sale_value_brl DESC)          AS rank_in_year,
         lag(base_year) OVER (PARTITION BY substance_group ORDER BY base_year)      AS prev_year,
         lag(sale_value_brl) OVER (PARTITION BY substance_group ORDER BY base_year) AS prev_value,
         lag(production_qty) OVER (PARTITION BY substance_group ORDER BY base_year) AS prev_qty
  FROM base
)
SELECT base_year, substance_group, substance_class_en, sale_value_brl, production_qty, unit, n_producing_ufs,
       share_of_national, rank_in_year,
       sum(share_of_national) OVER (PARTITION BY base_year ORDER BY rank_in_year, substance_group
                                    ROWS UNBOUNDED PRECEDING) AS cumulative_share,
       CASE WHEN prev_year = base_year - 1 AND prev_value > 0 THEN sale_value_brl / prev_value - 1 END AS value_yoy,
       CASE WHEN prev_year = base_year - 1 AND prev_qty > 0 THEN production_qty / prev_qty - 1 END     AS qty_yoy
FROM ranked;

-- Grain: base_year (national headline, value of beneficiated sales)
CREATE OR REPLACE TABLE mart_amb_national_year AS
SELECT base_year, sum(sale_value_brl) AS sale_value_brl,
       sum(sale_value_brl) / lag(sum(sale_value_brl)) OVER (ORDER BY base_year) - 1 AS value_yoy,
       count(DISTINCT uf) AS n_ufs, count(DISTINCT substance_group) AS n_substance_groups
FROM fct_amb_beneficiada GROUP BY base_year;

-- ---------- CFEM marts ----------
-- Grain: year x UF (usable months only)
CREATE OR REPLACE TABLE mart_cfem_uf_year AS
WITH base AS (
  SELECT year, coalesce(uf, 'N/A') AS uf, sum(cfem_brl) AS cfem_brl,
         count(DISTINCT period_month) AS n_months
  FROM v_cfem_usable GROUP BY ALL
)
SELECT b.year, cfem_year_status(b.year) AS year_status, b.uf, u.uf_name, u.region, b.cfem_brl, b.n_months,
       b.cfem_brl / sum(b.cfem_brl) OVER (PARTITION BY b.year)                     AS share_of_national,
       rank() OVER (PARTITION BY b.year ORDER BY b.cfem_brl DESC)                   AS rank_in_year,
       CASE WHEN lag(b.year) OVER w = b.year - 1 AND lag(b.cfem_brl) OVER w > 0 AND b.year < 2026
            THEN b.cfem_brl / lag(b.cfem_brl) OVER w - 1 END                       AS cfem_yoy
FROM base b LEFT JOIN dim_uf u USING (uf)
WINDOW w AS (PARTITION BY b.uf ORDER BY b.year);

-- Grain: year x substance group (national)
CREATE OR REPLACE TABLE mart_cfem_substance_year AS
SELECT year, cfem_year_status(year) AS year_status, substance_group, sum(cfem_brl) AS cfem_brl,
       sum(cfem_brl) / sum(sum(cfem_brl)) OVER (PARTITION BY year) AS share_of_national,
       rank() OVER (PARTITION BY year ORDER BY sum(cfem_brl) DESC) AS rank_in_year
FROM v_cfem_usable GROUP BY year, substance_group;

-- Grain: year x IBGE municipality (map layer). Municipality name = most frequent spelling.
CREATE OR REPLACE TABLE mart_cfem_municipality_year AS
WITH names AS (
  SELECT ibge_municipality_code, arg_max(municipality, n) AS municipality_name, arg_max(uf, n) AS uf
  FROM (SELECT ibge_municipality_code, municipality, uf, count(*) AS n FROM stg_cfem
        WHERE ibge_municipality_code IS NOT NULL GROUP BY ALL)
  GROUP BY 1
)
SELECT f.year, cfem_year_status(f.year) AS year_status, f.ibge_municipality_code, n.municipality_name, n.uf,
       sum(f.cfem_brl) AS cfem_brl,
       arg_max(f.substance_group, f.cfem_brl) AS main_substance_group,   -- the group with the largest line value
       rank() OVER (PARTITION BY f.year ORDER BY sum(f.cfem_brl) DESC) AS rank_in_year
FROM v_cfem_usable f JOIN names n USING (ibge_municipality_code)
GROUP BY f.year, f.ibge_municipality_code, n.municipality_name, n.uf;

-- Grain: month x substance group, on a dense month spine (missing month = 0 collected, by construction of CFEM:
-- no slip means nothing was collected). Rolling 12M and same-month-last-year comparison.
CREATE OR REPLACE TABLE mart_cfem_monthly AS
WITH spine AS (
  SELECT m.period_month, m.month_status, g.substance_group
  FROM stg_cfem_month_status m CROSS JOIN (SELECT DISTINCT substance_group FROM fct_cfem_monthly) g
  WHERE m.month_status IN ('complete', 'provisional')
),
agg AS (SELECT period_month, substance_group, sum(cfem_brl) AS cfem_brl FROM v_cfem_usable GROUP BY ALL),
dense AS (
  SELECT s.period_month, s.month_status, s.substance_group, coalesce(a.cfem_brl, 0) AS cfem_brl
  FROM spine s LEFT JOIN agg a USING (period_month, substance_group)
)
SELECT *,
       CASE WHEN count(*) OVER w12 = 12 THEN sum(cfem_brl) OVER w12 END            AS cfem_brl_rolling_12m,
       lag(cfem_brl, 12) OVER (PARTITION BY substance_group ORDER BY period_month)  AS cfem_brl_same_month_ly
FROM dense
WINDOW w12 AS (PARTITION BY substance_group ORDER BY period_month ROWS BETWEEN 11 PRECEDING AND CURRENT ROW);

-- Grain: year x substance group x holder key (company = CNPJ root). Shares within the substance group.
CREATE OR REPLACE TABLE mart_cfem_holder_substance_year AS
WITH base AS (
  SELECT year, substance_group, holder_key, holder_type, sum(cfem_brl) AS cfem_brl
  FROM v_cfem_usable GROUP BY ALL
)
SELECT year, cfem_year_status(year) AS year_status, substance_group, holder_key, holder_type, cfem_brl,
       cfem_brl / sum(cfem_brl) OVER (PARTITION BY year, substance_group)          AS share_in_substance,
       row_number() OVER (PARTITION BY year, substance_group ORDER BY cfem_brl DESC, holder_key) AS rank_in_substance,
       sum(cfem_brl) OVER (PARTITION BY year, substance_group ORDER BY cfem_brl DESC, holder_key ROWS UNBOUNDED PRECEDING)
         / sum(cfem_brl) OVER (PARTITION BY year, substance_group)                 AS cumulative_share
FROM base;

-- ---------- Concentration ----------
-- Grain: year x concentration_type x scope. HHI on 0-10,000 scale (sum of squared % shares).
-- geographic  : participants = UFs, measure = AMB beneficiated sales value (per substance group and all)
-- commodity   : participants = substance groups, measure = AMB value (national portfolio concentration)
-- business    : participants = companies (CNPJ root, PJ only), measure = CFEM collected, within a substance group
CREATE OR REPLACE TABLE mart_concentration AS
WITH geo AS (
  SELECT base_year AS year, 'geographic (UF, AMB value)' AS concentration_type, substance_group AS scope,
         uf AS participant, sum(sale_value_brl) AS v
  FROM fct_amb_beneficiada GROUP BY ALL
  UNION ALL
  SELECT base_year, 'geographic (UF, AMB value)', 'All substances', uf, sum(sale_value_brl)
  FROM fct_amb_beneficiada GROUP BY ALL
),
com AS (
  SELECT base_year, 'commodity mix (AMB value)', 'Brazil', substance_group, sum(sale_value_brl)
  FROM fct_amb_beneficiada GROUP BY ALL
),
biz AS (
  SELECT year, 'business (CNPJ root, CFEM)', substance_group, holder_key, sum(cfem_brl)
  FROM v_cfem_usable WHERE holder_type = 'PJ' AND year < 2026 GROUP BY ALL
),
u AS (SELECT * FROM geo UNION ALL SELECT * FROM com UNION ALL SELECT * FROM biz),
s AS (
  SELECT *, 100 * v / NULLIF(sum(v) OVER (PARTITION BY year, concentration_type, scope), 0) AS pct,
         row_number() OVER (PARTITION BY year, concentration_type, scope ORDER BY v DESC, participant) AS rk
  FROM u WHERE v > 0
)
SELECT year, concentration_type, scope,
       count(*)                                  AS n_participants,
       round(sum(pct * pct), 1)                  AS hhi,
       round(max(pct), 2)                        AS cr1_pct,
       round(sum(pct) FILTER (rk <= 4), 2)       AS cr4_pct,
       arg_max(participant, v)                   AS top_participant,
       sum(v)                                    AS total_value_brl,
       CASE WHEN sum(pct * pct) < 1500 THEN 'unconcentrated'
            WHEN sum(pct * pct) <= 2500 THEN 'moderately concentrated'
            ELSE 'highly concentrated' END       AS hhi_band          -- US DOJ/FTC 2010 thresholds, reference only
FROM s GROUP BY year, concentration_type, scope;

-- ---------- AMB x CFEM integration ----------
-- Grain: year x UF x substance group, 2010-2025, for groups that exist in AMB.
-- Both sides are pre-aggregated to this grain before the FULL JOIN, so rows cannot multiply.
CREATE OR REPLACE TABLE mart_amb_cfem_uf_substance_year AS
WITH amb AS (
  SELECT base_year AS year, uf, substance_group, sum(sale_value_brl) AS amb_sale_value_brl
  FROM fct_amb_beneficiada GROUP BY ALL
),
cfem AS (
  SELECT year, uf, substance_group, sum(cfem_brl) AS cfem_brl
  FROM v_cfem_usable
  WHERE year BETWEEN 2010 AND 2025 AND uf IS NOT NULL
    AND substance_group IN (SELECT substance_group FROM dim_substance_group WHERE has_amb_equivalent)
  GROUP BY ALL
)
SELECT coalesce(a.year, c.year) AS year, coalesce(a.uf, c.uf) AS uf, coalesce(a.substance_group, c.substance_group) AS substance_group,
       a.amb_sale_value_brl, c.cfem_brl,
       CASE WHEN a.amb_sale_value_brl > 0 THEN c.cfem_brl / a.amb_sale_value_brl END AS cfem_to_amb_sales_ratio,
       CASE WHEN a.year IS NULL THEN 'cfem_only' WHEN c.year IS NULL THEN 'amb_only' ELSE 'both' END AS match_status
FROM amb a FULL JOIN cfem c ON a.year = c.year AND a.uf = c.uf AND a.substance_group = c.substance_group;
