"""File integrity and expected schemas of the raw ANM files."""
from __future__ import annotations

import hashlib

import pytest

from conftest import RAW

EXPECTED_HEADERS = {
    "AMB/Producao_Beneficiada.csv": [
        "Ano base", "UF", "Classe Substância", "Substância Mineral", "Quantidade Produção",
        "Unidade de Medida - Produção", "Quantidade Contido", "Unidade de Medida - Contido", "Indicação Contido",
        "Quantidade Venda", "Unidade de Medida - Venda", "Valor Venda (R$)", "Quantidade Consumo/Utilização na Usina",
        "Unidade de Medida - Consumo/Utilização na Usina", "Valor Consumo / Utilização na Usina (R$)",
        "Quantidade Transferência para Transformação / Utilização / Consumo",
        "Unidade de Medida - Transferência para Transformação / Utilização / Consumo",
        "Valor Transferência para Transformação / Utilização / Consumo (R$)"],
    "CFEM/CFEM_Arrecadacao.csv": [
        "Ano", "Mês", "Processo", "AnoDoProcesso", "Tipo_PF_PJ", "CPF_CNPJ", "Substância", "UF", "CodigoMunicipio",
        "Município", "QuantidadeComercializada", "UnidadeDeMedida", "ValorRecolhido", "DataCriacao"],
}


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_manifest_lists_all_required_files(manifest):
    files = {r["file"] for r in manifest}
    assert {"AMB/Producao_Beneficiada.csv", "AMB/Producao_Bruta.csv", "CFEM/CFEM_Arrecadacao.csv"} <= files


@pytest.mark.parametrize("idx", range(5))
def test_raw_file_matches_manifest(manifest, idx):
    """Raw files are unmodified: size and SHA-256 equal the values recorded at download."""
    row = manifest[idx]
    path = RAW / row["file"]
    assert path.exists(), path
    assert path.stat().st_size == int(row["bytes"])
    assert sha256(path) == row["sha256"]


@pytest.mark.parametrize("name,expected", EXPECTED_HEADERS.items())
def test_raw_header(name, expected):
    with open(RAW / name, encoding="latin-1") as fh:
        header = fh.readline().strip().split(",")
    assert [h.strip('"') for h in header] == expected


def test_staging_types(con):
    types = dict(con.execute("SELECT column_name, data_type FROM information_schema.columns "
                         "WHERE table_name = 'stg_cfem'").fetchall())
    assert types["year"] == "INTEGER" and types["month"] == "INTEGER"
    assert types["cfem_brl"] == "DOUBLE" and types["period_month"] == "DATE"
    assert types["slip_created_at"].startswith("TIMESTAMP")
