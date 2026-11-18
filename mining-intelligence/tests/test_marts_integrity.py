"""Key uniqueness, join integrity, aggregation reconciliation, units and KPI validity in the marts."""
from __future__ import annotations

import pytest

from conftest import row, scalar

GRAINS = {
    "fct_amb_beneficiada": "base_year, uf, amb_substance",
    "fct_amb_bruta": "base_year, uf, amb_substance",
    "fct_cfem_monthly": "period_month, uf, ibge_municipality_code, substance_group, holder_type, holder_key",
    "mart_amb_uf_substance_year": "base_year, uf, substance_group",
    "mart_amb_uf_year": "base_year, uf",
    "mart_amb_substance_year": "base_year, substance_group",
    "mart_amb_national_year": "base_year",
    "mart_cfem_uf_year": "year, uf",
    "mart_cfem_substance_year": "year, substance_group",
    "mart_cfem_municipality_year": "year, ibge_municipality_code",
    "mart_cfem_monthly": "period_month, substance_group",
    "mart_cfem_holder_substance_year": "year, substance_group, holder_key, holder_type",
    "mart_concentration": "year, concentration_type, scope",
    "mart_amb_cfem_uf_substance_year": "year, uf, substance_group",
    "dim_uf": "uf",
    "dim_substance_group": "substance_group",
}


@pytest.mark.parametrize("table,key", GRAINS.items())
def test_grain_is_unique(con, table, key):
    dup = scalar(con, f"SELECT count(*) FROM (SELECT {key}, count(*) n FROM {table} GROUP BY ALL HAVING count(*) > 1)")
    assert dup == 0, f"{table} not unique on ({key})"


def test_amb_value_reconciles_staging_to_marts(con):
    s = scalar(con, "SELECT sum(sale_value_brl) FROM stg_amb_beneficiada")
    for t in ("fct_amb_beneficiada", "mart_amb_uf_year", "mart_amb_substance_year", "mart_amb_uf_substance_year",
              "mart_amb_national_year"):
        assert scalar(con, f"SELECT sum(sale_value_brl) FROM {t}") == pytest.approx(s, rel=1e-12), t


def test_amb_collapse_only_removes_exact_repeats(con):
    """Quantity removed by the collapse rule equals the quantity on repeated (qty, value) rows."""
    stg = scalar(con, "SELECT sum(production_qty) FROM stg_amb_beneficiada")
    fct = scalar(con, "SELECT sum(production_qty) FROM fct_amb_beneficiada")
    removed = scalar(con, """
        SELECT sum(production_qty * (n - 1)) FROM (
          SELECT production_qty, count(*) n FROM stg_amb_beneficiada
          GROUP BY base_year, uf, amb_substance, production_qty, production_unit, sale_qty, sale_value_brl,
                   plant_use_value_brl, transfer_value_brl HAVING count(*) > 1)""")
    assert stg - fct == pytest.approx(removed, rel=1e-9)


def test_cfem_net_equals_gross_minus_excluded(con):
    g, n, x = row(con, "SELECT sum(cfem_brl_gross), sum(cfem_brl), sum(cfem_brl_excluded_duplicates) FROM fct_cfem_monthly")
    assert g == pytest.approx(scalar(con, "SELECT sum(cfem_brl) FROM stg_cfem"), rel=1e-12)
    assert g - x == pytest.approx(n, rel=1e-12)
    assert x == pytest.approx(296_280_241.37, abs=0.01)


def test_cfem_marts_reconcile_to_usable_view(con):
    u = scalar(con, "SELECT sum(cfem_brl) FROM v_cfem_usable")
    for t in ("mart_cfem_uf_year", "mart_cfem_substance_year", "mart_cfem_monthly", "mart_cfem_holder_substance_year"):
        assert scalar(con, f"SELECT sum(cfem_brl) FROM {t}") == pytest.approx(u, rel=1e-12), t


def test_usable_view_excludes_incomplete_and_partial_months(con):
    assert scalar(con, "SELECT count(*) FROM v_cfem_usable WHERE month_status NOT IN ('complete', 'provisional')") == 0
    assert scalar(con, "SELECT max(period_month) FROM v_cfem_usable").isoformat() == "2026-06-01"


def test_integration_join_has_no_fan_out(con):
    """Both sides of the AMB x CFEM FULL JOIN keep their pre-join totals."""
    amb, cfem = row(con, "SELECT sum(amb_sale_value_brl), sum(cfem_brl) FROM mart_amb_cfem_uf_substance_year")
    assert amb == pytest.approx(scalar(con, "SELECT sum(sale_value_brl) FROM fct_amb_beneficiada"), rel=1e-12)
    exp = scalar(con, """SELECT sum(cfem_brl) FROM v_cfem_usable WHERE year BETWEEN 2010 AND 2025 AND uf IS NOT NULL
                         AND substance_group IN (SELECT substance_group FROM dim_substance_group WHERE has_amb_equivalent)""")
    assert cfem == pytest.approx(exp, rel=1e-12)


def test_substance_map_join_integrity(con):
    assert scalar(con, "SELECT count(*) FROM seed_substance_map m ANTI JOIN seed_amb_substance a USING (amb_substance) "
                       "WHERE m.amb_substance IS NOT NULL") == 0
    assert scalar(con, "SELECT count(*) FROM seed_substance_map m JOIN seed_amb_substance a USING (amb_substance) "
                       "WHERE m.substance_group <> a.substance_group") == 0
    assert scalar(con, "SELECT count(*) - count(DISTINCT cfem_substance) FROM seed_substance_map") == 0


def test_unmapped_value_share_small(con):
    share = scalar(con, "SELECT sum(cfem_brl) FILTER (substance_group = 'Other (unmapped)') / sum(cfem_brl) FROM stg_cfem")
    assert share < 0.001


def test_one_unit_per_amb_fact_key(con):
    assert scalar(con, "SELECT max(n_units) FROM fct_amb_beneficiada") == 1


def test_quantity_null_when_units_mixed(con):
    bad = scalar(con, """
        SELECT count(*) FROM mart_amb_substance_year m
        JOIN (SELECT base_year, substance_group FROM fct_amb_beneficiada GROUP BY ALL HAVING count(DISTINCT unit) > 1) x
        USING (base_year, substance_group) WHERE m.production_qty IS NOT NULL""")
    assert bad == 0


def test_shares_sum_to_one(con):
    for t, k in (("mart_amb_uf_year", "base_year"), ("mart_amb_substance_year", "base_year"), ("mart_cfem_uf_year", "year")):
        dev = scalar(con, f"SELECT max(abs(s - 1)) FROM (SELECT sum(share_of_national) s FROM {t} GROUP BY {k})")
        assert dev < 1e-9, t


def test_yoy_never_crosses_a_gap_year(con):
    bad = scalar(con, """
        SELECT count(*) FROM (SELECT *, lag(base_year) OVER (PARTITION BY uf, substance_group ORDER BY base_year) prev
                              FROM mart_amb_uf_substance_year)
        WHERE value_yoy IS NOT NULL AND (prev IS NULL OR prev <> base_year - 1)""")
    assert bad == 0


def test_yoy_matches_manual_calculation(con):
    v24, v25, yoy = row(con, """SELECT max(sale_value_brl) FILTER (base_year = 2024), max(sale_value_brl) FILTER (base_year = 2025),
                                      max(value_yoy) FILTER (base_year = 2025)
                               FROM mart_amb_uf_year WHERE uf = 'MG'""")
    assert yoy == pytest.approx(v25 / v24 - 1, rel=1e-12)


def test_concentration_bounds(con):
    r = con.execute("""SELECT count(*) FILTER (hhi < 0 OR hhi > 10000.05),
                          count(*) FILTER (cr1_pct > cr4_pct + 1e-9 OR cr4_pct > 100.0001),
                          count(*) FILTER (hhi + 0.05 < 10000.0 / n_participants)  -- HHI >= 10000/N
                   FROM mart_concentration""").fetchone()
    assert r == (0, 0, 0)


def test_hhi_recomputed_independently(con):
    """Iron ore 2025 business HHI recomputed from the holder mart."""
    hhi = scalar(con, """SELECT sum(power(100 * cfem_brl / total, 2)) FROM (
                           SELECT cfem_brl, sum(cfem_brl) OVER () AS total FROM mart_cfem_holder_substance_year
                           WHERE year = 2025 AND substance_group = 'Iron ore' AND holder_type = 'PJ' AND cfem_brl > 0)""")
    stored = scalar(con, "SELECT hhi FROM mart_concentration WHERE year = 2025 AND scope = 'Iron ore' "
                         "AND concentration_type LIKE 'business%'")
    assert stored == pytest.approx(hhi, abs=0.1)


def test_cumulative_share_monotonic_and_ends_at_one(con):
    r = con.execute("""SELECT max(abs(last_cum - 1)), count(*) FILTER (NOT monotone) FROM (
                     SELECT year, substance_group, max(cumulative_share) last_cum,
                            bool_and(cumulative_share >= prev - 1e-12 OR prev IS NULL) monotone
                     FROM (SELECT *, lag(cumulative_share) OVER (PARTITION BY year, substance_group ORDER BY rank_in_substance) prev
                           FROM mart_cfem_holder_substance_year) GROUP BY ALL)""").fetchone()
    assert r[0] < 1e-9 and r[1] == 0


def test_company_names_cover_top_holders(con):
    import csv
    from conftest import ROOT
    with (ROOT / "seeds/company_names.csv").open(encoding="utf-8") as fh:
        names = {r["cnpj_root"]: r["legal_name"] for r in csv.DictReader(fh)}
    top10 = [r[0] for r in con.execute("""SELECT holder_key FROM mart_cfem_holder_substance_year WHERE year = 2025 AND holder_type = 'PJ'
                                       GROUP BY 1 ORDER BY sum(cfem_brl) DESC LIMIT 10""").fetchall()]
    missing = [k for k in top10 if not names.get(k)]
    assert not missing, missing
