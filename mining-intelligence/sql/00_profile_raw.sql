-- Phase 2 - Profiling of the raw ANM files (read-only, nothing is persisted).
-- Layout verified 2026-11-18: CP-1252 (read as latin-1), ',' separator, decimal-comma numbers in quotes.
-- The official metadata says ';' - it is wrong; the delimiter is set explicitly here.

CREATE OR REPLACE TEMP VIEW raw_cfem AS
SELECT * FROM read_csv('data/raw/CFEM/CFEM_Arrecadacao.csv',
    delim = ',', quote = '"', header = true, encoding = 'latin-1', all_varchar = true);

CREATE OR REPLACE TEMP VIEW raw_benef AS
SELECT * FROM read_csv('data/raw/AMB/Producao_Beneficiada.csv',
    delim = ',', quote = '"', header = true, encoding = 'latin-1', all_varchar = true);

CREATE OR REPLACE TEMP VIEW raw_bruta AS
SELECT * FROM read_csv('data/raw/AMB/Producao_Bruta.csv',
    delim = ',', quote = '"', header = true, encoding = 'latin-1', all_varchar = true);

-- ===================== CFEM =====================
-- name: cfem_schema
DESCRIBE raw_cfem;

-- name: cfem_overview
SELECT count(*)                                   AS rows,
       min(TRY_CAST("Ano" AS INT))                AS min_year,
       max(TRY_CAST("Ano" AS INT))                AS max_year,
       count(*) FILTER (TRY_CAST("Ano" AS INT) IS NULL OR TRY_CAST("Mês" AS INT) NOT BETWEEN 1 AND 12) AS bad_period,
       count(*) FILTER (make_date(TRY_CAST("Ano" AS INT), TRY_CAST("Mês" AS INT), 1) > DATE '2026-11-01') AS future_period,
       -- DuckDB reads empty CSV fields as NULL, so blanks are tested with coalesce
       count(*) FILTER (coalesce(trim("UF"), '') = '')              AS blank_uf,
       count(*) FILTER (coalesce(trim("CodigoMunicipio"), '') = '') AS blank_ibge_code,
       count(*) FILTER (length(trim("CodigoMunicipio")) <> 7)       AS ibge_code_not_7_digits,
       count(*) FILTER (coalesce(trim("Município"), '') = '')       AS blank_municipality,
       count(*) FILTER (coalesce(trim("Substância"), '') = '')      AS blank_substance,
       count(*) FILTER (coalesce(trim("UnidadeDeMedida"), '') = '') AS blank_unit,
       count(*) FILTER (coalesce(trim("QuantidadeComercializada"), '') = '') AS blank_qty,
       count(*) FILTER (coalesce(trim("CPF_CNPJ"), '') = '')        AS blank_holder_id,
       count(*) FILTER (coalesce(trim("DataCriacao"), '') = '')     AS blank_creation_date,
       count(*) FILTER ("ValorRecolhido" LIKE '%.%') AS value_with_dot,
       count(*) FILTER (TRY_CAST(replace("ValorRecolhido", ',', '.') AS DECIMAL(18,2)) IS NULL) AS unparseable_value,
       count(*) FILTER (TRY_CAST(replace("ValorRecolhido", ',', '.') AS DECIMAL(18,2)) <= 0) AS non_positive_value,
       count(*) FILTER (TRY_CAST(replace("QuantidadeComercializada", ',', '.') AS DOUBLE) IS NULL) AS unparseable_qty
FROM raw_cfem;

-- name: cfem_full_row_duplicates
SELECT (SELECT count(*) FROM raw_cfem)                            AS rows,
       (SELECT count(*) FROM (SELECT DISTINCT * FROM raw_cfem))    AS distinct_rows,
       (SELECT count(*) FROM raw_cfem) - (SELECT count(*) FROM (SELECT DISTINCT * FROM raw_cfem)) AS excess_identical_rows;

-- name: cfem_duplicate_value_share
-- Identical rows (same process, holder, substance, municipality, qty, value AND slip timestamp):
-- how much money do they represent? Decision on keeping/dropping is taken in staging.
WITH g AS (SELECT *, count(*) AS n FROM raw_cfem GROUP BY ALL HAVING count(*) > 1)
SELECT count(*) AS dup_groups, sum(n) AS rows_in_groups,
       round(sum((n - 1) * TRY_CAST(replace("ValorRecolhido", ',', '.') AS DECIMAL(18,2))) / 1e6, 2) AS excess_brl_mn
FROM g;

-- name: cfem_substance_naming_over_time
-- Are 'FERRO' and 'MINÉRIO DE FERRO' the same commodity named differently in different periods?
SELECT "Substância" AS substance, min(TRY_CAST("Ano" AS INT)) AS first_year, max(TRY_CAST("Ano" AS INT)) AS last_year,
       count(*) AS rows, round(sum(TRY_CAST(replace("ValorRecolhido", ',', '.') AS DECIMAL(18,2))) / 1e9, 3) AS cfem_brl_bn
FROM raw_cfem
WHERE "Substância" IN ('FERRO', 'MINÉRIO DE FERRO', 'OURO', 'MINÉRIO DE OURO', 'COBRE', 'MINÉRIO DE COBRE',
                       'BAUXITA', 'MINÉRIO DE ALUMÍNIO', 'NÍQUEL', 'MINÉRIO DE NÍQUEL')
GROUP BY 1 ORDER BY 1;

-- name: cfem_iron_by_year_and_name
SELECT TRY_CAST("Ano" AS INT) AS year,
       round(sum(TRY_CAST(replace("ValorRecolhido", ',', '.') AS DECIMAL(18,2))) FILTER ("Substância" = 'FERRO') / 1e9, 3) AS ferro_bn,
       round(sum(TRY_CAST(replace("ValorRecolhido", ',', '.') AS DECIMAL(18,2))) FILTER ("Substância" = 'MINÉRIO DE FERRO') / 1e9, 3) AS minerio_de_ferro_bn
FROM raw_cfem GROUP BY 1 ORDER BY 1;

-- name: cfem_last_months
SELECT TRY_CAST("Ano" AS INT) AS year, TRY_CAST("Mês" AS INT) AS month, count(*) AS rows,
       round(sum(TRY_CAST(replace("ValorRecolhido", ',', '.') AS DECIMAL(18,2))) / 1e6, 1) AS cfem_brl_mn
FROM raw_cfem WHERE TRY_CAST("Ano" AS INT) >= 2025 GROUP BY 1, 2 ORDER BY 1, 2;

-- name: cfem_holder_type_dash
SELECT "Ano", "CPF_CNPJ", "Substância", "UF", count(*) AS rows FROM raw_cfem WHERE "Tipo_PF_PJ" = '-' GROUP BY ALL LIMIT 10;

-- name: cfem_qty_unparseable_sample
SELECT "QuantidadeComercializada", "UnidadeDeMedida", count(*) AS rows FROM raw_cfem
WHERE TRY_CAST(replace("QuantidadeComercializada", ',', '.') AS DOUBLE) IS NULL GROUP BY ALL ORDER BY rows DESC LIMIT 10;

-- name: cfem_by_year
SELECT TRY_CAST("Ano" AS INT) AS year,
       count(*) AS rows,
       count(DISTINCT "Mês") AS months,
       round(sum(TRY_CAST(replace("ValorRecolhido", ',', '.') AS DECIMAL(18,2))) / 1e9, 3) AS cfem_brl_bn
FROM raw_cfem GROUP BY 1 ORDER BY 1;

-- name: cfem_holder_type
SELECT "Tipo_PF_PJ" AS holder_type,
       count(*) AS rows,
       count(DISTINCT "CPF_CNPJ") AS distinct_ids,
       count(*) FILTER (length("CPF_CNPJ") = 14 AND regexp_full_match("CPF_CNPJ", '[0-9]{14}')) AS full_cnpj,
       count(*) FILTER (contains("CPF_CNPJ", '*')) AS masked,
       round(sum(TRY_CAST(replace("ValorRecolhido", ',', '.') AS DECIMAL(18,2))) / 1e9, 3) AS cfem_brl_bn
FROM raw_cfem GROUP BY 1 ORDER BY 1;

-- name: cfem_units
SELECT trim("UnidadeDeMedida") AS unit, count(*) AS rows FROM raw_cfem GROUP BY 1 ORDER BY 2 DESC;

-- name: cfem_substances_mixed_units
SELECT "Substância" AS substance,
       count(DISTINCT trim("UnidadeDeMedida")) AS n_units,
       string_agg(DISTINCT trim("UnidadeDeMedida"), '|') AS units,
       round(sum(TRY_CAST(replace("ValorRecolhido", ',', '.') AS DECIMAL(18,2))) / 1e6, 1) AS cfem_brl_mn
FROM raw_cfem GROUP BY 1 HAVING count(DISTINCT trim("UnidadeDeMedida")) > 1 ORDER BY cfem_brl_mn DESC LIMIT 25;

-- name: cfem_top_substances
SELECT "Substância" AS substance, count(*) AS rows,
       round(sum(TRY_CAST(replace("ValorRecolhido", ',', '.') AS DECIMAL(18,2))) / 1e9, 3) AS cfem_brl_bn
FROM raw_cfem GROUP BY 1 ORDER BY 3 DESC LIMIT 20;

-- name: cfem_distinct_counts
SELECT count(DISTINCT "Substância") AS substances, count(DISTINCT "UF") AS ufs,
       count(DISTINCT "CodigoMunicipio") AS municipalities, count(DISTINCT "Processo" || '/' || "AnoDoProcesso") AS processes,
       count(DISTINCT "CPF_CNPJ") AS holders
FROM raw_cfem;

-- name: cfem_blank_uf_detail
SELECT "Ano", "Município", "CodigoMunicipio", count(*) AS rows,
       round(sum(TRY_CAST(replace("ValorRecolhido", ',', '.') AS DECIMAL(18,2))), 2) AS cfem_brl
FROM raw_cfem WHERE trim("UF") = '' GROUP BY ALL ORDER BY rows DESC LIMIT 10;

-- name: cfem_creation_lag
-- DataCriacao = slip generation date. Lag vs the collection month shows cash-basis timing.
SELECT CASE WHEN lag_m < 0 THEN 'created after collection month'
            WHEN lag_m = 0 THEN 'same month'
            WHEN lag_m <= 12 THEN '1-12 months earlier'
            ELSE '>12 months earlier' END AS bucket,
       count(*) AS rows
FROM (SELECT datediff('month', TRY_CAST("DataCriacao" AS TIMESTAMP)::DATE,
                      make_date(TRY_CAST("Ano" AS INT), TRY_CAST("Mês" AS INT), 1)) AS lag_m
      FROM raw_cfem)
GROUP BY 1 ORDER BY 2 DESC;

-- ===================== AMB =====================
-- name: amb_benef_key_duplicates
SELECT "Ano base", "UF", "Substância Mineral", count(*) AS n,
       string_agg("Indicação Contido", '|') AS contained_indicators
FROM raw_benef GROUP BY ALL HAVING count(*) > 1 ORDER BY n DESC LIMIT 15;

-- name: amb_benef_key_uniqueness_with_indicator
SELECT count(*) AS rows, count(DISTINCT ("Ano base", "UF", "Substância Mineral", "Indicação Contido")) AS distinct_keys
FROM raw_benef;

-- name: amb_bruta_key_uniqueness_with_indicator
SELECT count(*) AS rows, count(DISTINCT ("Ano base", "UF", "Substância Mineral", "Indicação Contido")) AS distinct_keys
FROM raw_bruta;

-- name: amb_benef_value_double_count_risk
-- When a (year, UF, substance) has several contained-indicator rows, is the sale value repeated?
WITH g AS (
  SELECT "Ano base", "UF", "Substância Mineral",
         count(*) AS n, count(DISTINCT "Valor Venda (R$)") AS distinct_values,
         count(DISTINCT "Quantidade Produção") AS distinct_qty
  FROM raw_benef GROUP BY ALL HAVING count(*) > 1)
SELECT count(*) AS groups, count(*) FILTER (distinct_values = 1) AS value_repeated,
       count(*) FILTER (distinct_qty = 1) AS qty_repeated FROM g;

-- name: amb_benef_value_double_count_detail
SELECT "Ano base", "UF", "Substância Mineral", "Indicação Contido", "Quantidade Produção", "Quantidade Contido",
       "Valor Venda (R$)"
FROM raw_benef
WHERE ("Ano base", "UF", "Substância Mineral") IN (
  SELECT ("Ano base", "UF", "Substância Mineral") FROM raw_benef GROUP BY ALL HAVING count(*) > 1)
ORDER BY 1, 2, 3 LIMIT 30;

-- name: amb_benef_exact_dup_rows
SELECT count(*) - (SELECT count(*) FROM (SELECT DISTINCT * FROM raw_benef)) AS benef_identical_excess,
       (SELECT count(*) FROM raw_bruta) - (SELECT count(*) FROM (SELECT DISTINCT * FROM raw_bruta)) AS bruta_identical_excess
FROM raw_benef;

-- name: amb_benef_units
SELECT "Unidade de Medida - Produção" AS prod_unit, "Unidade de Medida - Venda" AS sale_unit, count(*) AS rows
FROM raw_benef GROUP BY ALL ORDER BY rows DESC;

-- name: amb_benef_year_completeness
SELECT "Ano base" AS year, count(*) AS rows, count(DISTINCT "UF") AS ufs, count(DISTINCT "Substância Mineral") AS substances,
       round(sum(TRY_CAST(replace("Valor Venda (R$)", ',', '.') AS DOUBLE)) / 1e9, 2) AS sale_value_brl_bn,
       count(*) FILTER (TRY_CAST(replace("Valor Venda (R$)", ',', '.') AS DOUBLE) = 0) AS zero_sale_rows
FROM raw_benef GROUP BY 1 ORDER BY 1;

-- name: amb_benef_unparseable
SELECT count(*) FILTER (TRY_CAST(replace("Quantidade Produção", ',', '.') AS DOUBLE) IS NULL) AS bad_qty,
       count(*) FILTER (TRY_CAST(replace("Valor Venda (R$)", ',', '.') AS DOUBLE) IS NULL) AS bad_value,
       count(*) FILTER (TRY_CAST(replace("Valor Venda (R$)", ',', '.') AS DOUBLE) < 0) AS negative_value,
       count(*) FILTER ("Valor Venda (R$)" LIKE '%.%') AS value_with_dot
FROM raw_benef;

-- name: amb_substance_vocab
SELECT b."Classe Substância" AS class, b."Substância Mineral" AS substance, count(*) AS rows
FROM raw_benef b GROUP BY ALL ORDER BY class, substance;
