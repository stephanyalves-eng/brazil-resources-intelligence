# Analysis Methodology — Oil & Gas

| Topic | Method | Why this method |
|---|---|---|
| Daily average | monthly volume / calendar days | Removes the 28–31-day effect. MoM is reported on the daily average |
| Annual daily average | annual volume / days in year | |
| Long-run trend | OLS of ln(annual daily average) on year; growth = e^b − 1; R² reported | Constant-growth model, easy to read |
| Structural breaks | Exact dynamic-programming segmentation of ln(monthly daily average) into piecewise-linear segments, ≥ 36 months each, K ≤ 10 chosen by BIC | Interpretable slopes. A robustness check rejected the smoothed (12M rolling) input because BIC overfits on autocorrelated data. BIC deltas are published |
| Seasonality | Ratio to a 2×12 centred moving average (classical decomposition), averaged by calendar month (2011+). Effect size η². Permutation test with 5,000 shuffles and a fixed seed | Needs no distributional assumptions and no SciPy |
| Anomalies | Robust z = 0.6745 (x − median) / MAD of the MoM change in the daily average; flag at |z| > 3.5 (Iglewicz & Hoaglin). Local view: z against the previous 12 months | Robust to the outliers it is looking for. Results are labelled *statistical*, not incidents |
| Volatility | Std of the MoM change in the daily average, per era (1998–2009, 2010–19, 2020–26), and rolling 12M | |
| Concentration | HHI of UF shares of annual volume | Same definition as the mining project |
| Gas utilisation | reinjection, flaring & losses, own use and available, each ÷ gross production; balance gap reported | Valid because the balance identity holds (DATA_PROFILE) |
| Forecasting | Not performed | See ANALYSIS_FINDINGS, "Decision: no forecast" |

Reproduce:

```powershell
cd brazil-resources-intelligence\oil-gas-intelligence\src
..\..\.venv\Scripts\python.exe -m oilgas.eda
..\..\.venv\Scripts\python.exe -m oilgas.stats_analysis
..\..\.venv\Scripts\python.exe -m oilgas.charts
```
