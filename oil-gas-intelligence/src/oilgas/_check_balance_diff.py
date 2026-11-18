"""One-off Phase 7 check: which month differs between profiling and features gas-balance counts?"""
import pandas as pd

from oilgas.config import INTERIM_DIR, PROCESSED_DIR

u = pd.read_csv(PROCESSED_DIR / "gas_utilization_monthly.csv", parse_dates=["period_date"])
n = u[(u.level == "national") & u.balance_gap_pct.notna()].copy()
n.index = n.period_date.dt.strftime("%Y-%m")
feat_bad = set(n.index[n.balance_gap_pct.abs() > 0.005])

b = pd.read_csv(INTERIM_DIR / "profile_gas_balance.csv")
p = b.groupby(["year", "month"])[["gas", "gap"]].sum()
p.index = [f"{y}-{m:02d}" for y, m in p.index]
prof_bad = set(p.index[(p.gap / p.gas).abs() > 0.005])

for m in sorted(feat_bad ^ prof_bad):
    print(m, "features gap %:", round(100 * n.loc[m, "balance_gap_pct"], 3), "| profiling gap %:", round(100 * p.loc[m, "gap"] / p.loc[m, "gas"], 3))
    print(b[(b.year == int(m[:4])) & (b.month == int(m[5:]))].query("uses.isna() or gas.isna()", engine="python").to_string(index=False))
