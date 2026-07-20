#!/usr/bin/env python3
"""Baixa e inspeciona os agregados distritais do Censo 2022.

A primeira execução não escolhe variáveis socioeconômicas de forma automática.
Ela registra os arquivos, cabeçalhos e amostras referentes ao Município de São
Paulo para que renda, cor ou raça e infraestrutura sejam selecionadas com base
no dicionário oficial, sem depender de nomes de colunas presumidos.
"""

from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "raw" / "ibge" / "inspection"

UNIVERSE_DIRECTORY = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
    "Agregados_por_Setores_Censitarios/Agregados_por_Distrito_csv/"
)
INCOME_URL = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
    "Agregados_por_Setores_Censitarios_Rendimento_do_Responsavel/"
    "Agregados_por_distritos_renda_responsavel_BR_20260508_csv.zip"
)
USER_AGENT = "cemiterios-sp-cidadania-post-mortem/1.0"
MUNICIPALITY_CODE = "3550308"
MUNICIPALITY_NAME = "SAO PAULO"


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def normalize(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^A-Z0-9]+", "", text.upper())


def discover_universe_zip() -> str:
    html = fetch_bytes(UNIVERSE_DIRECTORY).decode("utf-8", errors="replace")
    links = re.findall(r'href=["\']([^"\']+\.zip)["\']', html, flags=re.I)
    if not links:
        raise RuntimeError(f"Nenhum ZIP encontrado em {UNIVERSE_DIRECTORY}")
    absolute = [urllib.parse.urljoin(UNIVERSE_DIRECTORY, link) for link in links]
    preferred = [
        url
        for url in absolute
        if "DISTRIT" in normalize(Path(urllib.parse.urlparse(url).path).name)
        and "DICION" not in normalize(url)
    ]
    return sorted(preferred or absolute)[-1]


def decode_csv(raw: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise UnicodeDecodeError("unknown", raw, 0, 1, "codificação não identificada")

    sample = text[:20000]
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=";,|\t").delimiter
    except csv.Error:
        delimiter = ";"
    return text, delimiter


def geographic_columns(fieldnames: list[str]) -> dict[str, str | None]:
    normalized = {column: normalize(column) for column in fieldnames}

    def find(*patterns: str) -> str | None:
        normalized_patterns = [normalize(pattern) for pattern in patterns]
        for column, value in normalized.items():
            if any(pattern == value for pattern in normalized_patterns):
                return column
        for column, value in normalized.items():
            if any(pattern in value for pattern in normalized_patterns):
                return column
        return None

    return {
        "municipality_code": find("CD_MUN", "CD_MUNICIPIO", "COD_MUNICIPIO"),
        "municipality_name": find("NM_MUN", "NM_MUNICIPIO", "NOME_MUNICIPIO"),
        "district_code": find("CD_DIST", "CD_DISTRITO", "COD_DISTRITO"),
        "district_name": find("NM_DIST", "NM_DISTRITO", "NOME_DISTRITO"),
    }


def is_sao_paulo(row: dict[str, str], columns: dict[str, str | None]) -> bool:
    code_column = columns.get("municipality_code")
    name_column = columns.get("municipality_name")
    if code_column:
        value = re.sub(r"\D", "", row.get(code_column, ""))
        if value.startswith(MUNICIPALITY_CODE):
            return True
    if name_column and normalize(row.get(name_column, "")) == MUNICIPALITY_NAME:
        return True
    return False


def inspect_zip(url: str, label: str) -> dict[str, Any]:
    raw_zip = fetch_bytes(url)
    archive = zipfile.ZipFile(io.BytesIO(raw_zip))
    files: list[dict[str, Any]] = []

    for member in sorted(archive.namelist()):
        if not member.lower().endswith((".csv", ".txt")):
            continue
        raw = archive.read(member)
        text, delimiter = decode_csv(raw)
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        fieldnames = list(reader.fieldnames or [])
        geo_columns = geographic_columns(fieldnames)
        samples: list[dict[str, str]] = []
        row_count = 0
        for row in reader:
            if is_sao_paulo(row, geo_columns):
                row_count += 1
                if len(samples) < 2:
                    samples.append(row)
        files.append(
            {
                "member": member,
                "delimiter": delimiter,
                "columns": fieldnames,
                "geographic_columns_detected": geo_columns,
                "sao_paulo_row_count": row_count,
                "sao_paulo_samples": samples,
            }
        )

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "source_url": url,
        "zip_size_bytes": len(raw_zip),
        "members_total": len(archive.namelist()),
        "tabular_members_inspected": len(files),
        "files": files,
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    universe_url = discover_universe_zip()
    inventories = {
        "distritos_universo": inspect_zip(universe_url, "Agregados distritais — universo"),
        "distritos_renda_responsavel": inspect_zip(
            INCOME_URL, "Agregados distritais — rendimento do responsável"
        ),
    }
    for name, payload in inventories.items():
        (OUTPUT_DIR / f"{name}_inventory.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    (OUTPUT_DIR / "sources.json").write_text(
        json.dumps(
            {
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "universe_directory": UNIVERSE_DIRECTORY,
                "universe_zip_resolved": universe_url,
                "income_zip": INCOME_URL,
                "municipality_filter": {
                    "code": MUNICIPALITY_CODE,
                    "name": MUNICIPALITY_NAME,
                },
                "note": (
                    "Inventário exploratório. A seleção de indicadores será feita somente "
                    "após conferência do dicionário oficial do IBGE."
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("Inventário dos agregados distritais do Censo 2022 atualizado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
