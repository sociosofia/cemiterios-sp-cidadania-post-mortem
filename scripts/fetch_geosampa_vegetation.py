#!/usr/bin/env python3
"""Coleta a cobertura vegetal oficial do GeoSampa no entorno dos cemitérios.

A fonte é o Mapeamento Digital da Cobertura Vegetal 2017, publicado pela
Secretaria Municipal do Verde e do Meio Ambiente em 2020. Para evitar baixar a
camada municipal inteira, a rotina consulta o WFS por caixa envolvente de cada
um dos 23 equipamentos já filtrados no projeto e deduplica as feições obtidas.

Saídas:
- data/raw/geosampa/cobertura_vegetal_2017_entorno_cemiterios_31983.geojson
- data/raw/geosampa/cobertura_vegetal_2017_entorno_cemiterios_metadata.json

A saída é um recorte de consulta, não um recorte geométrico: cada feição é
preservada integralmente como devolvida pelo WFS. A interseção exata com os
cemitérios é feita por scripts/analyze_cemetery_vegetation.py.
"""

from __future__ import annotations

import hashlib
import json
import sys
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from shapely.geometry import shape

SOURCE_CRS = "EPSG:31983"
ENDPOINTS = (
    "https://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs",
    "http://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs",
)
CANDIDATE_LAYERS = (
    "geoportal:cobertura_vegetal",
    "geoportal:mapeamento_cobertura_vegetal",
    "geoportal:vegetacao_cobertura",
)
PAGE_SIZE = 50000

METADATA_RECORD = (
    "https://metadados.geosampa.prefeitura.sp.gov.br/geonetwork/srv/api/records/"
    "367916b7-3af4-44be-ab72-cd07a4996b66"
)
METHODOLOGY_REPORT = (
    "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/meio_ambiente/"
    "RelCobVeg2020_vFINAL_compressed%281%29.pdf"
)

ROOT = Path(__file__).resolve().parents[1]
CEMETERIES_PATH = ROOT / "data" / "processed" / "cemiterios_concessao_31983.geojson"
RAW_DIR = ROOT / "data" / "raw" / "geosampa"
OUTPUT_GEOJSON = RAW_DIR / "cobertura_vegetal_2017_entorno_cemiterios_31983.geojson"
OUTPUT_METADATA = RAW_DIR / "cobertura_vegetal_2017_entorno_cemiterios_metadata.json"


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(ascii_value.lower().replace("_", " ").replace("-", " ").split())


def request_bytes(url: str, accept: str, timeout: int = 180) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "cemiterios-sp-cidadania-post-mortem/1.0 "
                "(pesquisa acadêmica; dados públicos)"
            ),
            "Accept": accept,
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def capabilities_url(endpoint: str) -> str:
    return f"{endpoint}?{urlencode({'service': 'WFS', 'version': '2.0.0', 'request': 'GetCapabilities'})}"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def discover_layers(endpoint: str) -> list[tuple[str, str, int]]:
    """Lista candidatos do GetCapabilities, ordenados por aderência semântica."""
    payload = request_bytes(capabilities_url(endpoint), "application/xml,text/xml")
    root = ET.fromstring(payload)
    candidates: list[tuple[str, str, int]] = []

    for element in root.iter():
        if local_name(element.tag) != "FeatureType":
            continue
        name = ""
        title = ""
        for child in element:
            child_name = local_name(child.tag)
            if child_name == "Name" and child.text:
                name = child.text.strip()
            elif child_name == "Title" and child.text:
                title = child.text.strip()
        if not name:
            continue

        text = normalize(f"{name} {title}")
        score = 0
        if "cobertura" in text and "vegetal" in text:
            score += 100
        if "mapeamento" in text:
            score += 20
        if "2017" in text:
            score += 20
        if normalize(name).endswith("cobertura vegetal"):
            score += 30
        if "atlas ambiental" in text or "1999" in text:
            score -= 80
        if score > 0:
            candidates.append((name, title, score))

    return sorted(candidates, key=lambda item: (-item[2], item[0]))


def feature_key(feature: dict[str, Any]) -> str:
    feature_id = feature.get("id")
    if feature_id:
        return str(feature_id)
    canonical = json.dumps(
        {
            "geometry": feature.get("geometry"),
            "properties": feature.get("properties"),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def request_feature_collection(
    endpoint: str,
    layer: str,
    bbox: tuple[float, float, float, float],
    count: int = PAGE_SIZE,
) -> tuple[dict[str, Any], str]:
    minx, miny, maxx, maxy = bbox
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": layer,
        "outputFormat": "application/json",
        "srsName": SOURCE_CRS,
        "bbox": f"{minx},{miny},{maxx},{maxy},{SOURCE_CRS}",
        "count": str(count),
    }
    url = f"{endpoint}?{urlencode(params)}"
    payload = request_bytes(url, "application/json,application/geo+json")
    data = json.loads(payload.decode("utf-8"))
    if data.get("type") != "FeatureCollection":
        raise ValueError("A resposta do WFS não é uma FeatureCollection.")
    returned = len(data.get("features", []))
    if returned >= count:
        raise RuntimeError(
            f"A consulta retornou o limite de {count} feições. "
            "Implemente paginação antes de usar o resultado."
        )
    return data, url


def probe_layer(
    endpoint: str,
    layer: str,
    bbox: tuple[float, float, float, float],
) -> bool:
    try:
        data, _ = request_feature_collection(endpoint, layer, bbox, count=PAGE_SIZE)
        return data.get("type") == "FeatureCollection"
    except (
        HTTPError,
        URLError,
        TimeoutError,
        RuntimeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return False


def resolve_endpoint_and_layer(
    probe_bbox: tuple[float, float, float, float],
) -> tuple[str, str, list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    errors: list[str] = []

    for endpoint in ENDPOINTS:
        for layer in CANDIDATE_LAYERS:
            success = probe_layer(endpoint, layer, probe_bbox)
            attempts.append({"endpoint": endpoint, "layer": layer, "success": success})
            if success:
                return endpoint, layer, attempts

        try:
            discovered = discover_layers(endpoint)
        except (HTTPError, URLError, TimeoutError, ET.ParseError, ValueError) as exc:
            errors.append(f"{endpoint}: falha no GetCapabilities: {exc}")
            continue

        for layer, title, score in discovered:
            success = probe_layer(endpoint, layer, probe_bbox)
            attempts.append(
                {
                    "endpoint": endpoint,
                    "layer": layer,
                    "title": title,
                    "score": score,
                    "success": success,
                }
            )
            if success:
                return endpoint, layer, attempts

    raise RuntimeError(
        "Não foi possível localizar a camada de cobertura vegetal no WFS do GeoSampa.\n"
        + "\n".join(errors)
    )


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cemeteries = json.loads(CEMETERIES_PATH.read_text(encoding="utf-8"))
    cemetery_features = cemeteries.get("features", [])
    if not cemetery_features:
        raise RuntimeError("A base de cemitérios está vazia.")

    cemetery_records: list[tuple[str, tuple[float, float, float, float]]] = []
    for feature in cemetery_features:
        geometry = shape(feature["geometry"])
        if not geometry.is_valid:
            geometry = geometry.buffer(0)
        equipment_id = str(
            (feature.get("properties") or {}).get("id_equipamento") or feature.get("id")
        )
        cemetery_records.append((equipment_id, geometry.bounds))

    endpoint, layer, discovery_attempts = resolve_endpoint_and_layer(cemetery_records[0][1])

    collected: dict[str, dict[str, Any]] = {}
    requests: list[dict[str, Any]] = []
    source_crs_member: dict[str, Any] | None = None

    for equipment_id, bbox in cemetery_records:
        data, url = request_feature_collection(endpoint, layer, bbox)
        if source_crs_member is None and isinstance(data.get("crs"), dict):
            source_crs_member = data["crs"]
        feature_count = len(data.get("features", []))
        requests.append(
            {
                "id_equipamento": equipment_id,
                "bbox_31983": [round(value, 3) for value in bbox],
                "request_url": url,
                "feature_count_returned": feature_count,
            }
        )
        for feature in data.get("features", []):
            collected[feature_key(feature)] = feature

    output: dict[str, Any] = {
        "type": "FeatureCollection",
        "name": "cobertura_vegetal_2017_entorno_cemiterios_31983",
        "features": list(collected.values()),
    }
    if source_crs_member is not None:
        output["crs"] = source_crs_member
    else:
        output["crs"] = {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:EPSG::31983"},
        }

    captured_at = datetime.now(timezone.utc).isoformat()
    OUTPUT_GEOJSON.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    metadata = {
        "captured_at_utc": captured_at,
        "source": "GeoSampa — Prefeitura do Município de São Paulo",
        "dataset": "Mapeamento Digital da Cobertura Vegetal 2017",
        "publication_year": 2020,
        "imagery_reference": "ortofotos 2017/2018 com apoio LiDAR",
        "metadata_record": METADATA_RECORD,
        "methodology_report": METHODOLOGY_REPORT,
        "endpoint": endpoint,
        "layer": layer,
        "source_crs": SOURCE_CRS,
        "equipment_count_queried": len(cemetery_records),
        "unique_feature_count": len(collected),
        "discovery_attempts": discovery_attempts,
        "requests": requests,
        "notes": [
            "A coleta usa uma caixa envolvente por equipamento para reduzir o volume transferido.",
            "As feições são preservadas integralmente; o recorte exato ocorre na etapa de análise.",
            "O produto mede cobertura vegetal classificada em 15 categorias, não cobertura estrita de copas.",
        ],
    }
    OUTPUT_METADATA.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        f"GeoSampa: camada {layer}; {len(collected)} feições únicas "
        f"coletadas para {len(cemetery_records)} equipamentos."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise
