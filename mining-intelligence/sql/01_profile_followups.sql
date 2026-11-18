-- Phase 2 follow-up checks (read-only).

-- name: amb_benef_uf_coverage
SELECT count(DISTINCT "UF") AS n_ufs, string_agg(DISTINCT "UF", ',' ORDER BY "UF") AS ufs
FROM read_csv('data/raw/AMB/Producao_Beneficiada.csv', delim = ',', quote = '"', header = true, encoding = 'latin-1', all_varchar = true);

-- name: cfem_total
SELECT round(sum(TRY_CAST(replace("ValorRecolhido", ',', '.') AS DECIMAL(18,2))) / 1e9, 3) AS cfem_total_brl_bn
FROM read_csv('data/raw/CFEM/CFEM_Arrecadacao.csv', delim = ',', quote = '"', header = true, encoding = 'latin-1', all_varchar = true);
