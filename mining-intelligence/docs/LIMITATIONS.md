# Limitations — Mining

## Measurement
1. **Nominal R$ only.** No inflation adjustment (IPCA was not added), so value growth includes inflation.
2. **AMB value = beneficiated sales**, not total production value. Own use and transfers are reported separately and not added.
3. **CFEM is a royalty, not revenue.** Its rate differs by substance (Lei 13.540/2017), so CFEM shares compare companies only *within* one substance group.
4. **The CFEM-to-AMB ratio is an indicator**, not a measured effective rate: it compares different bases and timings (cash collection vs RAL base year).
5. **Unit values are implied** (value ÷ quantity sold). They are not market prices, and the price/volume split is arithmetic, not causal.

## Coverage
6. AMB is published at **UF level only** (no mine or company). Acre does not appear in AMB Beneficiada.
7. CFEM 2002–2003 is partial; **Jul–Nov 2026 is incomplete and excluded**. 2026 appears only as YTD Jan–Jun (provisional).
8. **No municipal map:** the sources have no coordinates, so municipalities are shown as rankings.

## Entity and mapping
9. **Company = legal entity (CNPJ root), not economic group.** Group-level concentration is at least as high as reported.
10. Names were looked up for the 25 largest payers only; others appear as "CNPJ root …". Individuals (masked CPF) are grouped together.
11. **Substance harmonisation is a manual seed:** 148 CFEM names → 48 groups. Mappings tagged `judgment` (0.58 % of value) need domain review. "Stone – use unspecified" (2.5 %) has no AMB equivalent.

## Data quality (see [DATA_QUALITY_REPORT.md](DATA_QUALITY_REPORT.md))
12. **Feb 2024 CFEM duplicates** were removed by a threshold rule (> 5 % of a month's value). The threshold is a judgment; the gross figures remain available.
13. **ES iron ore is intermittent** (2021 and 2025 only). It is flagged but not corrected, so ES's 2025 ranking should be read with care.
14. Identical CFEM lines in other months are kept (≤ 0.16 % of any year's value), because a genuine repeated payment cannot be ruled out.
15. The dataset licence is not stated explicitly by ANM.

## Reproducibility
16. ANM updates files daily in place. Results are tied to the snapshot in `data/raw/MANIFEST.csv`, and tests pinned to profiled counts fail by design on a new snapshot.
17. The dashboard is built and checked locally but not published. Two views are simplified: the state ranking shows the top 15 states and the state × substance heatmap shows the 12 largest groups of 2025.
