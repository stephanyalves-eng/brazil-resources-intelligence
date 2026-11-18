"""Shared fixtures. Unit tests use synthetic data; data tests use the outputs of `python -m oilgas.pipeline`.

Run:  ..\\.venv\\Scripts\\python.exe -m pytest tests -v      (from oil-gas-intelligence/)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from oilgas.config import INTERIM_DIR, PROCESSED_DIR  # noqa: E402

BUILD_MONTH = pd.Timestamp("2026-11-01")  # month of the raw snapshot; no period may be later


def _need(path: Path) -> Path:
    if not path.exists():
        pytest.fail(f"{path} missing - run `python -m oilgas.pipeline` first")
    return path


@pytest.fixture(scope="session")
def long_clean() -> pd.DataFrame:
    return pd.read_csv(_need(INTERIM_DIR / "ppgn_long_clean.csv"), parse_dates=["period_date"])


@pytest.fixture(scope="session")
def features() -> pd.DataFrame:
    return pd.read_csv(_need(PROCESSED_DIR / "features_production_monthly.csv"), parse_dates=["period_date"])


@pytest.fixture(scope="session")
def utilization() -> pd.DataFrame:
    return pd.read_csv(_need(PROCESSED_DIR / "gas_utilization_monthly.csv"), parse_dates=["period_date"])
