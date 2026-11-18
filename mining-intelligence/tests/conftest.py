"""Shared fixtures. Tests run against the database built by src/run_pipeline.ps1 and the raw files.

Run:  ..\\.venv\\Scripts\\python.exe -m pytest tests -v      (from mining-intelligence/)
"""
from __future__ import annotations

import csv
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "interim" / "mining.duckdb"
RAW = ROOT / "data" / "raw"
BUILD_MONTH = "2026-11-01"   # month of the raw-data snapshot (MANIFEST downloaded_at); nothing may be later


@pytest.fixture(scope="session")
def con():
    if not DB.exists():
        pytest.fail(f"{DB} not found - run src/run_pipeline.ps1 first")
    c = duckdb.connect(str(DB), read_only=True)
    yield c
    c.close()


@pytest.fixture(scope="session")
def manifest() -> list[dict]:
    with (RAW / "MANIFEST.csv").open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _num(v):
    """Monetary and quantity columns are exact DECIMAL in DuckDB; compare them as float in tests."""
    from decimal import Decimal
    return float(v) if isinstance(v, Decimal) else v


def scalar(con, sql: str):
    return _num(con.execute(sql).fetchone()[0])


def row(con, sql: str) -> tuple:
    return tuple(_num(v) for v in con.execute(sql).fetchone())
