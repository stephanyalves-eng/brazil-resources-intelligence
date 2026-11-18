# Shared resources

| Path | Content |
|---|---|
| `design-system/SA_DESIGN_SYSTEM_TABLEAU.md` | Stephany Alves Design System tokens (taken verbatim from `C:\Tableau\FAB\FAB Supplier Concentration.html`), mapped to Tableau components and chart rules |
| `design-system/Preferences.tps` | Tableau colour palettes from those tokens. Copy it to `Documents\My Tableau Repository\` |
| `documentation-templates/` | Templates for phase records and dataset evaluations, used for both projects |
| `phase1_profiling/` | The scripts that produced the Phase 1 source evaluation (kept for traceability) |
| `render_dictionary.py` | Renders `<project>/tableau/data_dictionary.csv` into `docs/DATA_DICTIONARY.md` |

The two projects do not import code from each other or from `shared/`. They stay independent by design.
