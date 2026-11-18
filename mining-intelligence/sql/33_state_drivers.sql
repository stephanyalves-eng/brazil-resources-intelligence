-- Phase 6: what drives the share gains of ES and MT (and BA)?

-- name: q22_state_substance_drivers
WITH s AS (
  SELECT uf, substance_group,
         sum(sale_value_brl) FILTER (base_year = 2010) AS v2010,
         sum(sale_value_brl) FILTER (base_year = 2025) AS v2025
  FROM mart_amb_uf_substance_year WHERE uf IN ('ES', 'MT', 'BA')
  GROUP BY uf, substance_group
)
SELECT uf, substance_group, round(v2010 / 1e9, 2) AS bn_2010, round(v2025 / 1e9, 2) AS bn_2025,
       round(100 * v2025 / sum(v2025) OVER (PARTITION BY uf), 1) AS pct_of_uf_2025
FROM s QUALIFY row_number() OVER (PARTITION BY uf ORDER BY v2025 DESC NULLS LAST) <= 3
ORDER BY uf, v2025 DESC;

-- name: q23_es_iron_by_year
SELECT base_year, round(sale_value_brl / 1e9, 2) AS bn, production_qty, unit FROM mart_amb_uf_substance_year WHERE uf = 'ES' AND substance_group = 'Iron ore' ORDER BY 1;


-- name: q24_iron_volume_by_year
SELECT base_year, round(sum(sale_qty) / 1e6, 1) AS sale_mt, round(sum(production_qty) / 1e6, 1) AS prod_mt FROM fct_amb_beneficiada WHERE substance_group = 'Iron ore' GROUP BY 1 ORDER BY 1;

