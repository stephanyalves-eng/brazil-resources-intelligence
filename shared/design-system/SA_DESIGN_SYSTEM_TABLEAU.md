# Stephany Alves Design System — Tableau application

**Source of the tokens:** `C:\Tableau\FAB\FAB Supplier Concentration.html`. Its stylesheet opens with
*"Layout: Tableau dashboard spec … Stephany Alves Design System tokens"*. That is the only design-system file found under
`C:\Tableau`. Every value below is copied from it. **No colour, font or component was invented.** If an official token file
exists elsewhere, replace this page with it; the build guides refer to tokens **by name**, so only this file would change.

## 1. Tokens (light theme, used for Tableau)

| Token | Hex | Role in the dashboards |
|---|---|---|
| `--page` | `#F5F4EC` | Dashboard background |
| `--surface` | `#FFFFFF` | Panel and KPI-tile background |
| `--paper` | `#FBFAF6` | Methodology text blocks, table banding |
| `--ink` | `#101714` | Primary text, values |
| `--ink-2` | `#454C48` | Body text, insight sentences |
| `--ink-3` | `#5E6561` | Eyebrows, axis labels, footnotes |
| `--line` | `#D6D8D2` | Panel borders, dividers |
| `--grid` | `#E8E9E5` | Gridlines, table row lines |
| `--forest` | `#0B302B` | Header band, inverse KPI tile |
| `--forest-700` | `#1E5246` | **Highlighted series** (focus) |
| `--forest-600` | `#2F6B5B` | Second focus series |
| `--sage` | `#B8C9C0` | Text on forest, third series, light fills |
| `--sage-100` | `#E4ECE7` | Selected or hover background, area fill |
| `--signal` | `#16804F` | Positive change (▲) |
| `--context` | `#D6D8D2` | **Context (non-highlighted) bars and lines** |
| `--warn` | `#9A6412` | Thresholds, data-quality flags, provisional |
| `--warn-bg` | `#F4E8CF` | Background of flagged tags |
| `--err` | `#A63A2A` | Negative change (▼), anomalies |
| `--on-forest` | `#F5F4EC` | Text on `--forest` |

The dark-theme tokens exist in the source, but Tableau Public has no theme switching, so the dashboards use **light only**.

## 2. Typography

| Token | Family (source) | Fallback in source | Use in Tableau Public* |
|---|---|---|---|
| `--serif` | Newsreader 300/400 | Georgia | Dashboard title (h1): **Georgia**, 28–32 pt, `--ink` |
| `--sans` | IBM Plex Sans 400/500/600 | Arial | Everything else: **Arial**. Section titles (h2) 14 pt 500; body 10–11 pt; KPI value ("ban") 24–26 pt |
| `--mono` | IBM Plex Mono 500 | Consolas | Eyebrows, chips, table headers: **Consolas**, 8 pt, UPPERCASE (if Tableau Public substitutes it on the web, accept the substitution; no other font is introduced) |

\* Tableau Public renders text on the server with web-safe fonts. Newsreader and IBM Plex fall back, so the fallbacks the tokens
themselves declare (Georgia, Arial, Consolas) are used. In Tableau Desktop, with the Google fonts installed, the original
families can be used for static images only. Numbers are tabular in the source, so number formats must use fixed decimals.

## 3. Components (from the source CSS → Tableau objects)

| Component | Source rule | Tableau build |
|---|---|---|
| **Header band** | `.band`: `--forest` background, radius 4, padding 16/20, eyebrow in `--sage`, title in `--on-forest` | Horizontal container, background `#0B302B`; text objects for the eyebrow (mono, `--sage`) and title; filter chips inside the band |
| **Filter chip** | `.chip`: mono 11 px uppercase, 1 px border in `--on-forest` at 35 %, radius 2 | Parameter and filter controls placed in the band, with titles in mono 8 pt `--on-forest` |
| **KPI tile** | `.kpi`: `--surface`, 1 px `--line` border, radius 4, padding 16/18; eyebrow, value ("ban" 34 px 500), sub-line 12.5 px `--ink-3` | Sheet with a text mark; three lines: eyebrow (mono 8 pt `--ink-3`), value (Arial 24 pt `--ink`), sub (Arial 9 pt `--ink-3` with ▲ `--signal` / ▼ `--err`). Border 1 px `#D6D8D2`, inner padding 12 |
| **Inverse KPI tile** | `.kpi.inverse`: `--forest` background, eyebrow and sub in `--sage`, value in `--on-forest` | Used once per dashboard for the headline KPI |
| **Panel** | `.panel`: `--surface`, 1 px `--line`, radius 4, padding 18/20; h3 title plus a one-sentence `.insight` | Vertical container: title (Arial 11 pt 500), insight caption (Arial 9.5 pt `--ink-2`, key words bold `--ink`), then the sheet |
| **Focus + context bars** | `.bar .fill` `--context`; `.bar.hl .fill` `--forest-700`; left axis line `--ink-3`; value right-aligned | Bar charts colour **one** focus member `#1E5246` and the rest `#D6D8D2`, with labels at the end of the bar in `--ink` |
| **Threshold line** | `.thr`: dashed 1 px `--warn` | Reference lines (HHI 1,500 / 2,500, the 0.5 % balance band): dashed, `#9A6412` |
| **Tag** | `.tag` mono 10.5 px uppercase, border `--line`; `.tag.sole` `--warn` on `--warn-bg` | Status pills (PROVISIONAL, DQ FLAG) as text marks or shapes in `--warn` |
| **Table** | `th` mono 10.5 px uppercase `--ink-3`, `td` 13 px, row line `--grid`, right-aligned numbers | Text tables: header mono 8 pt; row banding off; row divider `#E8E9E5`; numbers right-aligned |
| **Footer** | `.foot`: 12 px `--ink-3`, top border `--line` | Text object: source, snapshot date, unit, author |

**Grid and spacing:** outer padding 24, gap 12–16 between tiles and panels, radius 4 (Tableau has no radius, so use 1 px borders
and padding), maximum width 1200. In the source, the KPI row has 4 columns on desktop, 2 below 900 px and 1 below 480 px. The
phone layouts follow the 1-column rule.

## 4. Chart colour rules

1. **Focus + context first.** One highlighted member in `--forest-700`, the rest in `--context`. This is the default for every ranking.
2. **Up to three categorical series:** `--forest-700`, `--forest-600`, `--sage`. In oil & gas, Oil = `--forest-700`,
   Natural gas = `--forest-600` (consistent across both projects' "primary/secondary" roles); NGL = `--sage`.
3. **Change:** positive `--signal`, negative `--err`. Use these only for change, never for categories.
4. **Flags:** `--warn` (provisional months, data-quality caveats, thresholds).
5. **Sequential fills (maps):** `--sage-100` → `--forest-700` (two-colour sequential).
6. Gridlines `--grid`, axes and zero line `--ink-3`, no chart borders. Panels carry the borders.

`Preferences.tps` (next to this file) defines these palettes in Tableau. Copy it to
`Documents\My Tableau Repository\Preferences.tps` and restart Tableau.
