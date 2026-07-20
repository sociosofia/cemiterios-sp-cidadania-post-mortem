#!/usr/bin/env python3
"""Baixa e extrai o Apêndice VI — Tratamento de Ossada.

A fonte é a página oficial dos contratos de concessão da Prefeitura de São
Paulo. O PDF original é preservado fora do repositório por tamanho/licença; o
repositório guarda texto extraído, hash, URL e metadados para auditoria.
"""

from __future__ import annotations

import hashlib
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "contracts"
URL = (
    "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/governo/"
    "desestatizacao/cemiterios-publicos/contratos/"
    "10._Anexo_III___Apendice_VI___Tratamento_de_Ossada_v22.pdf"
)
PAGE = (
    "https://prefeitura.sp.gov.br/web/desestatizacao_projetos/w/cemiterios/"
    "edital_cemiterios/340988"
)


def fetch() -> bytes:
    request = urllib.request.Request(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0 cemiterios-sp-cidadania-post-mortem/1.0",
            "Referer": PAGE,
            "Accept": "application/pdf,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        return response.read()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pdf = fetch()
    if not pdf.startswith(b"%PDF"):
        raise RuntimeError("A resposta não parece ser um PDF válido.")

    reader = PdfReader(io.BytesIO(pdf))
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(f"\n\n===== PÁGINA {number} =====\n\n{text.strip()}\n")

    text_path = OUT / "anexo_iii_apendice_vi_tratamento_ossada.txt"
    text_path.write_text("".join(pages), encoding="utf-8")

    metadata = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_page": PAGE,
        "source_pdf": URL,
        "document": "Anexo III — Apêndice VI — Tratamento de Ossada",
        "bytes": len(pdf),
        "sha256": hashlib.sha256(pdf).hexdigest(),
        "pages": len(reader.pages),
        "text_output": str(text_path.relative_to(ROOT)),
        "preservation_note": (
            "O PDF original não é versionado no repositório. O hash permite conferir "
            "se futuras coletas correspondem ao mesmo arquivo."
        ),
    }
    (OUT / "anexo_iii_apendice_vi_tratamento_ossada_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Anexo de ossadas extraído: {len(reader.pages)} páginas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
