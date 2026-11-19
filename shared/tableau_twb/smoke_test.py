"""Smoke test of the .twb writer: 1 source, 1 parameter, 2 calcs, 2 sheets, 1 dashboard."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from twb import F, Workbook, columns_from_dictionary  # noqa: E402

ROOT = Path(__file__).resolve().parents[2] / "mining-intelligence"
DATA = (ROOT / "tableau" / "data").as_posix()
DICT = str(ROOT / "tableau" / "data_dictionary.csv")

wb = Workbook("smoke")
wb.params.add("p Year", "integer", 2025, members=list(range(2010, 2026)))
ds = wb.datasource("amb_national_year", DATA, "amb_national_year.csv",
                   columns_from_dictionary(DICT, "amb_national_year", {"year": ("integer", "dimension", "ordinal")}))
ds.calc("Value (R$ bn)", "SUM([sale_value_brl]) / 1e9", "real", fmt="n#,##0.0")
ds.calc("Is Selected Year", "[year] = {{p Year}}", "boolean")
wb.sheet(name="Smoke bars", ds=ds, cols=[F("year", kind="ok")], rows=[F("Value (R$ bn)")], mark="Bar",
         color=F("Is Selected Year"), color_map={"true": "#1E5246", "false": "#D6D8D2"}, title="Annual value (R$ bn)")
wb.sheet(name="Smoke KPI", ds=ds, mark="Text", text=[F("Value (R$ bn)")], filters=[(F("Is Selected Year"), None)])
wb.dashboard("Smoke dashboard", 1200, 600, [
    {"type": "text", "x": 0, "y": 0, "w": 1200, "h": 70, "bg": "#0B302B", "border": False,
     "runs": [{"text": "SMOKE TEST", "color": "#B8C9C0", "size": 8, "br": True},
              {"text": "Brazilian Mining", "color": "#F5F4EC", "font": "Georgia", "size": 22}]},
    {"type": "param", "param": "p Year", "x": 960, "y": 15, "w": 220, "h": 45, "bg": "#0B302B", "border": False},
    {"type": "sheet", "sheet": "Smoke KPI", "x": 16, "y": 86, "w": 280, "h": 110, "bg": "#FFFFFF"},
    {"type": "sheet", "sheet": "Smoke bars", "x": 312, "y": 86, "w": 872, "h": 500, "bg": "#FFFFFF"},
], background="#F5F4EC")
out = Path(__file__).parent / "smoke_test.twb"
wb.save(out)
print(out)
