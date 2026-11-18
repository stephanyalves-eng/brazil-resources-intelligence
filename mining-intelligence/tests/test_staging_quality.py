"""Valid ranges, missing values, duplicates and temporal consistency in staging."""
from __future__ import annotations

from conftest import BUILD_MONTH, scalar


def test_cfem_row_count_preserved(con):
    assert scalar(con, "SELECT count(*) FROM stg_cfem") == 2_434_190


def test_cfem_years_and_months_in_range(con):
    assert scalar(con, "SELECT count(*) FROM stg_cfem WHERE year NOT BETWEEN 2002 AND 2026 OR month NOT BETWEEN 1 AND 12") == 0


def test_no_future_periods(con):
    assert scalar(con, f"SELECT count(*) FROM stg_cfem WHERE period_month > DATE '{BUILD_MONTH}'") == 0
    assert scalar(con, "SELECT max(base_year) FROM stg_amb_beneficiada") <= 2025


def test_cfem_values_parsed_and_positive(con):
    assert scalar(con, "SELECT count(*) FROM stg_cfem WHERE cfem_brl IS NULL OR cfem_brl <= 0") == 0


def test_amb_numeric_fields_parsed(con):
    assert scalar(con, "SELECT count(*) FROM stg_amb_beneficiada WHERE production_qty IS NULL OR sale_value_brl IS NULL") == 0
    assert scalar(con, "SELECT count(*) FROM stg_amb_beneficiada WHERE sale_value_brl < 0 OR production_qty < 0") == 0


def test_amb_year_range(con):
    assert con.execute("SELECT min(base_year), max(base_year) FROM stg_amb_beneficiada").fetchone() == (2010, 2025)


def test_uf_codes_valid(con):
    bad = scalar(con, "SELECT count(*) FROM (SELECT uf FROM stg_cfem UNION SELECT uf FROM stg_amb_beneficiada) "
                      "WHERE uf IS NOT NULL AND uf NOT IN (SELECT uf FROM seed_uf)")
    assert bad == 0


def test_missing_values_within_profiled_limits(con):
    """Missing UF / quantity are known and small; fail if they grow (would indicate a layout change)."""
    r = con.execute("SELECT count(*) FILTER (uf IS NULL), count(*) FILTER (quantity_sold IS NULL), "
                "count(*) FILTER (ibge_municipality_code IS NULL) FROM stg_cfem").fetchone()
    assert r[0] <= 1_628 and r[1] <= 15_990 and r[2] <= 1_628


def test_identical_repeats_flagged_as_profiled(con):
    assert scalar(con, "SELECT count(*) FILTER (is_identical_repeat) FROM stg_cfem") == 143_751


def test_excluded_duplicates_only_in_systematic_months(con):
    """T13 fires in Feb 2024 (systematic export duplicate) and in Aug 2002 (10 lines, 90 % repeats; that month is
    'partial_history' and outside every analysis), and nowhere else."""
    months = con.execute("SELECT DISTINCT period_month FROM stg_cfem WHERE is_excluded_duplicate ORDER BY 1").fetchall()
    assert [str(m[0]) for m in months] == ["2002-08-01", "2024-02-01"]
    assert scalar(con, "SELECT month_status FROM stg_cfem_month_status WHERE period_month = DATE '2002-08-01'") == "partial_history"
    assert scalar(con, "SELECT count(*) FROM stg_cfem WHERE is_excluded_duplicate AND NOT is_identical_repeat") == 0


def test_month_status_partition(con):
    r = dict(con.execute("SELECT month_status, count(*) FROM stg_cfem_month_status GROUP BY 1").fetchall())
    assert r["complete"] == 264 and r["incomplete"] == 5 and r["provisional"] == 6 and r["partial_history"] == 9


def test_month_spine_has_no_gaps_in_analysis_window(con):
    """From 2004 every month exists (2002-2003 is partial history with known gaps)."""
    gaps = scalar(con, """
        SELECT count(*) FROM (SELECT period_month, lag(period_month) OVER (ORDER BY period_month) AS prev
                              FROM stg_cfem_month_status WHERE period_month >= DATE '2004-01-01')
        WHERE prev IS NOT NULL AND date_diff('month', prev, period_month) <> 1""")
    assert gaps == 0
    assert scalar(con, "SELECT count(*) FROM stg_cfem_month_status WHERE period_month >= DATE '2004-01-01'") == 12 * 22 + 11


def test_monthly_mart_is_dense(con):
    n_groups = scalar(con, "SELECT count(DISTINCT substance_group) FROM mart_cfem_monthly")
    n_months = scalar(con, "SELECT count(DISTINCT period_month) FROM mart_cfem_monthly")
    assert scalar(con, "SELECT count(*) FROM mart_cfem_monthly") == n_groups * n_months
    assert n_months == 12 * 22 + 6   # 2004-01 .. 2026-06


def test_holder_key_assignment(con):
    assert scalar(con, "SELECT count(*) FROM stg_cfem WHERE holder_type = 'PJ' AND cnpj IS NOT NULL AND holder_key <> left(cnpj, 8)") == 0
    assert scalar(con, "SELECT count(*) FROM stg_cfem WHERE holder_type = 'PF' AND holder_key <> 'INDIVIDUALS (masked CPF)'") == 0
