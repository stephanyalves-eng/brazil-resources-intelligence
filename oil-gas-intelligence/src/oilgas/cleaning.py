"""Phase 5 - Data cleaning.

Turns the 7 published ANP files into one long, validated table on a dense monthly grid:

    series x period x UF x location  ->  value, status, flags

Rules (each one is logged in data/interim/corrections_log.csv with counts):
  R1  Cut-off: every series ends at the last month whose national total is > 0 in *all* series
      (removes the oil Oct-Dec 2026 placeholder zeros).
  R2  Densify: each series gets every month from its first published month to the cut-off, for every
      UF x location combination it ever published. Rows added this way get value = NaN and
      status = 'not_reported' - never 0.
  R3  Reported zeros stay 0 with status = 'reported'.
  R4  Negative 'available' gas is kept and flagged (balance allocation, not an error).
  R5  The months of the cut-off year are flagged is_provisional (subject to ANP revision).

CLI:  python -m oilgas.cleaning
"""
from __future__ import annotations

import calendar

import pandas as pd

from oilgas.config import INTERIM_DIR, LOCATION_EN, PROCESSED_DIR, SOURCES, UF_REFERENCE
from oilgas.readers import read_tidy

KEY = ["series", "year", "month", "uf_raw", "location_raw"]


def load_all() -> pd.DataFrame:
    frames = []
    for key, (_, _, unit, _) in SOURCES.items():
        df = read_tidy(key).rename(columns={"uf": "uf_raw", "location": "location_raw"})
        df.insert(0, "series", key)
        df["unit"] = unit
        frames.append(df[["series", "unit", "year", "month", "uf_raw", "location_raw", "value"]])
    out = pd.concat(frames, ignore_index=True)
    dup = out.duplicated(KEY)
    if dup.any():
        raise ValueError(f"Duplicate keys in raw data: {int(dup.sum())}")
    unknown = set(out.uf_raw) - set(UF_REFERENCE)
    if unknown:
        raise ValueError(f"UF names missing from UF_REFERENCE: {unknown}")
    return out


def common_cutoff(df: pd.DataFrame) -> pd.Period:
    """R1: earliest 'last month with national total > 0' across series."""
    nat = df.groupby(["series", "year", "month"])["value"].sum().reset_index()
    nat = nat[nat.value > 0]
    last = nat.assign(p=pd.PeriodIndex.from_fields(year=nat.year, month=nat.month, freq="M")).groupby("series").p.max()
    return last.min()


def densify(df: pd.DataFrame, cutoff: pd.Period) -> pd.DataFrame:
    """R2: dense grid per series, from the series' first month to the cut-off."""
    df = df.assign(period=pd.PeriodIndex.from_fields(year=df.year, month=df.month, freq="M"))
    parts = []
    for series, g in df.groupby("series", sort=False):
        months = pd.period_range(g.period.min(), cutoff, freq="M")
        combos = g[["uf_raw", "location_raw"]].drop_duplicates()
        grid = combos.merge(pd.DataFrame({"period": months}), how="cross")
        grid["series"] = series
        grid["unit"] = g.unit.iloc[0]
        parts.append(grid.merge(g[["series", "period", "uf_raw", "location_raw", "value"]],
                                on=["series", "period", "uf_raw", "location_raw"], how="left"))
    return pd.concat(parts, ignore_index=True)


def clean() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = load_all()
    log = []
    cutoff = common_cutoff(raw)

    raw_p = pd.PeriodIndex.from_fields(year=raw.year, month=raw.month, freq="M")
    beyond = raw[raw_p > cutoff]
    for s, g in beyond.groupby("series"):
        log.append({"rule": "R1 cut-off", "series": s, "rows": len(g), "value_sum": g.value.sum(),
                    "detail": f"rows after common cut-off {cutoff} removed"})
    kept = raw[raw_p <= cutoff]

    dense = densify(kept, cutoff)
    added = dense.value.isna()
    for s, g in dense[added].groupby("series"):
        log.append({"rule": "R2 densify", "series": s, "rows": len(g), "value_sum": None,
                    "detail": "unpublished UF x location x month added as NaN / not_reported"})

    ref = pd.DataFrame([(k, *v) for k, v in UF_REFERENCE.items()], columns=["uf_raw", "uf", "uf_name", "region"])
    out = dense.merge(ref, on="uf_raw", how="left")
    out["location"] = out.location_raw.map(LOCATION_EN)
    out["year"] = out.period.dt.year
    out["month"] = out.period.dt.month
    out["period_date"] = out.period.dt.to_timestamp()
    out["days_in_month"] = [calendar.monthrange(y, m)[1] for y, m in zip(out.year, out.month)]
    out["status"] = out.value.isna().map({True: "not_reported", False: "reported"})
    out["is_provisional"] = out.year == cutoff.year
    out["is_negative_balance"] = (out.series == "available") & (out.value < 0)

    for s, g in out[out.is_negative_balance].groupby("series"):
        log.append({"rule": "R4 negative kept", "series": s, "rows": len(g), "value_sum": g.value.sum(),
                    "detail": "negative available gas kept and flagged"})
    log.append({"rule": "R5 provisional", "series": "all", "rows": int(out.is_provisional.sum()), "value_sum": None,
                "detail": f"months of {cutoff.year} flagged provisional"})

    cols = ["series", "unit", "period_date", "year", "month", "days_in_month", "uf", "uf_name", "region",
            "location", "value", "status", "is_provisional", "is_negative_balance"]
    out = out[cols].sort_values(["series", "uf", "location", "period_date"]).reset_index(drop=True)
    return out, pd.DataFrame(log).assign(cutoff=str(cutoff))


def to_wide(long: pd.DataFrame) -> pd.DataFrame:
    """One row per month x UF x location with each product/flow as a column (LGN excluded: no location split)."""
    key = ["period_date", "uf", "location"]
    sub = long[long.series != "lgn"]
    # unstack on the minimal key only (NaN = not_reported or series not yet published), then attach attributes
    vals = sub.set_index(key + ["series"])["value"].unstack("series").reset_index()
    vals.columns.name = None
    attrs = sub[key + ["year", "month", "days_in_month", "uf_name", "region", "is_provisional"]].drop_duplicates(key)
    w = attrs.merge(vals, on=key, how="inner", validate="one_to_one")
    w = w.rename(columns={"oil": "oil_m3", "gas": "gas_1000m3", "reinjection": "reinjection_1000m3",
                          "flaring": "flaring_loss_1000m3", "own_use": "own_use_1000m3", "available": "available_1000m3"})
    return w.sort_values(["uf", "location", "period_date"]).reset_index(drop=True)


def main() -> None:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    long, log = clean()
    long.to_csv(INTERIM_DIR / "ppgn_long_clean.csv", index=False, encoding="utf-8")
    log.to_csv(INTERIM_DIR / "corrections_log.csv", index=False, encoding="utf-8")
    wide = to_wide(long)
    wide.to_csv(INTERIM_DIR / "ppgn_wide_clean.csv", index=False, encoding="utf-8")
    print(f"cut-off: {log.cutoff.iloc[0]} | long rows: {len(long):,} | wide rows: {len(wide):,}")
    print(log.drop(columns="cutoff").to_string(index=False))
    print(long.groupby(["series", "status"]).size().unstack(fill_value=0))


if __name__ == "__main__":
    main()
