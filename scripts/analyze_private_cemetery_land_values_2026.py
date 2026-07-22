#!/usr/bin/env python3
"""Calcula o valor fiscal do terreno no entorno dos cemitérios particulares candidatos.

O universo é derivado por diferença entre todas as feições da camada oficial
`geoportal:equipamento_cemiterio` e as feições já vinculadas à rede pública
municipal concedida em `data/reference/geosampa_mapping.csv`.

A classificação jurídica e a situação de funcionamento continuam pendentes de
validação externa. Por isso, os resultados são publicados como referentes a
cemitérios particulares, associativos, religiosos ou não concessionados
**candidatos**, e não como censo definitivo dos cemitérios privados ativos.
"""

from __future__ import annotations

import json
import statistics
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape
from shapely.ops import unary_union

import analyze_cemetery_land_values_2026 as analysis
from run_cemetery_land_values_2026 import robust_fetch_quadras_bbox

ROOT = Path(__file__).resolve().parents[1]
CEMETERY_GEOJSON = ROOT / "data" / "raw" / "geosampa" / "equipamento_cemiterio_31983.geojson"
PUBLIC_MAPPING = ROOT / "data" / "reference" / "geosampa_mapping.csv"
PGV_CSV = ROOT / "data" / "processed" / "pgv_2026_faces.csv"
PUBLIC_DETAIL = ROOT / "data" / "processed" / "cemiterios_valor_territorial_2026.csv"
PUBLIC_CATEGORIES = ROOT / "data" / "processed" / "categorias_valor_territorial_2026.csv"

RAW_QUADRAS = (
    ROOT
    / "data"
    / "raw"
    / "geosampa"
    / "quadra_fiscal_entorno_cemiterios_particulares_31983.geojson"
)
OUTPUT_DETAIL = (
    ROOT / "data" / "processed" / "cemiterios_particulares_valor_territorial_2026.csv"
)
OUTPUT_SUMMARY = (
    ROOT
    / "data"
    / "processed"
    / "cemiterios_particulares_valor_territorial_2026_resumo.csv"
)
OUTPUT_METADATA = (
    ROOT
    / "data"
    / "processed"
    / "cemiterios_particulares_valor_territorial_2026_metadata.json"
)
OUTPUT_REPORT = ROOT / "docs" / "RESULTADOS_VALOR_TERRITORIAL_PARTICULARES_2026.md"

CRS_METRIC = analysis.CRS_METRIC


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    return " ".join(text.split())


def title_name(value: str) -> str:
    exceptions = {"DA", "DE", "DO", "DAS", "DOS", "E"}
    words = []
    for index, word in enumerate(str(value or "").strip().split()):
        upper = word.upper()
        if index > 0 and upper in exceptions:
            words.append(upper.lower())
        else:
            words.append(word.capitalize())
    return " ".join(words)


def load_private_candidates() -> gpd.GeoDataFrame:
    source = json.loads(CEMETERY_GEOJSON.read_text(encoding="utf-8"))
    public_mapping = pd.read_csv(PUBLIC_MAPPING, dtype=str).fillna("")
    public_ids = set(public_mapping["feature_id_geosampa"].astype(str))

    records: list[dict[str, Any]] = []
    for feature in source.get("features", []):
        feature_id = str(feature.get("id") or "")
        if not feature_id or feature_id in public_ids:
            continue
        geometry_payload = feature.get("geometry")
        if not geometry_payload:
            continue
        properties = feature.get("properties") or {}
        name = str(properties.get("nm_equipamento") or "").strip()
        address = str(properties.get("tx_endereco_equipamento") or "").strip()
        group_key = f"{normalize_text(name)}|{normalize_text(address)}"
        records.append(
            {
                "group_key": group_key,
                "feature_id_geosampa": feature_id,
                "nome_geosampa": name,
                "endereco_geosampa": address,
                "bairro_geosampa": str(properties.get("nm_bairro_equipamento") or "").strip(),
                "cep_geosampa": str(properties.get("cd_cep_equipamento") or "").strip(),
                "geometry": analysis.safe_make_valid(shape(geometry_payload)),
            }
        )

    frame = gpd.GeoDataFrame(records, geometry="geometry", crs=CRS_METRIC)
    if frame.empty:
        raise RuntimeError("Nenhuma feição não concessionada foi encontrada no GeoSampa.")

    grouped_rows: list[dict[str, Any]] = []
    for group_key, group in frame.groupby("group_key", sort=True):
        grouped_rows.append(
            {
                "group_key": group_key,
                "nome_geosampa": group["nome_geosampa"].iloc[0],
                "endereco_geosampa": group["endereco_geosampa"].iloc[0],
                "bairro_geosampa": group["bairro_geosampa"].iloc[0],
                "cep_geosampa": group["cep_geosampa"].iloc[0],
                "feature_ids_geosampa": "|".join(sorted(group["feature_id_geosampa"])),
                "numero_feicoes": len(group),
                "geometry": analysis.safe_make_valid(unary_union(list(group.geometry))),
            }
        )

    grouped = gpd.GeoDataFrame(grouped_rows, geometry="geometry", crs=CRS_METRIC)
    grouped = grouped.sort_values(["nome_geosampa", "endereco_geosampa"]).reset_index(drop=True)
    grouped["id_equipamento"] = [
        f"priv_geosampa_{index:02d}" for index in range(1, len(grouped) + 1)
    ]
    grouped["nome_oficial"] = grouped["nome_geosampa"].map(
        lambda value: f"Cemitério {title_name(value)}"
    )
    grouped["tipo"] = "cemiterio_particular_candidato"
    grouped["complexo"] = ""
    grouped["bloco_concessao"] = ""
    grouped["concessionaria"] = ""
    grouped["categoria_tarifaria"] = ""
    grouped["destino_gratuidade_hipossuficiencia"] = ""
    grouped["classificacao_preliminar"] = "particular_associativo_religioso_ou_nao_concessionado"
    grouped["status_validacao"] = "pendente"
    return grouped


def analyze_candidates(
    candidates: gpd.GeoDataFrame,
    quadras: gpd.GeoDataFrame,
    values_by_sq: dict[str, list[float]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, unit in candidates.iterrows():
        unit_rows = analysis.analyze_unit(
            unit, quadras, values_by_sq, "cemiterio_particular_candidato"
        )
        for record in unit_rows:
            record.update(
                {
                    "nome_geosampa": unit["nome_geosampa"],
                    "endereco_geosampa": unit["endereco_geosampa"],
                    "bairro_geosampa": unit["bairro_geosampa"],
                    "cep_geosampa": unit["cep_geosampa"],
                    "feature_ids_geosampa": unit["feature_ids_geosampa"],
                    "numero_feicoes": int(unit["numero_feicoes"]),
                    "classificacao_preliminar": unit["classificacao_preliminar"],
                    "status_validacao": unit["status_validacao"],
                }
            )
            rows.append(record)
    return rows


def summary_rows(detail: pd.DataFrame) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for ring, group in detail.groupby("anel", sort=True):
        values = pd.to_numeric(group["vm2t_faces_mediana"], errors="coerce").dropna().tolist()
        results.append(
            {
                "universo": "candidatos_particulares_ou_nao_concessionados",
                "anel": ring,
                "cemiterios_n": len(group),
                "cemiterios_com_valor_n": len(values),
                "mediana_das_medianas_cemiteriais": analysis.round_or_none(
                    statistics.median(values) if values else None
                ),
                "q1_das_medianas_cemiteriais": analysis.round_or_none(
                    analysis.quantile(values, 0.25)
                ),
                "q3_das_medianas_cemiteriais": analysis.round_or_none(
                    analysis.quantile(values, 0.75)
                ),
                "min_das_medianas_cemiteriais": analysis.round_or_none(
                    min(values) if values else None
                ),
                "max_das_medianas_cemiteriais": analysis.round_or_none(
                    max(values) if values else None
                ),
            }
        )
    return results


def brl(value: Any) -> str:
    if value is None or pd.isna(value):
        return "—"
    text = f"{float(value):,.2f}"
    return "R$ " + text.replace(",", "X").replace(".", ",").replace("X", ".")


def build_report(
    detail: pd.DataFrame,
    summary: pd.DataFrame,
    metadata: dict[str, Any],
) -> str:
    lines = [
        "# Resultados preliminares — valor territorial dos cemitérios particulares candidatos (PGV 2026)",
        "",
        "## Estatuto",
        "",
        "O universo foi obtido por diferença entre a camada completa de cemitérios do GeoSampa e as feições já vinculadas documentalmente à rede municipal concedida. A classificação jurídica e o funcionamento atual ainda precisam ser validados. Portanto, os resultados não constituem um censo definitivo dos cemitérios privados ativos.",
        "",
        "## Cobertura",
        "",
        f"- unidades candidatas analisadas: {metadata['candidate_unit_count']};",
        f"- feições do GeoSampa agregadas: {metadata['candidate_feature_count']};",
        f"- quadras fiscais únicas coletadas: {metadata['quadra_sq_count']};",
        f"- quadras vinculadas à PGV: {metadata['quadra_sq_with_pgv_count']} ({metadata['quadra_sq_match_rate_pct']}%);",
        f"- consultas WFS realizadas: {metadata['wfs_request_count']}.",
        "",
        "## Síntese por anel",
        "",
        "| Anel | Cemitérios com valor | Mediana | Q1 | Q3 | Mínimo | Máximo |",
        "|:---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.itertuples(index=False):
        lines.append(
            f"| {row.anel} | {row.cemiterios_com_valor_n} | "
            f"{brl(row.mediana_das_medianas_cemiteriais)} | "
            f"{brl(row.q1_das_medianas_cemiteriais)} | "
            f"{brl(row.q3_das_medianas_cemiteriais)} | "
            f"{brl(row.min_das_medianas_cemiteriais)} | "
            f"{brl(row.max_das_medianas_cemiteriais)} |"
        )

    lines.extend(
        [
            "",
            "## Unidades candidatas — anel de 0–250 m",
            "",
            "| Unidade GeoSampa | Bairro | Mediana da PGV | Quadras com PGV | Cobertura das quadras | Validação |",
            "|:---|:---|---:|---:|---:|:---:|",
        ]
    )
    immediate = detail[detail["anel"] == "0-250m"].copy()
    immediate["vm2t_faces_mediana_num"] = pd.to_numeric(
        immediate["vm2t_faces_mediana"], errors="coerce"
    )
    immediate = immediate.sort_values("vm2t_faces_mediana_num", ascending=False)
    for row in immediate.itertuples(index=False):
        lines.append(
            f"| {row.nome_oficial} | {row.bairro_geosampa} | {brl(row.vm2t_faces_mediana)} | "
            f"{row.quadras_com_pgv} | {row.cobertura_area_quadras_pgv_pct}% | {row.status_validacao} |"
        )

    if PUBLIC_CATEGORIES.exists():
        public_categories = pd.read_csv(PUBLIC_CATEGORIES)
        public_250 = public_categories[public_categories["anel"] == "0-250m"].copy()
        private_250 = summary[summary["anel"] == "0-250m"]
        lines.extend(
            [
                "",
                "## Comparação exploratória com a rede municipal concedida — 0–250 m",
                "",
                "| Universo | Mediana das medianas cemiteriais |",
                "|:---|---:|",
            ]
        )
        if not private_250.empty:
            lines.append(
                f"| Candidatos particulares ou não concessionados | {brl(private_250.iloc[0]['mediana_das_medianas_cemiteriais'])} |"
            )
        for row in public_250.sort_values("categoria_tarifaria").itertuples(index=False):
            lines.append(
                f"| Rede municipal — categoria {row.categoria_tarifaria} | {brl(row.mediana_das_medianas_cemiteriais)} |"
            )

    lines.extend(
        [
            "",
            "## Limites",
            "",
            "- PGV é valor fiscal oficial, não preço de mercado;",
            "- a classificação privada, associativa, religiosa ou não concessionada ainda é preliminar;",
            "- situação de funcionamento e regime de acesso não foram validados nesta etapa;",
            "- o GeoSampa classifica todas as feições como MUNICIPAL no campo de esfera administrativa, que não foi usado para definir propriedade;",
            "- duas feições do Cemitério do Morumby são agregadas como uma unidade;",
            "- equipamentos no mesmo endereço, mas com nomes distintos, permanecem separados até validação institucional;",
            "- a geometria disponível é da quadra fiscal, não de cada face de quadra.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    for path in (CEMETERY_GEOJSON, PUBLIC_MAPPING, PGV_CSV):
        if not path.exists():
            raise FileNotFoundError(f"Entrada ausente: {path}")

    candidates = load_private_candidates()

    analysis.fetch_quadras_bbox = robust_fetch_quadras_bbox
    analysis.RAW_QUADRAS = RAW_QUADRAS

    _, values_by_sq = analysis.load_pgv()
    quadras, request_urls = analysis.collect_quadras(candidates)
    detail_rows = analyze_candidates(candidates, quadras, values_by_sq)
    analysis.write_csv(OUTPUT_DETAIL, detail_rows)

    detail = pd.DataFrame(detail_rows)
    summary_data = summary_rows(detail)
    analysis.write_csv(OUTPUT_SUMMARY, summary_data)
    summary = pd.DataFrame(summary_data)

    matched_sq = set(quadras[quadras["sq"].isin(values_by_sq)]["sq"])
    all_sq = set(quadras["sq"])
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "interpretive_status": "preliminary inventory and spatial comparison; external legal and operational validation required",
        "crs": CRS_METRIC,
        "rings_m": [
            {"inner": inner, "outer": outer} for inner, outer in analysis.RINGS
        ],
        "sources": {
            "cemetery_polygons": str(CEMETERY_GEOJSON.relative_to(ROOT)),
            "public_mapping": str(PUBLIC_MAPPING.relative_to(ROOT)),
            "pgv": str(PGV_CSV.relative_to(ROOT)),
            "quadras_wfs_layer": analysis.LAYER,
        },
        "source_sha256": {
            "cemetery_polygons": analysis.sha256(CEMETERY_GEOJSON),
            "public_mapping": analysis.sha256(PUBLIC_MAPPING),
            "pgv": analysis.sha256(PGV_CSV),
        },
        "candidate_feature_count": int(candidates["numero_feicoes"].sum()),
        "candidate_unit_count": len(candidates),
        "candidate_status_counts": candidates["status_validacao"].value_counts().to_dict(),
        "quadra_sq_count": len(all_sq),
        "quadra_sq_with_pgv_count": len(matched_sq),
        "quadra_sq_match_rate_pct": analysis.round_or_none(
            100 * len(matched_sq) / len(all_sq) if all_sq else None, 1
        ),
        "wfs_request_count": len(request_urls),
        "wfs_request_urls": request_urls,
        "quadra_data_dates": sorted(
            {
                value
                for value in quadras.get("dt_carga", pd.Series(dtype=str)).astype(str)
                if value
            }
        ),
        "method": {
            "universe": "set difference between all GeoSampa cemetery features and feature IDs in the municipal-concession mapping",
            "deduplication": "normalized cemetery name plus normalized address",
            "primary_indicator": "median of all PGV face values in intersecting fiscal blocks",
            "secondary_indicator": "median of block medians",
            "weighted_indicator": "mean of block medians weighted by intersection area with ring",
            "spatial_unit": "external annuli around official GeoSampa cemetery polygons",
            "pgv_join": "SQ = zero-padded cd_setor_fiscal + cd_quadra_fiscal",
        },
        "limitations": [
            "PGV is an official fiscal value, not a market transaction price.",
            "Legal ownership, operational status and access regime remain pending external validation.",
            "The GeoSampa administrative-sphere field labels all cemetery features as MUNICIPAL and is not used to infer ownership.",
            "Association with the private-candidate universe does not establish a causal effect of ownership regime on land value.",
        ],
    }
    OUTPUT_METADATA.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_METADATA.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_REPORT.write_text(
        build_report(detail, summary, metadata), encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "candidate_units": len(candidates),
                "candidate_features": int(candidates["numero_feicoes"].sum()),
                "detail_rows": len(detail_rows),
                "quadra_sq_count": len(all_sq),
                "quadra_sq_match_rate_pct": metadata["quadra_sq_match_rate_pct"],
                "outputs": [
                    str(OUTPUT_DETAIL.relative_to(ROOT)),
                    str(OUTPUT_SUMMARY.relative_to(ROOT)),
                    str(OUTPUT_METADATA.relative_to(ROOT)),
                    str(OUTPUT_REPORT.relative_to(ROOT)),
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
