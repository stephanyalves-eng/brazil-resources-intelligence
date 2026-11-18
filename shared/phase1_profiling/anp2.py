import sys
import pandas as pd

D = sys.argv[1]
M = {m: i for i, m in enumerate(["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"], 1)}
def load(f, col):
    df = pd.read_csv(f"{D}/{f}", sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)
    df["v"] = pd.to_numeric(df[col].str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="coerce")
    df["m"] = df["MÊS"].map(M); df["ANO"] = df["ANO"].astype(int)
    return df
oil = load("producao-petroleo-m3.csv", "PRODUÇÃO")
print("oil NaN:", int(oil.v.isna().sum()), "neg:", int((oil.v < 0).sum()), "zero rows:", int((oil.v == 0).sum()))
print("oil 2026 by month (m3):", oil[oil.ANO == 2026].groupby("m").v.sum().to_dict())
print("oil 2025 by month (m3):", oil[oil.ANO == 2025].groupby("m").v.sum().round(0).to_dict())
print("oil annual total 2015-2025 (million m3):", (oil[oil.ANO >= 2015].groupby("ANO").v.sum() / 1e6).round(2).to_dict())
print("oil UF list:", sorted(oil["UNIDADE DA FEDERAÇÃO"].unique()))
g = load("producao-gas-natural-1000m3.csv", "PRODUÇÃO")
print("gas 2026 by month (1000 m3):", g[g.ANO == 2026].groupby("m").v.sum().round(0).to_dict())
k = ["ANO", "m", "UNIDADE DA FEDERAÇÃO", "LOCALIZAÇÃO"]
parts = {"reinj": ("reinjecao-gn-1000m3", "REINJETADO"), "queima": ("queima-e-perda-gn-1000m3.csv", "QUEIMADO"),
         "consumo": ("consumo-proprio-gn1000m3.csv", "CONSUMO"), "disp": ("gn-disponivel-1000m3.csv", "DISPONÍVEL")}
bal = g[g.ANO >= 2000][k + ["v"]].rename(columns={"v": "prod"})
for n, (f, c) in parts.items():
    bal = bal.merge(load(f, c)[k + ["v"]].rename(columns={"v": n}), on=k, how="outer")
print("balance rows:", len(bal), "rows missing a component:", int(bal.isna().any(axis=1).sum()))
b = bal.dropna()
b = b[b["prod"] > 0]
b["gap_pct"] = (b["prod"] - b[["reinj", "queima", "consumo", "disp"]].sum(axis=1)) / b["prod"] * 100
print("balance gap % (prod - sum of uses)/prod: describe", b.gap_pct.describe().round(3).to_dict())
nat = bal.groupby("ANO")[["prod", "reinj", "queima", "consumo", "disp"]].sum()
print("national annual (bn m3) 2021-2025:\n", (nat.loc[2021:2025] / 1e6).round(2))
