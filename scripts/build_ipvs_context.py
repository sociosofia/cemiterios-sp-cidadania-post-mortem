#!/usr/bin/env python3
"""Calcula o contexto IPVS no entorno dos cemitérios concedidos.

São produzidos indicadores em buffers de 500 m, 1 km e 2 km. A distribuição
populacional é aproximada pela fração da área de cada setor interceptada pelo
buffer; por isso é apresentada juntamente com a distribuição puramente areal.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any

from shapely.geometry import shape
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
DOCS = ROOT / "docs"

CEMETERIES = PROCESSED / "cemiterios_concessao_31983.geojson"
IPVS = PROCESSED / "ipvs_sp_2022_31983.geojson"
OUTPUT = PROCESSED / "cemiterios_contexto_ipvs_2022.csv"
SUMMARY = PROCESSED / "resumo_ipvs_cemiterios_2022.json"
REPORT = DOCS / "RESULTADOS_IPVS_2022.md"
BUFFERS = (500, 1000, 2000)


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "sim", "yes"}


def numeric_group(value: object) -> int | None:
    text = "".join(character for character in str(value or "") if character.isdigit())
    if not text:
        return None
    number = int(text)
    return number if 1 <= number <= 6 else None


def finite(value: float | None) -> bool:
    return value is not None and math.isfinite(value)


def query_indices(tree: STRtree, geometries: list[Any], target: Any) -> list[int]:
    result = tree.query(target)
    if len(result) == 0:
        return []
    first = result[0]
    if isinstance(first, (int,)) or hasattr(first, "item"):
        return [int(item) for item in result]
    identity = {id(geometry): index for index, geometry in enumerate(geometries)}
    return [identity[id(geometry)] for geometry in result if id(geometry) in identity]


def weighted_median(values: list[tuple[int, float]]) -> float | None:
    clean = sorted((value, weight) for value, weight in values if weight > 0)
    total = sum(weight for _, weight in clean)
    if total <= 0:
        return None
    threshold = total / 2
    running = 0.0
    for value, weight in clean:
        running += weight
        if running >= threshold:
            return float(value)
    return float(clean[-1][0]) if clean else None


def summarize_buffer(buffer_geometry: Any, sectors: list[dict[str, Any]], tree: STRtree, sector_geometries: list[Any]) -> dict[str, Any]:
    area_by_group: dict[int, float] = defaultdict(float)
    population_by_group: dict[int, float] = defaultdict(float)
    total_area = 0.0
    total_population = 0.0
    intersected = 0

    for index in query_indices(tree, sector_geometries, buffer_geometry):
        item = sectors[index]
        geometry = item["geometry"]
        if not geometry.intersects(buffer_geometry):
            continue
        intersection = geometry.intersection(buffer_geometry)
        if intersection.is_empty:
            continue
        area = intersection.area
        if area <= 0:
            continue
        intersected += 1
        group = item["group"]
        if group is None:
            continue
        area_by_group[group] += area
        total_area += area

        population = item["population"]
        sector_area = geometry.area
        if finite(population) and sector_area > 0:
            estimated = float(population) * min(1.0, area / sector_area)
            population_by_group[group] += estimated
            total_population += estimated

    result: dict[str, Any] = {
        "setores_intersectados": intersected,
        "area_classificada_m2": total_area,
        "populacao_estimada": total_population if total_population > 0 else None,
    }
    for group in range(1, 7):
        result[f"pct_area_grupo_{group}"] = (
            area_by_group[group] / total_area if total_area > 0 else None
        )
        result[f"pct_pop_grupo_{group}"] = (
            population_by_group[group] / total_population if total_population > 0 else None
        )

    result["pct_area_grupos_4_6"] = (
        sum(area_by_group[group] for group in (4, 5, 6)) / total_area
        if total_area > 0
        else None
    )
    result["pct_pop_grupos_4_6"] = (
        sum(population_by_group[group] for group in (4, 5, 6)) / total_population
        if total_population > 0
        else None
    )
    result["grupo_mediano_area"] = weighted_median(list(area_by_group.items()))
    result["grupo_mediano_pop"] = weighted_median(list(population_by_group.items()))
    return result


def stats(rows: list[dict[str, Any]], field: str) -> dict[str, float | int | None]:
    values = [float(row[field]) for row in rows if row.get(field) not in (None, "")]
    return {
        "n": len(values),
        "media": mean(values) if values else None,
        "mediana": median(values) if values else None,
    }


def format_pct(value: object) -> str:
    if value in (None, ""):
        return "—"
    return f"{100 * float(value):.1f}%".replace(".", ",")


def main() -> int:
    cemeteries_data = json.loads(CEMETERIES.read_text(encoding="utf-8"))
    ipvs_data = json.loads(IPVS.read_text(encoding="utf-8"))

    sectors: list[dict[str, Any]] = []
    for feature in ipvs_data["features"]:
        geometry = shape(feature["geometry"])
        if geometry.is_empty:
            continue
        properties = feature.get("properties", {})
        sectors.append(
            {
                "geometry": geometry,
                "group": numeric_group(properties.get("ipvs_grupo")),
                "population": properties.get("populacao"),
            }
        )
    sector_geometries = [item["geometry"] for item in sectors]
    tree = STRtree(sector_geometries)

    rows: list[dict[str, Any]] = []
    for feature in cemeteries_data["features"]:
        properties = feature.get("properties", {})
        geometry = shape(feature["geometry"])
        row: dict[str, Any] = {
            "id_equipamento": properties.get("id_equipamento") or properties.get("id"),
            "nome_oficial": properties.get("nome_oficial") or properties.get("nome"),
            "categoria_tarifaria": properties.get("categoria_tarifaria"),
            "destino_gratuidade_hipossuficiencia": truthy(
                properties.get("destino_gratuidade_hipossuficiencia")
            ),
        }
        for distance in BUFFERS:
            result = summarize_buffer(geometry.buffer(distance), sectors, tree, sector_geometries)
            for key, value in result.items():
                row[f"{key}_{distance}m"] = value
        rows.append(row)

    fieldnames = list(rows[0].keys()) if rows else []
    with OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    cemeteries_only = [row for row in rows if row.get("categoria_tarifaria") not in (None, "")]
    free = [row for row in cemeteries_only if row["destino_gratuidade_hipossuficiencia"]]
    other = [row for row in cemeteries_only if not row["destino_gratuidade_hipossuficiencia"]]

    summary: dict[str, Any] = {
        "method": (
            "Interseção de buffers com setores IPVS 2022. A população é estimada "
            "proporcionalmente à área interceptada, pressupondo distribuição uniforme dentro do setor."
        ),
        "equipment_count": len(cemeteries_only),
        "groups": {},
        "by_tariff_category": {},
    }
    for label, group_rows in (("destinos_gratuitos", free), ("demais_cemiterios", other)):
        summary["groups"][label] = {
            "n": len(group_rows),
            "pct_pop_grupos_4_6_1000m": stats(group_rows, "pct_pop_grupos_4_6_1000m"),
            "pct_area_grupos_4_6_1000m": stats(group_rows, "pct_area_grupos_4_6_1000m"),
            "grupo_mediano_pop_1000m": stats(group_rows, "grupo_mediano_pop_1000m"),
        }
    categories = sorted({str(row["categoria_tarifaria"]) for row in cemeteries_only})
    for category in categories:
        category_rows = [row for row in cemeteries_only if str(row["categoria_tarifaria"]) == category]
        summary["by_tariff_category"][category] = {
            "n": len(category_rows),
            "pct_pop_grupos_4_6_1000m": stats(category_rows, "pct_pop_grupos_4_6_1000m"),
            "pct_area_grupos_4_6_1000m": stats(category_rows, "pct_area_grupos_4_6_1000m"),
            "grupo_mediano_pop_1000m": stats(category_rows, "grupo_mediano_pop_1000m"),
        }

    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    report = [
        "# IPVS 2022 no entorno dos cemitérios — resultados preliminares",
        "",
        "A análise cruza os polígonos dos cemitérios com os setores censitários do IPVS 2022.",
        "O indicador principal abaixo considera um buffer de 1 km.",
        "",
        "## Destinos gratuitos e demais cemitérios",
        "",
        "| Grupo | Cemitérios | População estimada nos grupos 4–6 | Área nos grupos 4–6 |",
        "|---|---:|---:|---:|",
    ]
    for label, title in (("destinos_gratuitos", "Destinos gratuitos"), ("demais_cemiterios", "Demais cemitérios")):
        item = summary["groups"][label]
        report.append(
            f"| {title} | {item['n']} | "
            f"{format_pct(item['pct_pop_grupos_4_6_1000m']['media'])} | "
            f"{format_pct(item['pct_area_grupos_4_6_1000m']['media'])} |"
        )

    report.extend(
        [
            "",
            "## Por categoria tarifária",
            "",
            "| Categoria | Cemitérios | População estimada nos grupos 4–6 | Área nos grupos 4–6 |",
            "|---:|---:|---:|---:|",
        ]
    )
    for category, item in summary["by_tariff_category"].items():
        report.append(
            f"| {category} | {item['n']} | "
            f"{format_pct(item['pct_pop_grupos_4_6_1000m']['media'])} | "
            f"{format_pct(item['pct_area_grupos_4_6_1000m']['media'])} |"
        )

    report.extend(
        [
            "",
            "## Limitação",
            "",
            "A estimativa populacional distribui uniformemente a população dentro de cada setor censitário. "
            "Ela descreve o entorno dos equipamentos e não o perfil das pessoas sepultadas.",
        ]
    )
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Contexto IPVS calculado para {len(rows)} equipamentos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
