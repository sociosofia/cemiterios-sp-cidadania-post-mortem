#!/usr/bin/env python3
"""Associa cemitérios a distritos e subprefeituras por interseção de área.

A unidade administrativa principal é aquela que contém a maior parcela da área
do equipamento. Todas as interseções relevantes são preservadas com suas
proporções, evitando uma classificação puramente baseada no centroide.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
CEMETERIES_31983 = ROOT / "data" / "processed" / "cemiterios_concessao_31983.geojson"
CEMETERIES_4326 = ROOT / "data" / "processed" / "cemiterios_concessao_4326.geojson"
DISTRICTS = ROOT / "data" / "raw" / "geosampa" / "distritos_31983.geojson"
SUBPREFECTURES = ROOT / "data" / "raw" / "geosampa" / "subprefeituras_31983.geojson"
PROCESSED_DIR = ROOT / "data" / "processed"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_name_field(features: list[dict[str, Any]], kind: str) -> str:
    if not features:
        raise RuntimeError(f"Camada de {kind} vazia.")
    keys = list((features[0].get("properties") or {}).keys())
    candidates = {
        "distrito": [
            "nm_distrito_municipal",
            "nm_distrito",
            "nome_distrito",
            "ds_distrito",
        ],
        "subprefeitura": [
            "nm_subprefeitura",
            "nm_subprefeitura_municipal",
            "nome_subprefeitura",
            "ds_subprefeitura",
        ],
    }[kind]
    for candidate in candidates:
        if candidate in keys:
            return candidate
    for key in keys:
        normalized = key.lower()
        if kind in normalized and ("nm" in normalized or "nome" in normalized):
            return key
    raise RuntimeError(
        f"Campo de nome não encontrado na camada de {kind}. Campos: {keys}"
    )


def prepare_units(
    feature_collection: dict[str, Any], name_field: str
) -> list[tuple[str, Any]]:
    units = []
    for feature in feature_collection.get("features", []):
        name = str((feature.get("properties") or {}).get(name_field, "")).strip()
        if not name:
            continue
        geometry = shape(feature["geometry"])
        if not geometry.is_valid:
            geometry = geometry.buffer(0)
        units.append((name, geometry))
    return units


def area_shares(geometry, units: list[tuple[str, Any]]) -> list[dict[str, Any]]:
    total_area = geometry.area
    overlaps = []
    for name, unit_geometry in units:
        if not geometry.intersects(unit_geometry):
            continue
        intersection_area = geometry.intersection(unit_geometry).area
        if intersection_area <= 1:
            continue
        overlaps.append(
            {
                "nome": name,
                "area_m2": round(intersection_area, 3),
                "proporcao": intersection_area / total_area if total_area else 0,
            }
        )
    overlaps.sort(key=lambda item: item["area_m2"], reverse=True)
    return overlaps


def serialize_shares(shares: list[dict[str, Any]]) -> str:
    return "|".join(
        f"{item['nome']}:{item['proporcao'] * 100:.2f}%" for item in shares
    )


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    cemeteries_31983 = read_json(CEMETERIES_31983)
    cemeteries_4326 = read_json(CEMETERIES_4326)
    districts = read_json(DISTRICTS)
    subprefectures = read_json(SUBPREFECTURES)

    district_name_field = find_name_field(districts.get("features", []), "distrito")
    subprefecture_name_field = find_name_field(
        subprefectures.get("features", []), "subprefeitura"
    )
    district_units = prepare_units(districts, district_name_field)
    subprefecture_units = prepare_units(subprefectures, subprefecture_name_field)

    context_by_id: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []

    for feature in cemeteries_31983.get("features", []):
        properties = feature["properties"]
        geometry = shape(feature["geometry"])
        district_shares = area_shares(geometry, district_units)
        subprefecture_shares = area_shares(geometry, subprefecture_units)
        context = {
            "distrito_principal": district_shares[0]["nome"] if district_shares else None,
            "distritos_intersectados": serialize_shares(district_shares),
            "numero_distritos_intersectados": len(district_shares),
            "subprefeitura_principal": (
                subprefecture_shares[0]["nome"] if subprefecture_shares else None
            ),
            "subprefeituras_intersectadas": serialize_shares(subprefecture_shares),
            "numero_subprefeituras_intersectadas": len(subprefecture_shares),
            "metodo_contexto_administrativo": "maior_area_de_intersecao_em_EPSG_31983",
        }
        properties.update(context)
        context_by_id[feature["id"]] = context
        rows.append(
            {
                "id_equipamento": feature["id"],
                "nome_oficial": properties.get("nome_oficial"),
                "categoria_tarifaria": properties.get("categoria_tarifaria"),
                "destino_gratuidade_hipossuficiencia": properties.get(
                    "destino_gratuidade_hipossuficiencia"
                ),
                **context,
            }
        )

    for feature in cemeteries_4326.get("features", []):
        feature["properties"].update(context_by_id[feature["id"]])

    (PROCESSED_DIR / "cemiterios_concessao_contexto_31983.geojson").write_text(
        json.dumps(cemeteries_31983, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (PROCESSED_DIR / "cemiterios_concessao_contexto_4326.geojson").write_text(
        json.dumps(cemeteries_4326, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with (PROCESSED_DIR / "cemiterios_contexto_administrativo.csv").open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "district_name_field": district_name_field,
        "subprefecture_name_field": subprefecture_name_field,
        "district_count": len(district_units),
        "subprefecture_count": len(subprefecture_units),
        "equipment_count": len(rows),
        "method": "interseção de polígonos e seleção da maior área em EPSG:31983",
    }
    (PROCESSED_DIR / "contexto_administrativo_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"Contexto administrativo associado a {len(rows)} equipamentos "
        f"usando {district_name_field} e {subprefecture_name_field}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
