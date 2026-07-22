#!/usr/bin/env python3
"""Cruza os cemitérios concedidos com a cobertura vegetal oficial de 2017.

A rotina distingue explicitamente:
- área territorial do equipamento;
- área classificada como cobertura vegetal;
- proporção territorial coberta por vegetação;
- composição por categoria do mapeamento municipal.

Não se usa a expressão "cobertura de copas" para os resultados desta rotina. O
produto municipal de copas é distinto e não foi localizado como camada vetorial
pública no WFS durante esta etapa.

Saídas:
- data/processed/cemiterios_cobertura_vegetal_2017.csv
- data/processed/resumo_cobertura_vegetal_cemiterios_2017.json
- docs/RESULTADOS_COBERTURA_VEGETAL_CEMITERIOS.md
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
CEMETERIES_PATH = ROOT / "data" / "processed" / "cemiterios_concessao_31983.geojson"
VEGETATION_PATH = (
    ROOT
    / "data"
    / "raw"
    / "geosampa"
    / "cobertura_vegetal_2017_entorno_cemiterios_31983.geojson"
)
VEGETATION_METADATA_PATH = (
    ROOT
    / "data"
    / "raw"
    / "geosampa"
    / "cobertura_vegetal_2017_entorno_cemiterios_metadata.json"
)
OUTPUT_CSV = ROOT / "data" / "processed" / "cemiterios_cobertura_vegetal_2017.csv"
OUTPUT_JSON = (
    ROOT / "data" / "processed" / "resumo_cobertura_vegetal_cemiterios_2017.json"
)
OUTPUT_REPORT = ROOT / "docs" / "RESULTADOS_COBERTURA_VEGETAL_CEMITERIOS.md"

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


def valid_geometry(feature: dict[str, Any]):
    geometry = shape(feature["geometry"])
    if not geometry.is_valid:
        geometry = geometry.buffer(0)
    return geometry


def bboxes_intersect(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def category_code(properties: dict[str, Any]) -> int | None:
    for field in ("vg_categ", "CAT", "cat", "categoria", "CATEGORY"):
        value = properties.get(field)
        if value in (None, ""):
            continue
        try:
            return int(float(value))
        except (TypeError, ValueError):
            continue
    return None


def category_description(properties: dict[str, Any], code: int | None) -> str:
    for field in ("vg_descric", "DESCRICAO", "descricao", "description"):
        value = properties.get(field)
        if value not in (None, ""):
            return str(value).strip()
    if code is None:
        return "Categoria não identificada"
    return CATEGORY_NAMES.get(code, f"Categoria {code}")


def format_number(value: float, decimals: int = 2) -> str:
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def report_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Cemitério/equipamento | Bloco | Área territorial (m²) | Cobertura vegetal (m²) | Cobertura (%) |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {name} | {block} | {area} | {vegetation} | {pct} |".format(
                name=row["nome_oficial"],
                block=row["bloco_concessao"],
                area=format_number(row["area_territorial_m2"], 1),
                vegetation=format_number(row["cobertura_vegetal_m2"], 1),
                pct=format_number(row["cobertura_vegetal_percentual"], 2),
            )
        )
    return "\n".join(lines)


def build_report(
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    category_totals: list[dict[str, Any]],
) -> str:
    overall = summary["geral_23_equipamentos"]
    cemeteries = summary["somente_22_cemiterios"]
    blocks = summary["por_bloco"]

    category_lines = [
        "| Categoria | Descrição | Área dentro dos equipamentos (m²) | Participação na cobertura (%) |",
        "|---:|---|---:|---:|",
    ]
    for item in category_totals:
        category_lines.append(
            f"| {item['categoria']} | {item['descricao']} | "
            f"{format_number(item['area_m2'], 1)} | "
            f"{format_number(item['participacao_na_cobertura_percentual'], 2)} |"
        )

    block_lines = [
        "| Bloco | Concessionária | Área territorial (m²) | Cobertura vegetal (m²) | Cobertura (%) |",
        "|---:|---|---:|---:|---:|",
    ]
    for block in blocks:
        block_lines.append(
            f"| {block['bloco_concessao']} | {block['concessionaria']} | "
            f"{format_number(block['area_territorial_m2'], 1)} | "
            f"{format_number(block['cobertura_vegetal_m2'], 1)} | "
            f"{format_number(block['cobertura_vegetal_percentual'], 2)} |"
        )

    return f"""# Cobertura vegetal nos cemitérios públicos concedidos de São Paulo

## Resultado principal

O cruzamento usa os polígonos oficiais dos 23 equipamentos da concessão e o
**Mapeamento Digital da Cobertura Vegetal 2017**, produzido com fotointerpretação
de ortofotos de 2017/2018 e apoio LiDAR, publicado pela Secretaria Municipal do
Verde e do Meio Ambiente em 2020.

Nos 23 equipamentos, incluindo o Crematório Vila Alpina, foram identificados
**{format_number(overall['cobertura_vegetal_m2'], 1)} m² de cobertura vegetal**, o
que corresponde a **{format_number(overall['cobertura_vegetal_percentual'], 2)}%**
da área territorial analisada. Considerando apenas os 22 cemitérios, o total é de
**{format_number(cemeteries['cobertura_vegetal_m2'], 1)} m²**, ou
**{format_number(cemeteries['cobertura_vegetal_percentual'], 2)}%** de seus
perímetros atuais.

## Cautela conceitual

Este resultado mede **cobertura vegetal**, composta por 15 categorias que incluem
florestas, bosques urbanos, vegetação arbórea, formações herbáceo-arbustivas,
agricultura e classes mistas. Ele **não equivale à cobertura de copas de árvores**.
O relatório municipal informa a existência de um produto específico de copas,
derivado do Modelo Digital de Vegetação Normalizado, mas esse produto não foi
localizado como camada vetorial pública no WFS usado nesta rotina.

Também não se confunde cobertura vegetal com área permeável. A interseção mede a
parcela dos polígonos cemiteriais classificada como vegetação na base de 2017/2018.

## Resultado por bloco contratual

{"\n".join(block_lines)}

## Resultado por equipamento

{report_table(rows)}

## Composição das classes de vegetação

{"\n".join(category_lines)}

## Leitura para o Artigo Holanda

A medição permite substituir a fusão discursiva entre **área cemiterial** e **área
verde** por uma descrição verificável. Os cemitérios formam uma rede territorial de
quase 296 hectares, mas apenas a parcela efetivamente classificada como cobertura
vegetal deve ser mobilizada como indicador ambiental.

A base também permite comparar os quatro blocos concessionados. Isso abre uma
frente empírica sobre a fragmentação contratual de uma infraestrutura verde que o
Plano Diretor tratou como sistema municipal integrado. Diferenças entre blocos não
provam desempenho das concessionárias, porque o mapeamento retrata imagens de
2017/2018, anteriores ao início da concessão. Elas funcionam como **linha de base
pré-concessão** para análises posteriores.

## Limites

- referência temporal da vegetação: ortofotos de 2017/2018;
- referência atual dos perímetros cemiteriais: camada consultada no GeoSampa pelo
  workflow do projeto;
- pequenas diferenças de data e de delimitação podem afetar as bordas;
- a análise não mede saúde das árvores, biodiversidade, conectividade ecológica,
  permeabilidade nem acesso público;
- a afirmação histórica de que os cemitérios constituíam a segunda maior área
  arborizada da cidade ainda exige uma comparação homogênea com parques e outras
  classes de áreas verdes.

## Fontes

- Prefeitura de São Paulo / SVMA. *Mapeamento Digital da Cobertura Vegetal do
  Município de São Paulo*. Relatório final, 2020.
- Catálogo de Metadados Geográficos do GeoSampa: registro
  `367916b7-3af4-44be-ab72-cd07a4996b66`.
- GeoSampa: camada WFS identificada e registrada automaticamente nos metadados da
  coleta.
"""


def main() -> int:
    cemeteries_data = json.loads(CEMETERIES_PATH.read_text(encoding="utf-8"))
    vegetation_data = json.loads(VEGETATION_PATH.read_text(encoding="utf-8"))
    vegetation_metadata = json.loads(
        VEGETATION_METADATA_PATH.read_text(encoding="utf-8")
    )

    vegetation_features: list[dict[str, Any]] = []
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

    rows: list[dict[str, Any]] = []
    all_category_geometries: dict[int | None, list[Any]] = defaultdict(list)

    for feature in cemeteries_data.get("features", []):
        cemetery = valid_geometry(feature)
        properties = feature.get("properties") or {}
        territorial_area = float(properties.get("area_m2_31983") or cemetery.area)

        intersections: list[Any] = []
        category_intersections: dict[int | None, list[Any]] = defaultdict(list)
        category_descriptions: dict[int | None, str] = {}

        for vegetation in vegetation_features:
            if not bboxes_intersect(cemetery.bounds, vegetation["bounds"]):
                continue
            intersection = cemetery.intersection(vegetation["geometry"])
            if intersection.is_empty or intersection.area <= 0:
                continue
            intersections.append(intersection)
            category = vegetation["category"]
            category_intersections[category].append(intersection)
            category_descriptions[category] = vegetation["description"]
            all_category_geometries[category].append(intersection)

        vegetation_union = unary_union(intersections) if intersections else None
        vegetation_area = float(vegetation_union.area) if vegetation_union else 0.0
        percentage = (vegetation_area / territorial_area * 100) if territorial_area else 0.0

        category_areas: dict[str, float] = {}
        category_labels: dict[str, str] = {}
        for category, geometries in category_intersections.items():
            category_union = unary_union(geometries)
            key = "na" if category is None else str(category)
            category_areas[key] = round(float(category_union.area), 3)
            category_labels[key] = category_descriptions.get(
                category, CATEGORY_NAMES.get(category, "Categoria não identificada")
            )

        rows.append(
            {
                "id_equipamento": properties.get("id_equipamento") or feature.get("id"),
                "nome_oficial": properties.get("nome_oficial"),
                "tipo": properties.get("tipo"),
                "bloco_concessao": properties.get("bloco_concessao"),
                "concessionaria": properties.get("concessionaria"),
                "area_territorial_m2": round(territorial_area, 3),
                "cobertura_vegetal_m2": round(vegetation_area, 3),
                "cobertura_vegetal_percentual": round(percentage, 4),
                "categorias_area_m2_json": json.dumps(
                    category_areas, ensure_ascii=False, sort_keys=True
                ),
                "categorias_descricao_json": json.dumps(
                    category_labels, ensure_ascii=False, sort_keys=True
                ),
                "referencia_imagens": "2017/2018",
                "fonte_cobertura_vegetal": vegetation_metadata.get("layer"),
            }
        )

    rows.sort(key=lambda item: (int(item["bloco_concessao"]), item["nome_oficial"]))

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    def aggregate(selected: list[dict[str, Any]]) -> dict[str, Any]:
        territorial = sum(float(row["area_territorial_m2"]) for row in selected)
        vegetation = sum(float(row["cobertura_vegetal_m2"]) for row in selected)
        return {
            "equipment_count": len(selected),
            "area_territorial_m2": round(territorial, 3),
            "cobertura_vegetal_m2": round(vegetation, 3),
            "cobertura_vegetal_percentual": round(
                vegetation / territorial * 100 if territorial else 0.0, 4
            ),
        }

    by_block: list[dict[str, Any]] = []
    block_groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        block_groups[int(row["bloco_concessao"])].append(row)
    for block, selected in sorted(block_groups.items()):
        item = aggregate(selected)
        item.update(
            {
                "bloco_concessao": block,
                "concessionaria": selected[0]["concessionaria"],
            }
        )
        by_block.append(item)

    total_category_area = 0.0
    category_totals: list[dict[str, Any]] = []
    temporary: list[tuple[int | None, str, float]] = []
    for category, geometries in all_category_geometries.items():
        area = float(unary_union(geometries).area)
        description = CATEGORY_NAMES.get(category, "Categoria não identificada")
        temporary.append((category, description, area))
        total_category_area += area
    for category, description, area in sorted(
        temporary, key=lambda item: (999 if item[0] is None else item[0])
    ):
        category_totals.append(
            {
                "categoria": "não identificada" if category is None else category,
                "descricao": description,
                "area_m2": round(area, 3),
                "participacao_na_cobertura_percentual": round(
                    area / total_category_area * 100 if total_category_area else 0.0, 4
                ),
            }
        )

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": vegetation_metadata.get("dataset"),
        "layer": vegetation_metadata.get("layer"),
        "imagery_reference": vegetation_metadata.get("imagery_reference"),
        "source_crs": "EPSG:31983",
        "geral_23_equipamentos": aggregate(rows),
        "somente_22_cemiterios": aggregate(
            [row for row in rows if row["tipo"] == "cemiterio"]
        ),
        "crematorio_vila_alpina": aggregate(
            [row for row in rows if row["tipo"] == "crematorio"]
        ),
        "por_bloco": by_block,
        "categorias": category_totals,
        "interpretation_notes": [
            "O indicador mede cobertura vegetal classificada em 15 categorias.",
            "Não equivale a cobertura estrita de copas nem a área permeável.",
            "A referência de 2017/2018 é anterior à concessão e funciona como linha de base.",
            "A soma por bloco não mede desempenho posterior das concessionárias.",
        ],
    }
    OUTPUT_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    OUTPUT_REPORT.write_text(
        build_report(rows, summary, category_totals), encoding="utf-8"
    )

    overall = summary["geral_23_equipamentos"]
    print(
        "Cobertura vegetal: "
        f"{overall['cobertura_vegetal_m2']:.3f} m² "
        f"({overall['cobertura_vegetal_percentual']:.2f}%) em 23 equipamentos."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
