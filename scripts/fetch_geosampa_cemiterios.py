#!/usr/bin/env python3
"""Baixa a camada oficial de cemitérios do WFS do GeoSampa.

Saídas:
- data/raw/geosampa/equipamento_cemiterio_31983.geojson
- data/processed/geosampa_cemiterios_4326.geojson
- data/processed/geosampa_cemiterios.csv
- data/processed/geosampa_cemiterios_metadata.json

A resposta original é preservada sem alteração. A cópia em EPSG:4326 é
produzida apenas para interoperabilidade e mapas web.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pyproj import Transformer

LAYER = "geoportal:equipamento_cemiterio"
SOURCE_CRS = "EPSG:31983"
TARGET_CRS = "EPSG:4326"
ENDPOINTS = (
    "https://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs",
    "http://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs",
)

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "geosampa"
PROCESSED_DIR = ROOT / "data" / "processed"


def request_geojson() -> tuple[dict[str, Any], str]:
    """Obtém a camada via WFS, tentando HTTPS e depois HTTP."""
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": LAYER,
        "outputFormat": "application/json",
        "srsName": SOURCE_CRS,
    }
    errors: list[str] = []

    for endpoint in ENDPOINTS:
        url = f"{endpoint}?{urlencode(params)}"
        request = Request(
            url,
            headers={
                "User-Agent": (
                    "cemiterios-sp-cidadania-post-mortem/1.0 "
                    "(pesquisa acadêmica; dados públicos)"
                ),
                "Accept": "application/json, application/geo+json",
            },
        )
        try:
            with urlopen(request, timeout=120) as response:
                payload = response.read()
            data = json.loads(payload.decode("utf-8"))
            if data.get("type") != "FeatureCollection":
                raise ValueError("A resposta do WFS não é uma FeatureCollection.")
            return data, url
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{url}: {exc}")

    raise RuntimeError("Falha ao consultar o GeoSampa:\n" + "\n".join(errors))


def transform_coordinates(coords: Any, transformer: Transformer) -> Any:
    """Transforma recursivamente coordenadas de qualquer geometria GeoJSON."""
    if not isinstance(coords, list):
        return coords
    if len(coords) >= 2 and all(isinstance(v, (int, float)) for v in coords[:2]):
        x, y = transformer.transform(coords[0], coords[1])
        transformed = [x, y]
        if len(coords) > 2:
            transformed.extend(coords[2:])
        return transformed
    return [transform_coordinates(item, transformer) for item in coords]


def to_wgs84(data: dict[str, Any]) -> dict[str, Any]:
    transformer = Transformer.from_crs(SOURCE_CRS, TARGET_CRS, always_xy=True)
    output = json.loads(json.dumps(data))
    for feature in output.get("features", []):
        geometry = feature.get("geometry")
        if geometry and geometry.get("coordinates") is not None:
            geometry["coordinates"] = transform_coordinates(
                geometry["coordinates"], transformer
            )
    # A especificação moderna do GeoJSON assume WGS 84; não se inclui o membro crs.
    output.pop("crs", None)
    return output


def scalar_properties(features: list[dict[str, Any]]) -> list[str]:
    fields: set[str] = set()
    for feature in features:
        for key, value in (feature.get("properties") or {}).items():
            if value is None or isinstance(value, (str, int, float, bool)):
                fields.add(key)
    return sorted(fields)


def write_flat_csv(
    source: dict[str, Any], transformed: dict[str, Any], destination: Path
) -> None:
    source_features = source.get("features", [])
    target_features = transformed.get("features", [])
    property_fields = scalar_properties(source_features)
    fixed_fields = [
        "feature_id",
        "geometry_type",
        "x_31983",
        "y_31983",
        "longitude",
        "latitude",
    ]

    with destination.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fixed_fields + property_fields)
        writer.writeheader()
        for index, feature in enumerate(source_features):
            geometry = feature.get("geometry") or {}
            target_geometry = (
                target_features[index].get("geometry") or {}
                if index < len(target_features)
                else {}
            )
            row: dict[str, Any] = {
                "feature_id": feature.get("id", ""),
                "geometry_type": geometry.get("type", ""),
                "x_31983": "",
                "y_31983": "",
                "longitude": "",
                "latitude": "",
            }

            if geometry.get("type") == "Point":
                coordinates = geometry.get("coordinates") or []
                target_coordinates = target_geometry.get("coordinates") or []
                if len(coordinates) >= 2:
                    row["x_31983"], row["y_31983"] = coordinates[:2]
                if len(target_coordinates) >= 2:
                    row["longitude"], row["latitude"] = target_coordinates[:2]

            for field in property_fields:
                value = (feature.get("properties") or {}).get(field)
                if value is None or isinstance(value, (str, int, float, bool)):
                    row[field] = value
                else:
                    row[field] = json.dumps(value, ensure_ascii=False)
            writer.writerow(row)


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    source, request_url = request_geojson()
    transformed = to_wgs84(source)
    captured_at = datetime.now(timezone.utc).isoformat()

    raw_path = RAW_DIR / "equipamento_cemiterio_31983.geojson"
    web_path = PROCESSED_DIR / "geosampa_cemiterios_4326.geojson"
    csv_path = PROCESSED_DIR / "geosampa_cemiterios.csv"
    metadata_path = PROCESSED_DIR / "geosampa_cemiterios_metadata.json"

    raw_path.write_text(
        json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    web_path.write_text(
        json.dumps(transformed, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_flat_csv(source, transformed, csv_path)

    metadata = {
        "captured_at_utc": captured_at,
        "source": "GeoSampa — Prefeitura do Município de São Paulo",
        "request_url": request_url,
        "layer": LAYER,
        "source_crs": SOURCE_CRS,
        "derived_crs": TARGET_CRS,
        "feature_count": len(source.get("features", [])),
        "license": "CC BY-SA 4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "notes": [
            "A geometria bruta é preservada em data/raw/geosampa.",
            "A transformação para EPSG:4326 usa pyproj com always_xy=True.",
            "A camada do GeoSampa é uma fonte espacial; nomes e vínculos contratuais serão confrontados com o inventário documental.",
        ],
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        f"GeoSampa: {metadata['feature_count']} feições baixadas; "
        f"captura em {captured_at}."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # mantém a mensagem clara no GitHub Actions
        print(f"ERRO: {exc}", file=sys.stderr)
        raise
