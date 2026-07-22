#!/usr/bin/env python3
"""Extrai a Listagem de Valores Unitários de Terreno da PGV 2026.

Entrada:
- data/raw/pgv_2026/anexo_lei_18330_2025_145975345.pdf

Saídas:
- data/processed/pgv_2026_faces.csv
- data/processed/pgv_2026_faces_metadata.json

O Anexo II apresenta linhas no formato `Codlog SQ vm2t`. O campo SQ é
preservado com seis dígitos e também desdobrado em setor e quadra, com três
dígitos cada. O script exige `pdftotext` (poppler-utils) e rejeita duplicidades
exatas de CODLOG + SQ.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import statistics
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "data" / "raw" / "pgv_2026" / "anexo_lei_18330_2025_145975345.pdf"
CSV_PATH = ROOT / "data" / "processed" / "pgv_2026_faces.csv"
METADATA_PATH = ROOT / "data" / "processed" / "pgv_2026_faces_metadata.json"

ROW_PATTERN = re.compile(r"^\s*(\d{6})\s+(\d{6})\s+(\d+(?:[.,]\d+)?)\s*$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"Fonte da PGV não encontrada: {PDF_PATH}")

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".txt") as temp:
        subprocess.run(
            ["pdftotext", "-layout", str(PDF_PATH), temp.name],
            check=True,
        )

        rows: list[tuple[str, str, str, str, float]] = []
        with open(temp.name, encoding="utf-8", errors="replace") as source:
            for line in source:
                match = ROW_PATTERN.match(line)
                if not match:
                    continue
                codlog, sq, raw_value = match.groups()
                value = float(raw_value.replace(",", "."))
                rows.append((codlog, sq, sq[:3], sq[3:], value))

    if not rows:
        raise RuntimeError("Nenhuma linha `Codlog SQ vm2t` foi extraída do Anexo II.")

    keys = [(codlog, sq) for codlog, sq, _, _, _ in rows]
    duplicate_count = len(keys) - len(set(keys))
    if duplicate_count:
        raise RuntimeError(
            f"Foram encontradas {duplicate_count} duplicidades de CODLOG + SQ."
        )

    with CSV_PATH.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.writer(destination)
        writer.writerow(["codlog", "sq", "setor", "quadra", "vm2t_2026"])
        for codlog, sq, setor, quadra, value in rows:
            normalized = int(value) if value.is_integer() else value
            writer.writerow([codlog, sq, setor, quadra, normalized])

    values = [row[4] for row in rows]
    unique_sq = {row[1] for row in rows}
    unique_codlog = {row[0] for row in rows}
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Anexo II da Lei municipal 18.330/2025",
        "source_file": str(PDF_PATH.relative_to(ROOT)),
        "source_sha256": sha256(PDF_PATH),
        "output_file": str(CSV_PATH.relative_to(ROOT)),
        "row_format": "Codlog SQ vm2t",
        "sq_interpretation": {
            "setor": "primeiros três dígitos de SQ",
            "quadra": "últimos três dígitos de SQ",
        },
        "row_count": len(rows),
        "unique_sq_count": len(unique_sq),
        "unique_codlog_count": len(unique_codlog),
        "duplicate_codlog_sq_count": duplicate_count,
        "vm2t_2026": {
            "minimum": min(values),
            "median": statistics.median(values),
            "maximum": max(values),
        },
        "interpretive_status": (
            "extração tabular da fonte oficial; a associação espacial depende de "
            "validação entre SQ/CODLOG e as geometrias cadastrais do GeoSampa"
        ),
    }
    METADATA_PATH.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        f"PGV 2026: {len(rows)} linhas, {len(unique_sq)} SQ e "
        f"{len(unique_codlog)} CODLOG extraídos."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
