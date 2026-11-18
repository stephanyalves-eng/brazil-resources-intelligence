# Test Report — Mining Intelligence

**Run:** 2026-11-18 16:05 (UTC−3) · Python 3.12.10 · pytest 9.2.0 · duckdb 2.0.0 · Windows 11
**Command:** `..\.venv\Scripts\python.exe -m pytest tests -v` (from `mining-intelligence/`, after `src\run_pipeline.ps1`)
**Evidence:** `tests/results/pytest_output.txt`, `tests/results/junit.xml`

## Result

| Module | Tests | Passed | Failed |
|---|---|---|---|
| `test_raw_and_schema.py` | 9 | 9 | 0 |
| `test_staging_quality.py` | 14 | 14 | 0 |
| `test_marts_integrity.py` | 33 | 33 | 0 |
| **Total** | **56** | **56** | **0** |

Every test was executed. None was skipped or marked xfail.

## Coverage by requirement

| Requirement (master prompt §5) | Tests |
|---|---|
| File integrity | `test_raw_file_matches_manifest` ×5 (size and SHA-256 against MANIFEST), `test_manifest_lists_all_required_files` |
| Expected schemas | `test_raw_header` ×2 (exact column lists), `test_staging_types` |
| Types and valid ranges | `test_cfem_years_and_months_in_range`, `test_cfem_values_parsed_and_positive`, `test_amb_numeric_fields_parsed`, `test_amb_year_range`, `test_uf_codes_valid` |
| Duplicates | `test_identical_repeats_flagged_as_profiled`, `test_excluded_duplicates_only_in_systematic_months` |
| Missing values | `test_missing_values_within_profiled_limits` |
| Key uniqueness | `test_grain_is_unique` ×16 (every fact, mart and dimension at its documented grain) |
| Join integrity | `test_substance_map_join_integrity`, `test_integration_join_has_no_fan_out`, `test_unmapped_value_share_small` |
| Aggregation reconciliation | `test_amb_value_reconciles_staging_to_marts`, `test_amb_collapse_only_removes_exact_repeats`, `test_cfem_net_equals_gross_minus_excluded`, `test_cfem_marts_reconcile_to_usable_view` |
| Unit consistency | `test_one_unit_per_amb_fact_key`, `test_quantity_null_when_units_mixed` |
| Temporal consistency | `test_month_status_partition`, `test_month_spine_has_no_gaps_in_analysis_window`, `test_monthly_mart_is_dense`, `test_usable_view_excludes_incomplete_and_partial_months`, `test_yoy_never_crosses_a_gap_year` |
| No future periods | `test_no_future_periods` |
| KPI correctness | `test_yoy_matches_manual_calculation`, `test_shares_sum_to_one`, `test_concentration_bounds` (0 ≤ HHI ≤ 10,000, HHI ≥ 10,000/N, CR1 ≤ CR4 ≤ 100), `test_hhi_recomputed_independently`, `test_cumulative_share_monotonic_and_ends_at_one`, `test_holder_key_assignment`, `test_company_names_cover_top_holders` |
| Exported files | **Not covered yet.** The Tableau exports are produced in Phase 8, and their tests will be added and run then |

## Failures found while building the suite, and what was done

| # | First result | Diagnosis | Action |
|---|---|---|---|
| 1 | 44 failed | Test-harness bug: DuckDB 2.0 removed `Relation.fetchone()` | Tests switched to `con.execute()`. No data issue |
| 2 | `test_hhi_recomputed_independently` binder error | A window function nested inside an aggregate, which is invalid SQL | Rewritten with a subquery |
| 3 | `test_excluded_duplicates_only_in_systematic_months` | **Real finding:** rule T13 also fires for Aug 2002 (10 lines, 90 % repeats). The docs had said "only Feb 2024" | Rule kept (the month is `partial_history` and excluded from every analysis). Test and ANALYSIS_FINDINGS DQ1 corrected |
| 4 | `test_month_spine_has_no_gaps` | **Real finding:** the CFEM month spine has gaps in 2002–2003 | Test scoped to the analysis window (from 2004), plus a new test that the monthly mart is dense (270 months × groups) |

## Remaining constraints
- Tests run against the built `mining.duckdb`. They do not rebuild it, so run the pipeline first.
- Thresholds that encode profiled counts (e.g. 143,751 repeats, ≤ 1,628 missing UFs) **will fail by design** when ANM republishes the files. That is the intended signal to re-profile.
- Mapping rows tagged `judgment` are checked for referential integrity only, not for domain correctness.
