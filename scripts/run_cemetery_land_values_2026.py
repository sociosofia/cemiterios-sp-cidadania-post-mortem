#!/usr/bin/env python3
"""Executa a análise territorial com consulta WFS tolerante a variantes de BBOX.

O GeoServer do GeoSampa rejeita algumas combinações de WFS 2.0 e CRS no
parâmetro BBOX. Este lançador testa, em ordem, BBOX sem CRS explícito e BBOX
com URN OGC, preservando `srsName=EPSG:31983` na resposta.
"""

from __future__ import annotations

import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import analyze_cemetery_land_values_2026 as analysis


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
            features_all: list[dict[str, Any]] = []
            request_urls: list[str] = []
            start_index = 0
            try:
                while True:
                    params = {
                        "service": "WFS",
                        "version": "2.0.0",
                        "request": "GetFeature",
                        "typeNames": analysis.LAYER,
                        "outputFormat": "application/json",
                        "srsName": analysis.CRS_METRIC,
                        "bbox": bbox_value,
                        "count": analysis.PAGE_SIZE,
                        "startIndex": start_index,
                    }
                    url = f"{endpoint}?{urlencode(params)}"
                    payload, final_url = request_payload(url)
                    request_urls.append(final_url)
                    features = payload.get("features", [])
                    features_all.extend(features)
                    returned = payload.get("numberReturned", len(features))
                    matched = payload.get("numberMatched")
                    if not features or returned < analysis.PAGE_SIZE:
                        break
                    start_index += len(features)
                    if isinstance(matched, int) and start_index >= matched:
                        break
                    if start_index > 250_000:
                        raise RuntimeError(
                            "Paginação excedeu 250 mil feições para uma única BBOX."
                        )
                return features_all, request_urls
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
