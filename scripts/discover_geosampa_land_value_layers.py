#!/usr/bin/env python3
"""Inventaria camadas do WFS GeoSampa relacionadas a solo, quadras e valores.

O objetivo é localizar as geometrias necessárias para ligar a PGV 2026 às
faces de quadra e calcular indicadores no entorno dos cemitérios. A descoberta
é mantida separada da escolha final da camada para evitar nomes presumidos.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "geosampa"
OUTPUT = ROOT / "data" / "processed" / "geosampa_land_value_layer_candidates.json"

ENDPOINTS = (
    "https://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs",
    "http://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs",
)
TERMS = (
    "valor",
    "terreno",
    "outorga",
    "quadra",
    "face",
    "lote",
    "iptu",
    "fiscal",
    "codlog",
    "logradouro",
)
USER_AGENT = (
    "cemiterios-sp-cidadania-post-mortem/1.0 "
    "(pesquisa acadêmica; dados públicos)"
)


def fetch_capabilities() -> tuple[bytes, str]:
    errors: list[str] = []
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetCapabilities",
    }
    for endpoint in ENDPOINTS:
        url = f"{endpoint}?{urlencode(params)}"
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/xml,text/xml"})
        try:
            with urlopen(request, timeout=120) as response:
                return response.read(), response.geturl()
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("Falha ao consultar capabilities do GeoSampa:\n" + "\n".join(errors))


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(element: ET.Element, name: str) -> str:
    for child in list(element):
        if local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def normalize(text: str) -> str:
    text = text.casefold()
    text = re.sub(r"[^a-z0-9áàâãéêíóôõúç]+", " ", text)
    return " ".join(text.split())


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    payload, request_url = fetch_capabilities()
    raw_path = RAW_DIR / "wfs_capabilities.xml"
    raw_path.write_bytes(payload)

    root = ET.fromstring(payload)
    layers: list[dict[str, object]] = []
    for element in root.iter():
        if local_name(element.tag) != "FeatureType":
            continue
        name = child_text(element, "Name")
        title = child_text(element, "Title")
        abstract = child_text(element, "Abstract")
        haystack = normalize(f"{name} {title} {abstract}")
        matched = sorted(term for term in TERMS if term in haystack)
        if matched:
            layers.append(
                {
                    "name": name,
                    "title": title,
                    "abstract": abstract,
                    "matched_terms": matched,
                }
            )

    layers.sort(key=lambda item: (-len(item["matched_terms"]), str(item["name"])))
    metadata = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "GeoSampa — WFS GetCapabilities",
        "request_url": request_url,
        "raw_file": str(raw_path.relative_to(ROOT)),
        "search_terms": list(TERMS),
        "candidate_count": len(layers),
        "candidates": layers,
        "interpretive_status": (
            "inventário técnico; a camada adequada deve ser validada por schema, "
            "geometria, data de atualização e documentação oficial"
        ),
    }
    OUTPUT.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"GeoSampa: {len(layers)} camadas candidatas registradas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
