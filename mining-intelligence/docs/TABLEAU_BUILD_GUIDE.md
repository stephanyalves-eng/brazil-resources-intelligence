# Tableau Build Guide — Brazilian Mining Performance & Market Concentration

> **Status:** this is a specification and a manual build procedure. **No Tableau workbook (.twb/.twbx) has been created.**
> There is no reliable free way to generate a Tableau Public workbook automatically, so the dashboard is built by hand in
> Tableau Public (free) from the files in `tableau/data/`. Every number to verify after building is listed in §7.

Design: [SA Design System for Tableau](../../shared/design-system/SA_DESIGN_SYSTEM_TABLEAU.md). Tokens are referred to by name (`--forest-700` = `#1E5246`).
Data model and safe aggregation: [TABLEAU_DATA_MODEL.md](TABLEAU_DATA_MODEL.md). KPIs: [KPI_DEFINITIONS.md](KPI_DEFINITIONS.md).

## 0. Prerequisites (Windows)
1. Install **Tableau Public** (free desktop app) and sign in with a Tableau Public account. Creating the account is your step; no paid product is needed.
2. Copy `shared/design-system/Preferences.tps` to `Documents\My Tableau Repository\Preferences.tps`, then restart Tableau. The *SA* palettes appear under *Edit Colors*.
3. Rebuild the data if needed: `powershell -ExecutionPolicy Bypass -File src\run_pipeline.ps1` (from `mining-intelligence/`).

## 1. Connect the data
1. *Connect → Text file* → `tableau/data/amb_uf_substance_year.csv`. Then add the other CSVs **as separate data sources**, one per file. This keeps each grain separate (data model doc).
2. In the sources that have them, add **relationships** (drag `dim_uf` and `dim_substance` onto the canvas) on `uf` and `substance_group`. Do not create joins.
3. Field settings (each source):

| Field | Action |
|---|---|
| `year` | Convert to **Dimension**, discrete; type Whole number |
| `uf` | Geographic role → *State/Province*; *Edit Locations* → Country = **Brazil** |
| `company_key`, `ibge_municipality_code` | Change data type to **String** |
| `period_month` | Date |
| all `*_brl`, `*_qty`, shares, `hhi` | Measures; default number format set in §3 |

## 2. Parameters

| Name | Type | Values | Default | Used by |
|---|---|---|---|---|
| `p Year` | Integer | List 2010–2025 (AMB) | 2025 | All pages |
| `p CFEM Year` | Integer | List 2004–2025 | 2025 | Market Structure, CFEM views |
| `p Substance` | String | List from `dim_substance.substance_group` | Iron ore | Highlight and commodity drill |
| `p Concentration Type` | String | geographic (UF, AMB value) / commodity mix (AMB value) / business (CNPJ root, CFEM) | business (CNPJ root, CFEM) | Market Structure |

Show `p Year` and `p Substance` as single-value dropdowns inside the header band (chip style).

## 3. Calculated fields (copy exactly; create them in the source named in brackets)

```text
// [amb_national_year]
KPI Value (R$ bn)        = SUM(IF [year] = [p Year] THEN [sale_value_brl] END) / 1e9
KPI Value Prev (R$ bn)   = SUM(IF [year] = [p Year] - 1 THEN [sale_value_brl] END) / 1e9
KPI Value YoY            = IF [KPI Value Prev (R$ bn)] > 0 THEN [KPI Value (R$ bn)] / [KPI Value Prev (R$ bn)] - 1 END
KPI CAGR since 2010      = IF [p Year] > 2010 THEN
                             POWER([KPI Value (R$ bn)] / (SUM(IF [year] = 2010 THEN [sale_value_brl] END) / 1e9),
                                   1 / ([p Year] - 2010)) - 1 END
Value (R$ bn)            = SUM([sale_value_brl]) / 1e9
YoY Arrow                = IF [KPI Value YoY] >= 0 THEN "▲ " ELSE "▼ " END

// [amb_substance_year]
KPI Iron Share           = SUM(IF [year] = [p Year] AND [substance_group] = "Iron ore" THEN [sale_value_brl] END)
                           / SUM(IF [year] = [p Year] THEN [sale_value_brl] END)
KPI Top3 Share           = SUM(IF [year] = [p Year] AND [rank_in_year] <= 3 THEN [sale_value_brl] END)
                           / SUM(IF [year] = [p Year] THEN [sale_value_brl] END)
Highlight Substance      = IF [substance_group] = [p Substance] THEN [substance_group] ELSE "Other substances" END
Share (recomputed)       = SUM([sale_value_brl]) / TOTAL(SUM([sale_value_brl]))          // table calc: compute along substance_group
Pareto Cumulative        = RUNNING_SUM(SUM([sale_value_brl])) / TOTAL(SUM([sale_value_brl])) // sort descending by value

// [amb_uf_year] and [amb_uf_substance_year]
Is Selected Year         = [year] = [p Year]
State Label              = ATTR([uf_name]) + " · " + STR(ROUND(SUM([share_of_national]) * 100, 1)) + "%"   // amb_uf_year only; ATTR avoids mixing aggregate and row-level
Quantity (selected group)= IF [substance_group] = [p Substance] THEN [production_qty] END             // never sum across groups
DQ Caveat                = IF [dq_flag_intermittent_series] THEN "Intermittent reporting (see methodology)" END

// [amb_price_volume]
Unit Value               = SUM([sale_value_brl]) / SUM([sale_qty])

// [cfem_uf_substance_year] / [cfem_municipality_year]
CFEM (R$ mn)             = SUM([cfem_brl]) / 1e6
Is Selected CFEM Year    = [year] = [p CFEM Year]
Municipal Share          = SUM([cfem_brl]) / TOTAL(SUM([cfem_brl]))
KPI Top10 Municipal Share= SUM(IF [year] = [p CFEM Year] AND [rank_in_year] <= 10 THEN [cfem_brl] END)
                           / SUM(IF [year] = [p CFEM Year] THEN [cfem_brl] END)

// [cfem_company_substance_year]
Company Label            = IF [rank] <= 10 THEN STR([rank]) + ". " + [company_name] ELSE [company_name] END
Is Top Company           = [rank] = 1

// [amb_cfem_uf_substance_year]
CFEM per R$ of Sales     = SUM(IF [match_status] = "both" THEN [cfem_brl] END)
                           / SUM(IF [match_status] = "both" THEN [amb_sale_value_brl] END)
```

Number formats: R$ bn → `R$ #,##0.0 "bn"`; R$ mn → `R$ #,##0 "mn"`; shares → `0.0%`; HHI → `#,##0`; YoY → `+0.0%;-0.0%`.

## 4. Sheets

| ID | Sheet | Source | Marks / shelves | Filters | Colour | Tooltip |
|---|---|---|---|---|---|---|
| E1 | KPI · Value | amb_national_year | Text: eyebrow "VALUE OF BENEFICIATED SALES", `KPI Value (R$ bn)`, sub `YoY Arrow` + `KPI Value YoY` "vs previous year" | — | Inverse tile (`--forest`) | none |
| E2 | KPI · YoY / CAGR | amb_national_year | Text: `KPI CAGR since 2010` | — | Tile | none |
| E3 | KPI · Iron ore share | amb_substance_year | Text: `KPI Iron Share`, sub "Top 3: " + `KPI Top3 Share` | — | Tile | none |
| E4 | KPI · Geographic HHI | concentration | Text: `MAX([hhi])`, sub `hhi_band` | type = geographic, scope = All substances, `year = [p Year]` | Tile | none |
| E5 | Annual evolution | amb_national_year | Columns `year`; Rows `Value (R$ bn)`; bar | — | `--context`; `Is Selected Year` → `--forest-700` | "<year>: R$ <value> bn · YoY <value_yoy>" |
| E6 | Regional share (map) | amb_uf_year | Filled map on `uf`; colour `SUM(share_of_national)` | `year = [p Year]` | Sequential *SA – Sequential sage-forest* | "<uf_name> · <share> of national · rank <rank_in_year> · YoY <value_yoy>" |
| E7 | Top substances | amb_substance_year | Rows `substance_group` (sorted by value desc, top 10 by `rank_in_year <= 10`), Columns `Value (R$ bn)` bars; label share | `year = [p Year]` | `Highlight Substance`: selected `--forest-700`, others `--context` | "<group> · R$ <bn> · <share> · YoY <value_yoy>" |
| R1 | State ranking | amb_uf_year | Bars by `uf_name` sorted, label `State Label`; `rank_change` as a ▲▼ text column | `year = [p Year]` | Focus + context (top 2 `--forest-700`) | "<uf_name>: rank <rank> (change <rank_change>), cumulative <cumulative_share>" |
| R2 | State × substance heatmap | amb_uf_substance_year | Rows `substance_group` (top 12), Columns `uf`; square; colour `SUM(uf_share_of_substance)` | `year = [p Year]` | Sequential SA | "<uf> holds <uf_share_of_substance> of national <group> value"; + `DQ Caveat` |
| R3 | Substance evolution | amb_substance_year | Columns `year`, Rows `Value (R$ bn)`, line by `Highlight Substance` | — | Selected `--forest-700` 2 pt, others `--context` 1 pt | "<group> <year>: R$ <bn>, share <share>" |
| R4 | Volume vs unit value | amb_price_volume | Columns `year`; Rows Measure Values (`volume_effect_logpts`, `unit_value_effect_logpts`) stacked bars | `substance_group = [p Substance]` | volume `--forest-700`, unit value `--sage` | "<year>: volume <v> log-pts, unit value <p> log-pts; unit value R$ <unit_value_brl>/<unit>" |
| R5 | Production volume (selected) | amb_substance_year | Line `SUM(production_qty)` by `year` | `substance_group = [p Substance]` | `--forest-600` | "<year>: <qty> <unit>" |
| M1 | HHI over time | concentration | Line `MAX(hhi)` by `year`; reference lines 1,500 and 2,500 (dashed `--warn`) | `concentration_type = [p Concentration Type]`, `scope = [p Substance]` (or *All substances* / *Brazil*) | `--forest-700` | "<year>: HHI <hhi> (<hhi_band>), N = <n_participants>, CR4 <cr4_pct>%" |
| M2 | Company Pareto | cfem_company_substance_year | Bars `cfem_brl` by `Company Label` (rank order) + line `cumulative_share` (dual axis) | `year = [p CFEM Year]`, `substance_group = [p Substance]` | `Is Top Company` → `--forest-700`, others `--context`; line `--warn` | "<company_name> · R$ <mn> · <share_in_substance> · cumulative <cumulative_share>" + footnote "legal entity, not group" |
| M3 | Concentration table | concentration | Text table: scope × (HHI, CR1, CR4, N, top participant) for the business type | `year = [p CFEM Year]`, CFEM ≥ R$ 50 mn (filter on `total_value_brl`) | Table style | none |
| M4 | Municipal concentration | cfem_municipality_year | Bars top 15 by `rank_in_year`, label `Municipal Share` | `year = [p CFEM Year]` | top 2 `--forest-700` | "<municipality>, <uf> · R$ <mn> · main: <main_substance_group>" |
| M5 | Mix change | amb_substance_year | Area 100 % stacked `share_of_national` by `year`, colour `Highlight Substance` | — | Focus + context | "<group> <year>: <share>" |
| M6 | CFEM per R$ of sales | amb_cfem_uf_substance_year | Line `CFEM per R$ of Sales` by `year`, for all and for `p Substance` (two sheets or a dual axis) | `year` 2010–2025 | `--forest-700` / `--sage` | "<year>: <ratio>" + caveat text |
| D1 | Sources table | metadata | Text table of all columns | — | Table style | none |

## 5. Dashboards (desktop 1200 × 900 fixed; one dashboard per page with navigation buttons)

All pages share the header band (title, eyebrow "BRAZILIAN MINING · AMB + CFEM", parameters as chips, navigation buttons) and the footer
("Source: ANM AMB & CFEM, snapshot 2026-11-18 · nominal R$ · CFEM is royalty, not revenue").

**1 · Executive Overview**
```
┌ header band (forest) ─────────────────────────────────────────────── p Year ▾  p Substance ▾ ┐
├ E1 (inverse) ─┬ E2 ──────────┬ E3 ──────────┬ E4 ──────────┤  KPI row, 4 × ~285 px, h 110
├ E5 Annual evolution (7/12) ──────────────────┬ E6 Regional share map (5/12) ─┤  h 330
├ E7 Top substances (12/12) ─────────────────────────────────────────────────────┤  h 280
└ footer ───────────────────────────────────────────────────────────────────────┘
```
Insight captions, which are real findings (F1, F3): "Value is 4.6× 2010 in nominal terms; for iron ore, gold and copper, unit value rose more than volume" ·
"Iron ore is 56.7 % of value in 2025, down from 75.8 % in 2021".

**2 · Regional & Commodity Analysis.** Row 1: R1 (5/12) + R2 (7/12), h 380. Row 2: R3 (6/12) + R4 (6/12), h 300. R5 is shown as a
small panel under R4, or put on a tooltip sheet (*viz in tooltip* of R3).

**3 · Market Structure.** Row 1: M1 (6/12) + M2 (6/12), h 360. Row 2: M3 (5/12) + M4 (4/12) + M5 (3/12), h 300. M6 sits on this
page as a slim panel beneath M1. A text note: "Geographic concentration ≠ business concentration".

**4 · Data & Methodology.** D1 table plus text blocks on `--paper`. They cover: definitions (K1, K13, K15), period (AMB 2010–2025;
CFEM 2004–Jun 2026), the rules (T8 collapse, T13 duplicates, completeness), the restrictions (LIMITATIONS.md headlines: nominal
values, legal entity ≠ group, ES iron-ore caveat, no municipal map), and the update procedure (`run_pipeline.ps1 -Download`).

### Phone layout (Tableau *Device Layouts → Phone*, 375 px, fit width)
Single column, in this order. Header band (title plus `p Year` only) → KPI tiles stacked 1 per row (E1, E3, E4; drop E2) → E5 → E7
(top 5 only) → E6 map → footer. On the Market Structure phone page: M1 → M2 (top 5) → M4 (top 5). Hide R2 (the heatmap is not
legible at 375 px) and replace it with R1. Titles at 12 pt, values at 20 pt.

## 6. Interactions

| Action | Type | Source → target | Effect |
|---|---|---|---|
| Select a substance | **Parameter action** | E7, R3, M5 click → `p Substance` | Updates highlight, R4, R5, M1, M2 |
| Select a year | Parameter action | E5 click → `p Year` | Drives KPIs, map, rankings |
| State drill | Filter action | E6 / R1 click → R2 | R2 shows the selected UF column; clearing restores all |
| Highlight | Highlight action | R2 hover → R1 | Highlights the state |
| Navigation | Navigation buttons | header | Page 1–4 |

Tooltips: sentence-style text in Arial 9.5, `--ink-2`, values bold `--ink`. Every CFEM tooltip ends with "CFEM = royalty collected".
Do not use *Show Me* default tooltips.

## 7. Verification checklist (values must match; from the 2026-11-18 build)

| Check | Expected |
|---|---|
| E1 at p Year = 2025 | R$ 281.7 bn, ▲ +15.2 % |
| E2 | +10.7 % CAGR since 2010 |
| E3 | 56.7 %, top 3 = 82.1 % |
| E4 | 2,862 · highly concentrated |
| E6 / R1 | MG 37.8 %, PA 36.9 %, BA 4.5 % (rank 3) |
| E5 peak | 2021 = R$ 322.2 bn |
| R4, Iron ore 2021 | volume +6.9, unit value +49.4 log-pts |
| M1, business Iron ore 2025 | HHI 5,104 |
| M2, Iron ore 2025 | 1. VALE S.A. 70.6 %; cumulative after 4 = 87.6 % |
| M4, 2025 | Canaã dos Carajás 15.8 %, Parauapebas 13.9 % |
| M6, 2025 | all mapped 2.70 %, iron ore 3.42 % |

## 8. Publish
*File → Save to Tableau Public As…* → name "Brazilian Mining Performance & Market Concentration". Tableau Public workbooks are
**public by default**. Publishing is your decision and your action. Afterwards, set *Allow workbook download* as you prefer, then add
the URL to `README.md`.
