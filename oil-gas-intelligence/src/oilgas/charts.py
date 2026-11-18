"""Phase 6 - Static analysis charts for the documentation (assets/*.png).

These are analyst charts for the write-up, not the Tableau dashboard. They use a neutral
palette on purpose: the SA Design System tokens are applied in Tableau only once confirmed
(see DESIGN_SYSTEM status in PHASE_LOG.md).

CLI:  python -m oilgas.charts
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from oilgas.config import PROCESSED_DIR, PROJECT_ROOT  # noqa: E402

A = PROCESSED_DIR / "analysis"
ASSETS = PROJECT_ROOT / "assets"
INK, MUTED, ACCENT, ACCENT2, GRID = "#1f2328", "#8a8f98", "#1f5f8b", "#c26a1b", "#e6e8eb"
SOURCE = "Source: ANP, production by state and location (monthly). Analysis: industrial-data-analytics."

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "xtick.color": INK, "ytick.color": INK, "figure.dpi": 150, "savefig.bbox": "tight",
})


def _finish(fig, name: str, subtitle: str) -> None:
    fig.tight_layout()
    fig.text(0.01, 0.0, subtitle + "\n" + SOURCE, fontsize=7, color=MUTED, ha="left", va="top",
             transform=fig.transFigure)
    ASSETS.mkdir(parents=True, exist_ok=True)
    fig.savefig(ASSETS / f"{name}.png")
    plt.close(fig)


def chart_production(f: pd.DataFrame, br: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(9, 6.2), sharex=True)
    for ax, s, scale, unit in ((axes[0], "oil", 1e3, "thousand m³/d"), (axes[1], "gas", 1e3, "million m³/d")):
        n = f[(f.level == "national") & (f.series == s)].sort_values("period_date")
        ax.plot(n.period_date, n.daily_avg / scale, color=MUTED, lw=0.7, label="monthly daily average")
        ax.plot(n.period_date, n.rolling_12m_daily_avg / scale, color=ACCENT, lw=1.8, label="12-month rolling")
        for _, r in br[br.series == s].iloc[1:].iterrows():
            ax.axvline(pd.Timestamp(r.start), color=ACCENT2, lw=0.8, ls="--")
        ax.set_ylabel(unit)
        ax.set_title(f"{'Oil' if s == 'oil' else 'Natural gas'} production, Brazil")
    axes[0].legend(frameon=False, loc="upper left")
    _finish(fig, "01_national_production",
            "Daily average = monthly volume / calendar days. Dashed lines: structural breaks (piecewise-linear "
            "segmentation, BIC). Last month: Sep 2026 (provisional).")


def chart_concentration(f: pd.DataFrame) -> None:
    uf = f[(f.level == "uf") & (f.series == "oil") & (f.year <= 2025)]
    a = uf.groupby(["year", "uf"]).value.sum().unstack()
    share = a.div(a.sum(axis=1), axis=0)
    loc = f[(f.level == "location") & (f.series == "oil") & (f.year <= 2025)].groupby(["year", "location"]).value.sum().unstack()
    off = loc["Offshore"] / loc.sum(axis=1)
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(share.index, share["RJ"] * 100, color=ACCENT, lw=2, label="Rio de Janeiro share of oil")
    ax.plot(share.index, (share["SP"] + share["ES"]) * 100, color=ACCENT2, lw=1.5, label="São Paulo + Espírito Santo")
    ax.plot(off.index, off * 100, color=INK, lw=1.2, ls=":", label="Offshore share of oil")
    ax.set_ylim(0, 100); ax.set_ylabel("% of national oil volume")
    ax.set_title("Oil is almost entirely offshore, and since 2016 it has re-concentrated in Rio de Janeiro")
    ax.legend(frameon=False, loc="center left")
    _finish(fig, "02_oil_geographic_concentration", "Annual volumes, complete years 1997-2025.")


def chart_gas_utilization(g: pd.DataFrame) -> None:
    n = g[(g.level == "national")].set_index("year").sort_index()
    cols = [("reinjection_rate", "Reinjection", ACCENT), ("available_rate", "Available (ANP 'disponível')", "#7fa7c4"),
            ("own_use_rate", "Own use in E&P", MUTED), ("flaring_loss_rate", "Flaring & losses", ACCENT2)]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.stackplot(n.index, *[n[c] * 100 for c, _, _ in cols], labels=[l for _, l, _ in cols],
                 colors=[c for _, _, c in cols], alpha=0.95)
    ax.set_ylim(0, 105); ax.set_ylabel("% of gas produced")
    ax.set_title("Where Brazil's natural gas goes: reinjection now takes more than half")
    h, l = ax.get_legend_handles_labels()
    ax.legend(h[::-1], l[::-1], frameon=False, loc="center left", bbox_to_anchor=(1.0, 0.5))
    _finish(fig, "03_gas_utilization", "National, annual, 2000-2025. Shares of gross production; balance closes within 0.5% "
                                       "except 2005 (Jul 2005 data issue).")


def chart_seasonality(s: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 3.2))
    w = 0.38
    for i, (series, color) in enumerate((("oil", ACCENT), ("gas", ACCENT2))):
        d = s[s.series == series]
        ax.bar(d.month + (i - 0.5) * w, (d.seasonal_index - 1) * 100, width=w, color=color,
               label=f"{series} (eta²={d.eta2.iloc[0]:.2f}, perm. p={d.perm_p_value.iloc[0]:.4f})")
    ax.axhline(0, color=INK, lw=0.6)
    ax.set_xticks(range(1, 13), ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
    ax.set_ylabel("% vs centred 12-month average")
    ax.set_title("A mild but significant seasonal dip in March-May")
    ax.legend(frameon=False)
    _finish(fig, "04_seasonality", f"Ratio to 2x12 centred moving average of the daily average, {s.window.iloc[0]}. "
                                   "Exploratory: cause of the pattern not established by this data.")


def chart_volatility(v: pd.DataFrame) -> None:
    d = v[v.location.isin(["Offshore", "Onshore"])]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.2), sharey=True)
    for ax, series in zip(axes, ("oil", "gas")):
        p = d[d.series == series].pivot(index="era", columns="location", values="std_mom") * 100
        p.plot.bar(ax=ax, color=[ACCENT, ACCENT2], rot=0, legend=(series == "oil"))
        ax.set_title(f"{series.capitalize()}: std of MoM change"); ax.set_xlabel(""); ax.set_ylabel("p.p.")
    axes[0].legend(frameon=False)
    _finish(fig, "05_volatility_regimes", "Standard deviation of month-on-month change in the daily average, by era.")


def main() -> None:
    f = pd.read_csv(PROCESSED_DIR / "features_production_monthly.csv", parse_dates=["period_date"])
    chart_production(f, pd.read_csv(A / "stats_structural_breaks.csv"))
    chart_concentration(f)
    chart_gas_utilization(pd.read_csv(A / "eda_gas_utilization_annual.csv"))
    chart_seasonality(pd.read_csv(A / "eda_seasonality.csv"))
    chart_volatility(pd.read_csv(A / "stats_volatility_regimes.csv"))
    print("charts:", sorted(p.name for p in ASSETS.glob("*.png")))


if __name__ == "__main__":
    main()
