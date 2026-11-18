-- Phase 5 helper: inventory of CFEM substances by value (input for the manual seed substance_map.csv).

-- name: cfem_substance_inventory
WITH s AS (
  SELECT "Substância" AS cfem_substance, count(*) AS rows,
         sum(TRY_CAST(replace("ValorRecolhido", ',', '.') AS DECIMAL(18,2))) AS brl
  FROM read_csv('data/raw/CFEM/CFEM_Arrecadacao.csv', delim = ',', quote = '"', header = true,
                encoding = 'latin-1', all_varchar = true)
  GROUP BY 1)
SELECT cfem_substance, rows, round(brl / 1e6, 2) AS brl_mn,
       round(100 * sum(brl) OVER (ORDER BY brl DESC ROWS UNBOUNDED PRECEDING) / sum(brl) OVER (), 3) AS cum_pct
FROM s ORDER BY brl DESC;
