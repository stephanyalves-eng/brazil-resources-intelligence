"""Generate notebooks/01_walkthrough.ipynb: a thin, read-only walkthrough that calls the package.
All logic lives in src/oilgas; the notebook only orchestrates and displays."""
import nbformat as nbf

from oilgas.config import PROJECT_ROOT

nb = nbf.v4.new_notebook()
c = []
c.append(nbf.v4.new_markdown_cell(
    "# Brazilian Oil & Gas Production — walkthrough\n\n"
    "Thin notebook: every computation is a function in `src/oilgas/`. Run the pipeline first "
    "(`python -m oilgas.pipeline`). Data: ANP, snapshot 2026-11-18; last month Sep 2026 (provisional)."))
c.append(nbf.v4.new_code_cell(
    "import sys, pathlib\n"
    "sys.path.insert(0, str(pathlib.Path.cwd().parent / 'src'))\n"
    "import pandas as pd\n"
    "from oilgas import eda, stats_analysis\n"
    "from oilgas.config import PROCESSED_DIR\n"
    "f, u = eda.load()\n"
    "f.shape, u.shape"))
c.append(nbf.v4.new_markdown_cell("## 1. Descriptive statistics and long-run trend"))
c.append(nbf.v4.new_code_cell("eda.descriptive(f).round(4)"))
c.append(nbf.v4.new_code_cell("eda.log_linear_trend(f).round(4)"))
c.append(nbf.v4.new_markdown_cell("## 2. Annual production, onshore vs offshore"))
c.append(nbf.v4.new_code_cell(
    "a = eda.annual_table(f)\n"
    "a[(a.series != 'lgn') & (a.year >= 2015)].pivot(index='year', columns='series', values=['daily_avg', 'offshore_share']).round(3)"))
c.append(nbf.v4.new_markdown_cell("## 3. Gas utilisation (national)"))
c.append(nbf.v4.new_code_cell(
    "g = eda.gas_utilization_annual(u)\n"
    "g[g.level == 'national'].set_index('year')[['reinjection_rate', 'flaring_loss_rate', 'own_use_rate', 'available_rate']].tail(6).round(4)"))
c.append(nbf.v4.new_markdown_cell("## 4. Structural breaks (BIC-selected)"))
c.append(nbf.v4.new_code_cell("breaks, bic = stats_analysis.structural_breaks(f)\nbreaks.round(4)"))
c.append(nbf.v4.new_markdown_cell(
    "## 5. Charts\n\n![production](../assets/01_national_production.png)\n\n![gas](../assets/03_gas_utilization.png)"))
nb["cells"] = c
out = PROJECT_ROOT / "notebooks" / "01_walkthrough.ipynb"
out.parent.mkdir(exist_ok=True)
nbf.write(nb, out)
print(out)
