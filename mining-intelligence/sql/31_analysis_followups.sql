-- Phase 6 follow-ups.

-- name: q15_2024_repeat_cluster
-- Where do the 2024 identical repeats come from?
SELECT period_month, holder_key, substance_group, uf,
       round(sum(cfem_brl_excluded_duplicates) / 1e6, 2) AS repeat_mn, round(sum(cfem_brl_gross) / 1e6, 2) AS total_mn,
       sum(n_lines) AS lines
FROM fct_cfem_monthly WHERE year = 2024 AND cfem_brl_excluded_duplicates > 0
GROUP BY ALL ORDER BY repeat_mn DESC LIMIT 10;

-- name: q16_2024_repeat_lines_detail
SELECT period_month, mining_process, cnpj, cfem_substance, municipality, quantity_sold, quantity_unit, cfem_brl,
       slip_created_at, count(*) AS copies
FROM stg_cfem
WHERE year = 2024 AND holder_key = (
  SELECT holder_key FROM fct_cfem_monthly WHERE year = 2024
  GROUP BY 1 ORDER BY sum(coalesce(cfem_brl_excluded_duplicates, 0)) DESC LIMIT 1)
GROUP BY ALL HAVING count(*) > 1 ORDER BY cfem_brl DESC LIMIT 15;

-- name: q17_holder_monthly_2024
-- Same holder, monthly totals 2023-2025: does 2024 stand out?
WITH h AS (
  SELECT holder_key FROM fct_cfem_monthly WHERE year = 2024
  GROUP BY 1 ORDER BY sum(coalesce(cfem_brl_excluded_duplicates, 0)) DESC LIMIT 1)
SELECT period_month, round(sum(cfem_brl_gross) / 1e6, 1) AS total_mn,
       round(sum(coalesce(cfem_brl_excluded_duplicates, 0)) / 1e6, 1) AS repeat_mn
FROM fct_cfem_monthly WHERE holder_key IN (SELECT holder_key FROM h) AND year BETWEEN 2023 AND 2025
GROUP BY 1 ORDER BY 1;

-- name: q18_top_roots_main_cnpj
-- Most frequent full CNPJ per top CNPJ root (used only to look up the registered company name).
WITH top AS (
  SELECT holder_key FROM mart_cfem_holder_substance_year WHERE year = 2025 AND holder_type = 'PJ'
  GROUP BY 1 ORDER BY sum(cfem_brl) DESC LIMIT 12
)
SELECT holder_key AS cnpj_root, arg_max(cnpj, n) AS main_cnpj
FROM (SELECT holder_key, cnpj, count(*) AS n FROM stg_cfem
      WHERE holder_key IN (SELECT holder_key FROM top) AND year = 2025 GROUP BY ALL)
GROUP BY 1;
