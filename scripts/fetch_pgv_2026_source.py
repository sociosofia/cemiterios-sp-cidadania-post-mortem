#!/usr/bin/env python3
"""Descobre e preserva a fonte oficial da PGV 2026 de São Paulo.

A Lei municipal 18.330/2025 remete ao Documento Anexo nº 145975345.
O portal pode alterar a URL efetiva do anexo. Este script:

1. consulta a página oficial da lei e a edição do Diário Oficial;
2. procura links associados ao número do documento anexo;
3. baixa a primeira resposta que pareça um PDF, DOCX, XLSX ou arquivo binário;
4. preserva HTML, arquivo bruto e metadados para inspeção e auditoria;
5. aceita PGV_SOURCE_URL para sobrepor a descoberta automática.

O script não converte ainda a listagem em valores por face de quadra. A coleta
bruta é uma etapa separada da extração tabular e do cruzamento espacial.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "pgv_2026"
METADATA_PATH = ROOT / "data" / "processed" / "pgv_2026_source_metadata.json"

LAW_URL = (
    "https://legislacao.prefeitura.sp.gov.br/"
    "lei-18330-de-11-de-novembro-de-2025"
)
OFFICIAL_GAZETTE_URL = (
    "https://diariooficial.prefeitura.sp.gov.br/md_epubli_controlador.php?"
    "acao=edicao_consultar&dta=12%2F11%2F2025&formato=O"
)
DOCUMENT_ID = "145975345"
USER_AGENT = (
    "cemiterios-sp-cidadania-post-mortem/1.0 "
    "(pesquisa acadêmica; dados públicos)"
)


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            self.links.append((self._href, " ".join(self._text).strip()))
            self._href = None
            self._text = []


def request(url: str, timeout: int = 120) -> tuple[bytes, dict[str, str], str]:
    req = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/pdf,application/vnd.openxmlformats-"
                "officedocument.wordprocessingml.document,application/octet-stream,*/*"
            ),
        },
    )
    with urlopen(req, timeout=timeout) as response:
        payload = response.read()
        headers = {key.lower(): value for key, value in response.headers.items()}
        return payload, headers, response.geturl()


def safe_fetch(url: str) -> tuple[bytes | None, dict[str, str], str, str | None]:
    try:
        payload, headers, final_url = request(url)
        return payload, headers, final_url, None
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        return None, {}, url, f"{type(exc).__name__}: {exc}"


def collect_candidates(base_url: str, html: str) -> list[str]:
    parser = LinkCollector()
    parser.feed(html)
    candidates: list[str] = []

    for href, text in parser.links:
        joined = f"{href} {text}".lower()
        if DOCUMENT_ID in joined:
            candidates.append(urljoin(base_url, href))
            continue
        if any(token in joined for token in ("anexo", "download", "visualizar")):
            if any(token in joined for token in ("18.330", "18330", "pgv")):
                candidates.append(urljoin(base_url, href))

    # Alguns portais imprimem a URL no HTML ou em JavaScript, fora de um <a>.
    url_pattern = re.compile(r"https?://[^\s\"'<>]+")
    for raw in url_pattern.findall(html):
        if DOCUMENT_ID in raw or "md_epubli_visualizar.php" in raw:
            candidates.append(raw.replace("&amp;", "&"))

    output: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            output.append(candidate)
    return output


def extension_from(headers: dict[str, str], final_url: str, payload: bytes) -> str:
    content_type = headers.get("content-type", "").lower()
    disposition = headers.get("content-disposition", "")

    filename_match = re.search(r"filename\*?=(?:UTF-8''|\")?([^\";]+)", disposition)
    if filename_match:
        suffix = Path(filename_match.group(1)).suffix.lower()
        if suffix:
            return suffix

    for suffix, marker in (
        (".pdf", "application/pdf"),
        (".docx", "wordprocessingml"),
        (".xlsx", "spreadsheetml"),
        (".doc", "application/msword"),
        (".xls", "application/vnd.ms-excel"),
        (".html", "text/html"),
    ):
        if marker in content_type:
            return suffix

    url_suffix = Path(final_url.split("?", 1)[0]).suffix.lower()
    if url_suffix in {".pdf", ".docx", ".xlsx", ".doc", ".xls", ".zip"}:
        return url_suffix

    if payload.startswith(b"%PDF"):
        return ".pdf"
    if payload.startswith(b"PK\x03\x04"):
        return ".zip"
    if payload.lstrip().startswith((b"<!DOCTYPE html", b"<html")):
        return ".html"
    return ".bin"


def looks_like_attachment(headers: dict[str, str], payload: bytes, final_url: str) -> bool:
    suffix = extension_from(headers, final_url, payload)
    if suffix in {".pdf", ".docx", ".xlsx", ".doc", ".xls", ".zip", ".bin"}:
        return len(payload) > 1_000
    return False


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)

    captured_at = datetime.now(timezone.utc).isoformat()
    pages: list[dict[str, object]] = []
    candidates: list[str] = []

    for label, url in (("lei", LAW_URL), ("diario_oficial", OFFICIAL_GAZETTE_URL)):
        payload, headers, final_url, error = safe_fetch(url)
        page_info: dict[str, object] = {
            "label": label,
            "requested_url": url,
            "final_url": final_url,
            "error": error,
        }
        if payload is not None:
            page_path = RAW_DIR / f"pagina_{label}.html"
            page_path.write_bytes(payload)
            page_info.update(
                {
                    "bytes": len(payload),
                    "sha256": sha256(payload),
                    "content_type": headers.get("content-type"),
                    "saved_as": str(page_path.relative_to(ROOT)),
                }
            )
            html = payload.decode("utf-8", errors="replace")
            candidates.extend(collect_candidates(final_url, html))
        pages.append(page_info)

    override = os.environ.get("PGV_SOURCE_URL", "").strip()
    if override:
        candidates.insert(0, override)

    # Tenta também páginas oficiais conhecidas. Elas podem redirecionar ao anexo.
    candidates.extend([LAW_URL, OFFICIAL_GAZETTE_URL])

    unique_candidates: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique_candidates.append(candidate)

    attempts: list[dict[str, object]] = []
    selected: dict[str, object] | None = None

    for index, candidate in enumerate(unique_candidates, start=1):
        payload, headers, final_url, error = safe_fetch(candidate)
        attempt: dict[str, object] = {
            "candidate": candidate,
            "final_url": final_url,
            "error": error,
        }
        if payload is not None:
            suffix = extension_from(headers, final_url, payload)
            attempt.update(
                {
                    "bytes": len(payload),
                    "sha256": sha256(payload),
                    "content_type": headers.get("content-type"),
                    "detected_extension": suffix,
                }
            )
            if looks_like_attachment(headers, payload, final_url):
                destination = RAW_DIR / f"anexo_lei_18330_2025_{DOCUMENT_ID}{suffix}"
                destination.write_bytes(payload)
                selected = {
                    **attempt,
                    "saved_as": str(destination.relative_to(ROOT)),
                    "candidate_rank": index,
                }
                attempts.append(attempt)
                break
        attempts.append(attempt)

    metadata = {
        "captured_at_utc": captured_at,
        "law": "Lei municipal 18.330/2025",
        "document_id": DOCUMENT_ID,
        "law_url": LAW_URL,
        "official_gazette_url": OFFICIAL_GAZETTE_URL,
        "pages": pages,
        "candidate_count": len(unique_candidates),
        "attempts": attempts,
        "selected_attachment": selected,
        "status": "attachment_downloaded" if selected else "source_discovery_incomplete",
        "notes": [
            "A listagem de valores da PGV 2026 está no Anexo II da Lei 18.330/2025.",
            "A coleta preserva a fonte bruta antes de qualquer extração tabular.",
            "A ausência de arquivo baixado não significa ausência da fonte; pode refletir URL dinâmica do Diário Oficial.",
            "PGV_SOURCE_URL pode ser informado para fixar manualmente a URL oficial do anexo.",
        ],
    }
    METADATA_PATH.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if selected:
        print(f"PGV 2026: fonte bruta preservada em {selected['saved_as']}.")
    else:
        print(
            "PGV 2026: páginas oficiais preservadas, mas o anexo ainda não foi "
            "baixado automaticamente. Consulte o arquivo de metadados.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
