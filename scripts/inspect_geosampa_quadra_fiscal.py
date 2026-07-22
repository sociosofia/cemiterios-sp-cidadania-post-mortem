#!/usr/bin/env python3
"""Baixa uma amostra da camada `geoportal:quadra_fiscal` do GeoSampa.

A amostra permite verificar os nomes dos campos, o sistema de referência e a
possibilidade de vínculo com o campo SQ da PGV 2026 antes de baixar ou consultar
a camada em larga escala.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "processed" / "geosampa_quadra_fiscal_sample.json"
ENDPOINTS = (
    "https://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs",
    "http://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs",
)
LAYER = "geoportal:quadra_fiscal"
USER_AGENT = (
    "cemiterios-sp-cidadania-post-mortem/1.0 "
    "(pesquisa acadêmica; dados públicos)"
)


def fetch() -> tuple[dict, str]:
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": LAYER,
        "outputFormat": "application/json",
        "srsName": "EPSG:31983",
        "count": 10,
    }
    errors: list[str] = []
    for endpoint in ENDPOINTS:
        url = f"{endpoint}?{urlencode(params)}"
        request = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json,application/geo+json",
            },
        )
        try:
            with urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return payload, response.geturl()
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("Falha ao consultar quadra_fiscal:\n" + "\n".join(errors))


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    collection, request_url = fetch()
    features = collection.get("features", [])
    fields = sorted(
        {
            key
            for feature in features
            for key in (feature.get("properties") or {}).keys()
        }
    )
    report = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "GeoSampa — WFS",
        "layer": LAYER,
        "request_url": request_url,
        "feature_count_in_sample": len(features),
        "fields": fields,
        "sample": features,
        "interpretive_status": (
            "amostra técnica; os campos de setor e quadra devem ser comparados "
            "com o SQ da PGV antes do cruzamento espacial"
        ),
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Quadra fiscal: {len(features)} feições e {len(fields)} campos inspecionados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
