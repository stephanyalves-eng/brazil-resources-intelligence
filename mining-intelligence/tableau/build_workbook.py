"""Generates the Brazilian Mining Performance workbook (.twb) from TABLEAU_BUILD_GUIDE.md.

The .twb is opened in Tableau Public 2026.3, checked against guide §7, finished in the UI
(reference lines, actions, navigation) and saved locally as a packaged .twbx.
Run:  python mining-intelligence/tableau/build_workbook.py
"""
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

wb = Workbook("Brazilian Mining Performance")
P = wb.params
P.add("p Year", "integer", 2025, members=list(range(2010, 2026)), fmt="n0;-0")
P.add("p CFEM Year", "integer", 2025, members=list(range(2004, 2026)), fmt="n0;-0")
SUBSTANCES = [line.split(",")[0] for line in (HERE / "data" / "dim_substance.csv").read_text(encoding="utf-8").splitlines()[1:]]
P.add("p Substance", "string", "Iron ore", members=SUBSTANCES)
CTYPES = ["geographic (UF, AMB value)", "commodity mix (AMB value)", "business (CNPJ root, CFEM)"]
P.add("p Concentration Type", "string", "business (CNPJ root, CFEM)", members=CTYPES)


def source(table, caption=None):
    cols = columns_from_dictionary(DICT, table, {"year": ("integer", "dimension", "ordinal")})
    for c in cols:
        if c.name == "[uf]":
            c.semantic_role = "[State].[Name]"
        n = c.name.strip("[]")
        if c.role == "measure" and ("share" in n or n.endswith("_rate")):
            c.default_format = "p0.0%"
        if c.role == "measure" and n.endswith("_yoy"):
            c.default_format = "*+0.0%;-0.0%"
        if n in ("hhi", "sale_value_brl", "cfem_brl", "production_qty", "amb_sale_value_brl", "total_value_brl"):
            c.default_format = "n#,##0"
        if c.name in ("[company_key]", "[ibge_municipality_code]"):
            c.datatype, c.role, c.type = "string", "dimension", "nominal"
    return wb.datasource(caption or table, DATA, f"{table}.csv", cols)


nat = source("amb_national_year")
sub = source("amb_substance_year")
ufy = source("amb_uf_year")
ufs = source("amb_uf_substance_year")
pv = source("amb_price_volume")
cfu = source("cfem_uf_substance_year")
cfm = source("cfem_municipality_year")
cfc = source("cfem_company_substance_year")
amc = source("amb_cfem_uf_substance_year")
con = source("concentration")
cmo = source("cfem_monthly")
meta = source("metadata")
dimu = source("dim_uf")
dims = source("dim_substance")

BN = "1000000000"
PCT, YOY, BNF, INT = "p0.0%", "*+0.0%;-0.0%", "n#,##0.0", "n#,##0"

# ---- calculated fields (guide §3) -------------------------------------------------------
nat.calc("KPI Value (R$ bn)", f"SUM(IF [year] = {{{{p Year}}}} THEN [sale_value_brl] END) / {BN}", "real", BNF)
nat.calc("KPI Value Prev (R$ bn)", f"SUM(IF [year] = {{{{p Year}}}} - 1 THEN [sale_value_brl] END) / {BN}", "real", BNF)
nat.calc("KPI Value YoY", "IF {{KPI Value Prev (R$ bn)}} > 0 THEN {{KPI Value (R$ bn)}} / {{KPI Value Prev (R$ bn)}} - 1 END", "real", YOY)
nat.calc("KPI CAGR since 2010", "IF {{p Year}} > 2010 THEN POWER({{KPI Value (R$ bn)}} / (SUM(IF [year] = 2010 THEN [sale_value_brl] END) / "
         + BN + "), 1 / ({{p Year}} - 2010)) - 1 END", "real", YOY)
nat.calc("Value (R$ bn)", f"SUM([sale_value_brl]) / {BN}", "real", BNF)
nat.calc("YoY Arrow", 'IF {{KPI Value YoY}} >= 0 THEN "▲ " ELSE "▼ " END', "string")
nat.calc("Is Selected Year", "[year] = {{p Year}}", "boolean")

sub.calc("KPI Iron Share", 'SUM(IF [year] = {{p Year}} AND [substance_group] = "Iron ore" THEN [sale_value_brl] END) '
         "/ SUM(IF [year] = {{p Year}} THEN [sale_value_brl] END)", "real", PCT)
sub.calc("KPI Top3 Share", "SUM(IF [year] = {{p Year}} AND [rank_in_year] <= 3 THEN [sale_value_brl] END) "
         "/ SUM(IF [year] = {{p Year}} THEN [sale_value_brl] END)", "real", PCT)
sub.calc("Highlight Substance", 'IF [substance_group] = {{p Substance}} THEN [substance_group] ELSE "Other substances" END', "string")
sub.calc("Value (R$ bn)", f"SUM([sale_value_brl]) / {BN}", "real", BNF)
sub.calc("Is Selected Year", "[year] = {{p Year}}", "boolean")
sub.calc("Is Selected Substance", "[substance_group] = {{p Substance}}", "boolean")
sub.calc("Top 10 in Year", "[rank_in_year] <= 10", "boolean")
sub.calc("Share (recomputed)", "SUM([sale_value_brl]) / TOTAL(SUM([sale_value_brl]))", "real", PCT)

ufy.calc("Is Selected Year", "[year] = {{p Year}}", "boolean")
ufy.calc("State Label", 'ATTR([uf_name]) + " · " + STR(ROUND(SUM([share_of_national]) * 100, 1)) + "%"', "string")
ufy.calc("Value (R$ bn)", f"SUM([sale_value_brl]) / {BN}", "real", BNF)
ufy.calc("Is Top 2", "[rank_in_year] <= 2", "boolean")
ufy.calc("Top 15 States", "[rank_in_year] <= 15", "boolean")
ufy.calc("Rank Change Arrow", 'IF [rank_change] > 0 THEN "▲" + STR([rank_change]) ELSEIF [rank_change] < 0 THEN "▼" + STR(-[rank_change]) ELSE "=" END', "string")

ufs.calc("Is Selected Year", "[year] = {{p Year}}", "boolean")
ufs.calc("Quantity (selected group)", "IF [substance_group] = {{p Substance}} THEN [production_qty] END", "real", INT)
ufs.calc("DQ Caveat", 'IF [dq_flag_intermittent_series] THEN "Intermittent reporting (see methodology)" END', "string")

pv.calc("Unit Value", "SUM([sale_value_brl]) / SUM([sale_qty])", "real", "n#,##0.00")
pv.calc("Is Selected Substance", "[substance_group] = {{p Substance}}", "boolean")

for d in (cfu, cfm):
    d.calc("CFEM (R$ mn)", "SUM([cfem_brl]) / 1000000", "real", INT)
    d.calc("Is Selected CFEM Year", "[year] = {{p CFEM Year}}", "boolean")
# share of ALL municipalities in the year (FIXED ignores the top-15 filter; TOTAL would only see the 15 bars)
cfm.calc("Municipal Share", "SUM([cfem_brl]) / MIN({FIXED [year] : SUM([cfem_brl])})", "real", PCT)
cfm.calc("KPI Top10 Municipal Share", "SUM(IF [year] = {{p CFEM Year}} AND [rank_in_year] <= 10 THEN [cfem_brl] END) "
         "/ SUM(IF [year] = {{p CFEM Year}} THEN [cfem_brl] END)", "real", PCT)
cfm.calc("Top 15", "[rank_in_year] <= 15", "boolean")
cfm.calc("Is Top 2", "[rank_in_year] <= 2", "boolean")
cfm.calc("Municipality Label", '[municipality_name] + ", " + [uf]', "string")

cfc.calc("Company Label", 'IF [rank] <= 10 THEN STR([rank]) + ". " + [company_name] ELSE [company_name] END', "string")
cfc.calc("Is Top Company", "[rank] = 1", "boolean")
cfc.calc("Is Selected CFEM Year", "[year] = {{p CFEM Year}}", "boolean")
cfc.calc("Is Selected Substance", "[substance_group] = {{p Substance}}", "boolean")
cfc.calc("Top 10", "[rank] <= 10", "boolean")
cfc.calc("CFEM (R$ mn)", "SUM([cfem_brl]) / 1000000", "real", INT)

# same definition as sql/30_analysis.sql Q12 (all mapped UF × substance rows), which produced guide §7
amc.calc("CFEM per R$ of Sales", 'SUM([cfem_brl]) / SUM([amb_sale_value_brl])',
         "real", "p0.00%")
amc.calc("CFEM per R$ of Sales (selected)", 'SUM(IF [substance_group] = {{p Substance}} THEN [cfem_brl] END) '
         '/ SUM(IF [substance_group] = {{p Substance}} THEN [amb_sale_value_brl] END)', "real", "p0.00%")
amc.calc("AMB Years", "[year] >= 2010 AND [year] <= 2025", "boolean")

con.calc("E4 Match", '[concentration_type] = "geographic (UF, AMB value)" AND [scope] = "All substances" AND [year] = {{p Year}}', "boolean")
con.calc("M1 Match", '[concentration_type] = {{p Concentration Type}} AND (IF [concentration_type] = "commodity mix (AMB value)" '
         'THEN [scope] = "Brazil" ELSEIF [concentration_type] = "geographic (UF, AMB value)" AND {{p Substance}} = "" THEN [scope] = "All substances" '
         'ELSE [scope] = {{p Substance}} END)', "boolean")
con.calc("M3 Match", '[concentration_type] = "business (CNPJ root, CFEM)" AND [year] = {{p CFEM Year}} AND [total_value_brl] >= 50000000', "boolean")
con.calc("HHI", "MAX([hhi])", "real", INT)
meta.calc("Row", '" "', "string")

# ---- sheets (guide §4) ------------------------------------------------------------------
HL = {s: F700 for s in SUBSTANCES}
HL["Other substances"] = CONTEXT
TF = {"true": F700, "false": CONTEXT}


def eyebrow(t, color=INK3):
    return {"text": t, "font": "Consolas", "size": 8, "color": color}


wb.sheet(name="E1 KPI Value", ds=nat, mark="Text", bg=FOREST,
         text=[F("KPI Value (R$ bn)"), F("YoY Arrow"), F("KPI Value YoY")],
         label=[eyebrow("VALUE OF BENEFICIATED SALES", SAGE), {"br": True},
                {"text": "R$ ", "size": 24, "color": ON_FOREST}, {"field": F("KPI Value (R$ bn)"), "size": 24, "color": ON_FOREST},
                {"text": " bn", "size": 24, "color": ON_FOREST}, {"br": True},
                {"field": F("YoY Arrow"), "size": 9, "color": SAGE}, {"field": F("KPI Value YoY"), "size": 9, "color": SAGE},
                {"text": " vs previous year", "size": 9, "color": SAGE}])
wb.sheet(name="E2 KPI CAGR", ds=nat, mark="Text", text=[F("KPI CAGR since 2010")],
         label=[eyebrow("GROWTH SINCE 2010 (CAGR, NOMINAL)"), {"br": True}, {"field": F("KPI CAGR since 2010"), "size": 24},
                {"br": True}, {"text": "compound annual growth of sales value", "size": 9, "color": INK3}])
wb.sheet(name="E3 KPI Iron share", ds=sub, mark="Text", text=[F("KPI Iron Share"), F("KPI Top3 Share")],
         label=[eyebrow("IRON ORE SHARE OF VALUE"), {"br": True}, {"field": F("KPI Iron Share"), "size": 24},
                {"br": True}, {"text": "Top 3: ", "size": 9, "color": INK3}, {"field": F("KPI Top3 Share"), "size": 9, "color": INK3}])
wb.sheet(name="E4 KPI Geographic HHI", ds=con, mark="Text", text=[F("HHI"), F("hhi_band", "attr")],
         filters=[(F("E4 Match"), None)],
         label=[eyebrow("GEOGRAPHIC HHI (STATES)"), {"br": True}, {"field": F("HHI"), "size": 24},
                {"br": True}, {"field": F("hhi_band", "attr"), "size": 9, "color": INK3}])
wb.sheet(name="E5 Annual evolution", ds=nat, mark="Bar", cols=[F("year", kind="ok")], rows=[F("Value (R$ bn)")],
         color=F("Is Selected Year"), color_map=TF, title="Annual evolution · R$ bn (nominal)",
         tooltip=[F("year", kind="ok"), F("Value (R$ bn)"), F("value_yoy", "sum")],
         tooltip_text=[{"field": F("year", kind="ok")}, {"text": ": R$ "}, {"field": F("Value (R$ bn)")}, {"text": " bn · YoY "},
                       {"field": F("value_yoy", "sum")}])
wb.sheet(name="E6 Regional share map", ds=ufy, mark="Multipolygon", geo=F("uf"), color=F("share_of_national", "sum"), color_seq=SEQ,
         filters=[(F("Is Selected Year"), None)], title="Regional share of sales value",
         tooltip=[F("uf_name"), F("share_of_national", "sum"), F("rank_in_year", "sum"), F("value_yoy", "sum")],
         tooltip_text=[{"field": F("uf_name")}, {"text": " · "}, {"field": F("share_of_national", "sum")}, {"text": " of national · rank "},
                       {"field": F("rank_in_year", "sum")}, {"text": " · YoY "}, {"field": F("value_yoy", "sum")}])
wb.sheet(name="E7 Top substances", ds=sub, mark="Bar", rows=[F("substance_group")], cols=[F("Value (R$ bn)")],
         color=F("Highlight Substance"), color_map=HL, filters=[(F("Is Selected Year"), None), (F("Top 10 in Year"), None)],
         sort=(F("substance_group"), F("sale_value_brl", "sum"), "DESC"), text=[F("share_of_national", "sum")], labels=True,
         title="Top substances by sales value", tooltip=[F("Value (R$ bn)"), F("share_of_national", "sum"), F("value_yoy", "sum")],
         tooltip_text=[{"field": F("substance_group")}, {"text": " · R$ "}, {"field": F("Value (R$ bn)")}, {"text": " bn · "},
                       {"field": F("share_of_national", "sum")}, {"text": " · YoY "}, {"field": F("value_yoy", "sum")}])
wb.sheet(name="R1 State ranking", ds=ufy, mark="Bar", rows=[F("uf_name"), F("Rank Change Arrow")], cols=[F("Value (R$ bn)")],
         color=F("Is Top 2"), color_map=TF, filters=[(F("Is Selected Year"), None), (F("Top 15 States"), None)], detail=[F("uf")],
         sort=(F("uf_name"), F("sale_value_brl", "sum"), "DESC"), text=[F("State Label")], labels=True, title="State ranking · top 15 (click a state to filter the heatmap)",
         tooltip=[F("rank_in_year", "sum"), F("rank_change", "sum"), F("cumulative_share", "sum")],
         tooltip_text=[{"field": F("uf_name")}, {"text": ": rank "}, {"field": F("rank_in_year", "sum")}, {"text": " (change "},
                       {"field": F("rank_change", "sum")}, {"text": "), cumulative "}, {"field": F("cumulative_share", "sum")}])
TOP12_2025 = None  # filled below from the data
wb.sheet(name="R2 State x substance", ds=ufs, mark="Square", rows=[F("substance_group")], cols=[F("uf")],
         color=F("uf_share_of_substance", "sum"), color_seq=SEQ, filters=[(F("Is Selected Year"), None)],
         title="Who holds each substance · state share of national value",
         tooltip=[F("uf_share_of_substance", "sum"), F("DQ Caveat")],
         tooltip_text=[{"field": F("uf")}, {"text": " holds "}, {"field": F("uf_share_of_substance", "sum")}, {"text": " of national "},
                       {"field": F("substance_group")}, {"text": " value "}, {"field": F("DQ Caveat")}])
wb.sheet(name="R3 Substance evolution", ds=sub, mark="Line", cols=[F("year", kind="ok")], rows=[F("Value (R$ bn)")],
         color=F("Highlight Substance"), color_map=HL, detail=[F("substance_group")], title="Substance evolution · R$ bn",
         tooltip=[F("share_of_national", "sum")],
         tooltip_text=[{"field": F("substance_group")}, {"text": " "}, {"field": F("year", kind="ok")}, {"text": ": R$ "},
                       {"field": F("Value (R$ bn)")}, {"text": " bn, share "}, {"field": F("share_of_national", "sum")}])
wb.sheet(name="R4 Volume vs unit value", ds=pv, mark="Bar", cols=[F("year", kind="ok")], rows=[F("Multiple Values")],
         measure_values=[F("volume_effect_logpts", "sum"), F("unit_value_effect_logpts", "sum")],
         color_map={"volume_effect_logpts": F700, "unit_value_effect_logpts": SAGE},
         filters=[(F("Is Selected Substance"), None)], title="Volume vs unit-value effect · log-points",
         tooltip=[F("volume_effect_logpts", "sum"), F("unit_value_effect_logpts", "sum"), F("unit_value_brl", "sum"), F("unit", "attr")],
         tooltip_text=[{"field": F("year", kind="ok")}, {"text": ": volume "}, {"field": F("volume_effect_logpts", "sum")},
                       {"text": " log-pts, unit value "}, {"field": F("unit_value_effect_logpts", "sum")},
                       {"text": " log-pts; unit value R$ "}, {"field": F("unit_value_brl", "sum")},
                       {"text": " per "}, {"field": F("unit", "attr")}])
wb.sheet(name="R5 Production volume", ds=sub, mark="Line", cols=[F("year", kind="ok")], rows=[F("production_qty", "sum")],
         filters=[(F("Is Selected Substance"), None)], mark_color=F600, title="Production volume (selected substance)",
         tooltip=[F("unit", "attr")],
         tooltip_text=[{"field": F("year", kind="ok")}, {"text": ": "}, {"field": F("production_qty", "sum")}, {"text": " "},
                       {"field": F("unit", "attr")}])
wb.sheet(name="M1 HHI over time", ds=con, mark="Line", cols=[F("year", kind="ok")], rows=[F("HHI")], mark_color=F700,
         filters=[(F("M1 Match"), None)], title="HHI over time (1,500 / 2,500 thresholds)",
         tooltip=[F("hhi_band", "attr"), F("n_participants", "sum"), F("cr4_pct", "sum")],
         tooltip_text=[{"field": F("year", kind="ok")}, {"text": ": HHI "}, {"field": F("HHI")}, {"text": " ("},
                       {"field": F("hhi_band", "attr")}, {"text": "), N = "}, {"field": F("n_participants", "sum")},
                       {"text": ", CR4 "}, {"field": F("cr4_pct", "sum")}, {"text": "%"}])
wb.sheet(name="M2 Company Pareto", ds=cfc, mark="Bar", rows=[F("Company Label")], cols=[F("CFEM (R$ mn)")],
         color=F("Is Top Company"), color_map=TF,
         filters=[(F("Is Selected CFEM Year"), None), (F("Is Selected Substance"), None), (F("Top 10"), None)],
         sort=(F("Company Label"), F("rank", "sum"), "ASC"), text=[F("share_in_substance", "sum"), F("cumulative_share", "sum")],
         label=[{"field": F("share_in_substance", "sum"), "size": 9}, {"text": " · cum. ", "size": 9, "color": INK3},
                {"field": F("cumulative_share", "sum"), "size": 9, "color": WARN}], labels=True,
         title="Company Pareto · CFEM (legal entity, not group)",
         tooltip=[F("company_name")],
         tooltip_text=[{"field": F("company_name")}, {"text": " · R$ "}, {"field": F("CFEM (R$ mn)")}, {"text": " mn · "},
                       {"field": F("share_in_substance", "sum")}, {"text": " · cumulative "}, {"field": F("cumulative_share", "sum")},
                       {"text": ". Legal entity, not group. CFEM = royalty collected"}])
wb.sheet(name="M3 Concentration table", ds=con, mark="Text", rows=[F("scope"), F("top_participant")], cols=[F(":Measure Names")],
         text=[F("Multiple Values")], measure_values=[F("hhi", "max"), F("cr1_pct", "max"), F("cr4_pct", "max"), F("n_participants", "max")],
         filters=[(F("M3 Match"), None)], sort=(F("scope"), F("hhi", "max"), "DESC"),
         title="Business concentration by substance (CFEM ≥ R$ 50 mn)")
wb.sheet(name="M4 Municipal concentration", ds=cfm, mark="Bar", rows=[F("Municipality Label")], cols=[F("CFEM (R$ mn)")],
         color=F("Is Top 2"), color_map=TF, filters=[(F("Is Selected CFEM Year"), None), (F("Top 15"), None)],
         sort=(F("Municipality Label"), F("cfem_brl", "sum"), "DESC"), text=[F("Municipal Share")], labels=True,
         title="Municipal concentration · top 15", tooltip=[F("main_substance_group")],
         tooltip_text=[{"field": F("Municipality Label")}, {"text": " · R$ "}, {"field": F("CFEM (R$ mn)")}, {"text": " mn · main: "},
                       {"field": F("main_substance_group")}, {"text": ". CFEM = royalty collected"}])
wb.sheet(name="M5 Mix change", ds=sub, mark="Area", cols=[F("year", kind="ok")], rows=[F("share_of_national", "sum")],
         color=F("Highlight Substance"), color_map=HL, title="Mix change · share of value",
         tooltip_text=[{"field": F("Highlight Substance")}, {"text": " "}, {"field": F("year", kind="ok")}, {"text": ": "},
                       {"field": F("share_of_national", "sum")}])
wb.sheet(name="M6 CFEM per R$ of sales", ds=amc, mark="Line", cols=[F("year", kind="ok")], rows=[F("Multiple Values")],
         measure_values=[F("CFEM per R$ of Sales"), F("CFEM per R$ of Sales (selected)")],
         color_map={"CFEM per R$ of Sales": F700, "CFEM per R$ of Sales (selected)": SAGE},
         filters=[(F("AMB Years"), None)], title="CFEM per R$ of sales · all mapped vs selected substance",
         tooltip_text=[{"field": F("year", kind="ok")}, {"text": ": all mapped "}, {"field": F("CFEM per R$ of Sales")},
                       {"text": " · selected "}, {"field": F("CFEM per R$ of Sales (selected)")},
                       {"text": ". Indicator only: CFEM base is gross revenue and cash timing; CFEM = royalty collected"}])
wb.sheet(name="D1 Sources", ds=meta, mark="Text", rows=[F("source_key"), F("source_name"), F("coverage"), F("note"), F("url")],
         text=[F("Row")], title="Sources")

# R2 top 12 groups of 2025 (Top-N by p Year is applied in the UI)
import csv  # noqa: E402
rows = [r for r in csv.DictReader(open(HERE / "data" / "amb_substance_year.csv", encoding="utf-8")) if r["year"] == "2025"]
top12 = [r["substance_group"] for r in sorted(rows, key=lambda r: int(r["rank_in_year"]))[:12]]
wb.sheets[[s.name for s in wb.sheets].index("R2 State x substance")].filters.append((F("substance_group"), top12))

# ---- dashboards (guide §5) ---------------------------------------------------------------
W, H, PAD, GAP = 1200, 900, 24, 12
COL = (W - 2 * PAD - 11 * GAP) / 12


def cx(c):
    return PAD + c * (COL + GAP)


def cw(n):
    return n * COL + (n - 1) * GAP


FOOT = "Source: ANM AMB & CFEM, snapshot 2026-11-18 · nominal R$ · CFEM is royalty, not revenue · Stephany Alves"


PAGES = [("1 · Executive Overview", "Overview"), ("2 · Regional & Commodity", "Regional"),
         ("3 · Market Structure", "Market"), ("4 · Data & Methodology", "Method")]
PLABEL = {"p Year": "YEAR (AMB)", "p CFEM Year": "YEAR (CFEM)", "p Substance": "SUBSTANCE", "p Concentration Type": "CONCENTRATION TYPE"}


def header(title, params, current=None):
    z = [{"type": "text", "x": 0, "y": 0, "w": W, "h": 80, "bg": FOREST, "border": False, "margin": 16,
          "runs": [{"text": "BRAZILIAN MINING · AMB + CFEM", "font": "Consolas", "size": 8, "color": SAGE, "br": True},
                   {"text": title, "font": "Georgia", "size": 22, "color": ON_FOREST}]}]
    x = 300
    for name, cap in PAGES:
        on = name == current
        z.append({"type": "nav", "target": name, "caption": cap, "x": x, "y": 6, "w": 88, "h": 22,
                  "bg": SAGE if on else F600, "fg": FOREST if on else ON_FOREST})
        x += 92
    x = W - PAD
    for p, w in reversed(params):
        x -= w
        z.append({"type": "text", "x": x, "y": 10, "w": w, "h": 20, "bg": FOREST, "border": False, "margin": 2,
                  "runs": [{"text": PLABEL[p], "font": "Consolas", "size": 8, "color": SAGE}]})
        z.append({"type": "param", "param": p, "x": x, "y": 32, "w": w, "h": 36, "bg": FOREST, "border": False, "title": False})
        x -= 10
    return z


def footer():
    return [{"type": "text", "x": PAD, "y": H - 34, "w": W - 2 * PAD, "h": 28, "border": False,
             "runs": [{"text": FOOT, "size": 8, "color": INK3}]}]


def sheet(name, c, n, y, h):
    return {"type": "sheet", "sheet": name, "x": cx(c), "y": y, "w": cw(n), "h": h, "bg": SURFACE}


def note(text, c, n, y, h=26, color=INK2, bold=False, bg=None):
    z = {"type": "text", "x": cx(c), "y": y, "w": cw(n), "h": h, "border": False, "runs": [{"text": text, "size": 9, "color": color, "bold": bold}]}
    if bg:
        z["bg"] = bg
    return z


Y0 = 92
kpis = [sheet("E1 KPI Value", 0, 3, Y0, 110), sheet("E2 KPI CAGR", 3, 3, Y0, 110), sheet("E3 KPI Iron share", 6, 3, Y0, 110),
        sheet("E4 KPI Geographic HHI", 9, 3, Y0, 110)]
kpis[0]["bg"] = FOREST
for k in kpis:
    k["title"] = False
wb.dashboard("1 · Executive Overview", W, H, header("Executive Overview", [("p Year", 120), ("p Substance", 190)], PAGES[0][0]) + kpis + [
    note("Value is 4.6× 2010 in nominal terms; for iron ore, gold and copper, unit value rose more than volume.", 0, 7, 214),
    note("Iron ore is 56.7 % of value in 2025, down from 75.8 % in 2021.", 7, 5, 214),
    sheet("E5 Annual evolution", 0, 7, 242, 316), sheet("E6 Regional share map", 7, 5, 242, 316),
    sheet("E7 Top substances", 0, 12, 570, 290)] + footer(), PAGE)

wb.dashboard("2 · Regional & Commodity", W, H, header("Regional & Commodity Analysis", [("p Year", 120), ("p Substance", 190)], PAGES[1][0]) + [
    sheet("R1 State ranking", 0, 5, Y0, 380), sheet("R2 State x substance", 5, 7, Y0, 380),
    sheet("R3 Substance evolution", 0, 6, 484, 376), sheet("R4 Volume vs unit value", 6, 6, 484, 236),
    sheet("R5 Production volume", 6, 6, 732, 128)] + footer(), PAGE)

wb.dashboard("3 · Market Structure", W, H, header("Market Structure",
                                                  [("p CFEM Year", 100), ("p Concentration Type", 200), ("p Substance", 170)], PAGES[2][0]) + [
    sheet("M1 HHI over time", 0, 6, Y0, 250), sheet("M6 CFEM per R$ of sales", 0, 6, 354, 110),
    sheet("M2 Company Pareto", 6, 6, Y0, 372),
    note("Geographic concentration ≠ business concentration: states (AMB value) and CNPJ roots (CFEM) answer different questions.",
         0, 12, 474, color=WARN),
    sheet("M3 Concentration table", 0, 5, 504, 356), sheet("M4 Municipal concentration", 5, 4, 504, 356),
    sheet("M5 Mix change", 9, 3, 504, 356)] + footer(), PAGE)

METH = [
    ("DEFINITIONS", "K1 value of beneficiated sales (AMB, nominal R$) · K13 HHI = Σ share² × 10,000 (≥ 2,500 highly concentrated, "
     "1,500–2,500 moderate) · K15 CFEM = royalty collected, not revenue."),
    ("PERIOD", "AMB 2010–2025 (base years). CFEM 2004 – Jun 2026 (usable months; 2026 partial)."),
    ("RULES", "T8 substance collapse into groups · T13 duplicate CFEM export of Feb 2024 removed · completeness checks per year."),
    ("RESTRICTIONS", "Nominal values (no deflation) · legal entity (CNPJ root) ≠ economic group · ES iron-ore caveat "
     "(pellet plants report sales of ore mined in MG) · no municipal map."),
    ("UPDATE", "From mining-intelligence/: powershell -ExecutionPolicy Bypass -File src\\run_pipeline.ps1 -Download, then refresh the extracts."),
]
mz = []
y = 440
for i, (k, v) in enumerate(METH):
    c = 0 if i % 2 == 0 else 6
    mz.append({"type": "text", "x": cx(c), "y": y, "w": cw(6), "h": 120, "bg": PAPER, "margin": 12,
               "runs": [{"text": k, "font": "Consolas", "size": 8, "color": INK3, "br": True}, {"text": v, "size": 10, "color": INK2}]})
    if i % 2 == 1:
        y += 132
wb.dashboard("4 · Data & Methodology", W, H, header("Data & Methodology", [], PAGES[3][0]) + [sheet("D1 Sources", 0, 12, Y0, 330)] + mz + footer(), PAGE)

# ---- interactions (guide §6) --------------------------------------------------------------
wb.param_action("Select substance (E7)", "1 · Executive Overview", ["E7 Top substances"], F("substance_group"), sub, "p Substance")
wb.param_action("Select year (E5)", "1 · Executive Overview", ["E5 Annual evolution"], F("year", kind="ok"), nat, "p Year")
wb.param_action("Select substance (R3)", "2 · Regional & Commodity", ["R3 Substance evolution"], F("substance_group"), sub, "p Substance")
wb.param_action("Select substance (M5)", "3 · Market Structure", ["M5 Mix change"], F("Highlight Substance"), sub, "p Substance")
wb.filter_action("State drill (R1 → R2)", "2 · Regional & Commodity", ["R1 State ranking"], ["R2 State x substance"])
SH = {x.name: x for x in wb.sheets}
SH["M1 HHI over time"].reflines = [1500, 2500]

if __name__ == "__main__":
    out = HERE / "Brazilian_Mining_Performance.twb"
    wb.save(out)
    print(out)
