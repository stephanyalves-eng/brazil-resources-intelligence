"""Low-level readers for the raw ANP files. They parse the published layout only; no cleaning.

Published layout (verified 2026-11-18): UTF-8 with BOM, ';' separator, decimal comma,
month as Portuguese abbreviation (JAN..DEZ), UF/region as upper-case full names.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from oilgas.config import RAW_DIR, SOURCES

MONTHS_PT = {m: i for i, m in enumerate(
    ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"], start=1)}


def parse_decimal_comma(s: pd.Series) -> pd.Series:
    """'134835,0003' -> 134835.0003. Thousands separators are not used in these files
    (verified: no value contains '.'), so only the decimal comma is replaced."""
    s = s.astype("string").str.strip()
    if s.str.contains(".", regex=False).any():
        raise ValueError("Unexpected '.' in a decimal-comma column; layout changed.")
    return pd.to_numeric(s.str.replace(",", ".", regex=False), errors="raise")


def read_raw(key: str, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Read one monthly state/location file as published (all columns as text)."""
    _, fname, _, _ = SOURCES[key]
    return pd.read_csv(raw_dir / "ppgn" / fname, sep=";", encoding="utf-8-sig",
                       dtype=str, keep_default_na=False)


def read_tidy(key: str, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Published file -> tidy frame: year, month, region, uf, location, raw_value, value, has_decimals.
    Files without LOCALIZAÇÃO (LGN) get location = 'TOTAL'."""
    df = read_raw(key, raw_dir)
    measure = SOURCES[key][3]
    out = pd.DataFrame({
        "year": df["ANO"].astype(int),
        "month": df["MÊS"].map(MONTHS_PT),
        "region": df["GRANDE REGIÃO"],
        "uf": df["UNIDADE DA FEDERAÇÃO"],
        "location": df["LOCALIZAÇÃO"] if "LOCALIZAÇÃO" in df else "TOTAL",
        "raw_value": df[measure],
    })
    if out["month"].isna().any():
        raise ValueError(f"{key}: unknown month labels {df.loc[out['month'].isna(), 'MÊS'].unique()}")
    out["month"] = out["month"].astype(int)
    out["value"] = parse_decimal_comma(out["raw_value"])
    out["has_decimals"] = out["raw_value"].str.contains(",", regex=False)
    return out


def read_anuario(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)
    df.columns = ["uf", "location", "year", "value"]  # header has a typo in t2-21 ("UNIDDES")
    df["year"] = df["year"].astype(int)
    df["value"] = parse_decimal_comma(df["value"])
    return df
