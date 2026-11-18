"""One-off Phase 2 check: national monthly gas balance gaps."""
import pandas as pd
from oilgas.config import INTERIM_DIR

b = pd.read_csv(INTERIM_DIR / "profile_gas_balance.csv")
n = b.groupby(["year", "month"])[["gas", "uses", "gap"]].sum()
n["pct"] = n.gap / n.gas * 100
print(n.sort_values("pct").head(4).round(2))
print("months with |gap| > 0.5%:", int((n.pct.abs() > 0.5).sum()), "of", len(n))
