"""Render a project's tableau/data_dictionary.csv into docs/DATA_DICTIONARY.md (single source of truth).

CLI:  python shared/render_dictionary.py mining-intelligence
      python shared/render_dictionary.py oil-gas-intelligence
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(project: str) -> None:
    p = ROOT / project
    rows = list(csv.DictReader((p / "tableau" / "data_dictionary.csv").open(encoding="utf-8")))
    by_table = defaultdict(list)
    for r in rows:
        by_table[r["table"]].append(r)
    out = [f"# Data Dictionary — {project}", "",
           "Generated from `tableau/data_dictionary.csv` by `shared/render_dictionary.py`; do not edit by hand.",
           "Every exported column is listed (enforced by `tests/test_tableau_exports.py`). Files: `tableau/data/<table>.csv`.", ""]
    for t, cols in by_table.items():
        f = p / "tableau" / "data" / f"{t}.csv"
        n = sum(1 for _ in f.open(encoding="utf-8")) - 1 if f.exists() else "?"
        out += [f"## `{t}` — {n:,} rows" if isinstance(n, int) else f"## `{t}`", "",
                "| Column | Tableau type | Unit | Description |", "|---|---|---|---|"]
        out += [f"| `{c['column']}` | {c['tableau_type']} | {c['unit']} | {c['description']} |" for c in cols]
        out.append("")
    (p / "docs" / "DATA_DICTIONARY.md").write_text("\n".join(out), encoding="utf-8")
    print(f"{project}: {len(rows)} columns in {len(by_table)} tables")


if __name__ == "__main__":
    main(sys.argv[1])
