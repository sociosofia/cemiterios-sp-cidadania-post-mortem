#!/usr/bin/env python3
"""Baixa e filtra a base cartográfica oficial do IPVS 2022 para São Paulo.

A rotina consulta o catálogo CKAN da Fundação Seade, baixa o ZIP em diretório
temporário, identifica a camada de setores censitários, filtra o município de
São Paulo e grava GeoJSON em EPSG:31983 e EPSG:4326. O arquivo bruto não é
versionado para evitar inflar o repositório; metadados e checksums são mantidos.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import shapefile  # pyshp
from pyproj import CRS, Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[1]
RAW_META = ROOT / "data" / "raw" / "seade" / "ipvs_2022"
PROCESSED = ROOT / "data" / "processed"

CKAN_API = "https://repositorio.seade.gov.br/api/3/action/package_show?id=seade-ipvs"
MUNICIPIO_CODIGOS = {"3550308", "355030"}
UA = "cemiterios-sp-cidadania-post-mortem/1.0"


def get_bytes(url: str, timeout: int = 240) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def normalize(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())


def choose_resource(package: dict[str, Any]) -> dict[str, Any]:
    resources = package.get("resources", [])
    scored: list[tuple[int, dict[str, Any]]] = []
    for resource in resources:
        text = " ".join(
            str(resource.get(key, ""))
            for key in ("name", "description", "format", "url")
        ).upper()
        score = 0
        if "ZIP" in text:
            score += 4
        if "2022" in text:
            score += 3
        if "CARTOGR" in text or "SHP" in text or "SHAPE" in text:
            score += 3
        if resource.get("url"):
            scored.append((score, resource))
    if not scored:
        raise RuntimeError("O catálogo do Seade não retornou recursos para o IPVS.")
    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best = scored[0]
    if best_score < 4:
        raise RuntimeError("Nenhum recurso cartográfico ZIP do IPVS 2022 foi identificado.")
    return best


def find_shapefile(directory: Path) -> Path:
    candidates = list(directory.rglob("*.shp"))
    if not candidates:
        raise RuntimeError("O ZIP do IPVS não contém arquivo SHP.")
    ranked = sorted(
        candidates,
        key=lambda path: (
            "IPVS" in normalize(path.name),
            "2022" in normalize(path.name),
            path.stat().st_size,
        ),
        reverse=True,
    )
    return ranked[0]


def read_with_encoding(path: Path) -> shapefile.Reader:
    last_error: Exception | None = None
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            reader = shapefile.Reader(str(path), encoding=encoding)
            _ = reader.fields
            return reader
        except Exception as exc:  # pragma: no cover - depende da fonte externa
            last_error = exc
    raise RuntimeError(f"Não foi possível ler o shapefile: {last_error}")


def find_field(fields: list[str], patterns: tuple[str, ...]) -> str | None:
    for field in fields:
        norm = normalize(field)
        if any(pattern in norm for pattern in patterns):
            return field
    return None


def municipality_matches(value: object) -> bool:
    digits = re.sub(r"\D", "", str(value or ""))
    return any(digits.startswith(code) for code in MUNICIPIO_CODIGOS)


def identify_fields(reader: shapefile.Reader) -> dict[str, str | None]:
    fields = [field[0] for field in reader.fields[1:]]
    municipality = find_field(fields, ("CDMUN", "CODMUN", "MUNICIP", "CODIBGE"))
    sector = find_field(fields, ("CDSETOR", "CODSETOR", "SETOR"))
    group = find_field(fields, ("IPVS", "GRUPO"))
    population = find_field(fields, ("POPULAC", "POP2022", "POPUL", "PESSOAS"))

    if municipality is None:
        candidates = [field for field in fields if "COD" in normalize(field) or "CD" in normalize(field)]
        for candidate in candidates:
            idx = fields.index(candidate)
            if any(municipality_matches(record[idx]) for record in reader.iterRecords()):
                municipality = candidate
                break
    if municipality is None:
        raise RuntimeError("Não foi possível identificar o código municipal no DBF do IPVS.")
    if group is None:
        raise RuntimeError("Não foi possível identificar o grupo IPVS no DBF.")

    return {
        "municipality": municipality,
        "sector": sector,
        "group": group,
        "population": population,
    }


def load_crs(shp_path: Path, reader: shapefile.Reader) -> CRS:
    prj_path = shp_path.with_suffix(".prj")
    if prj_path.exists():
        return CRS.from_wkt(prj_path.read_text(encoding="utf-8", errors="replace"))

    bbox = reader.bbox
    if -180 <= bbox[0] <= 180 and -180 <= bbox[2] <= 180:
        return CRS.from_epsg(4674)
    raise RuntimeError("Shapefile sem PRJ e com coordenadas projetadas não identificadas.")


def to_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def main() -> int:
    RAW_META.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)

    package_response = json.loads(get_bytes(CKAN_API).decode("utf-8"))
    if not package_response.get("success"):
        raise RuntimeError("A API CKAN do Seade respondeu sem sucesso.")
    package = package_response["result"]
    resource = choose_resource(package)
    resource_url = resource["url"]
    archive_bytes = get_bytes(resource_url)
    checksum = hashlib.sha256(archive_bytes).hexdigest()

    with tempfile.TemporaryDirectory(prefix="ipvs2022-") as temp:
        temp_path = Path(temp)
        with zipfile.ZipFile(Path(temp_path) / "ipvs.zip", "w") as _:
            pass
        archive_path = temp_path / "ipvs_download.zip"
        archive_path.write_bytes(archive_bytes)
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.namelist()
            archive.extractall(temp_path / "extracted")

        shp_path = find_shapefile(temp_path / "extracted")
        reader = read_with_encoding(shp_path)
        fields = [field[0] for field in reader.fields[1:]]
        field_map = identify_fields(reader)
        source_crs = load_crs(shp_path, reader)
        to_metric = Transformer.from_crs(source_crs, 31983, always_xy=True).transform
        to_web = Transformer.from_crs(source_crs, 4326, always_xy=True).transform

        features_metric: list[dict[str, Any]] = []
        features_web: list[dict[str, Any]] = []
        group_counts: Counter[str] = Counter()

        for shape_record in reader.iterShapeRecords():
            record = shape_record.record.as_dict()
            if not municipality_matches(record.get(field_map["municipality"])):
                continue

            geometry = shape(shape_record.shape.__geo_interface__)
            if not geometry.is_valid:
                geometry = geometry.buffer(0)
            if geometry.is_empty:
                continue

            group_value = record.get(field_map["group"])
            group_text = str(group_value).strip()
            population = (
                to_float(record.get(field_map["population"]))
                if field_map["population"]
                else None
            )
            properties = {
                "cd_municipio": str(record.get(field_map["municipality"], "")),
                "cd_setor": str(record.get(field_map["sector"], "")) if field_map["sector"] else None,
                "ipvs_grupo": group_text,
                "populacao": population,
            }
            group_counts[group_text] += 1

            metric_geometry = transform(to_metric, geometry)
            web_geometry = transform(to_web, geometry)
            features_metric.append(
                {"type": "Feature", "properties": properties, "geometry": mapping(metric_geometry)}
            )
            features_web.append(
                {"type": "Feature", "properties": properties, "geometry": mapping(web_geometry)}
            )

    if not features_metric:
        raise RuntimeError("O filtro não encontrou setores IPVS do Município de São Paulo.")

    metric_output = PROCESSED / "ipvs_sp_2022_31983.geojson"
    web_output = PROCESSED / "ipvs_sp_2022_4326.geojson"
    metric_output.write_text(
        json.dumps({"type": "FeatureCollection", "features": features_metric}, ensure_ascii=False),
        encoding="utf-8",
    )
    web_output.write_text(
        json.dumps({"type": "FeatureCollection", "features": features_web}, ensure_ascii=False),
        encoding="utf-8",
    )

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "catalog_api": CKAN_API,
        "resource_name": resource.get("name"),
        "resource_url": resource_url,
        "sha256": checksum,
        "archive_size_bytes": len(archive_bytes),
        "archive_members": members,
        "selected_shapefile": shp_path.name,
        "source_crs": source_crs.to_string(),
        "field_names": fields,
        "field_mapping": field_map,
        "sao_paulo_sector_count": len(features_metric),
        "group_counts": dict(sorted(group_counts.items())),
        "outputs": [str(metric_output.relative_to(ROOT)), str(web_output.relative_to(ROOT))],
    }
    (RAW_META / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"IPVS 2022: {len(features_metric)} setores de São Paulo processados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
