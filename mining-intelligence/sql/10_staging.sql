-- =====================================================================================
-- STAGING layer: typed, renamed (English snake_case), standardised. One row per raw record.
-- Raw files are read in place and never modified. Grain of each table is stated above it.
-- =====================================================================================

-- ---------- Seeds (hand-maintained, versioned reference data) ----------
CREATE OR REPLACE TABLE seed_uf AS
SELECT * FROM read_csv('seeds/uf.csv', header = true, all_varchar = true);

CREATE OR REPLACE TABLE seed_amb_substance AS
SELECT * FROM read_csv('seeds/amb_substance.csv', header = true, all_varchar = true);

CREATE OR REPLACE TABLE seed_substance_map AS
SELECT * FROM read_csv('seeds/substance_map.csv', header = true, all_varchar = true);

-- Decimal-comma text -> number. ',000000' and '1922,30299' both parse. NULL stays NULL.
CREATE OR REPLACE MACRO br_num(x) AS TRY_CAST(replace(trim(x), ',', '.') AS DOUBLE);

-- ---------- stg_amb_beneficiada ----------
-- Grain: one published AMB record (base year x UF x substance x contained-indicator, not unique; see DATA_PROFILE §2)
CREATE OR REPLACE TABLE stg_amb_beneficiada AS
WITH src AS (
  SELECT * FROM read_csv('data/raw/AMB/Producao_Beneficiada.csv', delim = ',', quote = '"', header = true,
                         encoding = 'latin-1', all_varchar = true)
)
SELECT
  row_number() OVER ()                                            AS record_id,
  CAST("Ano base" AS INTEGER)                                     AS base_year,
  upper(trim("UF"))                                               AS uf,
  trim("Classe Substância")                                       AS substance_class_pt,
  trim("Substância Mineral")                                      AS amb_substance,
  br_num("Quantidade Produção")                                   AS production_qty,
  lower(trim("Unidade de Medida - Produção"))                     AS production_unit,
  NULLIF(trim("Indicação Contido"), '')                           AS contained_indicator,
  br_num("Quantidade Contido")                                    AS contained_qty,
  NULLIF(NULLIF(lower(trim("Unidade de Medida - Contido")), '-'), '') AS contained_unit,
  br_num("Quantidade Venda")                                      AS sale_qty,
  lower(trim("Unidade de Medida - Venda"))                        AS sale_unit,
  round(br_num("Valor Venda (R$)"), 2)                            AS sale_value_brl,
  br_num("Quantidade Consumo/Utilização na Usina")                AS plant_use_qty,
  round(br_num("Valor Consumo / Utilização na Usina (R$)"), 2)    AS plant_use_value_brl,
  br_num("Quantidade Transferência para Transformação / Utilização / Consumo") AS transfer_qty,
  round(br_num("Valor Transferência para Transformação / Utilização / Consumo (R$)"), 2) AS transfer_value_brl
FROM src;

-- ---------- stg_amb_bruta ----------
-- Grain: one published AMB run-of-mine record (same non-unique key as above)
CREATE OR REPLACE TABLE stg_amb_bruta AS
WITH src AS (
  SELECT * FROM read_csv('data/raw/AMB/Producao_Bruta.csv', delim = ',', quote = '"', header = true,
                         encoding = 'latin-1', all_varchar = true)
)
SELECT
  row_number() OVER ()                                            AS record_id,
  CAST("Ano base" AS INTEGER)                                     AS base_year,
  upper(trim("UF"))                                               AS uf,
  trim("Classe Substância")                                       AS substance_class_pt,
  trim("Substância Mineral")                                      AS amb_substance,
  br_num("Quantidade Produção - Minério ROM (t)")                 AS rom_qty_t,
  NULLIF(trim("Indicação Contido"), '')                           AS contained_indicator,
  br_num("Quantidade Contido")                                    AS contained_qty,
  br_num("Quantidade Venda (t)")                                  AS sale_qty_t,
  round(br_num("Valor Venda (R$)"), 2)                            AS sale_value_brl,
  round(br_num("Valor Transformação / Consumo / Utilização nesta mina (R$)"), 2) AS mine_use_value_brl,
  round(br_num("Valor Transferência para Transformação / Utilização / Consumo (R$)"), 2) AS transfer_value_brl
FROM src;

-- ---------- stg_cfem ----------
-- Grain: one CFEM collection line as published (2,434,190 rows). Identical lines are kept and flagged.
CREATE OR REPLACE TABLE stg_cfem AS
WITH src AS (
  SELECT * FROM read_csv('data/raw/CFEM/CFEM_Arrecadacao.csv', delim = ',', quote = '"', header = true,
                         encoding = 'latin-1', all_varchar = true)
),
typed AS (
  SELECT
    CAST("Ano" AS INTEGER)                                        AS year,
    CAST("Mês" AS INTEGER)                                        AS month,
    trim("Processo") || '/' || trim("AnoDoProcesso")              AS mining_process,
    CASE trim("Tipo_PF_PJ") WHEN 'PJ' THEN 'PJ' WHEN 'PF' THEN 'PF' ELSE 'UNKNOWN' END AS holder_type,
    trim("CPF_CNPJ")                                              AS holder_id_raw,
    upper(trim("Substância"))                                     AS cfem_substance,
    NULLIF(upper(trim("UF")), '')                                 AS uf,
    CASE WHEN regexp_full_match(trim("CodigoMunicipio"), '[0-9]{7}') THEN trim("CodigoMunicipio") END AS ibge_municipality_code,
    NULLIF(trim("Município"), '')                                 AS municipality,
    br_num("QuantidadeComercializada")                            AS quantity_sold,
    NULLIF(lower(trim("UnidadeDeMedida")), '')                    AS quantity_unit,
    round(br_num("ValorRecolhido"), 2)                            AS cfem_brl,
    TRY_CAST("DataCriacao" AS TIMESTAMP)                          AS slip_created_at,
    -- identical-line flag: 2nd+ occurrence of a fully identical raw record
    -- (columns listed explicitly: PARTITION BY COLUMNS(*) does not expand inside a window)
    row_number() OVER (PARTITION BY "Ano", "Mês", "Processo", "AnoDoProcesso", "Tipo_PF_PJ", "CPF_CNPJ",
                       "Substância", "UF", "CodigoMunicipio", "Município", "QuantidadeComercializada",
                       "UnidadeDeMedida", "ValorRecolhido", "DataCriacao") > 1 AS is_identical_repeat
  FROM src
)
SELECT
  t.*,
  make_date(t.year, t.month, 1)                                   AS period_month,
  -- company key: CNPJ root (first 8 digits) groups all establishments of one legal entity
  CASE WHEN t.holder_type = 'PJ' AND regexp_full_match(t.holder_id_raw, '[0-9]{14}') THEN t.holder_id_raw END AS cnpj,
  CASE WHEN t.holder_type = 'PJ' AND regexp_full_match(t.holder_id_raw, '[0-9]{14}') THEN left(t.holder_id_raw, 8)
       WHEN t.holder_type = 'PF' THEN 'INDIVIDUALS (masked CPF)'
       ELSE 'UNIDENTIFIED' END                                    AS holder_key,
  coalesce(m.substance_group, 'Other (unmapped)')                 AS substance_group,
  m.amb_substance,
  coalesce(m.mapping_basis, 'unmapped')                           AS mapping_basis
FROM typed t
LEFT JOIN seed_substance_map m ON m.cfem_substance = t.cfem_substance;

-- ---------- Month completeness (data-driven) ----------
-- A month is 'incomplete' when its national total is < 50 % of the median of the 12 preceding months.
-- Years before 2004 are 'partial_history' (2002: 10 rows; 2003: 8 months).
CREATE OR REPLACE TABLE stg_cfem_month_status AS
WITH m AS (
  SELECT period_month, sum(cfem_brl) AS brl, count(*) AS rows FROM stg_cfem GROUP BY 1
),
w AS (
  SELECT *, median(brl) OVER (ORDER BY period_month ROWS BETWEEN 12 PRECEDING AND 1 PRECEDING) AS trailing_median
  FROM m
)
SELECT period_month, rows, brl, trailing_median,
       CASE WHEN year(period_month) < 2004 THEN 'partial_history'
            WHEN brl < 0.5 * trailing_median THEN 'incomplete'
            WHEN year(period_month) = 2026 THEN 'provisional'
            ELSE 'complete' END AS month_status
FROM w;
