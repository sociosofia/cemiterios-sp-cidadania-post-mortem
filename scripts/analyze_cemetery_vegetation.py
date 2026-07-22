#!/usr/bin/env python3
"""Cruza os cemitérios concedidos com a cobertura vegetal oficial de 2017.

Resultados:
- área territorial e cobertura vegetal por equipamento;
- composição pelas 15 categorias oficiais;
- agregado por bloco contratual;
- subtotal das classes com componente arbóreo explicitamente reconhecido.

O subtotal arbóreo não equivale à cobertura de copas: ele soma polígonos cujas
classes oficiais mencionam floresta, bosque, maciço ou cobertura arbórea. O
produto municipal específico de copas é distinto.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
CEMETERIES = ROOT / "data/processed/cemiterios_concessao_31983.geojson"
VEGETATION = ROOT / "data/raw/geosampa/cobertura_vegetal_2017_entorno_cemiterios_31983.geojson"
VEGETATION_METADATA = ROOT / "data/raw/geosampa/cobertura_vegetal_2017_entorno_cemiterios_metadata.json"
OUTPUT_CSV = ROOT / "data/processed/cemiterios_cobertura_vegetal_2017.csv"
OUTPUT_JSON = ROOT / "data/processed/resumo_cobertura_vegetal_cemiterios_2017.json"
OUTPUT_REPORT = ROOT / "docs/RESULTADOS_COBERTURA_VEGETAL_CEMITERIOS.md"

CATEGORY_NAMES = {
    1: "Floresta Ombrófila Densa Secundária — estágio avançado/primária",
    2: "Floresta Ombrófila Densa Secundária — estágio médio",
    3: "Floresta Ombrófila Densa Secundária — estágio inicial",
    4: "Floresta Ombrófila Densa Alto-Montana — mata nebular",
    5: "Floresta Paludosa e/ou de Várzea",
    6: "Campos Alto-Montanos",
    7: "Vegetação Herbáceo-Arbustiva de Várzea ou Brejo",
    8: "Vegetação Aquática Flutuante",
    9: "Maciços Florestais Heterogêneos e Bosques Urbanos",
    10: "Maciços Florestais Homogêneos",
    11: "Baixa cobertura arbórea, arbóreo-arbustiva e/ou arborescente",
    12: "Agricultura",
    13: "Média a alta cobertura arbórea, arbóreo-arbustiva e/ou arborescente",
    14: "Vegetação Herbáceo-Arbustiva",
    15: "Mista",
}
TREE_COMPONENT_CATEGORIES = {1, 2, 3, 4, 5, 9, 10, 11, 13}


def valid_geometry(feature: dict[str, Any]):
    geometry = shape(feature["geometry"])
    if not geometry.is_valid:
        geometry = geometry.buffer(0)
    return geometry


def intersects_bounds(a, b) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def category_code(properties: dict[str, Any]) -> int | None:
    preferred = (
        "cd_categoria_vegetacao",
        "vg_categ",
        "CAT",
        "categoria",
    )
    for field in preferred:
        value = properties.get(field)
        if value in (None, ""):
            continue
        try:
            return int(float(value))
        except (TypeError, ValueError):
            pass
    for field, value in properties.items():
        key = field.lower()
        if "categoria" not in key or "subcategoria" in key:
            continue
        try:
            return int(float(value))
        except (TypeError, ValueError):
            continue
    return None


def category_description(properties: dict[str, Any], code: int | None) -> str:
    preferred = (
        "tx_descricao_categoria_subcategoria",
        "vg_descric",
        "DESCRICAO",
        "descricao",
    )
    for field in preferred:
        value = properties.get(field)
        if value not in (None, ""):
            return str(value).strip()
    return CATEGORY_NAMES.get(code, "Categoria não identificada")


def union_area(geometries: list[Any]) -> float:
    return float(unary_union(geometries).area) if geometries else 0.0


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    territorial = sum(float(row["area_territorial_m2"]) for row in rows)
    vegetation = sum(float(row["cobertura_vegetal_m2"]) for row in rows)
    tree_component = sum(float(row["componente_arboreo_explicito_m2"]) for row in rows)
    return {
        "equipment_count": len(rows),
        "area_territorial_m2": round(territorial, 3),
        "cobertura_vegetal_m2": round(vegetation, 3),
        "cobertura_vegetal_percentual": round(vegetation / territorial * 100 if territorial else 0, 4),
        "componente_arboreo_explicito_m2": round(tree_component, 3),
        "componente_arboreo_percentual_do_territorio": round(
            tree_component / territorial * 100 if territorial else 0, 4
        ),
        "componente_arboreo_percentual_da_vegetacao": round(
            tree_component / vegetation * 100 if vegetation else 0, 4
        ),
    }


def br(value: float, decimals: int = 2) -> str:
    result = f"{value:,.{decimals}f}"
    return result.replace(",", "X").replace(".", ",").replace("X", ".")


def create_report(rows, summary, category_totals) -> str:
    general = summary["geral_23_equipamentos"]
    cemeteries = summary["somente_22_cemiterios"]

    block_lines = [
        "| Bloco | Concessionária | Área territorial (m²) | Vegetação (m²) | Vegetação (%) | Componente arbóreo explícito (%) |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for item in summary["por_bloco"]:
        block_lines.append(
            f"| {item['bloco_concessao']} | {item['concessionaria']} | "
            f"{br(item['area_territorial_m2'], 1)} | {br(item['cobertura_vegetal_m2'], 1)} | "
            f"{br(item['cobertura_vegetal_percentual'], 2)} | "
            f"{br(item['componente_arboreo_percentual_do_territorio'], 2)} |"
        )

    equipment_lines = [
        "| Equipamento | Bloco | Área (m²) | Vegetação (m²) | Vegetação (%) | Arbóreo explícito (%) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        equipment_lines.append(
            f"| {row['nome_oficial']} | {row['bloco_concessao']} | "
            f"{br(row['area_territorial_m2'], 1)} | {br(row['cobertura_vegetal_m2'], 1)} | "
            f"{br(row['cobertura_vegetal_percentual'], 2)} | "
            f"{br(row['componente_arboreo_percentual_do_territorio'], 2)} |"
        )

    category_lines = [
        "| Categoria | Descrição | Área (m²) | Participação na vegetação (%) |",
        "|---:|---|---:|---:|",
    ]
    for item in category_totals:
        category_lines.append(
            f"| {item['categoria']} | {item['descricao']} | {br(item['area_m2'], 1)} | "
            f"{br(item['participacao_na_cobertura_percentual'], 2)} |"
        )

    return f"""# Cobertura vegetal nos cemitérios públicos concedidos de São Paulo

## Resultado principal

O cruzamento utiliza os polígonos oficiais dos equipamentos e o **Mapeamento
Digital da Cobertura Vegetal 2017**, elaborado com ortofotos de 2017/2018 e apoio
LiDAR e publicado pela SVMA em 2020.

Nos 23 equipamentos, incluindo o Crematório Vila Alpina, foram identificados
**{br(general['cobertura_vegetal_m2'], 1)} m² de cobertura vegetal**, equivalentes
a **{br(general['cobertura_vegetal_percentual'], 2)}%** da área territorial. As
classes que explicitamente indicam floresta, bosque, maciço ou componente arbóreo
ocupam **{br(general['componente_arboreo_explicito_m2'], 1)} m²**, ou
**{br(general['componente_arboreo_percentual_do_territorio'], 2)}%** do território.

Considerando somente os 22 cemitérios, a cobertura vegetal é de
**{br(cemeteries['cobertura_vegetal_m2'], 1)} m²**
(**{br(cemeteries['cobertura_vegetal_percentual'], 2)}%**).

## Cautela conceitual

Cobertura vegetal não é sinônimo de área territorial, área permeável ou cobertura
de copas. O subtotal de componente arbóreo é uma agregação das categorias oficiais
1–5, 9–11 e 13; ele indica classes que contêm árvores, mas não mede diretamente a
projeção horizontal das copas. A categoria 15, mista, permanece separada porque sua
composição não pode ser atribuída integralmente ao estrato arbóreo.

## Por bloco contratual

{"\n".join(block_lines)}

As diferenças são uma **linha de base pré-concessão**, pois as imagens são de
2017/2018. Elas não medem o desempenho posterior das concessionárias.

## Por equipamento

{"\n".join(equipment_lines)}

## Classes de vegetação

{"\n".join(category_lines)}

## Interpretação para o Artigo Holanda

A análise permite separar três afirmações que apareciam fundidas no discurso
institucional: os cemitérios formam uma rede territorial de quase 296 hectares;
parte desse território foi classificada como cobertura vegetal; e uma parcela ainda
mais específica pertence a classes com componente arbóreo explícito. Essa distinção
preserva a força do argumento ambiental sem converter automaticamente todo solo
cemiterial em área verde.

O Plano Diretor integrou os cemitérios a um sistema municipal de áreas verdes e
espaços livres. A concessão dividiu essa infraestrutura em quatro blocos. O dado
pré-concessão permite examinar futuramente se manejo, compensações ambientais e
investimentos preservaram, ampliaram ou reduziram essa cobertura.

## Limites

- vegetação referente a ortofotos de 2017/2018;
- perímetros cemiteriais consultados no GeoSampa pelo workflow atual;
- não mede saúde das árvores, biodiversidade, conectividade, permeabilidade ou
  acesso público;
- não demonstra ainda que os cemitérios constituam a segunda maior área arborizada;
  essa afirmação requer comparação homogênea com parques e outras áreas verdes.
"""


def main() -> int:
    cemetery_data = json.loads(CEMETERIES.read_text(encoding="utf-8"))
    vegetation_data = json.loads(VEGETATION.read_text(encoding="utf-8"))
    metadata = json.loads(VEGETATION_METADATA.read_text(encoding="utf-8"))

    vegetation_features = []
    for feature in vegetation_data.get("features", []):
        geometry = valid_geometry(feature)
        if geometry.is_empty:
            continue
        properties = feature.get("properties") or {}
        code = category_code(properties)
        vegetation_features.append(
            {
                "geometry": geometry,
                "bounds": geometry.bounds,
                "category": code,
                "description": category_description(properties, code),
            }
        )

    rows = []
    global_categories: dict[int | None, list[Any]] = defaultdict(list)

    for feature in cemetery_data.get("features", []):
        cemetery = valid_geometry(feature)
        properties = feature.get("properties") or {}
        territorial = float(properties.get("area_m2_31983") or cemetery.area)
        all_intersections = []
        by_category: dict[int | None, list[Any]] = defaultdict(list)
        descriptions: dict[int | None, str] = {}

        for vegetation in vegetation_features:
            if not intersects_bounds(cemetery.bounds, vegetation["bounds"]):
                continue
            intersection = cemetery.intersection(vegetation["geometry"])
            if intersection.is_empty or intersection.area <= 0:
                continue
            code = vegetation["category"]
            all_intersections.append(intersection)
            by_category[code].append(intersection)
            global_categories[code].append(intersection)
            descriptions[code] = vegetation["description"]

        vegetation_area = union_area(all_intersections)
        category_areas = {code: union_area(items) for code, items in by_category.items()}
        tree_area = sum(
            area for code, area in category_areas.items() if code in TREE_COMPONENT_CATEGORIES
        )
        encoded_areas = {"na" if code is None else str(code): round(area, 3) for code, area in category_areas.items()}
        encoded_labels = {
            "na" if code is None else str(code): descriptions.get(code, CATEGORY_NAMES.get(code, "Categoria não identificada"))
            for code in category_areas
        }

        rows.append(
            {
                "id_equipamento": properties.get("id_equipamento") or feature.get("id"),
                "nome_oficial": properties.get("nome_oficial"),
                "tipo": properties.get("tipo"),
                "bloco_concessao": int(properties.get("bloco_concessao")),
                "concessionaria": properties.get("concessionaria"),
                "area_territorial_m2": round(territorial, 3),
                "cobertura_vegetal_m2": round(vegetation_area, 3),
                "cobertura_vegetal_percentual": round(vegetation_area / territorial * 100 if territorial else 0, 4),
                "componente_arboreo_explicito_m2": round(tree_area, 3),
                "componente_arboreo_percentual_do_territorio": round(tree_area / territorial * 100 if territorial else 0, 4),
                "categorias_area_m2_json": json.dumps(encoded_areas, ensure_ascii=False, sort_keys=True),
                "categorias_descricao_json": json.dumps(encoded_labels, ensure_ascii=False, sort_keys=True),
                "referencia_imagens": "2017/2018",
                "fonte_cobertura_vegetal": metadata.get("layer"),
            }
        )

    rows.sort(key=lambda row: (row["bloco_concessao"], row["nome_oficial"]))
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    blocks = []
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["bloco_concessao"]].append(row)
    for block, selected in sorted(grouped.items()):
        item = aggregate(selected)
        item.update({"bloco_concessao": block, "concessionaria": selected[0]["concessionaria"]})
        blocks.append(item)

    category_items = []
    category_total = 0.0
    raw_category_totals = []
    for code, geometries in global_categories.items():
        area = union_area(geometries)
        raw_category_totals.append((code, area))
        category_total += area
    for code, area in sorted(raw_category_totals, key=lambda item: 999 if item[0] is None else item[0]):
        category_items.append(
            {
                "categoria": "não identificada" if code is None else code,
                "descricao": CATEGORY_NAMES.get(code, "Categoria não identificada"),
                "area_m2": round(area, 3),
                "participacao_na_cobertura_percentual": round(area / category_total * 100 if category_total else 0, 4),
                "componente_arboreo_explicito": code in TREE_COMPONENT_CATEGORIES,
            }
        )

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": metadata.get("dataset"),
        "layer": metadata.get("layer"),
        "imagery_reference": metadata.get("imagery_reference"),
        "source_crs": "EPSG:31983",
        "geral_23_equipamentos": aggregate(rows),
        "somente_22_cemiterios": aggregate([row for row in rows if row["tipo"] == "cemiterio"]),
        "crematorio_vila_alpina": aggregate([row for row in rows if row["tipo"] == "crematorio"]),
        "por_bloco": blocks,
        "categorias": category_items,
        "tree_component_categories": sorted(TREE_COMPONENT_CATEGORIES),
        "interpretation_notes": [
            "Cobertura vegetal não equivale a cobertura estrita de copas nem a área permeável.",
            "O componente arbóreo explícito agrega categorias cuja definição oficial menciona floresta, bosque, maciço ou cobertura arbórea.",
            "A referência de 2017/2018 é anterior à concessão e funciona como linha de base.",
        ],
    }
    OUTPUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_REPORT.write_text(create_report(rows, summary, category_items), encoding="utf-8")

    result = summary["geral_23_equipamentos"]
    print(
        f"Cobertura vegetal: {result['cobertura_vegetal_m2']:.3f} m² "
        f"({result['cobertura_vegetal_percentual']:.2f}%); "
        f"componente arbóreo explícito: {result['componente_arboreo_explicito_m2']:.3f} m²."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
