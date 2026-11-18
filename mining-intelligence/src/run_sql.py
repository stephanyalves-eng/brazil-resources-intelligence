"""Execute DuckDB SQL scripts in order and print every result set.

Statements are separated by ';' at end of line. A comment line '-- name: <label>' before a
statement labels its output. Paths in SQL are relative to the project root (cwd is set there).

CLI:  python src/run_sql.py sql/00_profile_raw.sql [--db data/interim/mining.duckdb] [--out data/interim/profile]
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def split_statements(sql: str) -> list[tuple[str, str]]:
    out, label, buf = [], "", []
    for line in sql.splitlines():
        m = re.match(r"\s*--\s*name:\s*(.+)", line)
        if m:
            label = m.group(1).strip()
            continue
        if not buf and (not line.strip() or line.lstrip().startswith("--")):
            continue  # comments/blank lines between statements
        buf.append(line)
        if line.rstrip().endswith(";"):
            stmt = "\n".join(buf).strip()
            if re.sub(r"--.*", "", stmt).strip(" ;\n"):
                out.append((label, stmt))
            label, buf = "", []
    return out


def run(paths: list[Path], db: str, out_dir: Path | None) -> None:
    os.chdir(ROOT)
    con = duckdb.connect(db)
    for p in paths:
        print(f"\n######## {p}")
        for label, stmt in split_statements(p.read_text(encoding="utf-8")):
            rel = con.sql(stmt)
            if rel is None or not label:
                continue  # DDL and unlabelled statements produce no report
            df = rel.df()
            print(f"\n-- {label or stmt.splitlines()[0][:80]}  [{len(df)} rows]")
            print(df.head(60).to_string(index=False, max_colwidth=60))
            if out_dir and label:
                out_dir.mkdir(parents=True, exist_ok=True)
                df.to_csv(out_dir / f"{label}.csv", index=False)
    con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("sql", nargs="+", type=Path)
    ap.add_argument("--db", default=":memory:")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    run(a.sql, a.db, a.out)
