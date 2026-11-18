# Portfolio Kit — Brazilian Mining Performance & Market Concentration

Every number below comes from the 2026-11-18 build ([ANALYSIS_FINDINGS.md](ANALYSIS_FINDINGS.md)). There are no business-impact
claims (savings, productivity), because this is an analysis of public data, not a client engagement. Replace `[GitHub link]` and
`[Tableau Public link]` once they exist. **Do not post the Tableau link before the dashboard is actually published.**

---

## 1. Case study

**Executive summary.** I built a SQL pipeline in DuckDB over two official datasets from Brazil's mining regulator (ANM): 15 years of
state-level mineral sales and 2.4 million royalty (CFEM) payment lines. The output answers four questions: how the sector's value
evolved, whether price or volume drove it, which states and commodities dominate, and how concentrated the market is. It uses 14
tested Tableau-ready tables and a four-page dashboard specification.

**Business problem.** Headlines about Brazilian mining usually quote one number, the total value. Investors, suppliers and local
governments need to know *what* drives it (a commodity price or more tonnes), *where* it happens (which states and municipalities
depend on it), and *who* controls it (geographic and corporate concentration are different risks).

**Analytical approach.**
1. **Source evaluation.** Six candidate ANM files were profiled, then two selected and the integration rules defined (both sides are aggregated before joining).
2. **Layered SQL.** Raw → staging (typing, flags) → marts (dimensions, facts, 10 analytical marts), with the grain documented for every table.
3. **Analysis:**
   - a price/volume log-point decomposition;
   - shares, rankings and Pareto curves;
   - HHI and CR4 for three different kinds of concentration;
   - a CFEM-to-sales indicator.
4. **QA.** 117 pytest checks: SHA-256 of the raw files, key uniqueness of every table, value reconciliation from raw to export, join fan-out, units, time.

**Technical architecture.** ANM CSV (327 MB) → PowerShell acquisition with a hash manifest → DuckDB SQL (`10_staging`, `20_marts`,
`30–33` analysis, `40` export) → 14 CSVs → Tableau Public. Hand-maintained seeds map 148 CFEM commodity names to 48 groups, and the
company names come from the public CNPJ registry.

**Data preparation highlights.**
- The official metadata gives the wrong delimiter (`;`); the files use `,` with decimal commas inside quotes.
- `FERRO` and `MINÉRIO DE FERRO` appear in the same years. They are synonyms, not a renaming, so a mapping seed was needed.
- **The Feb 2024 CFEM file contains a duplicated export.** 32 % of that month's value is exact copies, against a 0.007 % median. Leaving it in would overstate 2024 royalty growth (+12.8 % instead of +8.4 %).
- Espírito Santo's iron ore appears in 2021 and 2025 only. It is flagged, not "fixed".

**Key findings.**
- Sales value went from R$ 61.4 bn to R$ 281.7 bn (2010–2025, nominal). For iron ore, gold and copper, unit value rose more than volume.
- Iron ore was 75.8 % of value in 2021 and 56.7 % in 2025. Gold grew at an 18.6 % CAGR over 2015–2025.
- Minas Gerais and Pará hold 74.7 % of value, and the lead has changed hands several times.
- Company concentration (HHI): iron ore 5,104, with VALE S.A. paying 70.6 % of its CFEM; copper 5,438; gold 1,166, the only large commodity below the "moderately concentrated" band.
- Mining in Canaã dos Carajás and Parauapebas accounts for 29.7 % of all CFEM collected, out of 2,851 municipalities with CFEM-paying extraction. Attribution is by place of extraction; the separate distribution of CFEM to municipalities is not analysed.

**Dashboard walkthrough (specified; [build guide](TABLEAU_BUILD_GUIDE.md)).**
1. *Executive Overview:* four KPI tiles, the annual trend, a state map and the top commodities.
2. *Regional & Commodity:* state ranking, a state × commodity heatmap, and the volume vs unit-value split.
3. *Market Structure:* HHI over time with reference bands, the company Pareto, and municipal concentration.
4. *Data & Methodology:* sources, rules and limitations.

Clicking a commodity or a year updates every view.

**Technical challenges.**
- DuckDB `PARTITION BY COLUMNS(*)` silently did not expand, so every row was flagged as a duplicate. I found it because the count did not match the profiling.
- A data-driven completeness rule (monthly value under 50 % of the trailing median) cleanly separated incomplete recent months.
- Tests caught two impossible IBGE municipality codes and an over-broad duplicate rule. Both were fixed and documented.

**Limitations.**
- Values are nominal (no IPCA adjustment).
- CFEM is a royalty, not revenue, and its rates differ by commodity.
- A company here is a legal entity, not an economic group.
- AMB is published at state level only.
- See [LIMITATIONS.md](LIMITATIONS.md).

**Skills demonstrated.**
- **SQL:** CTEs, window functions (`LAG`, `RANK`, `ROW_NUMBER`, `SUM OVER`, framed `median`), `FULL`/`ANTI`/`CROSS` joins, `QUALIFY`, macros.
- **Modelling and quality:** dimensional modelling, data-quality engineering, pytest.
- **Analysis:** concentration analysis (HHI, CR4, Pareto) and price/volume decomposition.
- **Delivery:** Tableau data modelling, technical documentation, working with public-sector open data.

---

## 2. Channel texts

### GitHub — repository description (≤ 350 chars)
SQL-first analysis of Brazilian mining (ANM AMB + CFEM, 2010–2026) in DuckDB: layered staging/marts, price-vs-volume decomposition, HHI/CR4 for geographic, commodity and company concentration, 117 pytest checks and Tableau-ready extracts.

**Topics:** `sql` `duckdb` `data-analytics` `data-quality` `mining` `brazil` `open-data` `tableau` `market-concentration` `hhi` `pytest`

### LinkedIn post
Brazil's mining sector sold R$ 281.7 bn of processed minerals in 2025. That's 4.6× the 2010 figure, but the headline hides more than it shows.

I rebuilt the numbers from the regulator's open data (ANM), using SQL in DuckDB:

→ For iron ore, gold and copper, rising unit values did more than rising tonnes. In 2021 alone, iron ore's value jumped 75.6 %, and most of that was unit value.
→ Iron ore's share fell from 75.8 % (2021) to 56.7 % (2025), while gold grew 18.6 % a year over the decade.
→ Concentration depends on what you measure. By company, iron ore is highly concentrated: one legal entity pays 70.6 % of the royalties. Gold is not (HHI 1,166).
→ Mining in just two municipalities in Pará generates almost 30 % of all royalties collected.

The most useful finding was a data-quality one: February 2024's royalty file contains a duplicated export. Leaving it in would show 2024 growth of +12.8 % instead of +8.4 %.

Everything is reproducible: raw-file hashes, 117 automated tests, documented rules. Repo: [GitHub link]

#DataAnalytics #SQL #DuckDB #Mining #OpenData #DataQuality

### Medium — article plan
**Title:** *Price, Volume or Concentration? Reading Brazil's Mining Data with SQL*
1. Hook: the R$ 281.7 bn figure and why one number is not enough.
2. The data: AMB and CFEM, what each one measures, and why CFEM is not revenue.
3. Price vs volume: the log-point decomposition, with the 2021 and 2025 iron ore examples.
4. Three kinds of concentration: geographic, commodity mix and company. Why they must not be mixed.
5. The duplicate that changed a growth rate: how the Feb 2024 issue was found and handled.
6. What I would add next: IPCA, corporate groups, municipal boundaries.
7. Code and data links.

### DEV Community — post outline
**Title:** *Building a layered SQL pipeline in DuckDB over 2.4 M rows of public data (and the bugs tests caught)*
Sections: project layout → `read_csv` with an explicit dialect (when the metadata is wrong) → staging flags vs deletions →
window-function KPIs (YoY that refuses to cross gap years, Pareto, HHI) → pytest against DuckDB (grain-uniqueness
parametrisation, reconciliation) → the bugs: `PARTITION BY COLUMNS(*)`, the DuckDB 2.0 `fetchone` change, invalid IBGE prefixes.
Tags: `#sql #duckdb #python #dataengineering`

### Peerlist — project card
**Brazilian Mining Performance & Market Concentration.** DuckDB SQL pipeline on ANM open data (AMB + 2.4 M CFEM lines). Price/volume
decomposition, HHI/CR4 by geography, commodity and company, 117 tests, Tableau-ready model. Stack: SQL, DuckDB, Python, pytest,
Tableau Public. [GitHub link]

### Personal portfolio — card
**Mining Intelligence · SQL**. *Which commodities, states and companies really drive Brazil's R$ 282 bn mining sector?* A
layered DuckDB pipeline over official ANM data, with concentration metrics and a reproducible QA suite.
`SQL` `DuckDB` `Data Quality` `Tableau` → [GitHub link] · [Tableau Public link]
