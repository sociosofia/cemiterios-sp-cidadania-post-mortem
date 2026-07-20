#!/usr/bin/env python3
"""Coleta renda e cor ou raça para os recortes internos de São Paulo.

O script primeiro registra amostras brutas dos códigos territoriais. A filtragem
municipal aceita o código IBGE completo (3550308) e a raiz sem dígito verificador
(355030), pois os agregados podem empregar códigos hierárquicos diferentes.
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
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "ibge" / "subdistritos_sp"
META = ROOT / "data" / "raw" / "ibge" / "inspection"
MUNICIPIO_COMPLETO = "3550308"
MUNICIPIO_RAIZ = "355030"
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


def belongs_to_sao_paulo(code: str) -> bool:
    digits = re.sub(r"\D", "", code)
    return digits.startswith(MUNICIPIO_COMPLETO) or digits.startswith(MUNICIPIO_RAIZ)


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
        all_rows = list(reader)
        rows = [
            row for row in all_rows
            if code_column and belongs_to_sao_paulo(row.get(code_column, ""))
        ]
        output = None
        if rows:
            safe = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(member).stem)
            output = OUT / f"{prefix}_{safe}.csv"
            with output.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
        code_values = [str(row.get(code_column, "")) for row in all_rows] if code_column else []
        lengths = Counter(len(re.sub(r"\D", "", code)) for code in code_values)
        members.append(
            {
                "member": member,
                "columns": fields,
                "delimiter": delimiter,
                "code_column": code_column,
                "total_rows": len(all_rows),
                "raw_samples": all_rows[:5],
                "raw_code_samples": code_values[:20],
                "numeric_code_lengths": dict(sorted(lengths.items())),
                "sao_paulo_rows": len(rows),
                "sao_paulo_samples": rows[:3],
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
        "municipality_code_full": MUNICIPIO_COMPLETO,
        "municipality_code_root": MUNICIPIO_RAIZ,
        "available_universe_zips": urls,
        "selected_race_zips": selected,
        "income": filter_zip(RENDA, "renda_responsavel"),
        "race": [filter_zip(url, f"cor_raca_{index}") for index, url in enumerate(selected, 1)],
        "warning": (
            "O inventário registra amostras brutas para validar a hierarquia territorial antes "
            "da junção com os limites distritais do GeoSampa."
        ),
    }
    (META / "subdistritos_sp_inventory.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Dados dos recortes paulistanos coletados e códigos auditados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
