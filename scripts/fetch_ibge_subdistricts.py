#!/usr/bin/env python3
"""Coleta renda e cor ou raça para os 96 recortes internos de São Paulo.

No IBGE, os 96 distritos administrativos da Prefeitura correspondem ao nível
``subdistrito``. Por isso a filtragem usa ``CD_SUBDIST`` e não somente
``CD_DIST``.
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

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "ibge" / "subdistritos_sp"
META = ROOT / "data" / "raw" / "ibge" / "inspection"
MUNICIPIO = "3550308"
UA = "cemiterios-sp-cidadania-post-mortem/1.0"

BASE = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
    "Agregados_por_Setores_Censitarios/Agregados_por_SubDistrito_csv/"
)
RENDA = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
    "Agregados_por_Setores_Censitarios_Rendimento_do_Responsavel/"
    "Agregados_por_subdistritos_renda_responsavel_BR_20260508_csv.zip"
)


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", "", text.upper())


def available_zips() -> list[str]:
    html = get(BASE).decode("utf-8", errors="replace")
    links = re.findall(r'href=["\']([^"\']+\.zip)["\']', html, re.I)
    return sorted({urllib.parse.urljoin(BASE, link) for link in links})


def race_zips(urls: list[str]) -> list[str]:
    result = []
    for url in urls:
        name = norm(Path(urllib.parse.urlparse(url).path).name)
        if "COR" in name and "RACA" in name and "INDIGENA" not in name and "QUILOMBOLA" not in name:
            result.append(url)
    return result


def decode(raw: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise RuntimeError("Não foi possível decodificar o CSV.")
    try:
        delimiter = csv.Sniffer().sniff(text[:20000], delimiters=";,|\t").delimiter
    except csv.Error:
        delimiter = ";"
    return text, delimiter


def filter_zip(url: str, prefix: str) -> dict:
    archive_bytes = get(url)
    archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    members = []
    for member in sorted(archive.namelist()):
        if not member.lower().endswith((".csv", ".txt")):
            continue
        text, delimiter = decode(archive.read(member))
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        fields = list(reader.fieldnames or [])
        subdistrict = next((c for c in fields if norm(c) in {"CDSUBDIST", "CDSUBDISTRITO"}), None)
        district = next((c for c in fields if norm(c) in {"CDDIST", "CDDISTRITO"}), None)
        code_column = subdistrict or district
        rows = []
        for row in reader:
            code = re.sub(r"\D", "", row.get(code_column, "")) if code_column else ""
            if code.startswith(MUNICIPIO):
                rows.append(row)
        output = None
        if rows:
            safe = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(member).stem)
            output = OUT / f"{prefix}_{safe}.csv"
            with output.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
        members.append(
            {
                "member": member,
                "columns": fields,
                "code_column": code_column,
                "sao_paulo_rows": len(rows),
                "samples": rows[:2],
                "output": str(output.relative_to(ROOT)) if output else None,
            }
        )
    return {
        "source_url": url,
        "zip_size_bytes": len(archive_bytes),
        "members": members,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)
    urls = available_zips()
    selected = race_zips(urls)
    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "geographic_level": "subdistrito",
        "municipality_prefix": MUNICIPIO,
        "available_universe_zips": urls,
        "selected_race_zips": selected,
        "income": filter_zip(RENDA, "renda_responsavel"),
        "race": [filter_zip(url, f"cor_raca_{index}") for index, url in enumerate(selected, 1)],
        "warning": (
            "Os 96 distritos administrativos municipais correspondem ao nível subdistrito do IBGE. "
            "Os códigos técnicos ainda precisam ser lidos com o dicionário oficial."
        ),
    }
    (META / "subdistritos_sp_inventory.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Dados dos subdistritos paulistanos coletados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
