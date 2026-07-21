#!/usr/bin/env python3
"""Constrói um inventário preliminar de cemitérios particulares no GeoSampa.

A camada ``geoportal:equipamento_cemiterio`` reúne cemitérios públicos e
privados, mas o atributo de esfera administrativa aparece como MUNICIPAL em
todas as feições da captura atual. Por isso, a classificação é feita por
diferença:

1. identifica as feições já vinculadas à rede pública municipal concedida em
   ``data/reference/geosampa_mapping.csv``;
2. classifica as demais como candidatas a cemitério particular ou outro
   equipamento não pertencente à rede concedida;
3. agrega feições duplicadas pela combinação normalizada de nome e endereço.

O resultado é preliminar e deve ser validado com SP Regula, SVMA e demais
cadastros oficiais antes de ser publicado como número definitivo.

Saídas:
- data/processed/cemiterios_particulares_candidatos_geosampa.csv
- data/processed/cemiterios_particulares_candidatos_geosampa_metadata.json
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEOSAMPA_CSV = ROOT / "data" / "processed" / "geosampa_cemiterios.csv"
PUBLIC_MAPPING_CSV = ROOT / "data" / "reference" / "geosampa_mapping.csv"
OUTPUT_CSV = (
    ROOT
    / "data"
    / "processed"
    / "cemiterios_particulares_candidatos_geosampa.csv"
)
OUTPUT_METADATA = (
    ROOT
    / "data"
    / "processed"
    / "cemiterios_particulares_candidatos_geosampa_metadata.json"
)


def normalize(value: str) -> str:
    """Normaliza texto para agrupamento, sem alterar o valor publicado."""
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.upper().strip()
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def main() -> int:
    geosampa_rows = load_csv(GEOSAMPA_CSV)
    mapping_rows = load_csv(PUBLIC_MAPPING_CSV)
    public_feature_ids = {
        row["feature_id_geosampa"].strip()
        for row in mapping_rows
        if row.get("feature_id_geosampa", "").strip()
    }

    unmatched = [
        row
        for row in geosampa_rows
        if row.get("feature_id", "").strip() not in public_feature_ids
    ]

    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in unmatched:
        key = (
            normalize(row.get("nm_equipamento", "")),
            normalize(row.get("tx_endereco_equipamento", "")),
        )
        grouped[key].append(row)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id_candidato",
        "nome_geosampa",
        "endereco_geosampa",
        "bairro_geosampa",
        "cep_geosampa",
        "feature_ids_geosampa",
        "numero_feicoes",
        "classificacao_preliminar",
        "status_validacao",
        "observacoes",
    ]

    output_rows: list[dict[str, str | int]] = []
    for index, ((_, _), rows) in enumerate(
        sorted(
            grouped.items(),
            key=lambda item: (
                normalize(item[1][0].get("nm_equipamento", "")),
                normalize(item[1][0].get("tx_endereco_equipamento", "")),
            ),
        ),
        start=1,
    ):
        first = rows[0]
        feature_ids = sorted(
            row.get("feature_id", "").strip()
            for row in rows
            if row.get("feature_id", "").strip()
        )
        observations: list[str] = []
        if len(rows) > 1:
            observations.append(
                "Mais de uma feição do GeoSampa foi agregada como uma unidade operacional."
            )
        if all(
            normalize(row.get("nm_esfera_administrativa_equipamento", ""))
            == "MUNICIPAL"
            for row in rows
        ):
            observations.append(
                "O GeoSampa registra esfera MUNICIPAL, atributo incompatível com a descrição geral da camada e que exige validação externa."
            )

        output_rows.append(
            {
                "id_candidato": f"priv_geosampa_{index:02d}",
                "nome_geosampa": first.get("nm_equipamento", "").strip(),
                "endereco_geosampa": first.get("tx_endereco_equipamento", "").strip(),
                "bairro_geosampa": first.get("nm_bairro_equipamento", "").strip(),
                "cep_geosampa": first.get("cd_cep_equipamento", "").strip(),
                "feature_ids_geosampa": "|".join(feature_ids),
                "numero_feicoes": len(rows),
                "classificacao_preliminar": (
                    "candidato_particular_ou_nao_concessionado"
                ),
                "status_validacao": "pendente",
                "observacoes": " ".join(observations),
            }
        )

    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    sphere_values = sorted(
        {
            row.get("nm_esfera_administrativa_equipamento", "").strip()
            for row in geosampa_rows
        }
    )
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": str(GEOSAMPA_CSV.relative_to(ROOT)),
        "public_mapping_file": str(PUBLIC_MAPPING_CSV.relative_to(ROOT)),
        "geosampa_feature_count": len(geosampa_rows),
        "public_concession_feature_count": len(public_feature_ids),
        "unmatched_feature_count": len(unmatched),
        "candidate_operational_unit_count": len(output_rows),
        "administrative_sphere_values_in_source": sphere_values,
        "method": (
            "Set difference between all GeoSampa cemetery features and the "
            "feature IDs already validated as part of the municipal concession network; "
            "unmatched features are grouped by normalized name and address."
        ),
        "interpretive_status": "preliminary inventory; external validation required",
        "limitations": [
            "The GeoSampa administrative-sphere field is not reliable for separating public and private cemeteries in the current capture.",
            "An unmatched feature may be private, associative, religious, inactive, duplicated or otherwise outside the concession inventory.",
            "The count must be checked against SP Regula, SVMA, sanitary and fiscal records before publication.",
        ],
    }
    OUTPUT_METADATA.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        f"GeoSampa: {len(geosampa_rows)} feições; "
        f"{len(public_feature_ids)} vinculadas à rede concedida; "
        f"{len(unmatched)} feições não vinculadas; "
        f"{len(output_rows)} unidades candidatas."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
