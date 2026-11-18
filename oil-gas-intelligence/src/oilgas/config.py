"""Paths and the official source registry (single source of truth for URLs)."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MANIFEST = RAW_DIR / "MANIFEST.csv"

_PPGN = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/ppgn-el/"
_ANUARIO = ("https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/"
            "anuario-estatistico-2026/secao-2/anuario-2026-dados_abertos-")

# key -> (url, local file name, unit, measure column as published)
SOURCES = {
    "oil":          (_PPGN + "producao-petroleo-m3.csv",         "producao-petroleo-m3.csv",         "m3",      "PRODUÇÃO"),
    "gas":          (_PPGN + "producao-gas-natural-1000m3.csv",  "producao-gas-natural-1000m3.csv",  "1000 m3", "PRODUÇÃO"),
    "lgn":          (_PPGN + "producao-lgn-m3.csv",              "producao-lgn-m3.csv",              "m3",      "PRODUÇÃO"),
    "reinjection":  (_PPGN + "reinjecao-gn-1000m3",              "reinjecao-gn-1000m3.csv",          "1000 m3", "REINJETADO"),
    "flaring":      (_PPGN + "queima-e-perda-gn-1000m3.csv",     "queima-e-perda-gn-1000m3.csv",     "1000 m3", "QUEIMADO"),
    "own_use":      (_PPGN + "consumo-proprio-gn1000m3.csv",     "consumo-proprio-gn1000m3.csv",     "1000 m3", "CONSUMO"),
    "available":    (_PPGN + "gn-disponivel-1000m3.csv",         "gn-disponivel-1000m3.csv",         "1000 m3", "DISPONÍVEL"),
}

# Annual benchmark tables (Anuário Estatístico 2026, section 2) used for reconciliation only.
BENCHMARKS = {
    "anuario_t2_14_oil_location_uf":   _ANUARIO + "tabela2-14.csv",
    "anuario_t2_19_gas_location_uf":   _ANUARIO + "tabela2-19.csv",
    "anuario_t2_21_reinjection":       _ANUARIO + "tabela2-21.csv",
    "anuario_t2_22_flaring":           _ANUARIO + "tabela2-22.csv",
}

# ANP publishes UF as upper-case full names. code, display name, region (English).
UF_REFERENCE = {
    "ALAGOAS": ("AL", "Alagoas", "Northeast"),
    "AMAZONAS": ("AM", "Amazonas", "North"),
    "BAHIA": ("BA", "Bahia", "Northeast"),
    "CEARÁ": ("CE", "Ceará", "Northeast"),
    "ESPÍRITO SANTO": ("ES", "Espírito Santo", "Southeast"),
    "MARANHÃO": ("MA", "Maranhão", "Northeast"),
    "PARANÁ": ("PR", "Paraná", "South"),
    "RIO DE JANEIRO": ("RJ", "Rio de Janeiro", "Southeast"),
    "RIO GRANDE DO NORTE": ("RN", "Rio Grande do Norte", "Northeast"),
    "SERGIPE": ("SE", "Sergipe", "Northeast"),
    "SÃO PAULO": ("SP", "São Paulo", "Southeast"),
}
LOCATION_EN = {"TERRA": "Onshore", "MAR": "Offshore", "TOTAL": "Total"}

# Volume conversion used only for an explicitly labelled bbl/d column (1 m3 = 6.28981 bbl).
# Cross-checked: Anuário 2026 t2.14 (thousand bbl) / monthly files (m3) median ratio = 158.9873 = 1000 / 6.28981.
BBL_PER_M3 = 6.28981

GAS_BALANCE_SERIES = ["gas", "reinjection", "flaring", "own_use", "available"]

METADATA = {
    "metadados-producao-petroleo.pdf": _PPGN + "metadados-producao-petroleo.pdf",
    "metadados-producao-gn.pdf":       _PPGN + "metadados-producao-gn.pdf",
    "metadados-queima-e-perda-gn.pdf": _PPGN + "metadados-queima-e-perda-gn.pdf",
    "metadados-reinjecao-gn.pdf":      _PPGN + "metadados-reinjecao-gn.pdf",
}
