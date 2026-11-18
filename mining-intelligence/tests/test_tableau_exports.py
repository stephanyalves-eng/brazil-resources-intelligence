"""Integrity of the Tableau extracts (tableau/data/*.csv) against the dictionary and the marts."""
from __future__ import annotations

import csv
from collections import defaultdict

import pytest

from conftest import ROOT, scalar

DATA = ROOT / "tableau" / "data"
FILES = sorted(DATA.glob("*.csv"))


def dictionary() -> dict[str, list[str]]:
    d = defaultdict(list)
    with (ROOT / "tableau" / "data_dictionary.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            d[r["table"]].append(r["column"])
    return d


def read(name: str):
    return f"read_csv('{(DATA / name).as_posix()}', header = true, all_varchar = true)"


def test_exports_exist():
    assert len(FILES) == 14


def test_dictionary_covers_every_file_and_column():
    d = dictionary()
    assert set(d) == {f.stem for f in FILES}
    for f in FILES:
        with f.open(encoding="utf-8") as fh:
            header = next(csv.reader(fh))
        assert header == d[f.stem], f.name


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_encoding_and_no_sentinel_strings(path):
    raw = path.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "BOM present"
    text = raw.decode("utf-8")
    for bad in (",nan,", ",NaN,", ",None,", ",inf,", ",-inf,", ",NULL,"):
        assert bad not in text, f"{bad} in {path.name}"


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_size_within_tableau_public_comfort(path):
    assert path.stat().st_size < 15_000_000


@pytest.mark.parametrize("name,mart", [
    ("amb_uf_year.csv", "mart_amb_uf_year"), ("amb_substance_year.csv", "mart_amb_substance_year"),
    ("amb_uf_substance_year.csv", "mart_amb_uf_substance_year"), ("amb_national_year.csv", "mart_amb_national_year"),
    ("cfem_municipality_year.csv", "mart_cfem_municipality_year"), ("cfem_monthly.csv", "mart_cfem_monthly"),
    ("concentration.csv", "mart_concentration"), ("amb_cfem_uf_substance_year.csv", "mart_amb_cfem_uf_substance_year"),
    ("dim_uf.csv", "dim_uf"), ("dim_substance.csv", "dim_substance_group")])
def test_row_counts_match_marts(con, name, mart):
    assert scalar(con, f"SELECT count(*) FROM {read(name)}") == scalar(con, f"SELECT count(*) FROM {mart}")


@pytest.mark.parametrize("name,key", [
    ("amb_uf_year.csv", "year, uf"), ("amb_substance_year.csv", "year, substance_group"),
    ("amb_uf_substance_year.csv", "year, uf, substance_group"), ("amb_price_volume.csv", "year, substance_group"),
    ("cfem_uf_substance_year.csv", "year, uf, substance_group"), ("cfem_municipality_year.csv", "year, ibge_municipality_code"),
    ("cfem_monthly.csv", "period_month, substance_group"), ("cfem_company_substance_year.csv", "year, substance_group, rank"),
    ("concentration.csv", "year, concentration_type, scope"), ("amb_cfem_uf_substance_year.csv", "year, uf, substance_group"),
    ("dim_uf.csv", "uf"), ("dim_substance.csv", "substance_group")])
def test_export_keys_unique(con, name, key):
    assert scalar(con, f"SELECT count(*) FROM (SELECT {key} FROM {read(name)} GROUP BY ALL HAVING count(*) > 1)") == 0


def test_value_totals_reconcile(con):
    amb = scalar(con, "SELECT sum(sale_value_brl) FROM fct_amb_beneficiada")
    for f in ("amb_uf_year.csv", "amb_substance_year.csv", "amb_uf_substance_year.csv", "amb_national_year.csv"):
        assert scalar(con, f"SELECT sum(CAST(sale_value_brl AS DOUBLE)) FROM {read(f)}") == pytest.approx(amb, rel=1e-9), f
    cfem = scalar(con, "SELECT sum(cfem_brl) FROM v_cfem_usable")
    for f in ("cfem_uf_substance_year.csv", "cfem_municipality_year.csv", "cfem_monthly.csv", "cfem_company_substance_year.csv"):
        got = scalar(con, f"SELECT sum(CAST(cfem_brl AS DOUBLE)) FROM {read(f)}")
        if f == "cfem_municipality_year.csv":   # lines without a valid IBGE code cannot be placed on a municipality
            cfem_mun = scalar(con, "SELECT sum(cfem_brl) FROM v_cfem_usable WHERE ibge_municipality_code IS NOT NULL")
            assert got == pytest.approx(cfem_mun, rel=1e-9)
        else:
            assert got == pytest.approx(cfem, rel=1e-9), f


def test_company_table_shares_close_to_one(con):
    dev = scalar(con, f"""SELECT max(abs(s - 1)) FROM (SELECT sum(CAST(share_in_substance AS DOUBLE)) s
                          FROM {read('cfem_company_substance_year.csv')} GROUP BY year, substance_group)""")
    assert dev < 1e-4


def test_identifier_formats_preserved(con):
    assert scalar(con, f"SELECT count(*) FROM {read('cfem_company_substance_year.csv')} "
                       "WHERE holder_type = 'PJ' AND company_key <> 'UNIDENTIFIED' "   # PJ line without a valid CNPJ
                       "AND NOT regexp_full_match(company_key, '[0-9]{8}')") == 0
    assert scalar(con, f"SELECT count(*) FROM {read('cfem_company_substance_year.csv')} WHERE company_key LIKE '0%'") > 0
    assert scalar(con, f"SELECT count(*) FROM {read('cfem_municipality_year.csv')} "
                       "WHERE NOT regexp_full_match(ibge_municipality_code, '[0-9]{7}')") == 0


def test_top_iron_ore_company_named(con):
    name = scalar(con, f"SELECT company_name FROM {read('cfem_company_substance_year.csv')} "
                       "WHERE year = '2025' AND substance_group = 'Iron ore' AND rank = '1'")
    assert name == "VALE S.A."


def test_referential_integrity_with_dimensions(con):
    for f in ("amb_uf_substance_year.csv", "amb_substance_year.csv", "cfem_uf_substance_year.csv", "cfem_monthly.csv",
              "cfem_company_substance_year.csv", "amb_cfem_uf_substance_year.csv", "amb_price_volume.csv"):
        assert scalar(con, f"SELECT count(*) FROM {read(f)} ANTI JOIN {read('dim_substance.csv')} USING (substance_group)") == 0, f
    for f in ("amb_uf_year.csv", "amb_uf_substance_year.csv", "cfem_municipality_year.csv", "amb_cfem_uf_substance_year.csv"):
        assert scalar(con, f"SELECT count(*) FROM {read(f)} ANTI JOIN {read('dim_uf.csv')} USING (uf)") == 0, f
    assert scalar(con, f"SELECT count(*) FROM {read('cfem_uf_substance_year.csv')} "
                       f"WHERE uf <> 'N/A' AND uf NOT IN (SELECT uf FROM {read('dim_uf.csv')})") == 0


def test_no_future_or_incomplete_periods_exported(con):
    assert scalar(con, f"SELECT max(CAST(period_month AS DATE)) FROM {read('cfem_monthly.csv')}").isoformat() == "2026-06-01"
    assert scalar(con, f"SELECT max(CAST(year AS INT)) FROM {read('amb_uf_year.csv')}") == 2025
    assert scalar(con, f"SELECT count(*) FROM {read('cfem_monthly.csv')} WHERE month_status NOT IN ('complete', 'provisional')") == 0


def test_price_volume_effects_add_up(con):
    bad = scalar(con, f"""
        WITH p AS (SELECT substance_group, CAST(year AS INT) y, CAST(sale_value_brl AS DOUBLE) v,
                          CAST(volume_effect_logpts AS DOUBLE) ve, CAST(unit_value_effect_logpts AS DOUBLE) pe
                   FROM {read('amb_price_volume.csv')}),
             l AS (SELECT *, lag(v) OVER (PARTITION BY substance_group ORDER BY y) v0 FROM p)
        SELECT count(*) FROM l WHERE ve IS NOT NULL AND abs(ve + pe - 100 * ln(v / v0)) > 0.01""")
    assert bad == 0
