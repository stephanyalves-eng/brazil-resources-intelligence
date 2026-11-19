# Data Profile — Oil & Gas (Phase 2)

Profiling of the raw files in `data/raw/MANIFEST.csv` (downloaded 2026-11-18). Reproduce with:

```powershell
cd brazil-resources-intelligence\oil-gas-intelligence\src
..\..\.venv\Scripts\python.exe -m oilgas.profiling
```

Outputs: `data/interim/profile_files.csv`, `profile_gas_balance.csv`, `profile_anuario_reconciliation.csv`.

## 1. File-level profile

| File | Unit | Rows | First | Last in file | Last month with national value > 0 | Key dups | Negatives | Zero rows | Missing UF×loc×month |
|---|---|---|---|---|---|---|---|---|---|
| oil | m³ | 7,920 | 1997-01 | **2026-12** | **2026-09** | 0 | 0 | 2,447 | 0 |
| gas | 1000 m³ | 7,775 | 1997-01 | 2026-09 | 2026-09 | 0 | 0 | 2,206 | 79 |
| lgn | m³ | 3,567 | 1997-01 | 2026-09 | 2026-09 | 0 | 0 | 807 | 3 |
| reinjection | 1000 m³ | 7,021 | 2000-01 | 2026-09 | 2026-09 | 0 | 0 | 4,805 | 41 |
| flaring (and losses) | 1000 m³ | 7,043 | 2000-01 | 2026-09 | 2026-09 | 0 | 0 | 2,453 | 19 |
| own_use | 1000 m³ | 7,034 | 2000-01 | 2026-09 | 2026-09 | 0 | 0 | 2,608 | 28 |
| available | 1000 m³ | 7,049 | 2000-01 | 2026-09 | 2026-09 | 0 | **681** | 2,268 | 13 |

22 UF × location combinations (11 UFs × TERRA/MAR; LGN has 10 UFs and no location split). The files cover 4 regions
(no Centro-Oeste).

### Findings

1. **Oil Oct–Dec 2026 are placeholder zeros.** All 66 rows are 0 nationally, while Sep 2026 is 22.47 million m³. These rows must be removed, not treated as production.
2. **Missing rows ≠ zero.** Some files skip UF × location × month combinations (e.g. gas 79). After densification these become `not_reported` (NULL). They are not set to 0.
3. **Negative "available gas" (681 rows).** These sit mainly in Ceará TERRA (275), Sergipe TERRA (265) and Espírito Santo TERRA (84): local uses (reinjection, own consumption) exceed local production. This reads as gas moved between areas inside ANP's balance. It is a **valid accounting value**: kept, flagged, and never clipped to 0.
4. **Gas balance identity** (production = reinjection + flaring + own use + available), per UF × location × month: 95.8 % of rows with production > 0 close within 1 %. Nationally, **307 of 321 months close within 0.5 %**. (Phase 2 profiling first reported 308 because it dropped UF-months that had any unpublished flow. Summing each flow nationally, which is the method used in the pipeline, puts Dec 2024 at −0.503 %. Several UFs left reinjection or own use unpublished that month. The Phase 7 test suite caught this.) The exceptions are **Jul 2005 (−27.98 %)**, Jan–Mar 2025 (about −0.6 %) and a few others. Big offsetting gaps in single states (e.g. May 2024: SP MAR −363 k vs RJ MAR +348 k thousand m³) show that ANP allocates volumes between states. Gas utilisation ratios are therefore most reliable **nationally and by location**, and are labelled "allocation-sensitive" at UF level.
5. **Decimal precision** appears from 1997–2000 depending on the file, so it cannot be used as a provisional-data marker. Instead, months in the current year are flagged `is_provisional` because ANP revises them.

## 2. Reconciliation with the Anuário Estatístico 2026 (2016–2025, annual, UF × Terra/Mar)

| Series | Anuário unit (derived) | Monthly-sum / Anuário ratio (median) | National annual deviation, 2016–2025 |
|---|---|---|---|
| Oil (t2.14) | **thousand barrels** (ratio 158.987 = 1000 / 6.2898) | 158.9873 | ≤ 0.000 % every year |
| Gas (t2.19) | million m³ | 1000.0 | ≤ 0.039 % (2020) |
| Reinjection (t2.21) | million m³ | 1000.0 | ≤ 0.000 % |
| Flaring (t2.22) | million m³ | 1000.0 | ≤ 0.030 % (2025) |

Cell-level deviations above 0.5 % are rounding on very small cells (Anuário values below 30 million m³), except **Espírito Santo
TERRA gas 2020**: monthly sum 45.30 vs Anuário 27.00 million m³ (+67.8 %). This is a revision between the two publications, recorded
in LIMITATIONS. Unmatched keys (about 70 per series) are combinations with 0 production in the monthly files that are absent from the
Anuário. They carry no volume.

**Conclusion:** the monthly state/location files are consistent with ANP's official annual statistics. They are
validated as the primary source.

## 3. Decisions for cleaning (Phase 5)

- Cut every series at the last month with national value > 0 that is common to all series used together (currently **2026-09**).
- Densify to the full UF × location × month grid. Rows that were never published get `value = NULL`, `status = 'not_reported'`.
- Keep negative available gas, with `is_negative_balance_flag`.
- Daily average = monthly volume / `days_in_month` (calendar days, leap years included).
- Oil and gas stay in separate columns and are never added. bbl/d is shown as an explicitly labelled conversion (×6.2898).
