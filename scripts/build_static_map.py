#!/usr/bin/env python3
"""Gera mapa estático dos estratos tarifários e destinos gratuitos."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from adjustText import adjust_text
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
CEMETERIES_PATH = ROOT / "data" / "processed" / "cemiterios_concessao_31983.geojson"
DISTRICTS_PATH = ROOT / "data" / "raw" / "geosampa" / "distritos_31983.geojson"
PNG_PATH = ROOT / "maps" / "mapa_estratos_gratuidade.png"
SVG_PATH = ROOT / "maps" / "mapa_estratos_gratuidade.svg"

COLORS = {
    1: "#8B1E3F",
    2: "#E67E22",
    3: "#D4A017",
    4: "#2E8B57",
    None: "#315A7D",
}

SHORT_NAMES = {
    "Cemitério da Consolação": "Consolação",
    "Cemitério da Quarta Parada": "Quarta Parada",
    "Cemitério Santana (Chora Menino)": "Santana",
    "Cemitério do Tremembé": "Tremembé",
    "Cemitério Vila Formosa I": "Vila Formosa I",
    "Cemitério Vila Formosa II": "Vila Formosa II",
    "Cemitério Vila Mariana": "Vila Mariana",
    "Cemitério do Araçá": "Araçá",
    "Cemitério Dom Bosco": "Dom Bosco",
    "Cemitério Santo Amaro": "Santo Amaro",
    "Cemitério São Paulo": "São Paulo",
    "Cemitério Vila Nova Cachoeirinha": "V. N. Cachoeirinha",
    "Cemitério Campo Grande": "Campo Grande",
    "Cemitério do Lageado": "Lageado",
    "Cemitério da Lapa": "Lapa",
    "Cemitério de Parelheiros": "Parelheiros",
    "Cemitério da Saudade": "Saudade",
    "Cemitério da Freguesia do Ó": "Freguesia do Ó",
    "Cemitério de Itaquera": "Itaquera",
    "Cemitério da Penha": "Penha",
    "Cemitério São Luiz": "São Luiz",
    "Cemitério São Pedro": "São Pedro",
    "Crematório Vila Alpina": "Crematório Vila Alpina",
}


def category(value):
    if value in (None, "", "None"):
        return None
    return int(value)


def polygon_parts(geometry):
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)
    return []


def draw_boundary(axis, geometry, **kwargs):
    for polygon in polygon_parts(geometry):
        x, y = polygon.exterior.xy
        axis.plot(x, y, **kwargs)
        for interior in polygon.interiors:
            ix, iy = interior.xy
            axis.plot(ix, iy, **kwargs)


def draw_fill(axis, geometry, **kwargs):
    for polygon in polygon_parts(geometry):
        x, y = polygon.exterior.xy
        axis.fill(x, y, **kwargs)


def main() -> int:
    cemeteries = json.loads(CEMETERIES_PATH.read_text(encoding="utf-8"))
    districts = json.loads(DISTRICTS_PATH.read_text(encoding="utf-8"))

    district_geometries = [shape(feature["geometry"]) for feature in districts["features"]]
    municipal_outline = unary_union(district_geometries)

    figure, axis = plt.subplots(figsize=(11.7, 11.7))
    figure.patch.set_facecolor("white")
    axis.set_facecolor("#F7F8FA")

    for geometry in district_geometries:
        draw_boundary(axis, geometry, color="#C5CDD5", linewidth=0.35, zorder=1)
    draw_boundary(axis, municipal_outline, color="#34495E", linewidth=1.2, zorder=2)

    texts = []
    cemetery_geometries = []
    for feature in cemeteries["features"]:
        properties = feature["properties"]
        geometry = shape(feature["geometry"])
        cemetery_geometries.append(geometry)
        stratum = category(properties.get("categoria_tarifaria"))
        color = COLORS[stratum]
        draw_fill(
            axis,
            geometry,
            facecolor=color,
            edgecolor="#FFFFFF",
            linewidth=0.65,
            alpha=0.72,
            zorder=3,
        )
        centroid = geometry.centroid
        marker = "s" if stratum is None else "o"
        axis.scatter(
            centroid.x,
            centroid.y,
            s=42,
            marker=marker,
            color=color,
            edgecolor="white",
            linewidth=0.8,
            zorder=5,
        )
        if properties.get("destino_gratuidade_hipossuficiencia"):
            axis.scatter(
                centroid.x,
                centroid.y,
                s=150,
                marker="*",
                color="#FFFFFF",
                edgecolor="#146B3A",
                linewidth=1.4,
                zorder=6,
            )
        label = SHORT_NAMES.get(properties["nome_oficial"], properties["nome_oficial"])
        texts.append(
            axis.text(
                centroid.x,
                centroid.y,
                label,
                fontsize=6.4,
                color="#243B53",
                zorder=7,
            )
        )

    adjust_text(
        texts,
        ax=axis,
        expand=(1.08, 1.18),
        force_text=(0.25, 0.35),
        force_points=(0.35, 0.45),
        arrowprops={"arrowstyle": "-", "color": "#8795A1", "lw": 0.45},
    )

    min_x, min_y, max_x, max_y = municipal_outline.bounds
    margin_x = (max_x - min_x) * 0.035
    margin_y = (max_y - min_y) * 0.035
    axis.set_xlim(min_x - margin_x, max_x + margin_x)
    axis.set_ylim(min_y - margin_y, max_y + margin_y)
    axis.set_aspect("equal")
    axis.axis("off")

    figure.suptitle(
        "Cemitérios públicos da concessão paulistana",
        x=0.08,
        y=0.97,
        ha="left",
        fontsize=20,
        fontweight="bold",
        color="#243B53",
    )
    axis.set_title(
        "Estratos tarifários, polígonos oficiais e destinos da gratuidade",
        loc="left",
        fontsize=11,
        color="#52606D",
        pad=18,
    )

    legend_items = [
        Patch(facecolor=COLORS[1], label="Estrato 1 — maior tarifa"),
        Patch(facecolor=COLORS[2], label="Estrato 2"),
        Patch(facecolor=COLORS[3], label="Estrato 3"),
        Patch(facecolor=COLORS[4], label="Estrato 4 — menor tarifa"),
        Patch(facecolor=COLORS[None], label="Crematório"),
        Line2D(
            [0],
            [0],
            marker="*",
            color="none",
            markerfacecolor="white",
            markeredgecolor="#146B3A",
            markeredgewidth=1.4,
            markersize=12,
            label="Destino da gratuidade",
        ),
    ]
    axis.legend(
        handles=legend_items,
        loc="lower left",
        frameon=True,
        framealpha=0.96,
        edgecolor="#D9E2EC",
        fontsize=8.5,
        title="Legenda",
        title_fontsize=9.5,
    )

    figure.text(
        0.08,
        0.035,
        "Fonte espacial: GeoSampa — PMSP (CC BY-SA 4.0). Polígonos em SIRGAS 2000 / UTM 23S. "
        "Os marcadores estão nos centroides geométricos e não representam portões de acesso.",
        ha="left",
        va="bottom",
        fontsize=7.5,
        color="#52606D",
    )
    PNG_PATH.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(PNG_PATH, dpi=260, bbox_inches="tight", facecolor="white")
    figure.savefig(SVG_PATH, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    print(f"Mapas salvos em {PNG_PATH.relative_to(ROOT)} e {SVG_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
