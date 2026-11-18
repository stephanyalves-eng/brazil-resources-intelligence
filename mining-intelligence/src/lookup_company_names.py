"""Look up the registered legal name (razão social) of the largest CFEM payers.

CFEM publishes the CNPJ but not the company name. CNPJ registration data is public (Receita Federal);
BrasilAPI (https://brasilapi.com.br, free, no key) mirrors it. Only company CNPJs that appear in the
open CFEM file are sent - no personal data (CPFs are masked in the source and never looked up).

Writes seeds/company_names.csv (cnpj_root, cnpj_queried, legal_name, cnae, uf, status, source, retrieved_at).
CLI:  python src/lookup_company_names.py [--top 25]
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
API = "https://brasilapi.com.br/api/cnpj/v1/{}"


def top_cnpjs(n: int) -> list[tuple[str, str]]:
    con = duckdb.connect(str(ROOT / "data/interim/mining.duckdb"), read_only=True)
    rows = con.sql(f"""
        WITH top AS (
          SELECT holder_key FROM mart_cfem_holder_substance_year
          WHERE holder_type = 'PJ' AND year BETWEEN 2021 AND 2025
          GROUP BY 1 ORDER BY sum(cfem_brl) DESC LIMIT {int(n)})
        SELECT holder_key, arg_max(cnpj, k) FROM (
          SELECT holder_key, cnpj, count(*) AS k FROM stg_cfem
          WHERE holder_key IN (SELECT holder_key FROM top) GROUP BY ALL)
        GROUP BY 1 ORDER BY 1""").fetchall()
    con.close()
    return rows


def fetch(cnpj: str) -> dict:
    req = urllib.request.Request(API.format(cnpj), headers={"User-Agent": "industrial-data-analytics/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=25)
    a = ap.parse_args()
    out = []
    for root, cnpj in top_cnpjs(a.top):
        try:
            d = fetch(cnpj)
            out.append({"cnpj_root": root, "cnpj_queried": cnpj, "legal_name": d.get("razao_social", ""),
                        "cnae": d.get("cnae_fiscal_descricao", ""), "uf": d.get("uf", ""),
                        "status": d.get("descricao_situacao_cadastral", ""), "source": "BrasilAPI (Receita Federal)",
                        "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d")})
        except Exception as e:  # keep going; a missing name is shown as the CNPJ root
            out.append({"cnpj_root": root, "cnpj_queried": cnpj, "legal_name": "", "cnae": "", "uf": "",
                        "status": f"lookup failed: {type(e).__name__}", "source": "BrasilAPI",
                        "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d")})
        print(f"{root} {out[-1]['legal_name'] or out[-1]['status']}")
        time.sleep(1.0)  # be polite to a free public service
    with (ROOT / "seeds/company_names.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)


if __name__ == "__main__":
    main()
