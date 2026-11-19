# Changelog — Mining Intelligence

All dates 2026-11-18 (single build session). Commits are in the repository history.

| Version | Phase | Change |
|---|---|---|
| 0.1.0 | 1 | Source discovery: ANM AMB and CFEM evaluated; AMB Beneficiada (primary) + CFEM Arrecadação (complementary) selected |
| 0.2.0 | 2 | Full profiling (2.43 M CFEM rows) in DuckDB; metadata/file discrepancies documented |
| 0.3.0 | 3–4 | Project scaffold, Python 3.12 venv, `acquire_raw.ps1` with SHA-256 manifest |
| 0.4.0 | 5 | Seeds (UF, AMB substances, substance map); staging, facts, 10 marts (HHI/CR4, Pareto, AMB×CFEM). Fixed: repeat flag (`PARTITION BY COLUMNS(*)` did not expand) |
| 0.5.0 | 6 | 24 analytical queries; company legal names; **rule T13** removes the Feb 2024 duplicate export (R$ 296.3 M); ES iron-ore caveat |
| 0.6.0 | 7 | pytest suite (56). Found: T13 also fires in Aug 2002; 2002–03 month gaps |
| 0.7.0 | 8 | 14 Tableau extracts, data dictionary, data model, export tests (117 total). Fixed: IBGE codes validated by state prefix; UF derived from the code |
| 0.8.0 | 9 | KPI definitions and Tableau build guide in the SA Design System |
| 1.0.0 | 10 | README, data sources, limitations, portfolio kit. A clean rebuild exposed non-deterministic output (float sums, `arg_max` ties); fixed with exact decimals, ordered aggregates and unique ordering (rule T15). 3 builds byte-identical; 117/117 tests |
| 1.1.0 | Tableau build | Tableau workbook built from the guide (`tableau/build_workbook.py` → `.twbx`), all §7 values verified in Tableau Public 2026.3. Fixed: M6 / K18 formula aligned with Q12 (no `match_status` filter) |
| 1.2.0 | Tableau interactivity | Dashboards made interactive: YEAR / SUBSTANCE / STATE filters (All by default) drive every page; clicking a bar, state, heatmap cell or table row sets them (parameter actions). Views that need one substance show iron ore when All. Header with filters and page buttons aligned in the dark band; regular grid layout; worksheet tabs hidden. §7 values unchanged at the defaults |
