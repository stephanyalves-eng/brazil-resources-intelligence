# Shared resources

| Path | Content |
|---|---|
| `design-system/SA_DESIGN_SYSTEM_TABLEAU.md` | Stephany Alves Design System tokens (taken verbatim from `C:\Tableau\FAB\FAB Supplier Concentration.html`), mapped to Tableau components and chart rules |
| `design-system/Preferences.tps` | Tableau colour palettes from those tokens. Copy it to `Documents\My Tableau Repository\` |
| `documentation-templates/` | Templates for phase records and dataset evaluations, used for both projects |
| `phase1_profiling/` | The scripts that produced the Phase 1 source evaluation (kept for traceability) |
| `tableau_twb/twb.py` | Dependency-free writer for Tableau workbook XML (2026.x), used by each project's `tableau/build_workbook.py` to generate its `.twb`. The format follows files saved by Tableau Public 2026.3; `smoke_test.py` builds a minimal workbook |
| `render_dictionary.py` | Renders `<project>/tableau/data_dictionary.csv` into `docs/DATA_DICTIONARY.md` |

The two projects do not import code from each other. Their pipelines do not import from `shared/`; only the optional workbook builders (`tableau/build_workbook.py`) use `shared/tableau_twb/`.
