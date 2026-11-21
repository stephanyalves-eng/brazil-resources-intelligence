"""Generates the Brazilian Oil & Gas Production Analytics workbook (.twb) from TABLEAU_BUILD_GUIDE.md.

The .twb is opened in Tableau Public 2026.3, checked against guide §7 and saved locally as a packaged .twbx.
Run:  python oil-gas-intelligence/tableau/build_workbook.py
"""
import csv
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "shared" / "tableau_twb"))
from twb import F, Workbook, columns_from_dictionary  # noqa: E402

DATA = (HERE / "data").as_posix()
DICT = str(HERE / "data_dictionary.csv")

PAGE, SURFACE, PAPER = "#F5F4EC", "#FFFFFF", "#FBFAF6"
INK, INK2, INK3 = "#101714", "#454C48", "#5E6561"
FOREST, F700, F600, SAGE, SAGE100 = "#0B302B", "#1E5246", "#2F6B5B", "#B8C9C0", "#E4ECE7"
CONTEXT, WARN, SIGNAL, ERR, ON_FOREST = "#D6D8D2", "#9A6412", "#16804F", "#A63A2A", "#F5F4EC"
SEQ = (SAGE100, F700)
BBL = "6.28981"

wb = Workbook("Brazilian Oil & Gas Production Analytics")
wb.extract_dir = wb.extract_dir + "_oil"      # separate folder: dim_uf / metadata extracts differ from the mining ones
P = wb.params
P.add("p Product", "string", "Oil", members=["Oil", "Natural gas", "NGL (LGN)"])
P.add("p Unit Oil", "string", "bbl/d", members=["m3/d", "bbl/d"])
P.add("p Window", "string", "Since 2000", members=["Since 2000", "Last 10 years", "Last 36 months"])
P.add("p Year", "integer", 2025, members=list(range(2000, 2026)), fmt="n0;-0")
ALL_UF = "All states"
UF_NAMES = {r["uf"]: r["uf_name"] for r in csv.DictReader(open(HERE / "data" / "dim_uf.csv", encoding="utf-8"))}
P.add("p State", "string", ALL_UF, members=[ALL_UF] + sorted(UF_NAMES))
UF_ALL = '{{p State}} = "' + ALL_UF + '"'


def source(table, caption=None, levels=None):
    cols = columns_from_dictionary(DICT, table, {"year": ("integer", "dimension", "ordinal"),
                                                 "month": ("integer", "dimension", "ordinal")})
    for c in cols:
        n = c.name.strip("[]")
        if n == "uf":
            c.semantic_role = "[State].[Name]"
        if n in ("year", "month"):
            c.default_format = "n0;-0"
        if c.role == "measure" and (n.endswith("_rate") or "share" in n or n in ("yoy", "mom", "daily_avg_mom", "pct_of_historical_peak",
                                                                               "balance_gap_pct", "deviation_from_baseline_pct",
                                                                               "annualised_growth")):
            c.default_format = "p0.0%"
        if c.role == "measure" and ("daily_avg" in n or n in ("volume", "annual_volume")) and c.default_format is None:
            c.default_format = "n#,##0"
    ds = wb.datasource(caption or table, DATA, f"{table}.csv", cols)
    if levels:
        ds.ds_filters.append(("level", levels))
    return ds


pn = source("production_monthly", "prod · national", ["national"])
pl = source("production_monthly", "prod · location", ["location"])
pu = source("production_monthly", "prod · uf", ["uf"])
pul = source("production_monthly", "prod · uf_location", ["uf_location"])
pnl = source("production_monthly", "prod · national+location", ["national", "location"])
un = source("gas_utilization_monthly", "util · national", ["national"])
ul = source("gas_utilization_monthly", "util · location", ["location"])
uu = source("gas_utilization_monthly", "util · uf", ["uf"])
uul = source("gas_utilization_monthly", "util · uf_location", ["uf_location"])
ann = source("annual_summary")
hhi = source("regional_hhi")
brk = source("structural_breaks")
sea = source("seasonality")
ano = source("anomalies")
meta = source("metadata")
dimu = source("dim_uf")

PCT, YOY, INT = "p0.0%", "*+0.0%;-0.0%", "n#,##0"

# ---- calculated fields (guide §3) -----------------------------------------------------------
for d in (pn, pl, pu, pul, pnl):
    d.calc("Is Product", "[product] = {{p Product}}", "boolean")
    d.calc("Daily Avg", "SUM([volume]) / SUM([days_in_month])", "real", INT)
    d.calc("Daily Avg Display", 'IF {{p Product}} = "Oil" AND {{p Unit Oil}} = "bbl/d" THEN {{Daily Avg}} * ' + BBL + " ELSE {{Daily Avg}} END",
           "real", INT)
    d.calc("Display Unit", 'IF {{p Product}} = "Oil" AND {{p Unit Oil}} = "bbl/d" THEN "bbl/d" ELSEIF {{p Product}} = "Natural gas" '
           'THEN "thousand m³/d" ELSE "m³/d" END', "string")
    d.calc("Latest Month", "{ FIXED : MAX([period_date]) }", "date", role="dimension")
    d.calc("Is Latest", "[period_date] = {{Latest Month}}", "boolean")
    d.calc("In Window", 'CASE {{p Window}} WHEN "Since 2000" THEN [period_date] >= #2000-01-01# '
           'WHEN "Last 10 years" THEN [period_date] > DATEADD(\'year\', -10, {{Latest Month}}) '
           'WHEN "Last 36 months" THEN [period_date] > DATEADD(\'month\', -36, {{Latest Month}}) END', "boolean")
    d.calc("Is Selected Year", "[year] = {{p Year}}", "boolean")

pn.calc("KPI Latest Daily", "SUM(IF {{Is Latest}} THEN [volume] END) / SUM(IF {{Is Latest}} THEN [days_in_month] END)", "real", INT)
pn.calc("KPI Latest Daily Display", 'IF {{p Product}} = "Oil" AND {{p Unit Oil}} = "bbl/d" THEN {{KPI Latest Daily}} * ' + BBL
        + " ELSE {{KPI Latest Daily}} END", "real", INT)
pn.calc("KPI Daily MoM", "MAX(IF {{Is Latest}} THEN [daily_avg_mom] END)", "real", YOY)
pn.calc("KPI Volume MoM", "MAX(IF {{Is Latest}} THEN [mom] END)", "real", YOY)
pn.calc("KPI YoY", "MAX(IF {{Is Latest}} THEN [yoy] END)", "real", YOY)
pn.calc("KPI % of Peak", "MAX(IF {{Is Latest}} THEN [pct_of_historical_peak] END)", "real", "p0%")
pn.calc("Peak Label", 'IF MAX(IF {{Is Latest}} AND [is_new_peak] THEN 1 END) = 1 THEN "new peak" ELSE "of historical peak" END', "string")
pn.calc("Provisional Label", 'IF MAX(IF {{Is Latest}} AND [is_provisional] THEN 1 END) = 1 THEN "PROVISIONAL" END', "string")
pn.calc("Latest Month Label", "UPPER(DATENAME('month', MAX({{Latest Month}}))) + \" \" + STR(YEAR(MAX({{Latest Month}})))", "string")
pn.calc("Change Arrow", 'IF {{KPI Daily MoM}} >= 0 THEN "▲ " ELSE "▼ " END', "string")
pn.calc("YoY Arrow", 'IF {{KPI YoY}} >= 0 THEN "▲ " ELSE "▼ " END', "string")
pn.calc("Rolling 12M Display", 'IF {{p Product}} = "Oil" AND {{p Unit Oil}} = "bbl/d" THEN AVG([rolling_12m_daily_avg]) * ' + BBL
        + " ELSE AVG([rolling_12m_daily_avg]) END", "real", INT)
pn.calc("Baseline Band Low", "AVG([baseline_12m_prior_daily_avg]) * 0.95", "real", INT)
pn.calc("Baseline Band High", "AVG([baseline_12m_prior_daily_avg]) * 1.05", "real", INT)
pn.calc("Anomaly Marker", "IF MAX(INT([is_statistical_anomaly])) = 1 THEN {{Daily Avg}} END", "real", INT)
pn.calc("Last 36 Months", "[period_date] > DATEADD('month', -36, {{Latest Month}})", "boolean")

for d in (pu, pul):
    d.calc("Share (recomputed)", "SUM([volume]) / MIN({FIXED [product], [year] : SUM([volume])})", "real", PCT)
pl.calc("Share (recomputed)", "SUM([volume]) / TOTAL(SUM([volume]))", "real", PCT)

# top-4 producing states per product in 2025 (focus series for G4)
rows = [r for r in csv.DictReader(open(HERE / "data" / "production_monthly.csv", encoding="utf-8")) if r["level"] == "uf" and r["year"] == "2025"]
TOP = {}
for prod in ("Oil", "Natural gas", "NGL (LGN)"):
    c = Counter()
    for r in rows:
        if r["product"] == prod:
            c[r["uf"]] += float(r["volume"])
    TOP[prod] = [u for u, _ in c.most_common(4)]
cases = " ".join(f'WHEN "{p}" THEN (CASE [uf] ' + " ".join(f'WHEN "{u}" THEN [uf_name]' for u in ufs) + ' ELSE "Other states" END)'
                 for p, ufs in TOP.items())
pu.calc("State Focus", f'CASE [product] {cases} END', "string")
STATE_NAMES = {r["uf"]: r["uf_name"] for r in rows}
FOCUS_COLORS = {}
for ufs in TOP.values():
    for i, u in enumerate(ufs):
        FOCUS_COLORS.setdefault(STATE_NAMES[u], [F700, F600, SAGE, INK3][i])
FOCUS_COLORS["Other states"] = CONTEXT

for d, key in ((pu, "[uf]"), (pul, "[uf] + [location]")):
    d.calc("State Filter", f"{UF_ALL} OR [uf] = {{{{p State}}}}", "boolean")
    d.calc("Days", f"SUM([days_in_month]) / COUNTD({key})", "real", INT)
pul.calc("Daily Avg (states)", "SUM([volume]) / {{Days}}", "real", INT)
pu.calc("State Highlight", f'IF {UF_ALL} THEN "All" ELSEIF [uf] = {{{{p State}}}} THEN "Selected" ELSE "Other" END', "string")
for d, key in ((un, None), (ul, "[location]"), (uu, "[uf]"), (uul, "[uf] + [location]")):
    d.calc("Days", "SUM([days_in_month])" + (f" / COUNTD({key})" if key else ""), "real", INT)
    if key and "[uf]" in key:
        d.calc("State Filter", f"{UF_ALL} OR [uf] = {{{{p State}}}}", "boolean")
for d in (un, ul, uu, uul):
    d.calc("Reinjection Rate", "SUM([reinjection_1000m3]) / SUM([gas_production_1000m3])", "real", PCT)
    d.calc("Flaring Rate", "SUM([flaring_loss_1000m3]) / SUM([gas_production_1000m3])", "real", PCT)
    d.calc("Own Use Rate", "SUM([own_use_1000m3]) / SUM([gas_production_1000m3])", "real", PCT)
    d.calc("Available Rate", "SUM([available_1000m3]) / SUM([gas_production_1000m3])", "real", PCT)
    d.calc("Balance Gap %", "(SUM([gas_production_1000m3]) - SUM([reinjection_1000m3]) - SUM([flaring_loss_1000m3]) "
           "- SUM([own_use_1000m3]) - SUM([available_1000m3])) / SUM([gas_production_1000m3])", "real", "p0.00%")
    d.calc("Flaring per Day", "SUM([flaring_loss_1000m3]) / {{Days}}", "real", INT)
    d.calc("Gas Production per Day", "SUM([gas_production_1000m3]) / {{Days}}", "real", INT)
    d.calc("Reinjection per Day", "SUM([reinjection_1000m3]) / {{Days}}", "real", INT)
    d.calc("Is Selected Year", "[year] = {{p Year}}", "boolean")
    d.calc("Outside Band", "ABS({{Balance Gap %}}) > 0.005", "boolean")

ann.calc("Is Product", "[product] = {{p Product}}", "boolean")
ann.calc("Is Selected Year", "[year] = {{p Year}}", "boolean")
ann.calc("Since 2000", "[year] >= 2000", "boolean")
ann.calc("YoY Label", "IF [year] = {{p Year}} THEN [yoy] END", "real", YOY)
hhi.calc("Is Product", "[product] = {{p Product}}", "boolean")
brk.calc("Start Date", 'DATEPARSE("yyyy-MM", [start])', "date", role="dimension")
brk.calc("End Date", 'DATEPARSE("yyyy-MM", [end])', "date", role="dimension")
brk.calc("Duration (days)", "DATEDIFF('day', {{Start Date}}, {{End Date}})", "integer", role="measure")
brk.calc("Fast Regime", "[annualised_growth] > 0.05", "boolean")
brk.calc("Regime Label", 'STR(ROUND([annualised_growth] * 100, 1)) + "%/yr"', "string")
brk.calc("Regime Period", '[start] + " → " + [end]', "string")
sea.calc("Seasonal Deviation", "AVG([seasonal_index]) - 1", "real", YOY)
sea.calc("Above Average", "[seasonal_index] >= 1", "boolean")
meta.calc("Row", '" "', "string")

# ---- sheets (guide §4) -------------------------------------------------------------------------
TF = {"true": F700, "false": CONTEXT}


def eyebrow(t, color=INK3):
    return {"text": t, "font": "Consolas", "size": 8, "color": color}


def ttip(*parts):
    return [{"field": p} if isinstance(p, F) else {"text": p} for p in parts]


M = F("period_date", "tmn")
Y = F("period_date", "yr")

wb.sheet(name="P1 KPI Latest daily avg", ds=pn, mark="Text", bg=FOREST, filters=[(F("Is Product"), None)],
         text=[F("Latest Month Label"), F("KPI Latest Daily Display"), F("Display Unit", "attr"), F("Provisional Label")],
         label=[eyebrow("LATEST MONTH · ", SAGE), {"field": F("Latest Month Label"), "font": "Consolas", "size": 8, "color": SAGE},
                {"text": " · ", "font": "Consolas", "size": 8, "color": SAGE}, {"field": F("Provisional Label"), "font": "Consolas", "size": 8, "color": "#E0B25C"}, {"br": True},
                {"field": F("KPI Latest Daily Display"), "size": 24, "color": ON_FOREST}, {"br": True},
                {"field": F("Display Unit", "attr"), "size": 9, "color": SAGE}, {"text": " · daily average", "size": 9, "color": SAGE}])
wb.sheet(name="P2 KPI MoM", ds=pn, mark="Text", filters=[(F("Is Product"), None)],
         text=[F("Change Arrow"), F("KPI Daily MoM"), F("KPI Volume MoM")],
         label=[eyebrow("MONTH ON MONTH (DAILY AVERAGE)"), {"br": True}, {"field": F("Change Arrow"), "size": 24},
                {"field": F("KPI Daily MoM"), "size": 24}, {"br": True}, {"text": "volume MoM ", "size": 9, "color": INK3},
                {"field": F("KPI Volume MoM"), "size": 9, "color": INK3}, {"text": " (month lengths differ)", "size": 9, "color": INK3}])
wb.sheet(name="P3 KPI YoY", ds=pn, mark="Text", filters=[(F("Is Product"), None)], text=[F("YoY Arrow"), F("KPI YoY")],
         label=[eyebrow("YEAR ON YEAR"), {"br": True}, {"field": F("YoY Arrow"), "size": 24}, {"field": F("KPI YoY"), "size": 24},
                {"br": True}, {"text": "same month, previous year", "size": 9, "color": INK3}])
wb.sheet(name="P4 KPI % of peak", ds=pn, mark="Text", filters=[(F("Is Product"), None)], text=[F("KPI % of Peak"), F("Peak Label")],
         label=[eyebrow("HISTORICAL PEAK (DAILY AVERAGE)"), {"br": True}, {"field": F("KPI % of Peak"), "size": 24, "color": F700},
                {"br": True}, {"field": F("Peak Label"), "size": 9, "color": INK3}])
wb.sheet(name="P5 Monthly volume", ds=pn, mark="Bar", cols=[M], rows=[F("volume", "sum")], color=F("Is Latest"), color_map=TF,
         filters=[(F("Is Product"), None), (F("Last 36 Months"), None)], title="Monthly volume · last 36 months (m³ / thousand m³)",
         tooltip=[F("days_in_month", "sum"), F("Daily Avg")],
         tooltip_text=ttip(M, ": ", F("volume", "sum"), " · ", F("days_in_month", "sum"), " days · daily ", F("Daily Avg")))
wb.sheet(name="P6 Historical daily average", ds=pn, mark="Line", cols=[M], rows=[F("Multiple Values")],
         measure_values=[F("Daily Avg Display"), F("Rolling 12M Display")],
         color_map={"Daily Avg Display": CONTEXT, "Rolling 12M Display": F700},
         filters=[(F("Is Product"), None), (F("In Window"), None)], title="Historical daily average with 12-month rolling mean",
         tooltip_text=ttip(M, ": daily ", F("Daily Avg Display"), " · 12M ", F("Rolling 12M Display")))
wb.sheet(name="P7 Annual summary", ds=ann, mark="Bar", cols=[F("year", kind="ok")], rows=[F("annual_daily_avg", "sum")],
         color=F("Is Selected Year"), color_map={"true": F700, "false": F600},
         filters=[(F("Is Product"), None), (F("Since 2000"), None)], text=[F("YoY Label", "sum")], labels=True,
         axis_titles={F("annual_daily_avg", "sum"): "daily average"},
         title="Annual daily average (click a year to set p Year)",
         tooltip=[F("unit_daily", "attr"), F("offshore_share", "sum")],
         tooltip_text=ttip(F("year", kind="ok"), ": ", F("annual_daily_avg", "sum"), " ", F("unit_daily", "attr"), " · YoY ", F("yoy", "sum"),
                           " · offshore ", F("offshore_share", "sum")))

wb.sheet(name="G1 State share map", ds=pu, mark="Multipolygon", geo=F("uf"), color=F("Share (recomputed)"), color_seq=SEQ,
         filters=[(F("Is Product"), None), (F("Is Selected Year"), None)], title="State share of national production · click a state",
         tooltip_text=ttip(F("uf_name", "attr"), ": ", F("Share (recomputed)"), " of national ", F("product", "attr"), " in ",
                           F("year", "attr")))
wb.sheet(name="G2 State ranking", ds=pu, mark="Bar", rows=[F("uf_name")], cols=[F("volume", "sum")], color=F("State Highlight"),
         color_map={"All": F600, "Selected": F700, "Other": CONTEXT}, filters=[(F("Is Product"), None), (F("Is Selected Year"), None)],
         detail=[F("uf")], sort=(F("uf_name"), F("volume", "sum"), "DESC"), text=[F("Share (recomputed)")], labels=True,
         title="State ranking for the selected year · click a state", axis_titles={F("volume", "sum"): "volume (m³ / thousand m³)"},
         tooltip_text=ttip(F("uf_name"), ": ", F("volume", "sum"), " · ", F("Share (recomputed)")))
wb.sheet(name="G3 Onshore vs offshore", ds=pul, mark="Area", cols=[M], rows=[F("Daily Avg (states)")], color=F("location"),
         color_map={"Offshore": F700, "Onshore": SAGE}, filters=[(F("Is Product"), None), (F("In Window"), None), (F("State Filter"), None)],
         title="Onshore vs offshore · daily average (selected state)", axis_titles={F("Daily Avg (states)"): ""},
         tooltip_text=ttip(F("location"), " ", M, ": ", F("Daily Avg (states)")))
wb.sheet(name="G4 State trends", ds=pu, mark="Line", cols=[M], rows=[F("rolling_12m_daily_avg", "sum")], color=F("State Focus"),
         color_map=FOCUS_COLORS, detail=[F("uf_name")], filters=[(F("Is Product"), None), (F("In Window"), None), (F("State Filter"), None)],
         title="State trends · 12-month rolling daily average", axis_titles={F("rolling_12m_daily_avg", "sum"): ""},
         tooltip_text=ttip(F("uf_name"), " ", M, ": ", F("rolling_12m_daily_avg", "sum")))
wb.sheet(name="G5 Geographic HHI", ds=hhi, mark="Line", cols=[F("year", kind="ok")], rows=[F("hhi", "sum")], mark_color=F700,
         filters=[(F("Is Product"), None)], reflines=[1500, 2500], title="Geographic HHI (1,500 / 2,500)", axis_titles={F("hhi", "sum"): ""},
         tooltip=[F("top_uf", "attr"), F("top_share", "sum")],
         tooltip_text=ttip(F("year", kind="ok"), ": HHI ", F("hhi", "sum"), ", top ", F("top_uf", "attr"), " ", F("top_share", "sum")))

wb.sheet(name="S1 Baseline band + anomalies", ds=pn, mark="Line", cols=[M], rows=[F("Multiple Values")],
         measure_values=[F("Daily Avg"), F("Baseline Band Low"), F("Baseline Band High"), F("Anomaly Marker")],
         color_map={"Daily Avg": F700, "Baseline Band Low": SAGE, "Baseline Band High": SAGE, "Anomaly Marker": ERR},
         filters=[(F("Is Product"), None), (F("In Window"), None)], title="Daily average vs prior-12M baseline ±5 % · anomalies in red",
         tooltip=[F("deviation_from_baseline_pct", "sum"), F("zscore_vs_prior_12m", "sum")],
         tooltip_text=ttip(M, ": daily ", F("Daily Avg"), ", vs prior-12M baseline ", F("deviation_from_baseline_pct", "sum"), ", z = ",
                           F("zscore_vs_prior_12m", "sum"), ". Statistical anomaly, not a verified incident."))
pnl.calc("Volatility Series", 'IF [level] = "national" THEN "National" ELSE [location] END', "string")
wb.sheet(name="S2 Volatility", ds=pnl, mark="Line", cols=[M], rows=[F("volatility_12m", "avg")], color=F("Volatility Series"),
         color_map={"National": F700, "Onshore": SAGE, "Offshore": F600}, filters=[(F("Is Product"), None), (F("In Window"), None)],
         title="12-month volatility", axis_titles={F("volatility_12m", "avg"): ""}, tooltip_text=ttip(F("Volatility Series"), " ", M, ": 12M volatility ", F("volatility_12m", "avg")))
wb.sheet(name="S3 Growth regimes", ds=brk, mark="Bar", rows=[F("product"), F("Regime Period")], cols=[F("annualised_growth", "sum")],
         color=F("Fast Regime"), color_map={"true": F700, "false": F600}, text=[F("annualised_growth", "sum")], labels=True,
         sort=(F("Regime Period"), F("Start Date", "min"), "ASC"), row_labels=False,
         axis_titles={F("annualised_growth", "sum"): "annualised growth of the daily average"},
         title="Growth regimes (structural breaks) · annualised growth per period · click a product",
         tooltip=[F("annualised_growth", "sum"), F("n_months", "sum")],
         tooltip_text=ttip(F("product"), " ", F("Regime Period"), ": ", F("annualised_growth", "sum"), "/yr over ", F("n_months", "sum"), " months"))
wb.sheet(name="S4 Seasonality", ds=sea, mark="Bar", cols=[F("product"), F("month", kind="ok")], rows=[F("Seasonal Deviation")],
         color=F("Above Average"), color_map={"true": SIGNAL, "false": ERR}, title="Seasonality · index − 1 by month · click a product", axis_titles={F("Seasonal Deviation"): ""},
         tooltip=[F("eta2", "avg"), F("perm_p_value", "avg")],
         tooltip_text=ttip(F("month", kind="ok"), ": ", F("Seasonal Deviation"), " vs centred 12M average (η² ", F("eta2", "avg"), ", p ",
                           F("perm_p_value", "avg"), ")"))
wb.sheet(name="S5 Anomaly log", ds=ano, mark="Text", rows=[F("period"), F("product"), F("location"), F("direction")],
         cols=[F(":Measure Names")], text=[F("Multiple Values")], measure_values=[F("daily_avg_mom", "sum"), F("robust_z_mom", "sum")],
         filters=[(F("level"), ["national"])], title="Anomaly log (national) · statistical anomaly, not verified as an operational incident")

wb.sheet(name="U1 Gas balance", ds=uu, filters=[(F("State Filter"), None)], mark="Area", cols=[Y], rows=[F("Multiple Values")],
         measure_values=[F("Reinjection Rate"), F("Available Rate"), F("Own Use Rate"), F("Flaring Rate")],
         color_map={"Reinjection Rate": F700, "Available Rate": SAGE, "Own Use Rate": CONTEXT, "Flaring Rate": WARN},
         title="Where the gas goes · share of production (click a year)", axis_titles={},
         tooltip_text=ttip(Y, ": reinjected ", F("Reinjection Rate"), ", available ", F("Available Rate"), ", own use ", F("Own Use Rate"),
                           ", flared ", F("Flaring Rate")))
wb.sheet(name="U2 Production vs reinjection", ds=uu, filters=[(F("State Filter"), None)], mark="Line", cols=[M], rows=[F("Multiple Values")],
         measure_values=[F("Gas Production per Day"), F("Reinjection per Day")],
         color_map={"Gas Production per Day": F600, "Reinjection per Day": F700},
         title="Gas produced vs reinjected · thousand m³/d",
         tooltip_text=ttip(M, ": produced ", F("Gas Production per Day"), ", reinjected ", F("Reinjection per Day"), " (thousand m³/d)"))
YC = F("period_date", "tyr")
wb.sheet(name="U3 Flaring rate", ds=uu, filters=[(F("State Filter"), None)], mark="Line", cols=[YC], rows=[F("Flaring Rate")], mark_color=WARN,
         title="Flaring rate (share of gas produced)", axis_titles={F("Flaring Rate"): ""},
         tooltip=[F("Flaring per Day")], tooltip_text=ttip(YC, ": ", F("Flaring Rate"), " · ", F("Flaring per Day"), " thousand m³/d"))
wb.sheet(name="U4 Offshore vs onshore rates", ds=uul, mark="Bar", rows=[F("location"), F(":Measure Names")], cols=[F("Multiple Values")],
         text=[F("Multiple Values")], labels=True, row_labels=False,
         measure_values=[F("Reinjection Rate"), F("Available Rate"), F("Own Use Rate"), F("Flaring Rate")],
         color_map={"Reinjection Rate": F700, "Available Rate": SAGE, "Own Use Rate": CONTEXT, "Flaring Rate": WARN},
         filters=[(F("Is Selected Year"), None), (F("State Filter"), None)], title="Offshore vs onshore rates · selected year and state",
         tooltip_text=ttip(F("location"), " ", F("year", "attr"), ": reinjected ", F("Reinjection Rate"), ", flared ", F("Flaring Rate")))
wb.sheet(name="U5 Balance quality", ds=uu, filters=[(F("State Filter"), None)], mark="Bar", cols=[M], rows=[F("Balance Gap %")], color=F("Outside Band"),
         color_map={"true": ERR, "false": CONTEXT}, reflines=[-0.005, 0.005], axis_range=(F("Balance Gap %"), -0.02, 0.02),
         axis_titles={F("Balance Gap %"): ""}, title="Balance gap · band ±0.5 % (axis clipped at ±2 %)",
         tooltip_text=ttip(M, ": gap ", F("Balance Gap %")))
for i, (nm, fld, sub) in enumerate([("REINJECTION RATE", "Reinjection Rate", "of gas produced"), ("FLARING RATE", "Flaring Rate", "flared or lost"),
                                    ("OWN-USE RATE", "Own Use Rate", "consumed on site"), ("AVAILABLE RATE", "Available Rate", "made available")]):
    wb.sheet(name=f"U0{i + 1} KPI {fld}", ds=uu, mark="Text", bg=FOREST if i == 0 else "#FFFFFF",
             filters=[(F("Is Selected Year"), None), (F("State Filter"), None)],
             text=[F(fld), F("year", "attr")],
             label=[eyebrow(nm + " · ", SAGE if i == 0 else INK3),
                    {"field": F("year", "attr"), "font": "Consolas", "size": 8, "color": SAGE if i == 0 else INK3}, {"br": True},
                    {"field": F(fld), "size": 24, "color": ON_FOREST if i == 0 else INK}, {"br": True},
                    {"text": sub, "size": 9, "color": SAGE if i == 0 else INK3}])
wb.sheet(name="D1 Sources", ds=meta, mark="Text", rows=[F("source_key"), F("source_name"), F("coverage"), F("note"), F("url")],
         text=[F("Row")], title="Sources")

# ---- dashboards (guide §5) -------------------------------------------------------------------------
W, H, PAD, GAP = 1200, 926, 24, 12
BAND, SHIFT = 106, 26
COL = (W - 2 * PAD - 11 * GAP) / 12


def cx(c):
    return PAD + c * (COL + GAP)


def cw(n):
    return n * COL + (n - 1) * GAP


FOOT = ("Source: ANP — production by state and location, snapshot 2026-11-18 · last month Sep 2026 (provisional) · "
        "oil and gas are never summed · click a year, state or product to filter · Stephany Alves")
PAGES = [("1 · Production Overview", "Overview"), ("2 · Regional Analysis", "Regional"), ("3 · Production Stability", "Stability"),
         ("4 · Natural Gas Utilization", "Gas use"), ("5 · Methodology", "Method")]
PLABEL = {"p Product": "PRODUCT", "p Unit Oil": "OIL UNIT", "p Window": "WINDOW", "p Year": "YEAR", "p State": "STATE"}
CHIPS = [("p Product", 130), ("p Unit Oil", 80), ("p Window", 130), ("p Year", 80), ("p State", 110)]


def header(title, current):
    z = [{"type": "text", "x": 0, "y": 0, "w": W, "h": BAND, "bg": FOREST, "border": False, "margin": 0, "runs": [{"text": " "}]},
         {"type": "text", "x": PAD, "y": 10, "w": 560, "h": 54, "bg": FOREST, "border": False, "margin": 0,
          "runs": [{"text": "BRAZILIAN OIL & GAS · ANP MONTHLY", "font": "Consolas", "size": 8, "color": SAGE, "br": True},
                   {"text": title, "font": "Georgia", "size": 22, "color": ON_FOREST}]}]
    bw, gap = 96, 6
    x = W - PAD - len(PAGES) * bw - (len(PAGES) - 1) * gap
    for name, cap in PAGES:
        on = name == current
        z.append({"type": "nav", "target": name, "caption": cap, "x": x, "y": 14, "w": bw, "h": 28,
                  "bg": SAGE if on else F600, "fg": FOREST if on else ON_FOREST})
        x += bw + gap
    x = PAD
    for p, w in CHIPS:
        lw = 8 + 7 * len(PLABEL[p])
        z.append({"type": "text", "x": x, "y": 72, "w": lw, "h": 24, "bg": FOREST, "border": False, "margin": 4,
                  "runs": [{"text": PLABEL[p], "font": "Consolas", "size": 8, "color": SAGE}]})
        z.append({"type": "param", "param": p, "x": x + lw, "y": 70, "w": w, "h": 28, "bg": FOREST, "border": False, "title": False,
                  "margin": 2})
        x += lw + w + 18
    return z


def body(zones):
    for z in zones:
        z["y"] += SHIFT
    return zones


def footer(h=None):
    return [{"type": "text", "x": PAD, "y": (h or H) - 34, "w": W - 2 * PAD, "h": 28, "border": False,
             "runs": [{"text": FOOT, "size": 8, "color": INK3}]}]


def sheet(name, c, n, y, h, title=True, bg=SURFACE):
    z = {"type": "sheet", "sheet": name, "x": cx(c), "y": y, "w": cw(n), "h": h, "bg": bg}
    if not title:
        z["title"] = False
    return z


def note(text, c, n, y, h=26, color=INK2):
    return {"type": "text", "x": cx(c), "y": y, "w": cw(n), "h": h, "border": False, "runs": [{"text": text, "size": 9, "color": color}]}


Y0 = 92
TOP, BOT = BAND + 12, H - 40      # body area between the dark band and the footer; rows share it with no orphan gaps
p1 = TOP + 104 + 10
p2 = p1 + 26
p3 = p2 + 300 + GAP
wb.dashboard(PAGES[0][0], W, H, header("Production Overview", PAGES[0][0]) + [
    sheet("P1 KPI Latest daily avg", 0, 3, TOP, 104, False, FOREST), sheet("P2 KPI MoM", 3, 3, TOP, 104, False),
    sheet("P3 KPI YoY", 6, 3, TOP, 104, False), sheet("P4 KPI % of peak", 9, 3, TOP, 104, False),
    note("Record month in Sep 2026; growth has accelerated since mid-2022 after a 2016–2022 plateau.", 0, 12, p1, 22),
    sheet("P6 Historical daily average", 0, 12, p2, 300),
    sheet("P5 Monthly volume", 0, 7, p3, BOT - p3), sheet("P7 Annual summary", 7, 5, p3, BOT - p3)] + footer(), PAGE)
g1 = TOP + 26
H2 = 1120
g2 = g1 + 360 + GAP
g3 = g2 + 330 + GAP
wb.dashboard(PAGES[1][0], W, H2, header("Regional Analysis", PAGES[1][0]) + [
    note("97.6 % of oil is offshore; Rio de Janeiro's share is back to 87.8 %.", 0, 12, TOP, 22),
    sheet("G1 State share map", 0, 5, g1, 360), sheet("G2 State ranking", 5, 7, g1, 360),
    sheet("G3 Onshore vs offshore", 0, 6, g2, 330), sheet("G4 State trends", 6, 6, g2, 330),
    sheet("G5 Geographic HHI", 0, 12, g3, H2 - 40 - g3)] + footer(H2), PAGE)
H3 = 1200
s2 = g1 + 340 + GAP
s3 = s2 + 330 + GAP
wb.dashboard(PAGES[2][0], W, H3, header("Production Stability", PAGES[2][0]) + [
    note("Anomalies are statistical; causes are not in the data.", 0, 12, TOP, 22, color=WARN),
    sheet("S1 Baseline band + anomalies", 0, 7, g1, 340), sheet("S5 Anomaly log", 7, 5, g1, 340),
    sheet("S2 Volatility", 0, 6, s2, 330), sheet("S4 Seasonality", 6, 6, s2, 330),
    sheet("S3 Growth regimes", 0, 12, s3, H3 - 40 - s3)] + footer(H3), PAGE)
H4 = 1180
u1 = TOP + 100 + 10
u2 = u1 + 26
u3 = u2 + 300 + GAP
u4 = u3 + 300 + GAP
wb.dashboard(PAGES[3][0], W, H4, header("Natural Gas Utilization", PAGES[3][0]) + [
    sheet("U01 KPI Reinjection Rate", 0, 3, TOP, 100, False, FOREST), sheet("U02 KPI Flaring Rate", 3, 3, TOP, 100, False),
    sheet("U03 KPI Own Use Rate", 6, 3, TOP, 100, False), sheet("U04 KPI Available Rate", 9, 3, TOP, 100, False),
    note("Reinjection took 54.4 % of gas in 2025 (19.1 % in 2010); flaring fell to 2.8 %.", 0, 12, u1, 22),
    sheet("U1 Gas balance", 0, 12, u2, 300),
    sheet("U2 Production vs reinjection", 0, 7, u3, 300), sheet("U4 Offshore vs onshore rates", 7, 5, u3, 300),
    sheet("U3 Flaring rate", 0, 6, u4, H4 - 40 - u4), sheet("U5 Balance quality", 6, 6, u4, H4 - 40 - u4)] + footer(H4), PAGE)
METH = [
    ("UNITS", "Oil and NGL in m³ (daily m³/d; bbl/d = m³/d × 6.28981); natural gas in thousand m³ (thousand m³/d). Oil and gas are never summed."),
    ("DEFINITIONS", "K2 daily average = Σ volume / Σ days (recomputed at any grain) · K4 YoY on the same month · K14 share of national · "
     "K15 HHI by state · K17–K20 gas reinjection, flaring, own-use and available rates (Σ/Σ)."),
    ("CLEANING RULES", "R1 one row per level × place × product × month · R2 'not reported' kept as nulls · R3 days-in-month weighting · "
     "R4 provisional flag for 2026 · R5 national = Σ states, reconciled with the ANP yearbook (≤ 0.04 %)."),
    ("LIMITATIONS", "2026 data are provisional · UF gas-use rates are allocation-sensitive · no field-level data · no forecast · "
     "anomalies are statistical, not verified incidents."),
    ("HOW TO USE", "The boxes in the band filter every page. Clicking a year (annual bars, gas balance, flaring), a state (map, ranking) "
     "or a product (growth regimes, seasonality, anomaly log) sets them; pick All states in the box to reset. The state filter applies to "
     "the regional and gas pages; production KPIs and stability views are national."),
    ("UPDATE", "From oil-gas-intelligence/src: ..\\..\\.venv\\Scripts\\python.exe -m oilgas.pipeline, then refresh the extracts."),
]
mz, y = [], 440
for i, (k, v) in enumerate(METH):
    c = 0 if i % 2 == 0 else 6
    mz.append({"type": "text", "x": cx(c), "y": y, "w": cw(6), "h": 120, "bg": PAPER, "margin": 12,
               "runs": [{"text": k, "font": "Consolas", "size": 8, "color": INK3, "br": True}, {"text": v, "size": 10, "color": INK2}]})
    if i % 2 == 1:
        y += 132
wb.dashboard(PAGES[4][0], W, H, header("Methodology", PAGES[4][0]) + body([sheet("D1 Sources", 0, 12, Y0, 330)] + mz) + footer(), PAGE)

# ---- interactions (guide §6) ------------------------------------------------------------------------
wb.param_action("Select year (P7)", PAGES[0][0], ["P7 Annual summary"], F("year", kind="ok"), ann, "p Year")
wb.param_action("Select year (U1)", PAGES[3][0], ["U1 Gas balance"], Y, uu, "p Year")
wb.param_action("State from map (G1)", PAGES[1][0], ["G1 State share map"], F("uf"), pu, "p State")
wb.param_action("State from ranking (G2)", PAGES[1][0], ["G2 State ranking"], F("uf"), pu, "p State")
wb.param_action("Product from regimes (S3)", PAGES[2][0], ["S3 Growth regimes"], F("product"), brk, "p Product")
wb.param_action("Product from seasonality (S4)", PAGES[2][0], ["S4 Seasonality"], F("product"), sea, "p Product")
wb.param_action("Product from anomaly log (S5)", PAGES[2][0], ["S5 Anomaly log"], F("product"), ano, "p Product")

if __name__ == "__main__":
    out = HERE / "Brazilian_Oil_Gas_Production.twb"
    wb.save(out)
    print(out)
