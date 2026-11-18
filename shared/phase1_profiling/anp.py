import sys, io
import pandas as pd

D = sys.argv[1]
files = ["producao-petroleo-m3.csv", "producao-lgn-m3.csv", "producao-gas-natural-1000m3.csv", "reinjecao-gn-1000m3",
         "queima-e-perda-gn-1000m3.csv", "consumo-proprio-gn1000m3.csv", "gn-disponivel-1000m3.csv"]
for f in files:
    raw = open(f"{D}/{f}", "rb").read()
    for enc in ("utf-8-sig", "latin-1"):
        try:
            txt = raw.decode(enc); break
        except UnicodeDecodeError:
            pass
    first = txt.splitlines()[0]
    sep = max([",", ";", "\t"], key=first.count)
    df = pd.read_csv(io.StringIO(txt), sep=sep, dtype=str, keep_default_na=False)
    print(f"\n== {f} enc={enc} sep={sep!r} rows={len(df)} cols={df.shape[1]} fullrow_dups={int(df.duplicated().sum())}")
    for c in df.columns:
        s = df[c]
        print(f"  {c!r}: blank%={(s.str.strip()=='').mean()*100:.1f} distinct={s.nunique()} ex={s.unique()[:6].tolist()}")
    dims = [c for c in df.columns if c.lower() not in ("produção", "producao") and not c.lower().startswith(("produ", "reinj", "queim", "consum", "dispon", "volume"))]
    numc = df.columns[-1]
    print("  candidate key cols:", dims, "dup on key:", int(df.duplicated(dims).sum()))
    if "ANO" in [c.upper() for c in df.columns]:
        ac = [c for c in df.columns if c.upper() == "ANO"][0]
        print("  years:", df[ac].min(), "-", df[ac].max(), "rows/yr last 3:", df[ac].value_counts().sort_index().tail(3).to_dict())
