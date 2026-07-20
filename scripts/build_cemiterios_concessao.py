#!/usr/bin/env python3
"""Filtra e enriquece os polígonos dos equipamentos da concessão.

O script cruza três fontes do próprio repositório:
- inventário documental dos equipamentos;
- associação auditável entre identificadores e feições do GeoSampa;
- GeoJSON bruto capturado pelo WFS oficial.

Produtos:
- data/processed/cemiterios_concessao_31983.geojson
- data/processed/cemiterios_concessao_4326.geojson
- data/processed/cemiterios_concessao_centroides.csv
- data/processed/cemiterios_concessao_metadata.json

Os centroides são pontos analíticos derivados dos polígonos. Eles não devem ser
interpretados como portões ou entradas de atendimento.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parents[1]
RAW_GEOJSON = ROOT / "data" / "raw" / "geosampa" / "equipamento_cemiterio_31983.geojson"
REFERENCE_CSV = ROOT / "data" / "reference" / "cemiterios_crematorio.csv"
MAPPING_CSV = ROOT / "data" / "reference" / "geosampa_mapping.csv"
PROCESSED_DIR = ROOT / "data" / "processed"

SOURCE_CRS = "EPSG:31983"
TARGET_CRS = "EPSG:4326"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def clean_value(value: str) -> Any:
    """Converte apenas tipos inequivocamente definidos no inventário."""
    if value == "":
        return None
    if value in {"True", "False"}:
        return value == "True"
    try:
        if value.isdigit():
            return int(value)
        if any(character in value for character in "."):
            return float(value)
    except ValueError:
        pass
    return value


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    source = json.loads(RAW_GEOJSON.read_text(encoding="utf-8"))
    source_by_id = {
        feature.get("id"): feature for feature in source.get("features", [])
    }
    reference_rows = read_csv(REFERENCE_CSV)
    reference_by_id = {row["id_equipamento"]: row for row in reference_rows}
    mapping_rows = read_csv(MAPPING_CSV)

    feature_ids_by_equipment: dict[str, list[str]] = defaultdict(list)
    mapping_notes_by_equipment: dict[str, list[str]] = defaultdict(list)
    for row in mapping_rows:
        feature_ids_by_equipment[row["id_equipamento"]].append(
            row["feature_id_geosampa"]
        )
        if row.get("observacoes"):
            mapping_notes_by_equipment[row["id_equipamento"]].append(
                row["observacoes"]
            )

    missing_reference = sorted(set(feature_ids_by_equipment) - set(reference_by_id))
    missing_mapping = sorted(set(reference_by_id) - set(feature_ids_by_equipment))
    missing_features = sorted(
        feature_id
        for feature_ids in feature_ids_by_equipment.values()
        for feature_id in feature_ids
        if feature_id not in source_by_id
    )
    if missing_reference or missing_mapping or missing_features:
        raise RuntimeError(
            "Falha de integridade no cruzamento. "
            f"Sem inventário: {missing_reference}; "
            f"sem mapeamento: {missing_mapping}; "
            f"feições ausentes no WFS: {missing_features}."
        )

    transformer = Transformer.from_crs(SOURCE_CRS, TARGET_CRS, always_xy=True)
    output_31983: list[dict[str, Any]] = []
    output_4326: list[dict[str, Any]] = []
    centroid_rows: list[dict[str, Any]] = []

    for equipment_id, reference in reference_by_id.items():
        source_features = [
            source_by_id[feature_id]
            for feature_id in feature_ids_by_equipment[equipment_id]
        ]
        geometries = []
        for feature in source_features:
            geometry = shape(feature["geometry"])
            if not geometry.is_valid:
                geometry = geometry.buffer(0)
            geometries.append(geometry)
        dissolved = unary_union(geometries)
        if not dissolved.is_valid:
            dissolved = dissolved.buffer(0)

        centroid = dissolved.centroid
        longitude, latitude = transformer.transform(centroid.x, centroid.y)
        dissolved_wgs84 = transform(transformer.transform, dissolved)

        geosampa_names = sorted(
            {
                str((feature.get("properties") or {}).get("nm_equipamento", ""))
                for feature in source_features
                if (feature.get("properties") or {}).get("nm_equipamento")
            }
        )
        geosampa_addresses = sorted(
            {
                str((feature.get("properties") or {}).get("tx_endereco_equipamento", ""))
                for feature in source_features
                if (feature.get("properties") or {}).get("tx_endereco_equipamento")
            }
        )
        geosampa_ceps = sorted(
            {
                str((feature.get("properties") or {}).get("cd_cep_equipamento", ""))
                for feature in source_features
                if (feature.get("properties") or {}).get("cd_cep_equipamento")
            }
        )

        properties: dict[str, Any] = {
            key: clean_value(value) for key, value in reference.items()
        }
        properties.update(
            {
                "feature_ids_geosampa": "|".join(
                    feature_ids_by_equipment[equipment_id]
                ),
                "nome_geosampa": "|".join(geosampa_names),
                "endereco_geosampa": "|".join(geosampa_addresses),
                "cep_geosampa": "|".join(geosampa_ceps),
                "notas_mapeamento": "|".join(
                    mapping_notes_by_equipment[equipment_id]
                ),
                "area_m2_31983": round(dissolved.area, 3),
                "perimetro_m_31983": round(dissolved.length, 3),
                "centroide_x_31983": round(centroid.x, 3),
                "centroide_y_31983": round(centroid.y, 3),
                "centroide_longitude": round(longitude, 8),
                "centroide_latitude": round(latitude, 8),
                "metodo_geometria": "poligono_wfs_geosampa_dissolvido",
                "metodo_ponto": "centroide_geometrico_derivado; nao representa entrada",
            }
        )

        feature_31983 = {
            "type": "Feature",
            "id": equipment_id,
            "properties": properties,
            "geometry": mapping(dissolved),
        }
        feature_4326 = {
            "type": "Feature",
            "id": equipment_id,
            "properties": properties,
            "geometry": mapping(dissolved_wgs84),
        }
        output_31983.append(feature_31983)
        output_4326.append(feature_4326)
        centroid_rows.append(properties)

    collection_31983 = {
        "type": "FeatureCollection",
        "name": "cemiterios_concessao_31983",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:EPSG::31983"},
        },
        "features": output_31983,
    }
    collection_4326 = {
        "type": "FeatureCollection",
        "name": "cemiterios_concessao_4326",
        "features": output_4326,
    }

    (PROCESSED_DIR / "cemiterios_concessao_31983.geojson").write_text(
        json.dumps(collection_31983, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (PROCESSED_DIR / "cemiterios_concessao_4326.geojson").write_text(
        json.dumps(collection_4326, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    fieldnames = list(centroid_rows[0].keys())
    with (PROCESSED_DIR / "cemiterios_concessao_centroides.csv").open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(centroid_rows)

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_crs": SOURCE_CRS,
        "web_crs": TARGET_CRS,
        "equipment_count": len(output_31983),
        "source_feature_count_used": sum(
            len(ids) for ids in feature_ids_by_equipment.values()
        ),
        "source_feature_count_total": len(source.get("features", [])),
        "notes": [
            "A camada WFS contém cemitérios fora do escopo da concessão; o produto filtrado usa somente as associações auditadas em data/reference/geosampa_mapping.csv.",
            "Feições múltiplas do mesmo equipamento são dissolvidas em uma única geometria.",
            "Centroides são derivados analíticos e não representam acessos públicos.",
        ],
    }
    (PROCESSED_DIR / "cemiterios_concessao_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        f"Gerados {len(output_31983)} equipamentos a partir de "
        f"{metadata['source_feature_count_used']} feições do GeoSampa."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
