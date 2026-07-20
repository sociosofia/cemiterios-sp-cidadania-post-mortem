#!/usr/bin/env python3
"""Integra contexto socioeconômico distrital aos cemitérios da concessão.

Unidade de inferência: território onde o equipamento está localizado. O resultado
não identifica o perfil individual das pessoas sepultadas.
"""

from __future__ import annotations

import csv
import json
import math
import re
import statistics
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "ibge" / "distritos_sp"
PROCESSED = ROOT / "data" / "processed"
DOCS = ROOT / "docs"

CEMETERIES = PROCESSED / "cemiterios_contexto_administrativo.csv"
INCOME_GLOB = "renda_responsavel_*.csv"
RACE_GLOB = "cor_ou_raca_*.csv"

# Censo 2022 — população residente por cor ou raça.
RACE_COLUMNS = {
    "branca": "V01317",
    "preta": "V01318",
    "amarela": "V01319",
    "parda": "V01320",
    "indigena": "V01321",
}


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^A-Z0-9]+", "", text.upper())


def parse_number(value: object) -> float | None:
    text = str(value or "").strip()
    if not text or text in {"-", "X", "..."}:
        return None
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def single_match(pattern: str) -> Path:
    matches = sorted(RAW.glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"Esperado exatamente um arquivo para {pattern}; encontrados: {matches}")
    return matches[0]


def fmt_money(value: float | None) -> str:
    if value is None:
        return "—"
    return f"R$ {value:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%".replace(".", ",")


def median(values: list[float]) -> float | None:
    clean = [value for value in values if value is not None and math.isfinite(value)]
    return statistics.median(clean) if clean else None


def mean(values: list[float]) -> float | None:
    clean = [value for value in values if value is not None and math.isfinite(value)]
    return statistics.fmean(clean) if clean else None


def summarize(rows: list[dict]) -> dict:
    return {
        "n_equipamentos": len(rows),
        "n_distritos_unicos": len({row["distrito_ibge"] for row in rows}),
        "renda_mediana_distritos_media": mean([row["renda_mediana_responsavel"] for row in rows]),
        "renda_mediana_distritos_mediana": median([row["renda_mediana_responsavel"] for row in rows]),
        "renda_media_distritos_media": mean([row["renda_media_responsavel"] for row in rows]),
        "proporcao_preta_parda_media": mean([row["proporcao_preta_parda"] for row in rows]),
        "proporcao_preta_parda_mediana": median([row["proporcao_preta_parda"] for row in rows]),
    }


def summarize_unique_districts(rows: list[dict]) -> dict:
    unique = {}
    for row in rows:
        unique[row["distrito_ibge"]] = row
    summary = summarize(list(unique.values()))
    summary["unidade"] = "distrito_unico"
    return summary


def main() -> int:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)

    income_path = single_match(INCOME_GLOB)
    race_path = single_match(RACE_GLOB)
    income_rows = read_csv(income_path)
    race_rows = read_csv(race_path)
    cemetery_rows = read_csv(CEMETERIES)

    if len(income_rows) != 96 or len(race_rows) != 96:
        raise RuntimeError(
            f"A integração exige 96 distritos; renda={len(income_rows)}, raça={len(race_rows)}"
        )

    income_by_name = {normalize(row["NM_DIST"]): row for row in income_rows}
    race_by_name = {normalize(row["NM_DIST"]): row for row in race_rows}

    district_output = []
    for district_key, income in income_by_name.items():
        race = race_by_name.get(district_key)
        if not race:
            raise RuntimeError(f"Distrito sem correspondência no arquivo de cor ou raça: {income['NM_DIST']}")
        race_values = {name: parse_number(race.get(column)) or 0 for name, column in RACE_COLUMNS.items()}
        classified_total = sum(race_values.values())
        black_brown = race_values["preta"] + race_values["parda"]
        district_output.append(
            {
                "cd_dist": income["CD_DIST"],
                "distrito_ibge": income["NM_DIST"],
                "renda_media_responsavel": parse_number(income.get("V06004")),
                "renda_mediana_responsavel": parse_number(income.get("V06006")),
                "populacao_branca": race_values["branca"],
                "populacao_preta": race_values["preta"],
                "populacao_amarela": race_values["amarela"],
                "populacao_parda": race_values["parda"],
                "populacao_indigena": race_values["indigena"],
                "populacao_categorias_raca": classified_total,
                "proporcao_preta_parda": black_brown / classified_total if classified_total else None,
            }
        )

    district_by_name = {normalize(row["distrito_ibge"]): row for row in district_output}
    cemetery_output = []
    unmatched = []
    for cemetery in cemetery_rows:
        district = district_by_name.get(normalize(cemetery["distrito_principal"]))
        if not district:
            unmatched.append(cemetery["distrito_principal"])
            continue
        category = cemetery.get("categoria_tarifaria", "").strip()
        is_crematorium = cemetery["id_equipamento"].startswith("crem_")
        cemetery_output.append(
            {
                **cemetery,
                **district,
                "categoria_tarifaria": int(category) if category else None,
                "destino_gratuidade_hipossuficiencia": cemetery[
                    "destino_gratuidade_hipossuficiencia"
                ].lower()
                == "true",
                "tipo_analitico": "crematorio" if is_crematorium else "cemiterio",
                "nota_inferencia": (
                    "Indicadores do distrito onde se localiza o equipamento; "
                    "não representam o perfil individual das pessoas sepultadas."
                ),
            }
        )
    if unmatched:
        raise RuntimeError(f"Distritos dos cemitérios sem correspondência IBGE: {sorted(set(unmatched))}")

    def write_rows(path: Path, rows: list[dict]) -> None:
        if not rows:
            raise RuntimeError(f"Nenhuma linha para gravar em {path}")
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    write_rows(PROCESSED / "distritos_indicadores_sociais.csv", district_output)
    write_rows(PROCESSED / "cemiterios_contexto_socioeconomico.csv", cemetery_output)

    burial = [row for row in cemetery_output if row["tipo_analitico"] == "cemiterio"]
    free = [row for row in burial if row["destino_gratuidade_hipossuficiencia"]]
    other = [row for row in burial if not row["destino_gratuidade_hipossuficiencia"]]
    by_category = defaultdict(list)
    for row in burial:
        by_category[str(row["categoria_tarifaria"])].append(row)

    summaries = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "unit": "cemiterio_associado_ao_distrito_de_maior_area_de_intersecao",
        "all_burial_cemeteries": summarize(burial),
        "free_burial_destinations": summarize(free),
        "other_burial_cemeteries": summarize(other),
        "free_burial_unique_districts": summarize_unique_districts(free),
        "other_unique_districts": summarize_unique_districts(other),
        "by_tariff_category": {category: summarize(rows) for category, rows in sorted(by_category.items())},
        "methodological_warning": (
            "O perfil distrital descreve a localização do equipamento. Não permite concluir, "
            "sem dados de origem e destino, o perfil socioeconômico individual dos usuários."
        ),
        "income_variables": {
            "V06004": "rendimento nominal médio mensal do responsável com rendimento",
            "V06006": "rendimento nominal mediano mensal do responsável com rendimento",
        },
        "race_variables": RACE_COLUMNS,
    }
    (PROCESSED / "resumo_estratos_renda_raca.json").write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    free_summary = summaries["free_burial_destinations"]
    other_summary = summaries["other_burial_cemeteries"]
    lines = [
        "# Contexto socioeconômico dos cemitérios — resultados preliminares",
        "",
        "## O que esta etapa mede",
        "",
        "A análise associa cada equipamento ao distrito que contém a maior parcela de sua área e acrescenta indicadores do Censo 2022. Ela mede o **contexto territorial do cemitério**, não a renda ou a cor/raça das pessoas sepultadas.",
        "",
        "## Destinos gratuitos e demais cemitérios",
        "",
        "| Grupo | Equipamentos | Distritos únicos | Mediana distrital de renda (média entre equipamentos) | Mediana das rendas medianas distritais | Proporção preta+parda média |",
        "|---|---:|---:|---:|---:|---:|",
        (
            f"| Destinos gratuitos | {free_summary['n_equipamentos']} | {free_summary['n_distritos_unicos']} | "
            f"{fmt_money(free_summary['renda_mediana_distritos_media'])} | "
            f"{fmt_money(free_summary['renda_mediana_distritos_mediana'])} | "
            f"{fmt_pct(free_summary['proporcao_preta_parda_media'])} |"
        ),
        (
            f"| Demais cemitérios | {other_summary['n_equipamentos']} | {other_summary['n_distritos_unicos']} | "
            f"{fmt_money(other_summary['renda_mediana_distritos_media'])} | "
            f"{fmt_money(other_summary['renda_mediana_distritos_mediana'])} | "
            f"{fmt_pct(other_summary['proporcao_preta_parda_media'])} |"
        ),
        "",
        "## Por estrato tarifário",
        "",
        "| Estrato | Cemitérios | Renda mediana distrital média | Proporção preta+parda média |",
        "|---:|---:|---:|---:|",
    ]
    for category, summary in sorted(summaries["by_tariff_category"].items()):
        lines.append(
            f"| {category} | {summary['n_equipamentos']} | "
            f"{fmt_money(summary['renda_mediana_distritos_media'])} | "
            f"{fmt_pct(summary['proporcao_preta_parda_media'])} |"
        )
    lines.extend(
        [
            "",
            "## Cautela obrigatória",
            "",
            "O perfil do distrito não equivale ao perfil dos mortos ou de suas famílias. A hipótese de distribuição social efetiva dos sepultamentos exige registros anonimizados de residência/origem, modalidade tarifária e cemitério de destino.",
            "",
            "As médias desta página são descritivas, com poucos equipamentos por grupo. Não constituem teste causal nem estimativa individual.",
        ]
    )
    (DOCS / "RESULTADOS_SOCIOECONOMICOS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Contexto socioeconômico distrital integrado aos cemitérios.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
