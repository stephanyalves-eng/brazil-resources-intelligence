# Data Quality Report — Mining Intelligence

Snapshot: ANM files downloaded 2026-11-18 (see `data/raw/MANIFEST.csv`). Automated checks: **56/56 passed** ([TEST_REPORT.md](TEST_REPORT.md)).

## Quality indicators

| Indicator | AMB Beneficiada | CFEM Arrecadação |
|---|---|---|
| Rows (raw → staging) | 3,982 → 3,982 | 2,434,190 → 2,434,190 |
| Parse failures on numeric fields | 0 | 0 (value), 15,990 blank quantities |
| Records with missing geography | 0 | 1,628 (0.07 %) without UF/municipality |
| Exact duplicate records | 0 | 143,751 identical lines (0.44 % of gross value); repeats excluded only in the 2 systematic months (Feb 2024, Aug 2002) |
| Non-unique business key | 29 groups (6 after adding the indicator) | n/a (no natural key) |
| Mixed units per substance | 0 | Common, so quantities are used only within one unit |
| Value assigned to a named substance group | 100 % | 99.96 % |
| Months complete / usable | 16 / 16 base years | 264 complete + 6 provisional of 284 |
| Value reconciliation raw → marts | exact (R$ 2.388 tn) | exact (gross R$ 74.537 bn, net R$ 74.240 bn, usable R$ 74.009 bn) |

## Issue register

| ID | Issue | Severity | Detection | Correction | Residual risk |
|---|---|---|---|---|---|
| M-01 | Metadata says the separator is `;`, but the files use `,` | Medium | Phase 1 profiling | Explicit dialect in every `read_csv` | Header test fails on a future layout change |
| M-02 | ANM TLS chain incomplete | Low | Phase 1 | Download via the Windows TLS stack. Verification never disabled | — |
| M-03 | Columbita-Tantalita (AM) repeats qty and value per oxide | Medium | Phase 2 | T8 collapse, tested | — |
| M-04 | Calcário SP 2010–2015: two records per key with no indicator | Low | Phase 2 | Summed (different values) | Could be a duplicate in the source. Not verifiable |
| M-05 | CFEM `FERRO` and `MINÉRIO DE FERRO` (and 4 other pairs) coexist | High | Phase 2 | `substance_map.csv` groups them | Mappings tagged `judgment` (0.58 % of value) need expert review |
| M-06 | CFEM Jul–Nov 2026 incomplete | High | Phase 2 | T7 status, excluded from analysis | 2026 shown as YTD Jan–Jun, provisional |
| M-07 | **Feb 2024 CFEM duplicated export** (32 % of the month) | High | Phase 6 | T13 excludes R$ 296.3 M. 2024 YoY corrected from +12.8 % to +8.4 % | The threshold (5 %) is a judgment. Sensitivity in q13 |
| M-08 | T13 also fires in Aug 2002 | Low | Phase 7 test | Documented. The month is outside the analysis window | — |
| M-09 | ES iron ore intermittent (R$ 9.0 bn 2021, about 0 in 2022–24, R$ 10.8 bn 2025) | High | Phase 6 | Flagged, not corrected (no basis to impute) | ES rank and MG/PA shares in 2021 and 2025 carry a caveat |
| M-10 | CFEM month spine gaps 2002–2003 | Low | Phase 7 test | Partial history excluded | — |
| M-11 | AC absent from AMB Beneficiada | Low | Phase 2 | None (as published) | — |
| M-12 | CFEM has no company names | Medium | Phase 2 | Top 25 legal names from Receita Federal (BrasilAPI) | Legal entity ≠ economic group |
| M-13 | Dataset licence not stated | Low | Phase 1 | Attribution to ANM. Decreto 8.777/2016 cited | Recorded in LIMITATIONS |
