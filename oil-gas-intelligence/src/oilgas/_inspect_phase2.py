"""One-off Phase 2 inspection of profiling outputs (kept for traceability)."""
import pandas as pd
from oilgas.config import INTERIM_DIR

rec = pd.read_csv(INTERIM_DIR / "profile_anuario_reconciliation.csv")
scale = {"oil": 1000 / 6.2898, "gas": 1000, "reinjection": 1000, "flaring": 1000}
rec["dev_pct"] = (rec.ratio / rec.file.map(scale) - 1) * 100
m = rec.dropna(subset=["ratio"])
print("matched rows with |dev| > 0.5%:\n", m[m.dev_pct.abs() > 0.5][["file", "uf", "location", "year", "value_anuario", "value_monthly", "dev_pct"]].round(3).to_string(index=False))
print("\nunmatched sample:\n", rec[rec.ratio.isna()].groupby(["file"]).apply(lambda d: d[["uf", "location", "year", "value_anuario", "value_monthly"]].head(6), include_groups=False).to_string())
nat = rec.groupby(["file", "year"])[["value_anuario", "value_monthly"]].sum()
nat["dev_pct"] = (nat.value_monthly / nat.value_anuario / nat.index.get_level_values(0).map(scale) - 1) * 100
print("\nnational annual deviation % (monthly vs Anuário):\n", nat.dev_pct.unstack(0).round(3).to_string())

bal = pd.read_csv(INTERIM_DIR / "profile_gas_balance.csv")
neg = bal[bal.available < 0]
print("\nnegative available: rows", len(neg), "| by uf/location:", neg.groupby(["uf", "location"]).size().to_dict())
print("national monthly balance gap % describe:", (bal.groupby(["year", "month"]).gap.sum() / bal.groupby(["year", "month"]).gas.sum() * 100).describe().round(4).to_dict())
