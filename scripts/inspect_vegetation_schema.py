#!/usr/bin/env python3
"""Registra o esquema efetivamente devolvido pela camada WFS de vegetação."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INPUT = (
    ROOT
    / "data"
    / "raw"
    / "geosampa"
    / "cobertura_vegetal_2017_entorno_cemiterios_31983.geojson"
)
OUTPUT = ROOT / "data" / "processed" / "cobertura_vegetal_2017_schema.json"


def value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    return type(value).__name__


def main() -> int:
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    features = data.get("features", [])
    key_counts: Counter[str] = Counter()
    type_counts: dict[str, Counter[str]] = {}

    for feature in features:
        properties = feature.get("properties") or {}
        for key, value in properties.items():
            key_counts[key] += 1
            type_counts.setdefault(key, Counter())[value_type(value)] += 1

    samples = []
    for feature in features[:5]:
        samples.append(
            {
                "id": feature.get("id"),
                "properties": feature.get("properties") or {},
            }
        )

    result = {
        "feature_count": len(features),
        "property_keys": sorted(key_counts),
        "fields": {
            key: {
                "non_missing_feature_count": key_counts[key],
                "types": dict(type_counts[key]),
            }
            for key in sorted(key_counts)
        },
        "sample_features": samples,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Esquema registrado: {len(key_counts)} campos em {len(features)} feições.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
