#!/usr/bin/env python3
"""Gera o primeiro mapa web dos equipamentos da concessão."""

from __future__ import annotations

import json
from pathlib import Path

import folium
from folium import Element
from folium.plugins import Fullscreen, MiniMap
from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
CEMETERIES_PATH = ROOT / "data" / "processed" / "cemiterios_concessao_4326.geojson"
DISTRICTS_PATH = ROOT / "data" / "processed" / "distritos_4326.geojson"
OUTPUT_PATH = ROOT / "maps" / "cemiterios_concessao_interativo.html"

COLORS = {
    1: "#8B1E3F",  # maior tarifa
    2: "#E67E22",
    3: "#D4A017",
    4: "#2E8B57",  # menor tarifa
    None: "#315A7D",  # crematório
}


def category(value):
    if value in (None, "", "None"):
        return None
    return int(value)


def main() -> int:
    cemeteries = json.loads(CEMETERIES_PATH.read_text(encoding="utf-8"))
    districts = json.loads(DISTRICTS_PATH.read_text(encoding="utf-8"))

    geometries = [shape(feature["geometry"]) for feature in cemeteries["features"]]
    bounds = unary_union(geometries).bounds
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]

    map_object = folium.Map(
        location=center,
        zoom_start=10,
        tiles="CartoDB positron",
        control_scale=True,
        prefer_canvas=True,
    )
    Fullscreen(position="topright", title="Tela cheia", title_cancel="Sair").add_to(map_object)
    MiniMap(toggle_display=True).add_to(map_object)

    folium.GeoJson(
        districts,
        name="Distritos municipais",
        style_function=lambda _: {
            "color": "#7A8793",
            "weight": 0.7,
            "fillColor": "#F8F9FA",
            "fillOpacity": 0.08,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["nm_distrito_municipal"],
            aliases=["Distrito:"],
            sticky=False,
        ),
    ).add_to(map_object)

    for stratum in (1, 2, 3, 4, None):
        selected = {
            "type": "FeatureCollection",
            "features": [
                feature
                for feature in cemeteries["features"]
                if category(feature["properties"].get("categoria_tarifaria")) == stratum
            ],
        }
        if not selected["features"]:
            continue
        layer_name = "Crematório" if stratum is None else f"Estrato {stratum}"
        color = COLORS[stratum]
        folium.GeoJson(
            selected,
            name=layer_name,
            style_function=lambda _, color=color: {
                "color": color,
                "weight": 2,
                "fillColor": color,
                "fillOpacity": 0.46,
            },
            highlight_function=lambda _, color=color: {
                "color": "#111111",
                "weight": 3,
                "fillColor": color,
                "fillOpacity": 0.72,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=[
                    "nome_oficial",
                    "categoria_tarifaria",
                    "bloco_concessao",
                    "concessionaria",
                    "tarifa_sepultamento_avulso_2026",
                    "destino_gratuidade_hipossuficiencia",
                ],
                aliases=[
                    "Equipamento:",
                    "Estrato tarifário:",
                    "Bloco:",
                    "Concessionária:",
                    "Sepultamento avulso 2026 (R$):",
                    "Destino gratuito:",
                ],
                localize=True,
                sticky=False,
            ),
        ).add_to(map_object)

    # Destaque dos destinos gratuitos no centroide geométrico, não no portão.
    for feature in cemeteries["features"]:
        properties = feature["properties"]
        if not properties.get("destino_gratuidade_hipossuficiencia"):
            continue
        latitude = properties["centroide_latitude"]
        longitude = properties["centroide_longitude"]
        modality = properties.get("modalidade_gratuita") or ""
        folium.Marker(
            location=[latitude, longitude],
            tooltip=f"Destino gratuito: {properties['nome_oficial']}",
            popup=folium.Popup(
                (
                    f"<strong>{properties['nome_oficial']}</strong><br>"
                    f"Modalidade: {modality}<br>"
                    "Marcador no centroide geométrico; não representa o acesso público."
                ),
                max_width=320,
            ),
            icon=folium.DivIcon(
                html=(
                    '<div style="width:25px;height:25px;border-radius:50%;'
                    'background:#ffffff;border:3px solid #146B3A;'
                    'display:flex;align-items:center;justify-content:center;'
                    'font-size:17px;color:#146B3A;font-weight:bold;'
                    'box-shadow:0 1px 5px rgba(0,0,0,.45)">★</div>'
                ),
                icon_size=(25, 25),
                icon_anchor=(12, 12),
            ),
        ).add_to(map_object)

    title = """
    <div style="position:fixed;top:10px;left:50px;z-index:9999;
         background:rgba(255,255,255,.95);padding:10px 14px;border-radius:6px;
         box-shadow:0 1px 6px rgba(0,0,0,.25);max-width:520px">
      <div style="font-size:18px;font-weight:700;color:#243B53">
        Cemitérios da concessão paulistana
      </div>
      <div style="font-size:12px;color:#52606D;margin-top:3px">
        Polígonos oficiais do GeoSampa · cores por estrato tarifário · ★ destinos gratuitos
      </div>
    </div>
    """
    map_object.get_root().html.add_child(Element(title))

    legend = """
    <div style="position:fixed;bottom:28px;left:38px;z-index:9999;
         background:rgba(255,255,255,.96);padding:11px 14px;border-radius:6px;
         box-shadow:0 1px 6px rgba(0,0,0,.25);font-size:12px;line-height:1.55">
      <strong>Estratos tarifários</strong><br>
      <span style="color:#8B1E3F">■</span> 1 — maior tarifa<br>
      <span style="color:#E67E22">■</span> 2<br>
      <span style="color:#D4A017">■</span> 3<br>
      <span style="color:#2E8B57">■</span> 4 — menor tarifa<br>
      <span style="color:#315A7D">■</span> Crematório<br>
      <span style="color:#146B3A">★</span> Destino da gratuidade<br>
      <small>Fonte espacial: GeoSampa (CC BY-SA 4.0)</small>
    </div>
    """
    map_object.get_root().html.add_child(Element(legend))

    map_object.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    folium.LayerControl(collapsed=False).add_to(map_object)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    map_object.save(str(OUTPUT_PATH))
    print(f"Mapa salvo em {OUTPUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
