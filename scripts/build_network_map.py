#!/usr/bin/env python3
"""Gera mapa cartográfico real da rede funerária concedida de São Paulo.

A execução em pull request é usada como teste de regressão cartográfica.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
from adjustText import adjust_text
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pyproj import Transformer
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
CEMETERIES_PATH = ROOT / "data" / "processed" / "cemiterios_concessao_31983.geojson"
DISTRICTS_PATH = ROOT / "data" / "raw" / "geosampa" / "distritos_31983.geojson"
AGENCIES_PATH = ROOT / "data" / "processed" / "agencias_geocodificadas.csv"
PNG_PATH = ROOT / "maps" / "mapa_rede_funeraria_real.png"
SVG_PATH = ROOT / "maps" / "mapa_rede_funeraria_real.svg"

CATEGORY_COLORS = {
    1: "#7F1D3A",
    2: "#C65D1E",
    3: "#B28A00",
    4: "#287A50",
    None: "#294F6D",
}
LOT_COLORS = {
    1: "#225EA8",
    2: "#D94801",
    3: "#7A3E9D",
    4: "#2F855A",
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
TRANSFORM = Transformer.from_crs("EPSG:4326", "EPSG:31983", always_xy=True)


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


def load_agencies():
    if not AGENCIES_PATH.exists():
        return []
    with AGENCIES_PATH.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def main() -> int:
    cemeteries = json.loads(CEMETERIES_PATH.read_text(encoding="utf-8"))
    districts = json.loads(DISTRICTS_PATH.read_text(encoding="utf-8"))
    agencies = load_agencies()

    district_geometries = [shape(feature["geometry"]) for feature in districts["features"]]
    municipal_outline = unary_union(district_geometries)

    figure, axis = plt.subplots(figsize=(13.6, 11.0))
    figure.subplots_adjust(left=0.055, right=0.78, top=0.90, bottom=0.08)
    figure.patch.set_facecolor("white")
    axis.set_facecolor("#F8FAFC")

    for geometry in district_geometries:
        draw_boundary(axis, geometry, color="#CBD5E1", linewidth=0.32, zorder=1)
    draw_boundary(axis, municipal_outline, color="#334155", linewidth=1.25, zorder=2)

    texts = []
    for feature in cemeteries["features"]:
        properties = feature["properties"]
        geometry = shape(feature["geometry"])
        stratum = category(properties.get("categoria_tarifaria"))
        color = CATEGORY_COLORS[stratum]
        draw_fill(axis, geometry, facecolor=color, edgecolor="white", linewidth=0.55, alpha=0.72, zorder=3)
        centroid = geometry.centroid
        marker = "s" if stratum is None else "o"
        axis.scatter(centroid.x, centroid.y, s=42, marker=marker, color=color, edgecolor="white", linewidth=0.8, zorder=7)
        if properties.get("destino_gratuidade_hipossuficiencia"):
            axis.scatter(centroid.x, centroid.y, s=170, marker="*", facecolor="white", edgecolor="#0F5132", linewidth=1.25, zorder=8)
        label = SHORT_NAMES.get(properties["nome_oficial"], properties["nome_oficial"])
        texts.append(axis.text(centroid.x, centroid.y, label, fontsize=6.1, color="#1E293B", zorder=9))

    exact_count = 0
    provisional_count = 0
    missing_count = 0
    for row in agencies:
        if not row.get("latitude") or not row.get("longitude"):
            missing_count += 1
            continue
        lon = float(row["longitude"])
        lat = float(row["latitude"])
        x, y = TRANSFORM.transform(lon, lat)
        lot = int(row["bloco_concessao"])
        quality = int(float(row.get("qualidade_geocodificacao") or 0))
        exact = quality >= 3
        if exact:
            exact_count += 1
        else:
            provisional_count += 1
        axis.scatter(
            x,
            y,
            s=24 if exact else 28,
            marker="o" if exact else "^",
            facecolor=LOT_COLORS[lot] if exact else "white",
            edgecolor=LOT_COLORS[lot],
            linewidth=0.9,
            alpha=0.92,
            zorder=6,
        )

    adjust_text(
        texts,
        ax=axis,
        expand=(1.08, 1.18),
        force_text=(0.24, 0.34),
        force_points=(0.30, 0.40),
        arrowprops={"arrowstyle": "-", "color": "#94A3B8", "lw": 0.42},
    )

    min_x, min_y, max_x, max_y = municipal_outline.bounds
    margin_x = (max_x - min_x) * 0.035
    margin_y = (max_y - min_y) * 0.035
    axis.set_xlim(min_x - margin_x, max_x + margin_x)
    axis.set_ylim(min_y - margin_y, max_y + margin_y)
    axis.set_aspect("equal")
    axis.axis("off")

    figure.suptitle(
        "Rede funerária concedida no Município de São Paulo",
        x=0.055,
        y=0.965,
        ha="left",
        fontsize=19,
        fontweight="bold",
        color="#172B4D",
    )
    axis.set_title(
        "Polígonos oficiais dos cemitérios, destinos gratuitos, crematório e agências funerárias geocodificadas",
        loc="left",
        fontsize=10.5,
        color="#52606D",
        pad=16,
    )

    tariff_handles = [
        Patch(facecolor=CATEGORY_COLORS[1], label="Cemitério - estrato 1"),
        Patch(facecolor=CATEGORY_COLORS[2], label="Cemitério - estrato 2"),
        Patch(facecolor=CATEGORY_COLORS[3], label="Cemitério - estrato 3"),
        Patch(facecolor=CATEGORY_COLORS[4], label="Cemitério - estrato 4"),
        Patch(facecolor=CATEGORY_COLORS[None], label="Crematório Vila Alpina"),
        Line2D([0], [0], marker="*", color="none", markerfacecolor="white", markeredgecolor="#0F5132", markeredgewidth=1.25, markersize=12, label="Destino da gratuidade"),
    ]
    lot_handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=LOT_COLORS[1], markeredgecolor=LOT_COLORS[1], markersize=6, label="Agência - lote 1 / Consolare"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=LOT_COLORS[2], markeredgecolor=LOT_COLORS[2], markersize=6, label="Agência - lote 2 / Cortel SP"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=LOT_COLORS[3], markeredgecolor=LOT_COLORS[3], markersize=6, label="Agência - lote 3 / Grupo Maya"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=LOT_COLORS[4], markeredgecolor=LOT_COLORS[4], markersize=6, label="Agência - lote 4 / Velar SP"),
        Line2D([0], [0], marker="^", color="none", markerfacecolor="white", markeredgecolor="#64748B", markersize=6, label="Agência provisória / revisar"),
    ]

    legend1 = axis.legend(handles=tariff_handles, loc="upper left", bbox_to_anchor=(1.015, 0.98), frameon=True, framealpha=0.98, edgecolor="#D9E2EC", fontsize=8.2, title="Cemitérios e gratuidade", title_fontsize=9.2)
    axis.add_artist(legend1)
    axis.legend(handles=lot_handles, loc="upper left", bbox_to_anchor=(1.015, 0.57), frameon=True, framealpha=0.98, edgecolor="#D9E2EC", fontsize=8.2, title="Agências por lote", title_fontsize=9.2)

    figure.text(
        0.795,
        0.22,
        f"Geocodificação das agências\n\n"
        f"Exatas/edificação: {exact_count}\n"
        f"Provisórias: {provisional_count}\n"
        f"Não localizadas: {missing_count}\n\n"
        "Triângulos exigem conferência\nno GeoSampa e na ortofoto.",
        ha="left",
        va="top",
        fontsize=8.3,
        color="#334155",
        bbox={"boxstyle": "round,pad=0.55", "facecolor": "#F8FAFC", "edgecolor": "#CBD5E1"},
    )

    figure.text(
        0.055,
        0.027,
        "Fontes: GeoSampa/PMSP (geometria dos cemitérios e limites distritais); SP Regula (endereços e lotes); "
        "OpenStreetMap/Nominatim (geocodificação inicial das agências). CRS analítico: SIRGAS 2000 / UTM 23S (EPSG:31983). "
        "Polígonos e centroides dos cemitérios são oficiais; pontos das agências permanecem sujeitos a validação de acesso.",
        ha="left",
        va="bottom",
        fontsize=7.2,
        color="#52606D",
        wrap=True,
    )

    PNG_PATH.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(PNG_PATH, dpi=300, bbox_inches="tight", facecolor="white")
    figure.savefig(SVG_PATH, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    print(f"Mapa salvo em {PNG_PATH.relative_to(ROOT)} e {SVG_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
