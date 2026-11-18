"""One-off Phase 6 robustness check for the segmentation: does the K cap bind, smoothed vs raw input?"""
import numpy as np
import pandas as pd

from oilgas.stats_analysis import _segment_sse, load

f = load()
for series in ("oil", "gas"):
    g = f[(f.level == "national") & (f.series == series)].sort_values("period_date")
    for label, col in (("rolling12", "rolling_12m_daily_avg"), ("raw monthly", "daily_avg")):
        h = g.dropna(subset=[col]).reset_index(drop=True)
        y = np.log(h[col].values)
        n = len(y)
        sse = _segment_sse(y)
        idx = np.arange(n + 1)
        sse[(idx[None, :] - idx[:, None]) < 36] = np.inf
        cost = sse[0].copy()
        bics = []
        for k in range(1, 11):
            if k > 1:
                new = np.full(n + 1, np.inf)
                for j in range(n + 1):
                    c = cost[:j] + sse[:j, j]
                    if len(c):
                        new[j] = c.min()
                cost = new
            if not np.isfinite(cost[n]):
                break
            bics.append((k, round(n * np.log(cost[n] / n) + (3 * k - 1) * np.log(n), 1)))
        best = min(bics, key=lambda b: b[1])
        print(series, label, "best K =", best[0], "| BIC by K:", bics)
