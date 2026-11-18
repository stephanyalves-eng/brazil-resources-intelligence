import sys, io, zipfile, re
import pandas as pd

D = sys.argv[1]
rd = lambda f: pd.read_csv(f"{D}/{f}", encoding="latin-1", dtype=str, keep_default_na=False)
num = lambda s: pd.to_numeric(s.str.replace(",", ".", regex=False).replace({".": "0"}), errors="coerce")

b = rd("Producao_Bruta.csv")
print("BRUTA years:", b["Ano base"].value_counts().sort_index().to_dict())
k = ["Ano base", "UF", "Substância Mineral"]
print("BRUTA key (ano,uf,subst) dup:", int(b.duplicated(k).sum()))
v = num(b["Valor Venda (R$)"]); print("BRUTA valor venda NaN:", int(v.isna().sum()), "zero%:", round((v == 0).mean() * 100, 1))
print("BRUTA total valor venda by year (R$ bn):", (v.groupby(b["Ano base"]).sum() / 1e9).round(2).to_dict())

e = rd("Producao_Beneficiada.csv")
print("BENEF key dup:", int(e.duplicated(k).sum()))
print("BENEF units by subst sample:", e.groupby("Substância Mineral")["Unidade de Medida - Produção"].unique().head(60).to_dict())
ve = num(e["Valor Venda (R$)"]); print("BENEF total valor venda by year (R$ bn):", (ve.groupby(e["Ano base"]).sum() / 1e9).round(2).to_dict())
print("BENEF top subst value 2024:", (ve[e["Ano base"] == "2024"].groupby(e["Substância Mineral"]).sum() / 1e9).sort_values(ascending=False).head(8).round(2).to_dict())

c = pd.read_csv(f"{D}/CFEM_2022_2026_head.csv", encoding="latin-1", dtype=str, keep_default_na=False, on_bad_lines="skip", nrows=22000)
print("CFEM UF values:", sorted(c["UF"].unique()))
print("CFEM PJ id examples:", c.loc[c["Tipo_PF_PJ"] == "PJ", "CPF_CNPJ"].head(5).tolist())
print("CFEM PJ share rows:", round((c["Tipo_PF_PJ"] == "PJ").mean() * 100, 1))
print("CFEM units:", c["UnidadeDeMedida"].str.strip().value_counts().to_dict())
print("CFEM negative ValorRecolhido:", int((num(c["ValorRecolhido"]) < 0).sum()))

for m in ("metadados-amb.ods", "metadados-cfem.ods"):
    x = zipfile.ZipFile(f"{D}/{m}").read("content.xml").decode("utf-8")
    rows = re.findall(r"<table:table-row[^>]*>(.*?)</table:table-row>", x, re.S)
    print("==", m)
    for r in rows:
        cells = [re.sub(r"<[^>]+>", "", t).strip() for t in re.findall(r"<table:table-cell[^>]*>(.*?)</table:table-cell>", r, re.S)]
        cells = [t for t in cells if t]
        if cells:
            print(" | ".join(cells)[:300])
