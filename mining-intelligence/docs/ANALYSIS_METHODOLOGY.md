# Analysis Methodology — Mining

| Topic | Method | Notes |
|---|---|---|
| Value | AMB beneficiated sales value (R$, nominal), summed over UF × substance | Not "total production value": transfers and own use are separate fields |
| Volume | Only within one substance and its single published unit (t, kg, ct) | Never summed across substances |
| YoY | v(t) / v(t−1) − 1 when t−1 is the calendar previous year and v(t−1) > 0 | NULL otherwise |
| CAGR | (v_end / v_start)^(1/years) − 1 | |
| Price/volume split | ln(V₁/V₀) = ln(Q₁/Q₀) + ln(P₁/P₀), with P = value / quantity sold | Exact additive decomposition in log-points. Says nothing about causes |
| Shares and ranks | `SUM() OVER (PARTITION BY year)`, `RANK()` | Cumulative (Pareto) share ordered by rank |
| HHI | Σ (share %)², 0–10,000 | Bands (< 1,500 / 1,500–2,500 / > 2,500) follow the 2010 US DOJ/FTC guidelines, as a **reference only** |
| CR1 / CR4 | Share of the top 1 / top 4 participants | |
| Geographic vs business concentration | Geographic: participants = UFs, AMB value. Business: participants = CNPJ roots, CFEM collected, **within one substance group**, PJ only | Kept separate because CFEM rates differ between substances |
| Company names | Registered name of the most frequent CNPJ of each root (BrasilAPI mirror of Receita Federal), `seeds/company_names.csv` | Legal entity, not economic group |
| CFEM / AMB ratio | CFEM collected ÷ AMB sales value, same year × UF × group, mapped groups only | Indicator only: different base (CFEM = gross revenue less taxes, per Lei 13.540/2017) and timing (cash vs base year) |
| Duplicates | T13: identical CFEM lines excluded only in months where they exceed 5 % of value | Sensitivity in q13 |
| Completeness | CFEM months < 50 % of the trailing 12-month median are excluded. 2026 = YTD Jan–Jun, provisional | |
