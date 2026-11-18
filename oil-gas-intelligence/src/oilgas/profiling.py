"""Phase 2 - Data profiling of the raw ANP files.

Produces data/interim/profile_*.csv and prints a summary that feeds docs/DATA_PROFILE.md.
Profiling describes the raw data; it changes nothing.

CLI:  python -m oilgas.profiling
"""
from __future__ import annotations

import pandas as pd

from oilgas.config import INTERIM_DIR, RAW_DIR, SOURCES
from oilgas.readers import read_anuario, read_tidy as tidy

KEY = ["year", "month", "uf", "location"]


def profile_file(key: str, df: pd.DataFrame) -> dict:
    nat = df.groupby(["year", "month"])["value"].sum()
    nonzero = nat[nat > 0]
    last_nonzero = nonzero.index.max()
    after = nat[nat.index > last_nonzero]
    combos = df[["uf", "location"]].drop_duplicates()
    periods = pd.MultiIndex.from_frame(df[["year", "month"]].drop_duplicates())
    expected = len(combos) * len(periods)
    dec_by_year = df.groupby("year")["has_decimals"].mean()
    return {
        "file": key,
        "unit": SOURCES[key][2],
        "rows": len(df),
        "first_period": f"{df.year.min()}-{df[df.year == df.year.min()].month.min():02d}",
        "last_period_in_file": f"{df.year.max()}-{df[df.year == df.year.max()].month.max():02d}",
        "last_nonzero_national_month": f"{last_nonzero[0]}-{last_nonzero[1]:02d}",
        "trailing_all_zero_months": len(after),
        "key_duplicates": int(df.duplicated(KEY).sum()),
        "negative_values": int((df.value < 0).sum()),
        "zero_rows": int((df.value == 0).sum()),
        "uf_location_combos": len(combos),
        "missing_combo_months": expected - len(df),
        "first_year_with_decimals": int(dec_by_year[dec_by_year > 0].index.min()) if (dec_by_year > 0).any() else None,
        "regions": "|".join(sorted(df.region.unique())),
    }


def gas_balance(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    parts = ["gas", "reinjection", "flaring", "own_use", "available"]
    bal = None
    for p in parts:
        f = frames[p][KEY + ["value"]].rename(columns={"value": p})
        bal = f if bal is None else bal.merge(f, on=KEY, how="outer", indicator=False)
    bal = bal[bal.year >= 2000]
    bal["uses"] = bal[["reinjection", "flaring", "own_use", "available"]].sum(axis=1, min_count=4)
    bal["gap"] = bal["gas"] - bal["uses"]
    bal["gap_pct"] = bal["gap"] / bal["gas"].where(bal["gas"] > 0) * 100
    return bal


def reconcile_anuario(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compare annual sums of the monthly files with the Anuário 2026 (2016-2025)."""
    pairs = {"oil": "tabela2-14", "gas": "tabela2-19", "reinjection": "tabela2-21", "flaring": "tabela2-22"}
    rows = []
    for key, tab in pairs.items():
        a = read_anuario(RAW_DIR / "anuario_2026" / f"anuario-2026-dados_abertos-{tab}.csv")
        a = a[a.location.isin(["Terra", "Mar"])].copy()
        a["uf"] = a.uf.str.upper()
        a["location"] = a.location.str.upper()
        m = (frames[key].query("2016 <= year <= 2025")
             .groupby(["uf", "location", "year"], as_index=False)["value"].sum())
        j = a.merge(m, on=["uf", "location", "year"], how="outer", suffixes=("_anuario", "_monthly"))
        j["file"] = key
        rows.append(j)
    out = pd.concat(rows, ignore_index=True)
    out["ratio"] = out["value_monthly"] / out["value_anuario"].where(out["value_anuario"] != 0)
    return out


def main() -> None:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    frames = {k: tidy(k) for k in SOURCES}
    prof = pd.DataFrame([profile_file(k, v) for k, v in frames.items()])
    prof.to_csv(INTERIM_DIR / "profile_files.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(prof.T)

    bal = gas_balance(frames)
    bal.to_csv(INTERIM_DIR / "profile_gas_balance.csv", index=False)
    ok = bal.dropna(subset=["gas", "uses"])
    print(f"\nGas balance: {len(bal)} keys, {len(bal) - len(ok)} with a missing component")
    print("  |gap| <= 1 thousand m3:", f"{(ok.gap.abs() <= 1).mean():.1%}",
          "| |gap| <= 1% of production:", f"{(ok.gap_pct.abs() <= 1).mean():.1%} (of rows with production > 0)")
    print("  largest absolute gaps:\n", ok.reindex(ok.gap.abs().sort_values(ascending=False).index)
          .head(5)[KEY + ["gas", "uses", "gap"]].to_string(index=False))

    rec = reconcile_anuario(frames)
    rec.to_csv(INTERIM_DIR / "profile_anuario_reconciliation.csv", index=False)
    print("\nAnuário reconciliation (monthly sum / Anuário), by file:")
    print(rec.groupby("file")["ratio"].describe()[["count", "min", "50%", "max"]].round(4).to_string())
    print("  unmatched keys:", rec.groupby("file").apply(
        lambda d: int(d.value_anuario.isna().sum() + d.value_monthly.isna().sum()), include_groups=False).to_dict())


if __name__ == "__main__":
    main()
