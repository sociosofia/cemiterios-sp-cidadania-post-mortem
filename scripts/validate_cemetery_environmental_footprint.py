#!/usr/bin/env python3
"""Valida a extensão territorial dos cemitérios públicos concedidos.

A rotina distingue três grandezas que não devem ser tratadas como sinônimas:

1. área territorial dos polígonos dos equipamentos;
2. área verde ou permeável;
3. cobertura vegetal ou arbórea.

Somente a primeira é calculada com a base atual. As demais exigem camadas
ambientais específicas e interseção espacial posterior.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = ROOT / "data" / "processed" / "cemiterios_concessao_centroides.csv"
OUTPUT_JSON = ROOT / "data" / "processed" / "resumo_area_territorial_cemiterios.json"

OFFICIAL_2014_M2 = 3_278_272.0
THESIS_ESTIMATE_M2 = 3_600_000.0


def round3(value: float) -> float:
    return round(value, 3)


def comparison(reference_m2: float, current_m2: float) -> dict[str, float]:
    difference = reference_m2 - current_m2
    return {
        "reference_m2": round3(reference_m2),
        "current_m2": round3(current_m2),
        "difference_m2": round3(difference),
        "difference_percent_of_reference": round(difference / reference_m2 * 100, 3),
    }


def main() -> int:
    with INPUT_CSV.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise RuntimeError(f"Base vazia: {INPUT_CSV}")

    required = {"id_equipamento", "nome_oficial", "tipo", "bloco_concessao", "area_m2_31983"}
    missing = required - set(rows[0])
    if missing:
        raise RuntimeError(f"Colunas ausentes em {INPUT_CSV}: {sorted(missing)}")

    block_totals: dict[str, float] = defaultdict(float)
    equipment: list[dict[str, Any]] = []
    total_m2 = 0.0
    cemetery_m2 = 0.0
    crematorium_m2 = 0.0

    for row in rows:
        area = float(row["area_m2_31983"])
        total_m2 += area
        block_totals[row["bloco_concessao"]] += area

        if row["tipo"] == "cemiterio":
            cemetery_m2 += area
        elif row["tipo"] == "crematorio":
            crematorium_m2 += area

        equipment.append(
            {
                "id_equipamento": row["id_equipamento"],
                "nome_oficial": row["nome_oficial"],
                "tipo": row["tipo"],
                "bloco_concessao": int(row["bloco_concessao"]),
                "area_m2": round3(area),
            }
        )

    result = {
        "source_file": str(INPUT_CSV.relative_to(ROOT)),
        "source_crs": "EPSG:31983",
        "method": "soma das áreas dos polígonos oficiais do GeoSampa já dissolvidos por equipamento",
        "equipment_count": len(rows),
        "cemetery_count": sum(row["tipo"] == "cemiterio" for row in rows),
        "crematorium_count": sum(row["tipo"] == "crematorio" for row in rows),
        "total_equipment_footprint_m2": round3(total_m2),
        "total_equipment_footprint_hectares": round(total_m2 / 10_000, 3),
        "cemetery_footprint_m2": round3(cemetery_m2),
        "crematorium_footprint_m2": round3(crematorium_m2),
        "totals_by_block_m2": {
            str(block): round3(value)
            for block, value in sorted(block_totals.items(), key=lambda item: int(item[0]))
        },
        "comparison_official_2014": comparison(OFFICIAL_2014_M2, total_m2),
        "comparison_thesis_estimate": comparison(THESIS_ESTIMATE_M2, total_m2),
        "equipment": sorted(equipment, key=lambda item: item["area_m2"], reverse=True),
        "interpretive_limits": [
            "A soma mede a extensão territorial dos equipamentos, não a cobertura vegetal.",
            "Área cemiterial, área verde, área permeável e copa arbórea são grandezas diferentes.",
            "A validação ambiental exige interseção com camadas municipais de vegetação, cobertura arbórea, impermeabilização ou uso do solo.",
            "O total é uma soma por equipamento; eventuais sobreposições entre polígonos devem ser verificadas em uma etapa geométrica adicional.",
        ],
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
