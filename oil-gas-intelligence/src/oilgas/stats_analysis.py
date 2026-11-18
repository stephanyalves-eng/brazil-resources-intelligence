"""Phase 6 - Statistical analysis: anomalies, volatility regimes, structural breaks.

All methods are deliberately simple and interpretable:
  * Anomalies  - robust z-score of the month-on-month change of the daily average,
                 z = 0.6745 * (x - median) / MAD (Iglewicz & Hoaglin); |z| > 3.5 flags a month.
                 A second, local view: z-score vs the previous 12 months (feature from Phase 5).
                 These are STATISTICAL anomalies. They are not confirmed operational incidents.
  * Volatility - rolling 12-month std of daily_avg_mom, summarised by era.
  * Breaks     - optimal piecewise-linear segmentation of ln(monthly daily average) by dynamic
                 programming (exact, O(n^2 K)), min segment 36 months, K <= 10 chosen by BIC.
                 Each segment's slope is converted to an annual growth rate. The *unsmoothed*
                 series is used on purpose: on the 12-month rolling average (autocorrelated by
                 construction) BIC kept adding breaks until the minimum-length limit bound
                 (robustness check in _check_breaks.py), i.e. it overfits.

No forecasting model is fitted: the brief allows one only with a baseline and out-of-sample
validation, and none of the business questions here needs a forecast.

CLI:  python -m oilgas.stats_analysis
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from oilgas.config import PROCESSED_DIR

OUT = PROCESSED_DIR / "analysis"
ROBUST_Z = 3.5


def load() -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / "features_production_monthly.csv", parse_dates=["period_date"])


def robust_z(x: pd.Series) -> pd.Series:
    med = x.median()
    mad = (x - med).abs().median()
    return 0.6745 * (x - med) / mad if mad > 0 else pd.Series(np.nan, index=x.index)


def anomalies(f: pd.DataFrame) -> pd.DataFrame:
    rows = []
    scopes = [("national", "All", "All"), ("location", "All", "Offshore"), ("location", "All", "Onshore")]
    for series in ("oil", "gas"):
        for level, uf, loc in scopes:
            g = f[(f.level == level) & (f.series == series) & (f.uf == uf) & (f.location == loc)].sort_values("period_date")
            z = robust_z(g.daily_avg_mom.dropna())
            g = g.assign(robust_z_mom=z)
            flag = g[(g.robust_z_mom.abs() > ROBUST_Z)]
            for _, r in flag.iterrows():
                rows.append({"series": series, "level": level, "location": loc, "period": r.period_date.strftime("%Y-%m"),
                             "daily_avg": r.daily_avg, "daily_avg_mom": r.daily_avg_mom, "robust_z_mom": r.robust_z_mom,
                             "zscore_vs_prior_12m": r.zscore_vs_prior_12m,
                             "direction": "drop" if r.daily_avg_mom < 0 else "rise",
                             "classification": "statistical anomaly (not verified as an operational incident)"})
    return pd.DataFrame(rows).sort_values(["series", "level", "location", "period"])


def volatility_regimes(f: pd.DataFrame) -> pd.DataFrame:
    eras = [(1998, 2009, "1998-2009"), (2010, 2019, "2010-2019"), (2020, 2026, "2020-2026")]
    rows = []
    for series in ("oil", "gas"):
        for loc in ("All", "Offshore", "Onshore"):
            level = "national" if loc == "All" else "location"
            g = f[(f.level == level) & (f.series == series) & (f.location == loc)]
            for y0, y1, lbl in eras:
                w = g[(g.year >= y0) & (g.year <= y1)].daily_avg_mom.dropna()
                rows.append({"series": series, "location": loc, "era": lbl, "n_months": len(w),
                             "std_mom": w.std(), "mean_abs_mom": w.abs().mean(),
                             "share_months_abs_mom_gt_5pct": (w.abs() > 0.05).mean()})
    return pd.DataFrame(rows)


def _segment_sse(y: np.ndarray) -> np.ndarray:
    """SSE of the OLS line fitted to y[i:j] for all i<j, via cumulative sums (exact)."""
    n = len(y)
    t = np.arange(n, dtype=float)
    S = lambda a: np.concatenate([[0.0], np.cumsum(a)])
    s1, st, stt, sy, sty, syy = S(np.ones(n)), S(t), S(t * t), S(y), S(t * y), S(y * y)
    sse = np.full((n + 1, n + 1), np.inf)
    for i in range(n):
        j = np.arange(i + 2, n + 1)
        m = s1[j] - s1[i]; a = st[j] - st[i]; b = stt[j] - stt[i]
        c = sy[j] - sy[i]; d = sty[j] - sty[i]; e = syy[j] - syy[i]
        var_t = b - a * a / m
        cov = d - a * c / m
        with np.errstate(divide="ignore", invalid="ignore"):
            sse[i, j] = (e - c * c / m) - np.where(var_t > 0, cov * cov / var_t, 0.0)
    return np.maximum(sse, 0)


def segment(y: np.ndarray, k_max: int = 10, min_len: int = 36) -> tuple[list[tuple[int, int]], list[tuple[int, float]]]:
    """Returns (segments of the BIC-best K, [(K, BIC), ...])."""
    n = len(y)
    sse = _segment_sse(y)
    idx = np.arange(n + 1)
    sse[(idx[None, :] - idx[:, None]) < min_len] = np.inf
    best_bic, best, bics = np.inf, None, []
    cost = {1: sse[0].copy()}
    back = {}
    for k in range(1, k_max + 1):
        if k > 1:
            cost[k] = np.full(n + 1, np.inf)
            back[k] = np.zeros(n + 1, dtype=int)
            for j in range(n + 1):
                cand = cost[k - 1][:j] + sse[:j, j]
                if len(cand):
                    i = int(np.argmin(cand)); cost[k][j] = cand[i]; back[k][j] = i
        total = cost[k][n]
        if not np.isfinite(total):
            break
        p = 3 * k - 1                                    # 2 params per segment + (k-1) break locations
        bic = n * np.log(total / n) + p * np.log(n)
        bics.append((k, float(bic)))
        if bic < best_bic:
            bounds, j = [], n
            for kk in range(k, 1, -1):
                i = back[kk][j]; bounds.append((i, j)); j = i
            bounds.append((0, j))
            best_bic, best = bic, bounds[::-1]
    return best, bics


def structural_breaks(f: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, bic_rows = [], []
    for series in ("oil", "gas"):
        g = f[(f.level == "national") & (f.series == series)].sort_values("period_date")
        g = g.dropna(subset=["daily_avg"]).reset_index(drop=True)
        y = np.log(g.daily_avg.values)
        segs, bics = segment(y)
        best = min(b for _, b in bics)
        bic_rows += [{"series": series, "k_segments": k, "bic": b, "delta_vs_best": b - best} for k, b in bics]
        for i, j in segs:
            t = np.arange(i, j)
            slope = np.polyfit(t, y[i:j], 1)[0]
            rows.append({"series": series, "start": g.period_date[i].strftime("%Y-%m"),
                         "end": g.period_date[j - 1].strftime("%Y-%m"), "n_months": j - i,
                         "annualised_growth": np.exp(slope * 12) - 1,
                         "mean_daily_avg": g.daily_avg[i:j].mean(), "metric": "ln(monthly daily average)"})
    return pd.DataFrame(rows), pd.DataFrame(bic_rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    f = load()
    an, vol = anomalies(f), volatility_regimes(f)
    br, bic = structural_breaks(f)
    an.to_csv(OUT / "stats_anomalies.csv", index=False)
    vol.to_csv(OUT / "stats_volatility_regimes.csv", index=False)
    br.to_csv(OUT / "stats_structural_breaks.csv", index=False)
    bic.to_csv(OUT / "stats_structural_breaks_bic.csv", index=False)
    with pd.option_context("display.width", 220, "display.max_columns", 20, "display.float_format", "{:,.4f}".format):
        print("== anomalies (|robust z| > 3.5 on MoM of daily average)\n",
              an[an.level == "national"].drop(columns="classification").to_string(index=False))
        print("\n   counts by scope:\n", an.groupby(["series", "level", "location"]).size().to_string())
        print("\n== volatility regimes\n", vol.to_string(index=False))
        print("\n== structural breaks\n", br.to_string(index=False))
        print("\n== BIC by K\n", bic.pivot_table(index="k_segments", columns="series", values="delta_vs_best").round(1).to_string())


if __name__ == "__main__":
    main()
