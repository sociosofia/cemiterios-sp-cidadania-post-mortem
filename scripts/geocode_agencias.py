#!/usr/bin/env python3
"""Geocodifica as agências funerárias e registra qualidade e rastreabilidade.

A rotina usa Nominatim/OpenStreetMap apenas como geocodificador inicial. Cada
resultado é validado contra o limite municipal derivado dos 96 distritos do
GeoSampa. Resultados fora do município são rejeitados. Endereços sem número
(s/n) ou resultados em nível de logradouro são classificados como provisórios.
"""

from __future__ import annotations

import csv
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "reference" / "agencias_funerarias.csv"
DISTRICTS = ROOT / "data" / "raw" / "geosampa" / "distritos_31983.geojson"
OUT_CSV = ROOT / "data" / "processed" / "agencias_geocodificadas.csv"
OUT_GEOJSON = ROOT / "data" / "processed" / "agencias_geocodificadas_4326.geojson"
CACHE = ROOT / "data" / "raw" / "geocoding" / "nominatim_agencias.json"
REPORT = ROOT / "docs" / "RELATORIO_GEOCODIFICACAO_AGENCIAS.md"

USER_AGENT = "cemiterios-sp-cidadania-post-mortem/1.0 (pesquisa academica; github.com/sociosofia)"
TRANSFORM = Transformer.from_crs("EPSG:4326", "EPSG:31983", always_xy=True)


def load_cache() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def request_nominatim(query: str) -> list[dict]:
    params = {
        "q": query,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": 5,
        "countrycodes": "br",
        "viewbox": "-46.83,-23.35,-46.36,-24.02",
        "bounded": 1,
    }
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_query(address: str, bairro: str) -> list[str]:
    clean = address.replace(", sala 5", "").replace(", loja 1", "")
    candidates = [
        f"{clean}, {bairro}, São Paulo, SP, Brasil",
        f"{clean}, São Paulo, SP, Brasil",
    ]
    if "s/n" in clean.lower():
        street = clean.replace(", s/n", "").replace(", S/N", "")
        candidates.extend([
            f"{street}, {bairro}, São Paulo, SP, Brasil",
            f"{street}, São Paulo, SP, Brasil",
        ])
    return list(dict.fromkeys(candidates))


def inside_municipality(result: dict, municipal_outline) -> bool:
    lon = float(result["lon"])
    lat = float(result["lat"])
    x, y = TRANSFORM.transform(lon, lat)
    return municipal_outline.buffer(2).contains(Point(x, y))


def score_result(result: dict, original: str) -> tuple[int, str]:
    result_type = str(result.get("type", "")).lower()
    result_class = str(result.get("class", "")).lower()
    has_number = any(char.isdigit() for char in original) and "s/n" not in original.lower()
    address = result.get("address") or {}
    returned_number = bool(address.get("house_number"))

    if has_number and returned_number:
        return 3, "numero_confirmado"
    if result_type in {"house", "building", "office", "commercial", "yes"}:
        return 3, "edificacao_ou_estabelecimento"
    if result_class in {"place", "amenity", "office", "shop"}:
        return 2, "estabelecimento_sem_numero_confirmado"
    if result_type in {"residential", "tertiary", "secondary", "primary", "road", "street"}:
        return 1, "logradouro"
    return 1, f"resultado_{result_class}_{result_type}".strip("_")


def best_result(results: list[dict], original: str, municipal_outline) -> tuple[dict | None, int, str]:
    accepted = []
    for item in results:
        if not inside_municipality(item, municipal_outline):
            continue
        score, method = score_result(item, original)
        importance = float(item.get("importance") or 0)
        accepted.append((score, importance, item, method))
    if not accepted:
        return None, 0, "nao_localizado"
    accepted.sort(key=lambda row: (row[0], row[1]), reverse=True)
    score, _importance, item, method = accepted[0]
    return item, score, method


def main() -> int:
    districts = json.loads(DISTRICTS.read_text(encoding="utf-8"))
    municipal_outline = unary_union([shape(feature["geometry"]) for feature in districts["features"]])
    cache = load_cache()

    with INPUT.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    output_rows = []
    features = []
    for index, row in enumerate(rows, 1):
        original = row["endereco_oficial"]
        selected = None
        score = 0
        method = "nao_localizado"
        query_used = ""
        candidates_tested = []

        for query in normalize_query(original, row["bairro_publicado"]):
            query_used = query
            if query not in cache:
                time.sleep(1.1)
                try:
                    cache[query] = request_nominatim(query)
                except Exception as exc:  # rede externa pode oscilar
                    cache[query] = {"error": repr(exc)}
                save_cache(cache)
            cached = cache[query]
            if isinstance(cached, dict) and "error" in cached:
                candidates_tested.append({"query": query, "error": cached["error"]})
                continue
            candidates_tested.append({"query": query, "n": len(cached)})
            selected, score, method = best_result(cached, original, municipal_outline)
            if selected is not None and score >= 2:
                break

        status = {3: "validado_automaticamente", 2: "revisao_recomendada", 1: "provisorio_logradouro", 0: "nao_localizado"}[score]
        lon = float(selected["lon"]) if selected else None
        lat = float(selected["lat"]) if selected else None
        display_name = selected.get("display_name") if selected else None
        osm_type = selected.get("osm_type") if selected else None
        osm_id = selected.get("osm_id") if selected else None
        result_type = selected.get("type") if selected else None
        result_class = selected.get("class") if selected else None

        out = dict(row)
        out.update({
            "latitude": lat,
            "longitude": lon,
            "status_geocodificacao": status,
            "qualidade_geocodificacao": score,
            "metodo_geocodificacao": method,
            "consulta_utilizada": query_used,
            "endereco_retornado": display_name,
            "osm_type": osm_type,
            "osm_id": osm_id,
            "classe_resultado": result_class,
            "tipo_resultado": result_type,
            "capturado_em_utc": datetime.now(timezone.utc).isoformat(),
        })
        output_rows.append(out)

        if selected:
            features.append({
                "type": "Feature",
                "id": row["id_agencia"],
                "properties": {key: value for key, value in out.items() if key not in {"latitude", "longitude"}},
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
            })
        print(f"[{index:02d}/{len(rows)}] {row['id_agencia']}: {status} - {method}")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = list(output_rows[0].keys())
    with OUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)

    OUT_GEOJSON.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = {}
    for row in output_rows:
        counts[row["status_geocodificacao"]] = counts.get(row["status_geocodificacao"], 0) + 1
    lines = [
        "# Relatório de geocodificação das agências funerárias",
        "",
        f"Data UTC: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Resultado",
        "",
        "| Status | Quantidade |",
        "|---|---:|",
    ]
    for key in ["validado_automaticamente", "revisao_recomendada", "provisorio_logradouro", "nao_localizado"]:
        lines.append(f"| {key} | {counts.get(key, 0)} |")
    lines.extend([
        "",
        "## Regra de uso cartográfico",
        "",
        "- Todos os pontos foram restringidos ao limite municipal oficial derivado do GeoSampa.",
        "- Resultados de nível logradouro são provisórios e devem ser conferidos no GeoSampa/ortofoto.",
        "- A geocodificação automática não substitui validação de portão ou acesso público.",
        "- O arquivo bruto de respostas é preservado para auditoria e repetição.",
    ])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Geocodificação concluída: {len(features)}/{len(rows)} pontos localizados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
