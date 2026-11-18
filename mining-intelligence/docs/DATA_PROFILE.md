# Data Profile — Mining (Phase 2)

Full-file profiling of the raw files listed in `data/raw/MANIFEST.csv` (downloaded 2026-11-18).
Reproduce with:

```powershell
cd C:\Tableau\industrial-data-analytics\mining-intelligence
..\.venv\Scripts\python.exe src\run_sql.py sql\00_profile_raw.sql sql\01_profile_followups.sql --out data\interim\profile
```

The full CFEM scan (2.43 M rows, 325 MB) takes about 30 s in DuckDB 2.0.0. Each labelled query's result is saved as
`data/interim/profile/<label>.csv`.

## 1. CFEM Arrecadação (`CFEM/CFEM_Arrecadacao.csv`, SHA-256 `7a394968…e1c811`)

| Check | Result |
|---|---|
| Rows × columns | **2,434,190 × 14** |
| Period | 2002-?? (10 rows) and 2003 (8 months) are partial. **2004–2025 complete** (12 months each). 2026 has 11 months (Jan–Nov) |
| Total CFEM collected | R$ 74.537 bn (nominal, all years) |
| Future periods (after 2026-11) | 0 |
| Invalid year/month | 0 |
| Unparseable or non-positive `ValorRecolhido` | 0 / 0 (no '.' thousands separators) |
| Identical rows (all 14 fields, including the slip timestamp) | **143,751 excess rows** in 10,065 groups, worth **R$ 325.07 M (0.44 % of the total)** |
| Blank UF + municipality | 1,628 rows (1,622 also lack a 7-digit IBGE code) |
| Blank unit / blank quantity | 982 / 15,990 rows (the value is still present) |
| Blank holder ID | 334 rows. `Tipo_PF_PJ = '-'` on 55 rows (CALCÁRIO MG 2003–05, CASSITERITA PA 2026) |
| Holder type | PJ 2,363,543 rows / R$ 74.42 bn, with full 14-digit CNPJ on 99.99 % of PJ rows. PF 70,592 rows / R$ 0.115 bn, all CPFs masked (`***NNNNNN**`) |
| Distinct counts | 316 substances · 27 UFs · 3,985 municipality codes · 46,074 mining processes · 21,896 holders |
| Units | t 1.36 M · m3 0.79 M · l 0.13 M · g 0.10 M · kg 31 k · m2 16 k · ct 2 k · blank 982 |
| Mixed units within one substance | Common, e.g. FERRO (t, kg), MINÉRIO DE OURO (g, kg, ct), GRANITO (t, m2, m3) |
| Substance synonyms | `FERRO` (R$ 38.85 bn) and `MINÉRIO DE FERRO` (R$ 15.54 bn) **both appear in every year 2003–2026**. This is not a renaming. The same holds for OURO / MINÉRIO DE OURO, COBRE / MINÉRIO DE COBRE, BAUXITA / MINÉRIO DE ALUMÍNIO, NÍQUEL / MINÉRIO DE NÍQUEL |
| Recording lag (`DataCriacao` vs collection month) | Same month 92.7 % · 1–12 months earlier 4.4 % · more than 12 months earlier 2.8 % · after the collection month 576 rows |
| Recent months | Monthly totals sit around R$ 590–750 M through **Jun 2026**. They then drop to R$ 74 M (Jul), 5.6 M (Aug), 2.3 M (Sep), 7.9 M (Oct) and 0.4 M (Nov). **Jul–Nov 2026 are incomplete** |
| Row-count anomaly | Dec 2025 – Mar 2026 have 39–52 k rows per month (normally 9–15 k) with normal R$ totals. More, smaller slips. Recorded, not corrected |

### Decisions for staging (Phase 5)

1. **Analysis window:** full years 2004–2025 for annual KPIs. 2026 appears only as "YTD through Jun 2026", flagged provisional. 2002–2003 are excluded from trends.
2. **Identical rows are kept and flagged.** There is no slip/document ID, so a genuine repeated payment cannot be told apart from a duplicate export. The impact (0.44 % of value) is reported, and a sensitivity check (with/without) runs in QA.
3. **Substance mapping:** a seed table `substance_map.csv` maps CFEM names to `substance_group` (e.g. FERRO + MINÉRIO DE FERRO → Iron ore) and to the AMB substance. Unmapped value is reported.
4. **Quantities are never summed across units.** CFEM quantity is used only within (substance_group, unit). Value-based KPIs (R$) do not depend on units.
5. **Company concentration uses PJ only.** PF rows are grouped as "Individuals (masked)". Blank-ID and '-' rows are grouped as "Unidentified".
6. Rows with blank UF are kept in national totals and excluded from geographic shares, with a count shown.

## 2. AMB Produção Beneficiada (`AMB/Producao_Beneficiada.csv`, SHA-256 `dd7e5da6…f19879`)

| Check | Result |
|---|---|
| Rows × columns | 3,982 × 18 |
| Period | Base years 2010–2025, 232–263 rows per year |
| UF coverage | 26 UFs (**AC never appears**) |
| Substances | 52 in 4 classes (Metálicos 21, Não-Metálicos 26, Energéticos 3, Gemas e Diamantes 2) |
| Units | Production and sale units always match: t 3,519 rows, kg 397 (Ouro, Prata, Estanho, Gemas), ct 66 (Diamante) |
| Parse errors / negative values | 0 / 0 |
| Sales value total | from R$ 61.40 bn (2010) to R$ 322.23 bn (2021 peak) and R$ 281.69 bn (2025), nominal |
| Zero-sale rows | 16–41 per year (the production may have been consumed or transferred instead of sold) |
| Identical rows | 0 |
| (year, UF, substance) not unique | 29 groups. **Columbita-Tantalita** (AM, RO) has one row per contained oxide (Nb2O5 / Ta2O5). **Calcário SP 2010–2015** has 2 rows with no indicator and different values |
| Double-count risk | In **7 of the 29 groups** (Columbita-Tantalita AM), both rows repeat the same production quantity and value. Summing them would double-count |
| (year, UF, substance, indicator) | Still 6 duplicates, all Calcário SP |

### Decisions for staging

1. Grain of `stg_amb_beneficiada`: one row per published record, plus a surrogate `record_id`.
2. Fact grain (year, UF, substance): rows with identical quantity and value inside a group are **collapsed into one**. Different rows (Calcário SP, Columbita-Tantalita RO) are **summed**. A test reconciles both totals.
3. Quantities are summed only within one substance (one unit per substance, verified).

## 3. AMB Produção Bruta

6,307 × 14, 2010–2025, 27 UFs. There are 0 identical rows, but (year, UF, substance, indicator) has 33 duplicates. The same
collapse/sum rule applies. ROM tonnage is always in t.

## 4. Metadata vs. reality

| Metadata says | File has |
|---|---|
| Separator `;` | `,` with quoted decimal-comma numbers |
| Header `Ano Base` | `Ano base` |
| AMB "a partir de 2010" by UF | AC absent from Beneficiada |
