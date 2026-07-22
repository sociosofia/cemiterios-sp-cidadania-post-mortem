#!/usr/bin/env python3
"""Calcula o valor fiscal do terreno no entorno dos cemitérios municipais.

Fontes:
- polígonos de cemitérios: GeoSampa, EPSG:31983;
- quadras fiscais: GeoSampa WFS, consultadas por BBOX;
- valores unitários: Anexo II da Lei municipal 18.330/2025 (PGV 2026);
- inventário contratual e categorias: base de referência do projeto.

A PGV lista valores por CODLOG + SQ (setor/quadra), mas a camada pública
`quadra_fiscal` fornece polígonos por SQ, sem geometria de cada face. Por isso,
os indicadores principais são:

1. mediana de todos os valores de face registrados nas quadras que intersectam
   cada anel;
2. mediana das medianas por quadra;
3. média das medianas por quadra ponderada pela área da quadra dentro do anel.

Os anéis excluem o interior do cemitério: 0–250 m, 250–500 m e 500–1.000 m.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
CEMETERY_GEOJSON = ROOT / "data" / "raw" / "geosampa" / "equipamento_cemiterio_31983.geojson"
MAPPING_CSV = ROOT / "data" / "reference" / "geosampa_mapping.csv"
REFERENCE_CSV = ROOT / "data" / "reference" / "cemiterios_crematorio.csv"
PGV_CSV = ROOT / "data" / "processed" / "pgv_2026_faces.csv"

RAW_QUADRAS = ROOT / "data" / "raw" / "geosampa" / "quadra_fiscal_entorno_cemiterios_31983.geojson"
OUTPUT_DETAIL = ROOT / "data" / "processed" / "cemiterios_valor_territorial_2026.csv"
OUTPUT_CATEGORY = ROOT / "data" / "processed" / "categorias_valor_territorial_2026.csv"
OUTPUT_COMPLEX = ROOT / "data" / "processed" / "complexos_valor_territorial_2026.csv"
OUTPUT_METADATA = ROOT / "data" / "processed" / "cemiterios_valor_territorial_2026_metadata.json"
OUTPUT_REPORT = ROOT / "docs" / "RESULTADOS_VALOR_TERRITORIAL_2026.md"

WFS_ENDPOINTS = (
    "https://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs",
    "http://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs",
)
LAYER = "geoportal:quadra_fiscal"
CRS_METRIC = "EPSG:31983"
PAGE_SIZE = 5000
RINGS = ((0, 250), (250, 500), (500, 1000))
USER_AGENT = (
    "cemiterios-sp-cidadania-post-mortem/1.0 "
    "(pesquisa acadêmica; dados públicos)"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    series = pd.Series(values, dtype="float64")
    return float(series.quantile(q, interpolation="linear"))


def round_or_none(value: float | int | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return round(float(value), digits)


def safe_make_valid(geometry):
    if geometry is None or geometry.is_empty:
        return geometry
    if geometry.is_valid:
        return geometry
    try:
        return geometry.make_valid()
    except AttributeError:
        return geometry.buffer(0)


def load_cemetery_geometries() -> gpd.GeoDataFrame:
    source = json.loads(CEMETERY_GEOJSON.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for feature in source.get("features", []):
        geometry = feature.get("geometry")
        if not geometry:
            continue
        records.append(
            {
                "feature_id_geosampa": feature.get("id"),
                "geometry": safe_make_valid(shape(geometry)),
            }
        )
    geosampa = gpd.GeoDataFrame(records, geometry="geometry", crs=CRS_METRIC)

    mapping = pd.read_csv(MAPPING_CSV, dtype=str).fillna("")
    reference = pd.read_csv(REFERENCE_CSV, dtype=str).fillna("")
    merged = mapping.merge(geosampa, on="feature_id_geosampa", how="left", validate="many_to_one")
    if merged["geometry"].isna().any():
        missing = merged.loc[merged["geometry"].isna(), "feature_id_geosampa"].tolist()
        raise RuntimeError(f"Feições de cemitérios não localizadas no GeoSampa: {missing}")

    dissolved_rows: list[dict[str, Any]] = []
    for equipment_id, group in merged.groupby("id_equipamento", sort=False):
        dissolved_rows.append(
            {
                "id_equipamento": equipment_id,
                "geometry": safe_make_valid(unary_union(list(group["geometry"]))),
                "geosampa_feature_count": len(group),
            }
        )
    dissolved = gpd.GeoDataFrame(dissolved_rows, geometry="geometry", crs=CRS_METRIC)
    output = reference.merge(dissolved, on="id_equipamento", how="inner", validate="one_to_one")
    output = gpd.GeoDataFrame(output, geometry="geometry", crs=CRS_METRIC)

    expected = set(reference["id_equipamento"])
    found = set(output["id_equipamento"])
    missing_equipment = sorted(expected - found)
    if missing_equipment:
        raise RuntimeError(f"Equipamentos sem polígono oficial: {missing_equipment}")
    return output


def request_json(url: str) -> tuple[dict[str, Any], str]:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,application/geo+json",
        },
    )
    with urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8")), response.geturl()


def fetch_quadras_bbox(bounds: tuple[float, float, float, float]) -> tuple[list[dict[str, Any]], list[str]]:
    minx, miny, maxx, maxy = bounds
    all_features: list[dict[str, Any]] = []
    request_urls: list[str] = []
    errors: list[str] = []

    for endpoint in WFS_ENDPOINTS:
        all_features = []
        request_urls = []
        start_index = 0
        try:
            while True:
                params = {
                    "service": "WFS",
                    "version": "2.0.0",
                    "request": "GetFeature",
                    "typeNames": LAYER,
                    "outputFormat": "application/json",
                    "srsName": CRS_METRIC,
                    "bbox": f"{minx},{miny},{maxx},{maxy},{CRS_METRIC}",
                    "count": PAGE_SIZE,
                    "startIndex": start_index,
                }
                url = f"{endpoint}?{urlencode(params)}"
                payload, final_url = request_json(url)
                request_urls.append(final_url)
                features = payload.get("features", [])
                all_features.extend(features)
                returned = payload.get("numberReturned", len(features))
                matched = payload.get("numberMatched")
                if not features or returned < PAGE_SIZE:
                    break
                start_index += len(features)
                if isinstance(matched, int) and start_index >= matched:
                    break
                if start_index > 250_000:
                    raise RuntimeError("Paginação excedeu 250 mil feições para uma única BBOX.")
            return all_features, request_urls
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
            errors.append(f"{endpoint}: {type(exc).__name__}: {exc}")
    raise RuntimeError("Falha ao consultar quadras fiscais:\n" + "\n".join(errors))


def collect_quadras(cemeteries: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, list[str]]:
    by_id: dict[str, dict[str, Any]] = {}
    request_urls: list[str] = []

    for row in cemeteries.itertuples(index=False):
        bbox = row.geometry.buffer(1000).bounds
        features, urls = fetch_quadras_bbox(bbox)
        request_urls.extend(urls)
        for feature in features:
            feature_id = str(feature.get("id") or "")
            if not feature_id:
                properties = feature.get("properties") or {}
                feature_id = "|".join(
                    str(properties.get(field, ""))
                    for field in (
                        "cd_setor_fiscal",
                        "cd_quadra_fiscal",
                        "cd_subquadra_fiscal",
                        "cd_identificador",
                    )
                )
            by_id.setdefault(feature_id, feature)

    records: list[dict[str, Any]] = []
    raw_features: list[dict[str, Any]] = []
    for feature_id, feature in by_id.items():
        geometry_payload = feature.get("geometry")
        if not geometry_payload:
            continue
        properties = feature.get("properties") or {}
        geometry = safe_make_valid(shape(geometry_payload))
        setor = str(properties.get("cd_setor_fiscal") or "").strip().zfill(3)
        quadra = str(properties.get("cd_quadra_fiscal") or "").strip().zfill(3)
        sq = f"{setor}{quadra}" if setor.strip("0") and quadra.strip("0") else ""
        records.append(
            {
                "feature_id": feature_id,
                "sq": sq,
                "setor": setor,
                "quadra": quadra,
                "subquadra": str(properties.get("cd_subquadra_fiscal") or "").strip(),
                "tipo_quadra": str(properties.get("tx_tipo_quadra") or "").strip(),
                "dt_carga": str(properties.get("dt_carga") or "").strip(),
                "geometry": geometry,
            }
        )
        raw_features.append(feature)

    RAW_QUADRAS.parent.mkdir(parents=True, exist_ok=True)
    raw_collection = {
        "type": "FeatureCollection",
        "name": LAYER,
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::31983"}},
        "features": raw_features,
    }
    RAW_QUADRAS.write_text(json.dumps(raw_collection, ensure_ascii=False), encoding="utf-8")

    frame = gpd.GeoDataFrame(records, geometry="geometry", crs=CRS_METRIC)
    if frame.empty:
        raise RuntimeError("Nenhuma quadra fiscal foi retornada para os entornos.")
    frame = frame[frame["sq"] != ""].copy()

    dissolved_rows: list[dict[str, Any]] = []
    for sq, group in frame.groupby("sq", sort=False):
        dissolved_rows.append(
            {
                "sq": sq,
                "setor": group["setor"].iloc[0],
                "quadra": group["quadra"].iloc[0],
                "tipo_quadra": ";".join(sorted(set(filter(None, group["tipo_quadra"])))),
                "dt_carga": ";".join(sorted(set(filter(None, group["dt_carga"])))),
                "source_feature_count": len(group),
                "geometry": safe_make_valid(unary_union(list(group["geometry"]))),
            }
        )
    return gpd.GeoDataFrame(dissolved_rows, geometry="geometry", crs=CRS_METRIC), request_urls


def load_pgv() -> tuple[pd.DataFrame, dict[str, list[float]]]:
    pgv = pd.read_csv(PGV_CSV, dtype={"codlog": str, "sq": str, "setor": str, "quadra": str})
    pgv["sq"] = pgv["sq"].str.zfill(6)
    pgv["vm2t_2026"] = pd.to_numeric(pgv["vm2t_2026"], errors="coerce")
    pgv = pgv.dropna(subset=["vm2t_2026"]).copy()
    values_by_sq = {
        sq: group["vm2t_2026"].astype(float).tolist()
        for sq, group in pgv.groupby("sq", sort=False)
    }
    return pgv, values_by_sq


def analyze_unit(
    unit: pd.Series,
    quadras: gpd.GeoDataFrame,
    values_by_sq: dict[str, list[float]],
    unit_kind: str,
) -> list[dict[str, Any]]:
    geometry = unit["geometry"]
    records: list[dict[str, Any]] = []

    for inner, outer in RINGS:
        outer_buffer = geometry.buffer(outer)
        inner_geometry = geometry if inner == 0 else geometry.buffer(inner)
        ring = safe_make_valid(outer_buffer.difference(inner_geometry))
        ring_area = float(ring.area)

        candidates = quadras[quadras.intersects(ring)].copy()
        all_intersection_area = 0.0
        matched_intersection_area = 0.0
        face_values: list[float] = []
        quadra_medians: list[float] = []
        weighted_numerator = 0.0
        weighted_denominator = 0.0
        matched_sq: set[str] = set()
        unmatched_sq: set[str] = set()

        for quadra_row in candidates.itertuples(index=False):
            intersection = quadra_row.geometry.intersection(ring)
            area = float(intersection.area)
            if area <= 0:
                continue
            all_intersection_area += area
            values = values_by_sq.get(quadra_row.sq, [])
            if not values:
                unmatched_sq.add(quadra_row.sq)
                continue
            matched_sq.add(quadra_row.sq)
            matched_intersection_area += area
            face_values.extend(values)
            quadra_median = float(statistics.median(values))
            quadra_medians.append(quadra_median)
            weighted_numerator += quadra_median * area
            weighted_denominator += area

        record = {
            "unidade_analise": unit_kind,
            "id_equipamento": unit.get("id_equipamento", ""),
            "nome_oficial": unit.get("nome_oficial", ""),
            "tipo": unit.get("tipo", ""),
            "complexo": unit.get("complexo", ""),
            "bloco_concessao": unit.get("bloco_concessao", ""),
            "concessionaria": unit.get("concessionaria", ""),
            "categoria_tarifaria": unit.get("categoria_tarifaria", ""),
            "destino_gratuidade_hipossuficiencia": unit.get(
                "destino_gratuidade_hipossuficiencia", ""
            ),
            "anel": f"{inner}-{outer}m",
            "distancia_interna_m": inner,
            "distancia_externa_m": outer,
            "area_anel_m2": round_or_none(ring_area, 2),
            "quadras_intersectadas": len(candidates),
            "quadras_com_pgv": len(matched_sq),
            "quadras_sem_pgv": len(unmatched_sq),
            "registros_face_pgv": len(face_values),
            "cobertura_area_quadras_pgv_pct": round_or_none(
                100 * matched_intersection_area / all_intersection_area
                if all_intersection_area
                else None,
                2,
            ),
            "cobertura_area_anel_por_quadras_pct": round_or_none(
                100 * all_intersection_area / ring_area if ring_area else None,
                2,
            ),
            "vm2t_faces_mediana": round_or_none(statistics.median(face_values) if face_values else None),
            "vm2t_faces_q1": round_or_none(quantile(face_values, 0.25)),
            "vm2t_faces_q3": round_or_none(quantile(face_values, 0.75)),
            "vm2t_faces_min": round_or_none(min(face_values) if face_values else None),
            "vm2t_faces_max": round_or_none(max(face_values) if face_values else None),
            "vm2t_mediana_das_quadras": round_or_none(
                statistics.median(quadra_medians) if quadra_medians else None
            ),
            "vm2t_media_quadras_ponderada_area": round_or_none(
                weighted_numerator / weighted_denominator if weighted_denominator else None
            ),
        }
        records.append(record)
    return records


def build_complexes(cemeteries: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    rows: list[dict[str, Any]] = []

    vf = cemeteries[cemeteries["id_equipamento"].isin(["cem_vila_formosa_i", "cem_vila_formosa_ii"])]
    if len(vf) == 2:
        rows.append(
            {
                "id_equipamento": "complexo_vila_formosa",
                "nome_oficial": "Complexo Vila Formosa I e II",
                "tipo": "complexo_cemiterial",
                "complexo": "Vila Formosa I e II",
                "bloco_concessao": "1",
                "concessionaria": "Consolare",
                "categoria_tarifaria": "4",
                "destino_gratuidade_hipossuficiencia": "True",
                "geometry": safe_make_valid(unary_union(list(vf.geometry))),
            }
        )

    alpina = cemeteries[
        cemeteries["id_equipamento"].isin(["cem_sao_pedro", "crem_vila_alpina"])
    ]
    if len(alpina) == 2:
        rows.append(
            {
                "id_equipamento": "complexo_vila_alpina",
                "nome_oficial": "Complexo São Pedro e Crematório Vila Alpina",
                "tipo": "complexo_cemiterial",
                "complexo": "São Pedro e Crematório Vila Alpina",
                "bloco_concessao": "4",
                "concessionaria": "Velar SP",
                "categoria_tarifaria": "",
                "destino_gratuidade_hipossuficiencia": "True",
                "geometry": safe_make_valid(unary_union(list(alpina.geometry))),
            }
        )

    return gpd.GeoDataFrame(rows, geometry="geometry", crs=CRS_METRIC)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"Nenhum registro para escrever em {path}")
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def category_summary(detail: pd.DataFrame) -> list[dict[str, Any]]:
    subset = detail[
        (detail["unidade_analise"] == "ponto_operacional")
        & (detail["tipo"] == "cemiterio")
        & (detail["categoria_tarifaria"].astype(str).isin(["1", "2", "3", "4"]))
    ].copy()
    results: list[dict[str, Any]] = []
    for (category, ring), group in subset.groupby(["categoria_tarifaria", "anel"], sort=True):
        values = pd.to_numeric(group["vm2t_faces_mediana"], errors="coerce").dropna().tolist()
        results.append(
            {
                "categoria_tarifaria": category,
                "anel": ring,
                "cemiterios_n": len(group),
                "cemiterios_com_valor_n": len(values),
                "mediana_das_medianas_cemiteriais": round_or_none(
                    statistics.median(values) if values else None
                ),
                "q1_das_medianas_cemiteriais": round_or_none(quantile(values, 0.25)),
                "q3_das_medianas_cemiteriais": round_or_none(quantile(values, 0.75)),
                "min_das_medianas_cemiteriais": round_or_none(min(values) if values else None),
                "max_das_medianas_cemiteriais": round_or_none(max(values) if values else None),
            }
        )
    return results


def report_markdown(detail: pd.DataFrame, categories: pd.DataFrame, metadata: dict[str, Any]) -> str:
    lines = [
        "# Resultados preliminares — valor territorial no entorno dos cemitérios (PGV 2026)",
        "",
        "## Estatuto",
        "",
        "Os valores abaixo são valores fiscais oficiais de terreno da PGV 2026, não preços de mercado. "
        "A PGV lista valores por CODLOG + setor/quadra; como o GeoSampa não fornece, nesta etapa, "
        "a geometria individual de cada face, os valores das faces são associados às quadras fiscais "
        "que intersectam cada anel.",
        "",
        "## Cobertura da coleta",
        "",
        f"- equipamentos operacionais analisados: {metadata['operational_unit_count']};",
        f"- quadras fiscais únicas coletadas: {metadata['quadra_sq_count']};",
        f"- consultas WFS realizadas: {metadata['wfs_request_count']};",
        f"- referência temporal das quadras: {metadata.get('quadra_data_dates', [])}.",
        "",
        "## Categoria tarifária — mediana dos valores medianos de cada cemitério",
        "",
        "| Categoria | Anel | Cemitérios | Mediana (R$/m²) | Q1 | Q3 |",
        "|---:|:---:|---:|---:|---:|---:|",
    ]
    for row in categories.itertuples(index=False):
        lines.append(
            f"| {row.categoria_tarifaria} | {row.anel} | {row.cemiterios_com_valor_n} | "
            f"{row.mediana_das_medianas_cemiteriais:,.2f} | "
            f"{row.q1_das_medianas_cemiteriais:,.2f} | {row.q3_das_medianas_cemiteriais:,.2f} |"
        )

    lines.extend(
        [
            "",
            "## Pontos operacionais — anel de 0–250 m",
            "",
            "| Cemitério | Categoria | Gratuidade | Mediana das faces (R$/m²) | Quadras com PGV | Cobertura das quadras (%) |",
            "|:---|---:|:---:|---:|---:|---:|",
        ]
    )
    immediate = detail[
        (detail["unidade_analise"] == "ponto_operacional")
        & (detail["anel"] == "0-250m")
        & (detail["tipo"] == "cemiterio")
    ].sort_values(["categoria_tarifaria", "vm2t_faces_mediana"], ascending=[True, False])
    for row in immediate.itertuples(index=False):
        value = row.vm2t_faces_mediana
        value_text = f"{value:,.2f}" if pd.notna(value) else "—"
        lines.append(
            f"| {row.nome_oficial} | {row.categoria_tarifaria} | "
            f"{row.destino_gratuidade_hipossuficiencia} | {value_text} | "
            f"{row.quadras_com_pgv} | {row.cobertura_area_quadras_pgv_pct} |"
        )

    lines.extend(
        [
            "",
            "## Limites",
            "",
            "- valor fiscal não é valor de mercado;",
            "- a associação entre categoria e PGV não demonstra o critério que originou a categoria;",
            "- uma quadra pode conter várias faces com valores diferentes;",
            "- a ponderação por área usa a mediana das faces da quadra, não uma face georreferenciada;",
            "- Vila Formosa I e II também devem ser lidas como um único complexo territorial.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    for path in (CEMETERY_GEOJSON, MAPPING_CSV, REFERENCE_CSV, PGV_CSV):
        if not path.exists():
            raise FileNotFoundError(f"Entrada ausente: {path}")

    cemeteries = load_cemetery_geometries()
    pgv, values_by_sq = load_pgv()
    quadras, request_urls = collect_quadras(cemeteries)

    operational_rows: list[dict[str, Any]] = []
    for _, unit in cemeteries.iterrows():
        operational_rows.extend(analyze_unit(unit, quadras, values_by_sq, "ponto_operacional"))

    complexes = build_complexes(cemeteries)
    complex_rows: list[dict[str, Any]] = []
    for _, unit in complexes.iterrows():
        complex_rows.extend(analyze_unit(unit, quadras, values_by_sq, "complexo_territorial"))

    detail_rows = operational_rows + complex_rows
    write_csv(OUTPUT_DETAIL, detail_rows)
    write_csv(OUTPUT_COMPLEX, complex_rows)

    detail = pd.DataFrame(detail_rows)
    category_rows = category_summary(detail)
    write_csv(OUTPUT_CATEGORY, category_rows)
    categories = pd.DataFrame(category_rows)

    quadra_dates = sorted(
        {
            date
            for text in quadras["dt_carga"].astype(str)
            for date in text.split(";")
            if date
        }
    )
    matching_sq = set(quadras["sq"]) & set(values_by_sq)
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "crs": CRS_METRIC,
        "rings_m": [{"inner": inner, "outer": outer} for inner, outer in RINGS],
        "sources": {
            "cemetery_polygons": str(CEMETERY_GEOJSON.relative_to(ROOT)),
            "cemetery_mapping": str(MAPPING_CSV.relative_to(ROOT)),
            "cemetery_reference": str(REFERENCE_CSV.relative_to(ROOT)),
            "pgv": str(PGV_CSV.relative_to(ROOT)),
            "quadras_wfs_layer": LAYER,
        },
        "source_sha256": {
            "cemetery_polygons": sha256(CEMETERY_GEOJSON),
            "cemetery_mapping": sha256(MAPPING_CSV),
            "cemetery_reference": sha256(REFERENCE_CSV),
            "pgv": sha256(PGV_CSV),
        },
        "operational_unit_count": len(cemeteries),
        "complex_unit_count": len(complexes),
        "quadra_sq_count": len(quadras),
        "quadra_sq_with_pgv_count": len(matching_sq),
        "quadra_sq_match_rate_pct": round_or_none(100 * len(matching_sq) / len(quadras) if len(quadras) else None),
        "pgv_row_count": len(pgv),
        "pgv_unique_sq_count": len(values_by_sq),
        "wfs_request_count": len(request_urls),
        "wfs_request_urls": request_urls,
        "quadra_data_dates": quadra_dates,
        "method": {
            "primary_indicator": "median of all PGV face values in intersecting fiscal blocks",
            "secondary_indicator": "median of block medians",
            "weighted_indicator": "mean of block medians weighted by intersection area with ring",
            "spatial_unit": "external annuli around official cemetery polygons",
            "pgv_join": "SQ = zero-padded cd_setor_fiscal + cd_quadra_fiscal",
        },
        "limitations": [
            "PGV is an official fiscal value, not a market transaction price.",
            "PGV face records are joined to fiscal-block polygons because individual face geometries are unavailable in this workflow.",
            "Association with tariff category does not prove that land value defined the category.",
            "Vila Formosa I and II are reported separately and jointly for sensitivity.",
        ],
    }
    OUTPUT_METADATA.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_REPORT.write_text(report_markdown(detail, categories, metadata), encoding="utf-8")

    print(
        f"Valor territorial: {len(cemeteries)} pontos, {len(complexes)} complexos, "
        f"{len(quadras)} quadras e {len(detail_rows)} linhas calculadas."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERRO: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
