"""Generates the Brazilian Mining Performance workbook (.twb) from TABLEAU_BUILD_GUIDE.md.

The .twb is opened in Tableau Public 2026.3, checked against guide §7 and saved locally as a packaged .twbx.
Interactivity: three global filters (p Year, p Substance, p State) drive every sheet; clicking a bar, a state, a heatmap
cell or a table row sets them through parameter actions, so the whole dashboard follows the selection (deselect = reset).
Run:  python mining-intelligence/tableau/build_workbook.py
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "shared" / "tableau_twb"))
from twb import F, Workbook, columns_from_dictionary  # noqa: E402

DATA = (HERE / "data").as_posix()
DICT = str(HERE / "data_dictionary.csv")

# ---- SA design tokens -------------------------------------------------------------
PAGE, SURFACE, PAPER = "#F5F4EC", "#FFFFFF", "#FBFAF6"
INK, INK2, INK3 = "#101714", "#454C48", "#5E6561"
FOREST, F700, F600, SAGE, SAGE100 = "#0B302B", "#1E5246", "#2F6B5B", "#B8C9C0", "#E4ECE7"
CONTEXT, WARN, SIGNAL, ERR, ON_FOREST = "#D6D8D2", "#9A6412", "#16804F", "#A63A2A", "#F5F4EC"
SEQ = (SAGE100, F700)

ALL_SUB, ALL_UF = "All substances", "All states"
SUBSTANCES = [line.split(",")[0] for line in (HERE / "data" / "dim_substance.csv").read_text(encoding="utf-8").splitlines()[1:]]
UF_NAMES = {r["uf"]: r["uf_name"] for r in csv.DictReader(open(HERE / "data" / "dim_uf.csv", encoding="utf-8"))}

wb = Workbook("Brazilian Mining Performance")
P = wb.params
P.add("p Year", "integer", 2025, members=list(range(2010, 2026)), fmt="n0;-0")
P.add("p CFEM Year", "integer", 2025, members=list(range(2004, 2026)), fmt="n0;-0")
P.add("p Substance", "string", ALL_SUB, members=[ALL_SUB] + SUBSTANCES)
P.add("p State", "string", ALL_UF, members=[ALL_UF] + sorted(UF_NAMES))
CTYPES = ["geographic (UF, AMB value)", "commodity mix (AMB value)", "business (CNPJ root, CFEM)"]
P.add("p Concentration Type", "string", "business (CNPJ root, CFEM)", members=CTYPES)


def source(table, caption=None):
    cols = columns_from_dictionary(DICT, table, {"year": ("integer", "dimension", "ordinal")})
    for c in cols:
        n = c.name.strip("[]")
        if n == "uf":
            c.semantic_role = "[State].[Name]"
        if n == "year":
            c.default_format = "n0;-0"
        if c.role == "measure" and ("share" in n or n.endswith("_rate")):
            c.default_format = "p0.0%"
        if c.role == "measure" and n.endswith("_yoy"):
            c.default_format = "*+0.0%;-0.0%"
        if n in ("hhi", "sale_value_brl", "cfem_brl", "production_qty", "amb_sale_value_brl", "total_value_brl"):
            c.default_format = "n#,##0"
        if c.name in ("[company_key]", "[ibge_municipality_code]"):
            c.datatype, c.role, c.type = "string", "dimension", "nominal"
    return wb.datasource(caption or table, DATA, f"{table}.csv", cols)


sub = source("amb_substance_year")
ufs = source("amb_uf_substance_year")
pv = source("amb_price_volume")
cfm = source("cfem_municipality_year")
cfc = source("cfem_company_substance_year")
amc = source("amb_cfem_uf_substance_year")
con = source("concentration")
meta = source("metadata")
# the guide connects every CSV as its own source; these are not used by the current sheets
for _t in ("amb_national_year", "amb_uf_year", "cfem_uf_substance_year", "cfem_monthly", "dim_uf", "dim_substance"):
    source(_t)

BN = "1000000000"
PCT, YOY, BNF, INT = "p0.0%", "*+0.0%;-0.0%", "n#,##0.0", "n#,##0"
SUB_ALL = '{{p Substance}} = "' + ALL_SUB + '"'
UF_ALL = '{{p State}} = "' + ALL_UF + '"'
FOCUS = f'(IF {SUB_ALL} THEN "Iron ore" ELSE {{{{p Substance}}}} END)'
UF_CASE = "CASE [uf] " + " ".join(f'WHEN "{k}" THEN "{v}"' for k, v in sorted(UF_NAMES.items())) + " ELSE [uf] END"
SEL_LABEL = (f'(IF {SUB_ALL} THEN "ALL SUBSTANCES" ELSE UPPER({{{{p Substance}}}}) END) + " · " + '
             f'(IF {UF_ALL} THEN "BRAZIL" ELSE {{{{p State}}}} END)')

# ---- shared filter calcs -----------------------------------------------------------------
for d, col in ((sub, "substance_group"), (ufs, "substance_group"), (pv, "substance_group"), (cfc, "substance_group"),
               (amc, "substance_group"), (cfm, "main_substance_group")):
    d.calc("Substance Filter", f"{SUB_ALL} OR [{col}] = {{{{p Substance}}}}", "boolean")
    d.calc("Is Focus Substance", f"[{col}] = {FOCUS}", "boolean")
for d in (ufs, amc, cfm):
    d.calc("State Filter", f"{UF_ALL} OR [uf] = {{{{p State}}}}", "boolean")
for d in (sub, ufs, pv):
    d.calc("Is Selected Year", "[year] = {{p Year}}", "boolean")
for d in (sub, ufs):
    d.calc("Highlight Substance", f'IF [substance_group] = {FOCUS} THEN [substance_group] ELSE "Other substances" END', "string")
    d.calc("Value (R$ bn)", f"SUM([sale_value_brl]) / {BN}", "real", BNF)

# ---- page 1 / 2: value, states, substances (amb_uf_substance_year sums exactly to the national and state totals) ----------
ufs.calc("Selection Label", SEL_LABEL, "string")
ufs.calc("State Name", UF_CASE, "string")
ufs.calc("KPI Value (R$ bn)", f"SUM(IF [year] = {{{{p Year}}}} THEN [sale_value_brl] END) / {BN}", "real", BNF)
ufs.calc("KPI Value Prev (R$ bn)", f"SUM(IF [year] = {{{{p Year}}}} - 1 THEN [sale_value_brl] END) / {BN}", "real", BNF)
ufs.calc("KPI Value YoY", "IF {{KPI Value Prev (R$ bn)}} > 0 THEN {{KPI Value (R$ bn)}} / {{KPI Value Prev (R$ bn)}} - 1 END", "real", YOY)
ufs.calc("KPI CAGR since 2010", "IF {{p Year}} > 2010 THEN POWER({{KPI Value (R$ bn)}} / (SUM(IF [year] = 2010 THEN [sale_value_brl] END) / "
         + BN + "), 1 / ({{p Year}} - 2010)) - 1 END", "real", YOY)
ufs.calc("YoY Arrow", 'IF {{KPI Value YoY}} >= 0 THEN "▲ " ELSE "▼ " END', "string")
ufs.calc("Value YoY", "SUM([sale_value_brl]) / LOOKUP(SUM([sale_value_brl]), -1) - 1", "real", YOY)
# share of the selected substance(s) held by each state, and of the selected state held by each substance
ufs.calc("State Share", f"SUM([sale_value_brl]) / MIN({{FIXED [year] : SUM(IF {SUB_ALL} OR [substance_group] = {{{{p Substance}}}} "
         "THEN [sale_value_brl] END)})", "real", PCT)
ufs.calc("Substance Share", f"SUM([sale_value_brl]) / MIN({{FIXED [year] : SUM(IF {UF_ALL} OR [uf] = {{{{p State}}}} "
         "THEN [sale_value_brl] END)})", "real", PCT)
ufs.calc("State Label", 'ATTR({{State Name}}) + " · " + STR(ROUND({{State Share}} * 100, 1)) + "%"', "string")
ufs.calc("State Highlight", f'IF {UF_ALL} THEN "All" ELSEIF [uf] = {{{{p State}}}} THEN "Selected" ELSE "Other" END', "string")
ufs.calc("Quantity (selected group)", "IF [substance_group] = {{p Substance}} THEN [production_qty] END", "real", INT)
ufs.calc("DQ Caveat", 'IF [dq_flag_intermittent_series] THEN "Intermittent reporting (see methodology)" END', "string")

sub.calc("KPI Focus Share", f"SUM(IF [year] = {{{{p Year}}}} AND [substance_group] = {FOCUS} THEN [sale_value_brl] END) "
         "/ SUM(IF [year] = {{p Year}} THEN [sale_value_brl] END)", "real", PCT)
sub.calc("KPI Top3 Share", "SUM(IF [year] = {{p Year}} AND [rank_in_year] <= 3 THEN [sale_value_brl] END) "
         "/ SUM(IF [year] = {{p Year}} THEN [sale_value_brl] END)", "real", PCT)
sub.calc("Focus Label", f"UPPER({FOCUS})", "string")
sub.calc("Focus Rank", f"MIN(IF [year] = {{{{p Year}}}} AND [substance_group] = {FOCUS} THEN [rank_in_year] END)", "integer", "n0;-0")

pv.calc("Unit Value", "SUM([sale_value_brl]) / SUM([sale_qty])", "real", "n#,##0.00")

# ---- page 3: market structure ---------------------------------------------------------------
cfm.calc("CFEM (R$ mn)", "SUM([cfem_brl]) / 1000000", "real", INT)
cfm.calc("Is Selected CFEM Year", "[year] = {{p CFEM Year}}", "boolean")
cfm.calc("Municipal Share", "SUM([cfem_brl]) / MIN({FIXED [year] : SUM([cfem_brl])})", "real", PCT)
cfm.calc("Municipality Label", '[municipality_name] + ", " + [uf]', "string")
cfm.calc("Is Top 2", "[rank_in_year] <= 2", "boolean")
cfc.calc("Company Label", 'IF [rank] <= 10 THEN STR([rank]) + ". " + [company_name] ELSE [company_name] END', "string")
cfc.calc("Is Top Company", "[rank] = 1", "boolean")
cfc.calc("Is Selected CFEM Year", "[year] = {{p CFEM Year}}", "boolean")
cfc.calc("Top 10", "[rank] <= 10", "boolean")
cfc.calc("CFEM (R$ mn)", "SUM([cfem_brl]) / 1000000", "real", INT)
# same definition as sql/30_analysis.sql Q12 (all mapped UF × substance rows), which produced guide §7
amc.calc("CFEM per R$ of Sales", "SUM([cfem_brl]) / SUM([amb_sale_value_brl])", "real", "p0.00%")
amc.calc("CFEM per R$ of Sales (selected)", f"SUM(IF [substance_group] = {FOCUS} THEN [cfem_brl] END) "
         f"/ SUM(IF [substance_group] = {FOCUS} THEN [amb_sale_value_brl] END)", "real", "p0.00%")
amc.calc("AMB Years", "[year] >= 2010 AND [year] <= 2025", "boolean")
con.calc("E4 Match", f'[concentration_type] = "geographic (UF, AMB value)" AND [year] = {{{{p Year}}}} '
         f'AND [scope] = (IF {SUB_ALL} THEN "All substances" ELSE {{{{p Substance}}}} END)', "boolean")
con.calc("E4 Label", f'"GEOGRAPHIC HHI (STATES) · " + (IF {SUB_ALL} THEN "ALL SUBSTANCES" ELSE UPPER({{{{p Substance}}}}) END)', "string")
con.calc("M1 Match", '[concentration_type] = {{p Concentration Type}} AND (IF [concentration_type] = "commodity mix (AMB value)" '
         f'THEN [scope] = "Brazil" ELSE [scope] = {FOCUS} END)', "boolean")
con.calc("M3 Match", '[concentration_type] = "business (CNPJ root, CFEM)" AND [year] = {{p CFEM Year}} AND [total_value_brl] >= 50000000', "boolean")
con.calc("Is Focus Scope", f"[scope] = {FOCUS}", "boolean")
con.calc("HHI", "MAX([hhi])", "real", INT)
meta.calc("Row", '" "', "string")

# ---- sheets (guide §4) ------------------------------------------------------------------
HL = {s: F700 for s in SUBSTANCES}
HL["Other substances"] = CONTEXT
TF = {"true": F700, "false": CONTEXT}
SH_COL = {"All": F600, "Selected": F700, "Other": CONTEXT}
YEAR = F("year", kind="ok")
SEL_SUB_UF = [(F("Substance Filter"), None), (F("State Filter"), None)]
TOP_SUB_EXPR = f"SUM(IF [year] = {{{{p Year}}}} AND ({UF_ALL} OR [uf] = {{{{p State}}}}) THEN [sale_value_brl] END)"
TOP_UF_EXPR = f"SUM(IF [year] = {{{{p Year}}}} AND ({SUB_ALL} OR [substance_group] = {{{{p Substance}}}}) THEN [sale_value_brl] END)"
TOP_MUN_EXPR = (f"SUM(IF [year] = {{{{p CFEM Year}}}} AND ({SUB_ALL} OR [main_substance_group] = {{{{p Substance}}}}) "
                f"AND ({UF_ALL} OR [uf] = {{{{p State}}}}) THEN [cfem_brl] END)")


def eyebrow(t, color=INK3):
    return {"text": t, "font": "Consolas", "size": 8, "color": color}


def tt(*parts):
    return [{"field": p} if isinstance(p, F) else {"text": p} for p in parts]


wb.sheet(name="E1 KPI Value", ds=ufs, mark="Text", bg=FOREST, filters=SEL_SUB_UF,
         text=[F("Selection Label"), F("KPI Value (R$ bn)"), F("YoY Arrow"), F("KPI Value YoY")],
         label=[eyebrow("VALUE OF SALES · ", SAGE), {"field": F("Selection Label"), "font": "Consolas", "size": 8, "color": SAGE}, {"br": True},
                {"text": "R$ ", "size": 24, "color": ON_FOREST}, {"field": F("KPI Value (R$ bn)"), "size": 24, "color": ON_FOREST},
                {"text": " bn", "size": 24, "color": ON_FOREST}, {"br": True},
                {"field": F("YoY Arrow"), "size": 9, "color": SAGE}, {"field": F("KPI Value YoY"), "size": 9, "color": SAGE},
                {"text": " vs previous year", "size": 9, "color": SAGE}])
wb.sheet(name="E2 KPI CAGR", ds=ufs, mark="Text", filters=SEL_SUB_UF, text=[F("KPI CAGR since 2010")],
         label=[eyebrow("GROWTH SINCE 2010 (CAGR, NOMINAL)"), {"br": True}, {"field": F("KPI CAGR since 2010"), "size": 24},
                {"br": True}, {"text": "compound annual growth of sales value", "size": 9, "color": INK3}])
wb.sheet(name="E3 KPI Substance share", ds=sub, mark="Text", text=[F("Focus Label"), F("KPI Focus Share"), F("Focus Rank"), F("KPI Top3 Share")],
         label=[eyebrow("NATIONAL SHARE · "), {"field": F("Focus Label"), "font": "Consolas", "size": 8, "color": INK3}, {"br": True},
                {"field": F("KPI Focus Share"), "size": 24}, {"br": True}, {"text": "rank ", "size": 9, "color": INK3},
                {"field": F("Focus Rank"), "size": 9, "color": INK3}, {"text": " · top 3: ", "size": 9, "color": INK3},
                {"field": F("KPI Top3 Share"), "size": 9, "color": INK3}])
wb.sheet(name="E4 KPI Geographic HHI", ds=con, mark="Text", text=[F("E4 Label"), F("HHI"), F("hhi_band", "attr")],
         filters=[(F("E4 Match"), None)],
         label=[{"field": F("E4 Label"), "font": "Consolas", "size": 8, "color": INK3}, {"br": True}, {"field": F("HHI"), "size": 24},
                {"br": True}, {"field": F("hhi_band", "attr"), "size": 9, "color": INK3}])
wb.sheet(name="E5 Annual evolution", ds=ufs, mark="Bar", cols=[YEAR], rows=[F("Value (R$ bn)")], filters=SEL_SUB_UF,
         color=F("Is Selected Year"), color_map=TF, title="Annual evolution · R$ bn (nominal) · click a year",
         tooltip=[F("Value YoY")], tooltip_text=tt(YEAR, ": R$ ", F("Value (R$ bn)"), " bn · YoY ", F("Value YoY")))
wb.sheet(name="E6 Regional share map", ds=ufs, mark="Multipolygon", geo=F("uf"), color=F("State Share"), color_seq=SEQ,
         filters=[(F("Is Selected Year"), None), (F("Substance Filter"), None)],
         title="Where the value is produced · click a state",
         tooltip=[F("State Name"), F("Value (R$ bn)")],
         tooltip_text=tt(F("State Name"), " · ", F("State Share"), " of the selected value · R$ ", F("Value (R$ bn)"), " bn"))
wb.sheet(name="E7 Top substances", ds=ufs, mark="Bar", rows=[F("substance_group")], cols=[F("Value (R$ bn)")],
         color=F("Highlight Substance"), color_map=HL, filters=[(F("Is Selected Year"), None), (F("State Filter"), None)],
         topn=(F("substance_group"), 10, TOP_SUB_EXPR),
         sort=(F("substance_group"), F("sale_value_brl", "sum"), "DESC"), text=[F("Substance Share")], labels=True,
         title="Top substances by sales value · click a substance",
         tooltip_text=tt(F("substance_group"), " · R$ ", F("Value (R$ bn)"), " bn · ", F("Substance Share"), " of the selected state(s)"))

wb.sheet(name="R1 State ranking", ds=ufs, mark="Bar", rows=[F("State Name")], cols=[F("Value (R$ bn)")],
         color=F("State Highlight"), color_map=SH_COL, filters=[(F("Is Selected Year"), None), (F("Substance Filter"), None)],
         topn=(F("State Name"), 15, TOP_UF_EXPR), detail=[F("uf")],
         sort=(F("State Name"), F("sale_value_brl", "sum"), "DESC"), text=[F("State Label")], labels=True,
         title="State ranking · top 15 · click a state",
         tooltip_text=tt(F("State Name"), ": R$ ", F("Value (R$ bn)"), " bn · ", F("State Share"), " of the selected value"))
wb.sheet(name="R2 State x substance", ds=ufs, mark="Square", rows=[F("substance_group")], cols=[F("uf")],
         color=F("uf_share_of_substance", "sum"), color_seq=SEQ, filters=[(F("Is Selected Year"), None), (F("State Filter"), None)],
         title="Who holds each substance · state share of national value · click a cell",
         tooltip=[F("uf_share_of_substance", "sum"), F("DQ Caveat")],
         tooltip_text=tt(F("uf"), " holds ", F("uf_share_of_substance", "sum"), " of national ", F("substance_group"), " value ", F("DQ Caveat")))
wb.sheet(name="R3 Substance evolution", ds=ufs, mark="Line", cols=[YEAR], rows=[F("Value (R$ bn)")], filters=[(F("State Filter"), None)],
         color=F("Highlight Substance"), color_map=HL, detail=[F("substance_group")], title="Substance evolution · R$ bn · click a line",
         tooltip_text=tt(F("substance_group"), " ", YEAR, ": R$ ", F("Value (R$ bn)"), " bn"))
wb.sheet(name="R4 Volume vs unit value", ds=pv, mark="Bar", cols=[YEAR], rows=[F("Multiple Values")],
         measure_values=[F("volume_effect_logpts", "sum"), F("unit_value_effect_logpts", "sum")],
         color_map={"volume_effect_logpts": F700, "unit_value_effect_logpts": SAGE},
         filters=[(F("Is Focus Substance"), None)], title="Volume vs unit-value effect · log-points (national; iron ore when All)",
         tooltip=[F("volume_effect_logpts", "sum"), F("unit_value_effect_logpts", "sum"), F("unit_value_brl", "sum"), F("unit", "attr"),
                  F("substance_group", "attr")],
         tooltip_text=tt(F("substance_group", "attr"), " ", YEAR, ": volume ", F("volume_effect_logpts", "sum"), " log-pts, unit value ",
                         F("unit_value_effect_logpts", "sum"), " log-pts; unit value R$ ", F("unit_value_brl", "sum"), " per ", F("unit", "attr")))
wb.sheet(name="R5 Production volume", ds=ufs, mark="Line", cols=[YEAR], rows=[F("production_qty", "sum")],
         filters=[(F("Is Focus Substance"), None), (F("State Filter"), None)], mark_color=F600,
         title="Production volume (selected substance and state)", tooltip=[F("unit", "attr")],
         axis_titles={F("production_qty", "sum"): "quantity (unit in tooltip)"},
         tooltip_text=tt(YEAR, ": ", F("production_qty", "sum"), " ", F("unit", "attr")))

wb.sheet(name="M1 HHI over time", ds=con, mark="Line", cols=[YEAR], rows=[F("HHI")], mark_color=F700,
         filters=[(F("M1 Match"), None)], reflines=[1500, 2500], title="HHI over time (1,500 / 2,500) · iron ore when All",
         tooltip=[F("hhi_band", "attr"), F("n_participants", "sum"), F("cr4_pct", "sum"), F("scope", "attr")],
         tooltip_text=tt(F("scope", "attr"), " ", YEAR, ": HHI ", F("HHI"), " (", F("hhi_band", "attr"), "), N = ", F("n_participants", "sum"),
                         ", CR4 ", F("cr4_pct", "sum"), "%"))
wb.sheet(name="M2 Company Pareto", ds=cfc, mark="Bar", rows=[F("Company Label")], cols=[F("CFEM (R$ mn)")],
         color=F("Is Top Company"), color_map=TF,
         filters=[(F("Is Selected CFEM Year"), None), (F("Is Focus Substance"), None), (F("Top 10"), None)],
         sort=(F("Company Label"), F("rank", "sum"), "ASC"), text=[F("share_in_substance", "sum"), F("cumulative_share", "sum")],
         label=[{"field": F("share_in_substance", "sum"), "size": 9}, {"text": " · cum. ", "size": 9, "color": INK3},
                {"field": F("cumulative_share", "sum"), "size": 9, "color": WARN}], labels=True,
         title="Company Pareto · CFEM (legal entity, not group) · iron ore when All",
         tooltip=[F("company_name")],
         tooltip_text=tt(F("company_name"), " · R$ ", F("CFEM (R$ mn)"), " mn · ", F("share_in_substance", "sum"), " · cumulative ",
                         F("cumulative_share", "sum"), ". Legal entity, not group. CFEM = royalty collected"))
wb.sheet(name="M3 Concentration table", ds=con, mark="Text", rows=[F("scope"), F("top_participant")], cols=[F(":Measure Names")],
         text=[F("Multiple Values")], measure_values=[F("hhi", "max"), F("cr1_pct", "max"), F("cr4_pct", "max"), F("n_participants", "max")],
         filters=[(F("M3 Match"), None)], sort=(F("scope"), F("hhi", "max"), "DESC"),
         title="Business concentration by substance (CFEM ≥ R$ 50 mn) · click a row")
wb.sheet(name="M4 Municipal concentration", ds=cfm, mark="Bar", rows=[F("Municipality Label")], cols=[F("CFEM (R$ mn)")],
         color=F("Is Top 2"), color_map=TF, filters=[(F("Is Selected CFEM Year"), None), (F("Substance Filter"), None), (F("State Filter"), None)],
         topn=(F("Municipality Label"), 15, TOP_MUN_EXPR), detail=[F("uf")],
         sort=(F("Municipality Label"), F("cfem_brl", "sum"), "DESC"), text=[F("Municipal Share")], labels=True,
         title="Municipal concentration · top 15 · click a municipality", tooltip=[F("main_substance_group")],
         tooltip_text=tt(F("Municipality Label"), " · R$ ", F("CFEM (R$ mn)"), " mn · ", F("Municipal Share"), " of national CFEM · main: ",
                         F("main_substance_group"), ". CFEM = royalty collected"))
wb.sheet(name="M5 Mix change", ds=sub, mark="Area", cols=[YEAR], rows=[F("share_of_national", "sum")],
         color=F("Highlight Substance"), color_map=HL, title="Mix change · share of value", detail=[F("substance_group")],
         axis_titles={F("share_of_national", "sum"): ""},
         tooltip_text=tt(F("substance_group"), " ", YEAR, ": ", F("share_of_national", "sum")))
wb.sheet(name="M6 CFEM per R$ of sales", ds=amc, mark="Line", cols=[YEAR], rows=[F("Multiple Values")],
         measure_values=[F("CFEM per R$ of Sales"), F("CFEM per R$ of Sales (selected)")],
         color_map={"CFEM per R$ of Sales": F700, "CFEM per R$ of Sales (selected)": SAGE},
         filters=[(F("AMB Years"), None), (F("State Filter"), None)], title="CFEM per R$ of sales · all mapped vs selected substance",
         tooltip_text=tt(YEAR, ": all mapped ", F("CFEM per R$ of Sales"), " · selected ", F("CFEM per R$ of Sales (selected)"),
                         ". Indicator only: CFEM base is gross revenue and cash timing; CFEM = royalty collected"))
wb.sheet(name="D1 Sources", ds=meta, mark="Text", rows=[F("source_key"), F("source_name"), F("coverage"), F("note"), F("url")],
         text=[F("Row")], title="Sources")

# R2: the 12 largest groups of 2025 (a top-N inside a matrix would change rows with every click)
rows = [r for r in csv.DictReader(open(HERE / "data" / "amb_substance_year.csv", encoding="utf-8")) if r["year"] == "2025"]
top12 = [r["substance_group"] for r in sorted(rows, key=lambda r: int(r["rank_in_year"]))[:12]]
SH = {x.name: x for x in wb.sheets}
SH["R2 State x substance"].filters.append((F("substance_group"), top12))

# ---- dashboards (guide §5) ---------------------------------------------------------------
W, H, PAD, GAP = 1200, 926, 24, 12
BAND, SHIFT = 106, 26          # header band; body is shifted down by SHIFT versus the original 80 px band
COL = (W - 2 * PAD - 11 * GAP) / 12


def cx(c):
    return PAD + c * (COL + GAP)


def cw(n):
    return n * COL + (n - 1) * GAP


FOOT = "Source: ANM AMB & CFEM, snapshot 2026-11-18 · nominal R$ · CFEM is royalty, not revenue · click any bar, state or row to filter (All resets) · Stephany Alves"
PAGES = [("1 · Executive Overview", "Overview"), ("2 · Regional & Commodity", "Regional"),
         ("3 · Market Structure", "Market"), ("4 · Data & Methodology", "Method")]
PLABEL = {"p Year": "YEAR", "p CFEM Year": "CFEM YEAR", "p Substance": "SUBSTANCE", "p State": "STATE",
          "p Concentration Type": "CONCENTRATION"}


def header(title, params, current):
    """Dark band: eyebrow + title (left), page buttons (top right); one row of filters along the bottom of the band."""
    z = [{"type": "text", "x": 0, "y": 0, "w": W, "h": BAND, "bg": FOREST, "border": False, "margin": 0,
          "runs": [{"text": " "}]},
         {"type": "text", "x": PAD, "y": 10, "w": 560, "h": 54, "bg": FOREST, "border": False, "margin": 0,
          "runs": [{"text": "BRAZILIAN MINING · AMB + CFEM", "font": "Consolas", "size": 8, "color": SAGE, "br": True},
                   {"text": title, "font": "Georgia", "size": 22, "color": ON_FOREST}]}]
    bw, bg_ = 96, 6
    x = W - PAD - len(PAGES) * bw - (len(PAGES) - 1) * bg_
    for name, cap in PAGES:
        on = name == current
        z.append({"type": "nav", "target": name, "caption": cap, "x": x, "y": 14, "w": bw, "h": 28,
                  "bg": SAGE if on else F600, "fg": FOREST if on else ON_FOREST, "border": False})
        x += bw + bg_
    x = PAD
    for p, w in params:
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
GLOBAL = [("p Year", 90), ("p Substance", 190), ("p State", 120)]
TOP, BOT = BAND + 12, H - 40      # body area between the dark band and the footer; rows share it with no orphan gaps
D1 = PAGES[0][0]
y1 = TOP + 104 + 10
y2 = y1 + 26
y3 = y2 + 322 + GAP
wb.dashboard(D1, W, H, header("Executive Overview", GLOBAL, D1) + [
    sheet("E1 KPI Value", 0, 3, TOP, 104, False, FOREST), sheet("E2 KPI CAGR", 3, 3, TOP, 104, False),
    sheet("E3 KPI Substance share", 6, 3, TOP, 104, False), sheet("E4 KPI Geographic HHI", 9, 3, TOP, 104, False),
    note("Value is 4.6× 2010 in nominal terms; for iron ore, gold and copper, unit value rose more than volume.", 0, 7, y1, 22),
    note("Iron ore is 56.7 % of value in 2025, down from 75.8 % in 2021.", 7, 5, y1, 22),
    sheet("E5 Annual evolution", 0, 7, y2, 322), sheet("E6 Regional share map", 7, 5, y2, 322),
    sheet("E7 Top substances", 0, 12, y3, BOT - y3)] + footer(), PAGE)
H2 = 1120
r2 = TOP + 380 + GAP
r3 = r2 + 330 + GAP
wb.dashboard(PAGES[1][0], W, H2, header("Regional & Commodity Analysis", GLOBAL, PAGES[1][0]) + [
    sheet("R1 State ranking", 0, 5, TOP, 380), sheet("R2 State x substance", 5, 7, TOP, 380),
    sheet("R3 Substance evolution", 0, 6, r2, 330), sheet("R4 Volume vs unit value", 6, 6, r2, 330),
    sheet("R5 Production volume", 0, 12, r3, H2 - 40 - r3)] + footer(H2), PAGE)
H3 = 1190
m1 = TOP + 26
m2 = m1 + 290 + GAP
m3 = m2 + 370 + GAP
wb.dashboard(PAGES[2][0], W, H3, header("Market Structure", [("p CFEM Year", 90), ("p Substance", 180), ("p State", 110),
                                                             ("p Concentration Type", 210)], PAGES[2][0]) + [
    note("Geographic concentration ≠ business concentration: states (AMB value) and CNPJ roots (CFEM) answer different questions.",
         0, 12, TOP, 22, color=WARN),
    sheet("M1 HHI over time", 0, 6, m1, 290), sheet("M6 CFEM per R$ of sales", 6, 6, m1, 290),
    sheet("M2 Company Pareto", 0, 6, m2, 370), sheet("M4 Municipal concentration", 6, 6, m2, 370),
    sheet("M3 Concentration table", 0, 7, m3, H3 - 40 - m3), sheet("M5 Mix change", 7, 5, m3, H3 - 40 - m3)] + footer(H3), PAGE)
METH = [
    ("DEFINITIONS", "K1 value of beneficiated sales (AMB, nominal R$) · K13 HHI = Σ share² × 10,000 (≥ 2,500 highly concentrated, "
     "1,500–2,500 moderate) · K15 CFEM = royalty collected, not revenue."),
    ("PERIOD", "AMB 2010–2025 (base years). CFEM 2004 – Jun 2026 (usable months; 2026 partial)."),
    ("RULES", "T8 substance collapse into groups · T13 duplicate CFEM export of Feb 2024 removed · completeness checks per year."),
    ("RESTRICTIONS", "Nominal values (no deflation) · legal entity (CNPJ root) ≠ economic group · ES iron-ore caveat "
     "(pellet plants report sales of ore mined in MG) · no municipal map."),
    ("HOW TO USE", "The YEAR, SUBSTANCE and STATE boxes filter every page. Clicking a bar, a state, a heatmap cell or a table row sets "
     "them and the choice follows you across pages; pick All in the box to reset. Views that need one substance (price × volume, HHI, company Pareto) show iron ore when All is selected."),
    ("UPDATE", "From mining-intelligence/: powershell -ExecutionPolicy Bypass -File src\\run_pipeline.ps1 -Download, then refresh the extracts."),
]
mz, y = [], 440
for i, (k, v) in enumerate(METH):
    c = 0 if i % 2 == 0 else 6
    mz.append({"type": "text", "x": cx(c), "y": y, "w": cw(6), "h": 120, "bg": PAPER, "margin": 12,
               "runs": [{"text": k, "font": "Consolas", "size": 8, "color": INK3, "br": True}, {"text": v, "size": 10, "color": INK2}]})
    if i % 2 == 1:
        y += 132
wb.dashboard(PAGES[3][0], W, H, header("Data & Methodology", [], PAGES[3][0]) + body([sheet("D1 Sources", 0, 12, Y0, 330)] + mz) + footer(), PAGE)

# ---- interactions: every click sets a global filter; deselecting resets it ------------------------------
D1, D2, D3 = PAGES[0][0], PAGES[1][0], PAGES[2][0]
wb.param_action("Year from E5", D1, ["E5 Annual evolution"], YEAR, ufs, "p Year")
wb.param_action("Substance from E7", D1, ["E7 Top substances"], F("substance_group"), ufs, "p Substance")
wb.param_action("State from map", D1, ["E6 Regional share map"], F("uf"), ufs, "p State")
wb.param_action("State from R1", D2, ["R1 State ranking"], F("uf"), ufs, "p State")
wb.param_action("State from R2", D2, ["R2 State x substance"], F("uf"), ufs, "p State")
wb.param_action("Substance from R2", D2, ["R2 State x substance"], F("substance_group"), ufs, "p Substance")
wb.param_action("Substance from R3", D2, ["R3 Substance evolution"], F("substance_group"), ufs, "p Substance")
wb.param_action("Year from R4", D2, ["R4 Volume vs unit value"], YEAR, pv, "p Year")
wb.param_action("Substance from M3", D3, ["M3 Concentration table"], F("scope"), con, "p Substance")
wb.param_action("Substance from M5", D3, ["M5 Mix change"], F("substance_group"), sub, "p Substance")
wb.param_action("State from M4", D3, ["M4 Municipal concentration"], F("uf"), cfm, "p State")

if __name__ == "__main__":
    out = HERE / "Brazilian_Mining_Performance.twb"
    wb.save(out)
    print(out)
