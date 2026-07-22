#!/usr/bin/env python3
"""Executa a análise territorial com consulta WFS tolerante a variantes de BBOX.

A camada `quadra_fiscal` não possui chave primária declarada no GeoServer. O
uso de `startIndex` faz o WFS tentar uma ordenação natural e falhar. Como cada
consulta cobre apenas o entorno de 1 km de um equipamento, este lançador pede
até 10 mil feições numa única resposta, sem paginação, e rejeita silenciosamente
qualquer resultado que atinja esse teto.
"""

from __future__ import annotations

import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import analyze_cemetery_land_values_2026 as analysis

MAX_FEATURES_PER_BBOX = 10_000


def request_payload(url: str) -> tuple[dict[str, Any], str]:
    request = Request(
        url,
        headers={
            "User-Agent": analysis.USER_AGENT,
            "Accept": "application/json,application/geo+json",
        },
    )
    try:
        with urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8")), response.geturl()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:1500]
        raise RuntimeError(f"HTTP {exc.code} em {url}: {body}") from exc


def robust_fetch_quadras_bbox(
    bounds: tuple[float, float, float, float]
) -> tuple[list[dict[str, Any]], list[str]]:
    minx, miny, maxx, maxy = bounds
    bbox_variants = (
        f"{minx},{miny},{maxx},{maxy}",
        f"{minx},{miny},{maxx},{maxy},urn:ogc:def:crs:EPSG::31983",
        f"{minx},{miny},{maxx},{maxy},EPSG:31983",
    )
    errors: list[str] = []

    for endpoint in analysis.WFS_ENDPOINTS:
        for bbox_value in bbox_variants:
            try:
                params = {
                    "service": "WFS",
                    "version": "2.0.0",
                    "request": "GetFeature",
                    "typeNames": analysis.LAYER,
                    "outputFormat": "application/json",
                    "srsName": analysis.CRS_METRIC,
                    "bbox": bbox_value,
                    "count": MAX_FEATURES_PER_BBOX,
                }
                url = f"{endpoint}?{urlencode(params)}"
                payload, final_url = request_payload(url)
                features = payload.get("features", [])
                returned = payload.get("numberReturned", len(features))
                matched = payload.get("numberMatched")
                if returned >= MAX_FEATURES_PER_BBOX or (
                    isinstance(matched, int) and matched > MAX_FEATURES_PER_BBOX
                ):
                    raise RuntimeError(
                        "A consulta atingiu o teto de 10 mil feições; reduza a BBOX "
                        "antes de aceitar o resultado."
                    )
                return features, [final_url]
            except (
                HTTPError,
                URLError,
                TimeoutError,
                ValueError,
                json.JSONDecodeError,
                RuntimeError,
            ) as exc:
                errors.append(
                    f"endpoint={endpoint}; bbox={bbox_value}; "
                    f"{type(exc).__name__}: {exc}"
                )

    raise RuntimeError(
        "Falha em todas as variantes de consulta das quadras fiscais:\n"
        + "\n".join(errors)
    )


def main() -> int:
    analysis.fetch_quadras_bbox = robust_fetch_quadras_bbox
    return analysis.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERRO: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
