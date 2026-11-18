# Test Report — Oil & Gas Intelligence

**Run:** 2026-11-18 16:05 (UTC−3) · Python 3.12.10 · pytest 9.2.0 · pandas 3.1.1 · numpy 2.5.5 · Windows 11
**Command:** `..\.venv\Scripts\python.exe -m pytest tests -v` (from `oil-gas-intelligence/`, after `python -m oilgas.pipeline`)
**Evidence:** `tests/results/pytest_output.txt`, `tests/results/junit.xml`

## Result

| Module | Tests | Passed | Failed |
|---|---|---|---|
| `test_units.py` (synthetic data, no files) | 10 | 10 | 0 |
| `test_data_quality.py` (raw files and pipeline outputs) | 58 | 58 | 0 |
| **Total** | **68** | **68** | **0** |

Every test was executed. None was skipped or marked xfail.

## Coverage by requirement

| Requirement (master prompt §5) | Tests |
|---|---|
| File integrity | `test_raw_file_matches_manifest` ×15 (size and SHA-256 of every raw file) |
| Expected schemas | `test_raw_schema` ×7 |
| Types and valid ranges | `test_raw_values_parse_and_nonnegative_except_available` ×7, `test_parse_decimal_comma`, `..._rejects_thousand_separators`, `test_utilization_rates_valid` |
| Duplicates and key uniqueness | `test_clean_keys_unique` |
| Missing vs zero | `test_not_reported_is_nan_never_zero` (183 rows), `test_placeholder_zeros_removed`, `test_reported_rows_equal_raw_minus_cutoff` ×7 |
| Impossible values | `test_negative_values_only_flagged_available` (681 rows, all flagged), `test_no_infinite_values` |
| Unit consistency | `test_units_consistent`, `test_oil_and_gas_never_summed`, `test_daily_average_uses_real_month_length` |
| Temporal consistency | `test_grid_dense_per_entity` ×7, `test_days_in_month` (leap years), `test_dense_grid_assertion` |
| No future periods | `test_no_future_periods` |
| Aggregation reconciliation | `test_national_equals_sum_of_ufs` (national = Σ UF = Σ location), `test_shares_between_zero_and_one_and_sum_to_one`, `test_annual_totals_reconcile_with_anuario` (≤ 0.05 % every year 2016–2025), `test_gas_balance_closes_nationally` |
| Feature guard rails | `test_time_features_guard_first_observations`, `test_mom_nan_after_zero_and_missing`, `test_safe_ratio_zero_and_missing_denominator`, `test_rolling_daily_average_is_volume_weighted`, `test_mom_and_yoy_match_manual` |
| Statistical methods | `test_robust_z_flags_planted_outlier`, `test_segmentation_recovers_known_break` |
| Exported files | **Not covered yet.** Tableau exports are produced in Phase 8, and their tests will be added and run then |

## Failures found while building the suite, and what was done

| # | First result | Diagnosis | Action |
|---|---|---|---|
| 1 | `test_gas_balance_closes_nationally`: 86 % within 0.5 % | Test bug: 1997–1999 rows have production but no use flows (the files start in 2000), and their gap is correctly NaN | Test restricted to months with every flow, plus an assertion that the pre-2000 gaps are NaN, not a fake 100 % |
| 2 | Same test: 307 months within 0.5 % vs 308 expected | **Real finding:** profiling (Phase 2) dropped UF-months with an unpublished flow. The pipeline sums each flow nationally, so **Dec 2024** closes at −0.503 % (several UFs left reinjection or own use unpublished) | 307 is the correct count. DATA_PROFILE corrected. Diagnostic script kept: `src/oilgas/_check_balance_diff.py` |

## Remaining constraints
- Data tests read the pipeline outputs, so run `python -m oilgas.pipeline` first.
- Counts pinned to the 2026-11-18 snapshot (183 not-reported rows, 681 negative rows, 307 months) will fail by design after an ANP republication. That is the intended prompt to re-profile.
