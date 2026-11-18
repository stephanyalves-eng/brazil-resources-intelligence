# Analysis Findings — Brazilian Mining Performance & Market Concentration

Phase 6. Every number comes from `sql/30_analysis.sql` – `33_state_drivers.sql`, run on the 2026-11-18 build. Result files are in
`data/processed/analysis/q*.csv`. Values are **nominal R$**.
**AMB value** = value of *beneficiated* (processed) sales reported in the RAL. **CFEM** = royalty collected.
CFEM is not revenue. Company = legal entity (CNPJ root), not economic group. Findings describe the data; they do not
establish causes.

## Headline findings

| # | Finding | Evidence |
|---|---|---|
| F1 | **Sector value grew 4.6× in 15 years, and for the three metals that make up 82 % of it, unit value rose more than volume.** Beneficiated sales went from R$ 61.4 bn (2010) to R$ 281.7 bn (2025), a 10.7 % nominal CAGR. The peak was R$ 322.2 bn in 2021, followed by −28.0 % in 2022. Over 2011→2025 the log-points split as follows (unit value vs volume): iron ore 66 vs 33, gold 192 vs ≈34, copper 155 vs 62. | q01, q04 |
| F2 | **Iron ore moves the whole sector, and unit value drives it.** In 2021, iron ore value rose 75.6 %: +6.9 log-points from volume and +49.4 from unit value (R$ 387 → R$ 634/t). In 2022 it fell 39.7 %, of which −44.6 log-points came from unit value. 2025 is the opposite case: +9.4 from volume (433.7 Mt sold and 484.9 Mt produced, both series highs) and −2.2 from unit value. | q04, q24 |
| F3 | **Dependence on iron ore is falling, but concentration stays in metals.** Iron ore's share of national value was 68.0 % (2010), 75.8 % (2021 peak) and **56.7 % (2025)**. Only 2015 (52.0 %) and 2016 (55.9 %) were lower. Iron + gold + copper still make up 82.1 %. The commodity-mix HHI fell from 4,754 to 3,591, which is still "highly concentrated". | q02, q07 |
| F4 | **Gold and copper were the fastest-growing large commodities (2015→2025).** Gold rose from R$ 7.4 to 40.7 bn (CAGR 18.6 %) and copper from R$ 7.1 to 30.8 bn (15.9 %). For gold, the 2024–2025 rise came mostly from unit value (+33.2 and +36.2 log-points). Gold's implied unit value reached R$ 579/g in 2025. | q03, q04 |
| F5 | **Two states hold three-quarters of the value, and the lead changes hands.** MG + PA = 74.7 % (2025). MG fell from 49.3 % to 37.8 % (2010→2025), and PA rose from 29.6 % to 36.9 %. PA was ahead of MG from 2018 to 2021 and again in 2024. | q05, q06 |
| F6 | **Bahia and Mato Grosso are rising on gold.** BA rose from 2.9 % to 4.5 % of national value (#5 → #3); gold is 47.5 % of BA's value (R$ 0.42 → 5.97 bn). MT rose from 0.7 % to 3.1 % (#11 → #6); gold is 62.3 % (R$ 0.28 → 5.50 bn). | q05, q22 |
| F7 | **Company concentration is high in iron ore and copper and low in gold.** On CFEM, the iron ore HHI is 5,104 (2025). The top legal entity, **VALE S.A.**, has 70.6 % and the top 4 have 87.6 %, even though the number of payers rose from 53 to 98 (2010 → 2025). Copper: HHI 5,438, with **Salobo Metais S/A** at 72.0 %. Gold: HHI 1,166 across 79 companies, the only large commodity below the 1,500 band. | q07, q08, q09 |
| F8 | **One legal entity pays almost half of all company CFEM.** In 2025 VALE S.A. alone paid R$ 3.86 bn, 48.8 % of PJ CFEM. The top 10 entities paid 72.1 %. These are legal entities. Grouping entities under common ownership can only raise HHI and CR figures, so concentration at group level is **at least** this high. | q10 |
| F9 | **Royalties are highly concentrated geographically.** Of 2,851 municipalities with CFEM in 2025, **Canaã dos Carajás (15.8 %) and Parauapebas (13.9 %)**, both in PA and both iron ore, collected 29.7 %. The top 10 collected 61.6 %; 9 of them are iron ore, and Marabá is copper. | q11 |
| F10 | **The CFEM collected per R$ of AMB sales stepped up from 2018.** For iron ore it averaged 2.19 % in 2010–2017 (range 1.70–3.00) and 3.56 % in 2018–2025 (range 3.15–3.90); every year from 2018 (lowest: 3.15 %) is above every year in 2010–2017 (highest: 3.00 %, in 2013). This timing **is consistent with** Lei 13.540/2017, which changed CFEM rates and its calculation base (iron ore rate 3.5 %). The ratio compares different bases and timings, so it is an indicator, not a measured effective rate. | q12 |

## Data-quality findings that changed the analysis

| # | Finding | Action |
|---|---|---|
| DQ1 | **Feb 2024 CFEM contains a systematic duplicate export.** 32.4 % of that month's value comes from identical lines (same process, amount and slip timestamp). The monthly median for this share is 0.007 %. 774 lines appear exactly twice, and VALE S.A.'s Feb 2024 total doubles (R$ 597 M gross vs R$ 345 M net, against roughly R$ 300 M in neighbouring months). | Rule T13: identical repeats are excluded in months where they exceed 5 % of value (only Feb 2024). R$ 296.3 M was removed. With the duplicates, 2024 CFEM growth would read **+12.8 %**; the corrected figure is **+8.4 %**. Repeats in all other months stay (≤ 0.16 % of any year's value) |
| DQ2 | **Espírito Santo's iron ore is intermittent in AMB:** R$ 9.03 bn in 2021, then 0 in 2022, 0.11 bn in 2023, 0 in 2024, and 10.84 bn in 2025. This drives ES from #15 to #4. | Treated as a reporting inconsistency, not a production shift. Flagged in LIMITATIONS and in the dashboard. Iron ore geographic shares are presented with this caveat |
| DQ3 | **AMB Columbita-Tantalita (AM)** repeated the same quantity on two oxide rows. | Collapsed (rule T8). Value unaffected |

## Questions this data cannot answer
- Real (inflation-adjusted) growth: needs IPCA, which is not used.
- Group-level ownership concentration: needs a corporate-ownership dataset.
- Why unit values moved (world prices, FX, product mix): the data contains no price or FX series. F2 and F4 describe the arithmetic split only.
- Mine-level production: AMB is published at UF level only.
