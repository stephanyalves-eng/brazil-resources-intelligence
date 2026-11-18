-- Post-staging sanity checks (read-only). Formal assertions live in tests/ (Phase 7).

-- name: chk_cfem_totals
SELECT count(*) AS n, sum(is_identical_repeat::INT) AS repeats, round(sum(cfem_brl) / 1e9, 3) AS bn,
       count(*) FILTER (cnpj IS NULL AND holder_type = 'PJ') AS pj_without_valid_cnpj,
       count(*) FILTER (ibge_municipality_code IS NULL) AS no_ibge_code
FROM stg_cfem;

-- name: chk_cfem_mapping_coverage
SELECT mapping_basis, count(*) AS rows, round(sum(cfem_brl) / 1e9, 3) AS bn,
       round(100 * sum(cfem_brl) / sum(sum(cfem_brl)) OVER (), 3) AS pct_value
FROM stg_cfem GROUP BY 1 ORDER BY 3 DESC;

-- name: chk_cfem_month_status
SELECT month_status, count(*) AS months, min(period_month) AS first, max(period_month) AS last
FROM stg_cfem_month_status GROUP BY 1 ORDER BY 3;

-- name: chk_cfem_recent_months
SELECT * FROM stg_cfem_month_status WHERE period_month >= DATE '2025-11-01' ORDER BY 1;

-- name: chk_amb_parse
SELECT 'beneficiada' AS t, count(*) FILTER (production_qty IS NULL) AS qty_null,
       count(*) FILTER (sale_value_brl IS NULL) AS value_null, count(*) AS n FROM stg_amb_beneficiada
UNION ALL
SELECT 'bruta', count(*) FILTER (rom_qty_t IS NULL), count(*) FILTER (sale_value_brl IS NULL), count(*) FROM stg_amb_bruta;

-- name: chk_amb_substances_missing_from_seed
SELECT amb_substance FROM (SELECT DISTINCT amb_substance FROM stg_amb_beneficiada
                           UNION SELECT DISTINCT amb_substance FROM stg_amb_bruta)
ANTI JOIN seed_amb_substance USING (amb_substance);

-- name: chk_map_targets_missing_from_seed
SELECT DISTINCT m.amb_substance FROM seed_substance_map m
ANTI JOIN seed_amb_substance s USING (amb_substance) WHERE m.amb_substance IS NOT NULL;

-- name: chk_map_names_not_in_cfem
SELECT cfem_substance FROM seed_substance_map ANTI JOIN (SELECT DISTINCT cfem_substance FROM stg_cfem) USING (cfem_substance);

-- name: chk_cfem_uf_not_in_seed
SELECT DISTINCT uf FROM stg_cfem ANTI JOIN seed_uf USING (uf) WHERE uf IS NOT NULL;
