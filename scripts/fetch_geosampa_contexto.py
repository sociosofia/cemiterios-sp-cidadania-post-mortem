#!/usr/bin/env python3
"""Baixa camadas de contexto territorial do WFS do GeoSampa.

Camadas:
- distritos municipais;
- subprefeituras.

As respostas originais são preservadas em EPSG:31983 e versões em EPSG:4326
são geradas para o mapa web.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "geosampa"
PROCESSED_DIR = ROOT / "data" / "processed"
ENDPOINT = "https://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs"
SOURCE_CRS = "EPSG:31983"
TARGET_CRS = "EPSG:4326"
LAYERS = {
    "distritos": "geoportal:distrito_municipal",
    "subprefeituras": "geoportal:subprefeitura",
}


def transform_coordinates(coords: Any, transformer: Transformer) -> Any:
    if not isinstance(coords, list):
        return coords
    if len(coords) >= 2 and all(isinstance(value, (int, float)) for value in coords[:2]):
        x, y = transformer.transform(coords[0], coords[1])
        result = [x, y]
        result.extend(coords[2:])
        return result
    return [transform_coordinates(item, transformer) for item in coords]


def fetch_layer(layer: str) -> tuple[dict[str, Any], str]:
    parameters = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": layer,
        "outputFormat": "application/json",
        "srsName": SOURCE_CRS,
    }
    url = f"{ENDPOINT}?{urlencode(parameters)}"
    request = Request(
        url,
        headers={
            "User-Agent": "cemiterios-sp-cidadania-post-mortem/1.0",
            "Accept": "application/json, application/geo+json",
        },
    )
    with urlopen(request, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))
    if data.get("type") != "FeatureCollection":
        raise RuntimeError(f"Resposta inválida para {layer}.")
    return data, url


def to_wgs84(data: dict[str, Any]) -> dict[str, Any]:
    transformer = Transformer.from_crs(SOURCE_CRS, TARGET_CRS, always_xy=True)
    output = json.loads(json.dumps(data))
    output.pop("crs", None)
    for feature in output.get("features", []):
        geometry = feature.get("geometry")
        if geometry and geometry.get("coordinates") is not None:
            geometry["coordinates"] = transform_coordinates(
                geometry["coordinates"], transformer
            )
    return output


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    metadata: dict[str, Any] = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "GeoSampa — Prefeitura do Município de São Paulo",
        "source_crs": SOURCE_CRS,
        "derived_crs": TARGET_CRS,
        "license": "CC BY-SA 4.0",
        "layers": {},
    }

    for label, layer in LAYERS.items():
        source, request_url = fetch_layer(layer)
        transformed = to_wgs84(source)
        (RAW_DIR / f"{label}_31983.geojson").write_text(
            json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (PROCESSED_DIR / f"{label}_4326.geojson").write_text(
            json.dumps(transformed, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        metadata["layers"][label] = {
            "layer": layer,
            "request_url": request_url,
            "feature_count": len(source.get("features", [])),
        }
        print(f"{label}: {metadata['layers'][label]['feature_count']} feições.")

    (PROCESSED_DIR / "contexto_geosampa_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
