-- Phase 6: which months carry systematic identical repeats?

-- name: q19_repeat_share_by_month
SELECT period_month, sum(n_lines) AS lines,
       round(100 * sum((coalesce(cfem_brl_identical_repeats_kept, 0) + coalesce(cfem_brl_excluded_duplicates, 0))) / sum(cfem_brl_gross), 2) AS repeat_value_pct,
       round(sum((coalesce(cfem_brl_identical_repeats_kept, 0) + coalesce(cfem_brl_excluded_duplicates, 0))) / 1e6, 1) AS repeat_mn
FROM fct_cfem_monthly GROUP BY 1
HAVING 100 * sum((coalesce(cfem_brl_identical_repeats_kept, 0) + coalesce(cfem_brl_excluded_duplicates, 0))) / sum(cfem_brl_gross) >= 0.5 OR period_month = DATE '2024-02-01'
ORDER BY repeat_value_pct DESC LIMIT 15;

-- name: q20_feb2024_line_multiplicity
-- In Feb 2024, what share of distinct lines appears exactly twice?
WITH g AS (
  SELECT count(*) AS copies FROM stg_cfem WHERE period_month = DATE '2024-02-01'
  GROUP BY year, month, mining_process, holder_id_raw, cfem_substance, uf, ibge_municipality_code, municipality,
           quantity_sold, quantity_unit, cfem_brl, slip_created_at
)
SELECT copies, count(*) AS distinct_lines FROM g GROUP BY 1 ORDER BY 1;

-- name: q21_repeat_share_distribution
SELECT quantile_cont(p, 0.5) AS median_pct, quantile_cont(p, 0.95) AS p95_pct, max(p) AS max_pct,
       count(*) FILTER (p > 5) AS months_over_5pct
FROM (SELECT 100 * sum((coalesce(cfem_brl_identical_repeats_kept, 0) + coalesce(cfem_brl_excluded_duplicates, 0))) / sum(cfem_brl_gross) AS p FROM fct_cfem_monthly GROUP BY period_month);
