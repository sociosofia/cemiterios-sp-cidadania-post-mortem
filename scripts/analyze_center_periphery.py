#!/usr/bin/env python3
"""Produz indicadores descritivos de centralidade dos cemitérios.

Referência central: centroide geométrico do distrito Sé.
Medida: distância euclidiana entre centroides em EPSG:31983.

A medida não representa distância viária, tempo de viagem nem acessibilidade por
transporte público. Serve como primeiro indicador espacial reproduzível.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
CEMETERIES = ROOT / "data" / "processed" / "cemiterios_concessao_contexto_31983.geojson"
DISTRICTS = ROOT / "data" / "raw" / "geosampa" / "distritos_31983.geojson"
PROCESSED_DIR = ROOT / "data" / "processed"
RESULTS_DOC = ROOT / "docs" / "RESULTADOS_PRELIMINARES.md"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def category(value):
    if value in (None, "", "None"):
        return None
    return int(value)


def format_number(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    cemeteries = read_json(CEMETERIES)
    districts = read_json(DISTRICTS)

    se_features = [
        feature
        for feature in districts.get("features", [])
        if str((feature.get("properties") or {}).get("nm_distrito_municipal", "")).upper()
        == "SE"
    ]
    if len(se_features) != 1:
        raise RuntimeError(
            f"Esperava uma feição para o distrito Sé; encontrei {len(se_features)}."
        )
    se_geometry = shape(se_features[0]["geometry"])
    se_centroid = se_geometry.centroid

    rows: list[dict[str, Any]] = []
    by_category: dict[int, list[float]] = defaultdict(list)
    free_burial_distances: list[float] = []
    nonfree_burial_distances: list[float] = []

    for feature in cemeteries.get("features", []):
        properties = feature["properties"]
        geometry = shape(feature["geometry"])
        distance_km = geometry.centroid.distance(se_centroid) / 1000
        stratum = category(properties.get("categoria_tarifaria"))
        is_free = bool(properties.get("destino_gratuidade_hipossuficiencia"))
        modality = properties.get("modalidade_gratuita")
        equipment_type = properties.get("tipo")
        if stratum is not None:
            by_category[stratum].append(distance_km)
        if equipment_type == "cemiterio":
            if is_free and modality == "sepultamento":
                free_burial_distances.append(distance_km)
            else:
                nonfree_burial_distances.append(distance_km)

        rows.append(
            {
                "id_equipamento": feature["id"],
                "nome_oficial": properties.get("nome_oficial"),
                "tipo": equipment_type,
                "categoria_tarifaria": stratum,
                "destino_gratuidade_hipossuficiencia": is_free,
                "modalidade_gratuita": modality,
                "distrito_principal": properties.get("distrito_principal"),
                "subprefeitura_principal": properties.get("subprefeitura_principal"),
                "distancia_centroide_distrito_se_km": round(distance_km, 3),
                "metodo_distancia": "euclidiana_entre_centroides_EPSG_31983",
            }
        )

    output_csv = PROCESSED_DIR / "distancias_centroide_se.csv"
    with output_csv.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: row["distancia_centroide_distrito_se_km"]))

    category_summary = {}
    for stratum in sorted(by_category):
        values = by_category[stratum]
        category_summary[str(stratum)] = {
            "count": len(values),
            "mean_km": round(mean(values), 3),
            "median_km": round(median(values), 3),
            "minimum_km": round(min(values), 3),
            "maximum_km": round(max(values), 3),
        }

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "central_reference": "centroide geométrico do distrito Sé",
        "central_reference_x_31983": round(se_centroid.x, 3),
        "central_reference_y_31983": round(se_centroid.y, 3),
        "distance_method": "distância euclidiana entre centroides em EPSG:31983",
        "categories": category_summary,
        "free_burial_destinations": {
            "count": len(free_burial_distances),
            "mean_km": round(mean(free_burial_distances), 3),
            "median_km": round(median(free_burial_distances), 3),
            "minimum_km": round(min(free_burial_distances), 3),
            "maximum_km": round(max(free_burial_distances), 3),
        },
        "other_cemeteries": {
            "count": len(nonfree_burial_distances),
            "mean_km": round(mean(nonfree_burial_distances), 3),
            "median_km": round(median(nonfree_burial_distances), 3),
            "minimum_km": round(min(nonfree_burial_distances), 3),
            "maximum_km": round(max(nonfree_burial_distances), 3),
        },
        "limitations": [
            "Não representa distância viária nem tempo de deslocamento.",
            "O centroide do distrito Sé é uma referência analítica, não uma definição única de centro urbano.",
            "Os centroides dos cemitérios não representam portões de acesso.",
        ],
    }
    (PROCESSED_DIR / "analise_centro_periferia.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    category_lines = []
    for stratum in sorted(category_summary, key=int):
        values = category_summary[stratum]
        category_lines.append(
            f"| {stratum} | {values['count']} | {format_number(values['mean_km'])} | "
            f"{format_number(values['median_km'])} | {format_number(values['minimum_km'])}–{format_number(values['maximum_km'])} |"
        )

    free = summary["free_burial_destinations"]
    others = summary["other_cemeteries"]
    markdown = f"""# Resultados espaciais preliminares

## Referência metodológica

As distâncias abaixo são calculadas em linha reta entre o centroide geométrico de cada equipamento e o centroide do distrito Sé, em SIRGAS 2000 / UTM zona 23S (`EPSG:31983`). Não representam distância pela rede viária, tempo de viagem ou localização do portão de acesso.

## Distância por estrato tarifário

| Estrato | Equipamentos | Média (km) | Mediana (km) | Intervalo (km) |
|---:|---:|---:|---:|---:|
{chr(10).join(category_lines)}

## Destinos de sepultamento gratuito

Os {free['count']} destinos ordinários de sepultamento gratuito por hipossuficiência apresentam distância média de **{format_number(free['mean_km'])} km** e mediana de **{format_number(free['median_km'])} km** em relação ao centroide do distrito Sé. Nos demais cemitérios, a média é **{format_number(others['mean_km'])} km** e a mediana é **{format_number(others['median_km'])} km**.

Todos os destinos ordinários da gratuidade pertencem aos estratos 3 ou 4. Esse resultado é descritivo e não basta, isoladamente, para afirmar causalidade ou medir acessibilidade. A etapa seguinte deverá incorporar portões de entrada, rede viária, transporte público e indicadores socioeconômicos.

## Arquivos de apoio

- `data/processed/distancias_centroide_se.csv`
- `data/processed/analise_centro_periferia.json`
- `data/processed/cemiterios_contexto_administrativo.csv`
"""
    RESULTS_DOC.write_text(markdown, encoding="utf-8")
    print("Indicadores descritivos e resultados preliminares atualizados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
