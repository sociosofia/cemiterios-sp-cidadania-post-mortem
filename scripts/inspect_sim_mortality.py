#!/usr/bin/env python3
"""Inspeciona a estrutura das bases públicas SIM/PRO-AIM sem versionar microdados.

A rotina descobre os links anuais na página oficial, baixa apenas o ano mais
recente solicitado, lista membros e campos e descarta os registros individuais.
Também registra os arquivos oficiais de distritos e o dicionário do SIM.
"""

from __future__ import annotations

import csv
import io
import json
import re
import tempfile
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from dbfread import DBF

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "sim" / "inspection"

PAGE = "https://prefeitura.sp.gov.br/web/saude/w/epidemiologia_e_informacao/mortalidade/183816"
DISTRICTS = "https://prefeitura.sp.gov.br/cidade/secretarias/upload/saude/arquivos/mortalidade/distritos_administrativos.zip"
DICTIONARY = "https://prefeitura.sp.gov.br/cidade/secretarias/upload/saude/arquivos/mortalidade/Dicionario_de_Dados_SIM_tabela_DO.zip"
YEARS = (2022, 2023)
UA = "cemiterios-sp-cidadania-post-mortem/1.0"


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.links.append((" ".join(self._text).strip(), self._href))
            self._href = None
            self._text = []


def request(url: str, timeout: int = 240) -> tuple[bytes, dict[str, str], str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read(), dict(response.headers.items()), response.geturl()


def discover_year_urls(html: str) -> dict[int, str]:
    parser = LinkParser()
    parser.feed(html)
    result: dict[int, str] = {}
    for text, href in parser.links:
        normalized = re.sub(r"\D", "", text)
        if normalized.isdigit() and int(normalized) in YEARS:
            result[int(normalized)] = urllib.parse.urljoin(PAGE, href)
    return result


def inspect_csv(raw: bytes) -> dict[str, Any]:
    text = None
    encoding = None
    for candidate in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            text = raw.decode(candidate)
            encoding = candidate
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        return {"type": "csv", "error": "encoding_not_detected"}
    try:
        delimiter = csv.Sniffer().sniff(text[:30000], delimiters=";,|\t").delimiter
    except csv.Error:
        delimiter = ";"
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = next(reader, [])
    record_count = sum(1 for _ in reader)
    return {
        "type": "csv",
        "encoding": encoding,
        "delimiter": delimiter,
        "fields": header,
        "record_count": record_count,
    }


def inspect_dbf(path: Path) -> dict[str, Any]:
    table = DBF(str(path), load=False, char_decode_errors="replace")
    return {
        "type": "dbf",
        "fields": [field.name for field in table.fields],
        "field_specs": [
            {"name": field.name, "type": field.type, "length": field.length, "decimal_count": field.decimal_count}
            for field in table.fields
        ],
        "record_count": len(table),
    }


def inspect_archive(raw: bytes, label: str) -> dict[str, Any]:
    result: dict[str, Any] = {"label": label, "size_bytes": len(raw)}
    if not zipfile.is_zipfile(io.BytesIO(raw)):
        result["archive_type"] = "unknown_or_non_zip"
        result["first_bytes_hex"] = raw[:24].hex()
        return result

    result["archive_type"] = "zip"
    with tempfile.TemporaryDirectory(prefix=f"sim-{label}-") as temp:
        temp_path = Path(temp)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            result["members"] = archive.namelist()
            archive.extractall(temp_path)
        tables: list[dict[str, Any]] = []
        for path in temp_path.rglob("*"):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            try:
                if suffix == ".dbf":
                    info = inspect_dbf(path)
                elif suffix in {".csv", ".txt"}:
                    info = inspect_csv(path.read_bytes())
                else:
                    continue
                info["member"] = str(path.relative_to(temp_path))
                tables.append(info)
            except Exception as exc:  # pragma: no cover - depende da fonte externa
                tables.append({"member": str(path.relative_to(temp_path)), "error": str(exc)})
        result["tables"] = tables
    return result


def candidate_fields(fields: list[str]) -> dict[str, list[str]]:
    groups = {
        "district": ("DIST", "DISTR", "RES"),
        "race": ("RACA", "RACACOR", "COR"),
        "schooling": ("ESC", "ESCOLAR"),
        "age": ("IDADE", "DTNASC"),
        "death_date": ("DTOBITO", "DATAOBITO", "OBITO"),
        "sex": ("SEXO",),
    }
    output: dict[str, list[str]] = {}
    for label, tokens in groups.items():
        output[label] = [field for field in fields if any(token in field.upper() for token in tokens)]
    return output


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    page_raw, page_headers, final_page_url = request(PAGE)
    html = page_raw.decode("utf-8", errors="replace")
    year_urls = discover_year_urls(html)

    inventory: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_page": PAGE,
        "final_page_url": final_page_url,
        "page_headers": page_headers,
        "years_requested": list(YEARS),
        "year_urls": year_urls,
        "privacy_rule": (
            "Nenhum registro individual, amostra de linha ou identificador pessoal é persistido no repositório."
        ),
        "years": {},
        "reference_files": {},
    }

    for year in YEARS:
        url = year_urls.get(year)
        if not url:
            inventory["years"][str(year)] = {"error": "year_link_not_found"}
            continue
        raw, headers, final_url = request(url)
        info = inspect_archive(raw, str(year))
        info.update({"source_url": url, "final_url": final_url, "headers": headers})
        for table in info.get("tables", []):
            fields = table.get("fields") or []
            table["candidate_fields"] = candidate_fields(fields)
        inventory["years"][str(year)] = info

    for label, url in (("districts", DISTRICTS), ("dictionary", DICTIONARY)):
        try:
            raw, headers, final_url = request(url)
            info = inspect_archive(raw, label)
            info.update({"source_url": url, "final_url": final_url, "headers": headers})
            inventory["reference_files"][label] = info
        except Exception as exc:  # pragma: no cover
            inventory["reference_files"][label] = {"source_url": url, "error": str(exc)}

    (OUT / "sim_structure_inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Estrutura do SIM/PRO-AIM inspecionada sem persistência de microdados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
