"""Quick profiler for candidate CSVs. Usage: python -I profile.py <file> [nrows_cap] [--partial]"""
import sys, io
import pandas as pd

path = sys.argv[1]
partial = "--partial" in sys.argv
raw = open(path, "rb").read()
enc = None
for e in ("utf-8-sig", "utf-8", "latin-1"):
    try:
        txt = raw.decode(e)
        enc = e
        break
    except UnicodeDecodeError:
        continue
if partial:
    txt = txt[: txt.rfind("\n")]
first = txt.splitlines()[0]
sep = max([",", ";", "\t", "|"], key=first.count)
df = pd.read_csv(io.StringIO(txt), sep=sep, dtype=str, keep_default_na=False)
print(f"FILE {path}\nencoding={enc} sep={sep!r} rows={len(df)} cols={df.shape[1]} partial={partial}")
print("full-row duplicates:", int(df.duplicated().sum()))
for c in df.columns:
    s = df[c]
    blank = (s.str.strip() == "").mean() * 100
    ex = s[s.str.strip() != ""].unique()[:5].tolist()
    print(f"  {c!r}: blank%={blank:.1f} distinct={s.nunique()} ex={ex}")
