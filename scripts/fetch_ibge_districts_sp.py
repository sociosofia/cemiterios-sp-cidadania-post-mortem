#!/usr/bin/env python3
"""Coleta agregados do Censo 2022 para os 96 distritos de São Paulo.

Os arquivos temáticos são descobertos no índice oficial do IBGE para evitar
quebras causadas por datas ou sufixos acrescentados aos nomes dos ZIPs.
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
OUT = ROOT / "data" / "raw" / "ibge" / "distritos_sp"
META = ROOT / "data" / "raw" / "ibge" / "inspection"
UA = "cemiterios-sp-cidadania-post-mortem/1.0"
MUNICIPIO_COMPLETO = "3550308"
MUNICIPIO_RAIZ = "355030"

DISTRICT_DIRECTORY = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
    "Agregados_por_Setores_Censitarios/Agregados_por_Distrito_csv/"
)
RENDA = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
    "Agregados_por_Setores_Censitarios_Rendimento_do_Responsavel/"
    "Agregados_por_distritos_renda_responsavel_BR_20260508_csv.zip"
)


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^A-Z0-9]+", "", text.upper())


def directory_zips() -> list[str]:
    html = get(DISTRICT_DIRECTORY).decode("utf-8", errors="replace")
    links = re.findall(r'href=["\']([^"\']+\.zip)["\']', html, re.I)
    return sorted({urllib.parse.urljoin(DISTRICT_DIRECTORY, link) for link in links})


def choose(urls: list[str], required: tuple[str, ...], excluded: tuple[str, ...] = ()) -> str:
    candidates = []
    for url in urls:
        name = normalize(Path(urllib.parse.urlparse(url).path).name)
        if all(normalize(token) in name for token in required) and not any(
            normalize(token) in name for token in excluded
        ):
            candidates.append(url)
    if not candidates:
        raise RuntimeError(f"Nenhum arquivo encontrado para os termos: {required}")
    dated = [url for url in candidates if re.search(r"20\d{6}", url)]
    return sorted(dated or candidates)[-1]


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


def belongs_to_sao_paulo(value: str) -> bool:
    digits = re.sub(r"\D", "", value or "")
    return digits.startswith(MUNICIPIO_COMPLETO) or digits.startswith(MUNICIPIO_RAIZ)


def extract(url: str, prefix: str) -> dict:
    archive_bytes = get(url)
    archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    members = []
    for member in sorted(archive.namelist()):
        if not member.lower().endswith((".csv", ".txt")):
            continue
        text, delimiter = decode(archive.read(member))
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        fields = list(reader.fieldnames or [])
        code_column = next(
            (c for c in fields if normalize(c) in {"CDDIST", "CDDISTRITO"}),
            None,
        )
        all_rows = list(reader)
        rows = [
            row for row in all_rows
            if code_column and belongs_to_sao_paulo(row.get(code_column, ""))
        ]
        output = None
        if rows:
            OUT.mkdir(parents=True, exist_ok=True)
            safe = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(member).stem)
            output = OUT / f"{prefix}_{safe}.csv"
            with output.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
        codes = [str(row.get(code_column, "")) for row in all_rows] if code_column else []
        lengths = Counter(len(re.sub(r"\D", "", code)) for code in codes)
        members.append(
            {
                "member": member,
                "columns": fields,
                "delimiter": delimiter,
                "code_column": code_column,
                "total_rows": len(all_rows),
                "raw_code_samples": codes[:20],
                "numeric_code_lengths": dict(sorted(lengths.items())),
                "sao_paulo_rows": len(rows),
                "sao_paulo_samples": rows[:5],
                "output": str(output.relative_to(ROOT)) if output else None,
            }
        )
    return {"source_url": url, "zip_size_bytes": len(archive_bytes), "members": members}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)
    urls = directory_zips()
    race_url = choose(urls, ("cor", "raca"), ("indigena", "quilombola"))
    basic_url = choose(urls, ("basico",))
    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "geographic_level": "distrito",
        "municipality_code_full": MUNICIPIO_COMPLETO,
        "municipality_code_root": MUNICIPIO_RAIZ,
        "directory": DISTRICT_DIRECTORY,
        "available_zips": urls,
        "resolved_urls": {"income": RENDA, "race": race_url, "basic": basic_url},
        "income": extract(RENDA, "renda_responsavel"),
        "race": extract(race_url, "cor_ou_raca"),
        "basic": extract(basic_url, "basico"),
        "validation_rule": (
            "A coleta só será integrada ao mapa se retornar 96 distritos e se os nomes "
            "forem conciliados de modo auditável com o GeoSampa."
        ),
    }
    (META / "distritos_sp_inventory.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Agregados distritais de São Paulo coletados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
