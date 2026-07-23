from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_seade_mortalidade as seade  # noqa: E402


class SeadeMortalityTest(unittest.TestCase):
    def test_portuguese_number_parser(self) -> None:
        self.assertEqual(seade.integer("1.708"), 1708)
        self.assertEqual(seade.num("1.708,5"), 1708.5)
        self.assertEqual(seade.num("7,87"), 7.87)
        self.assertIsNone(seade.num(""))

    def test_offline_pipeline_with_consistent_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "fixture"
            source.mkdir()

            self._write(
                source / "mortalidade_geral.csv",
                [
                    "cod_ibge", "ano", "obitos_0a14", "obitos_15a29",
                    "obitos_30a44", "obitos_45a59", "obitos_60e+",
                    "obitos_ignorado", "obitos_total", "pop_0a14",
                    "pop_15a29", "pop_30a44", "pop_45a59", "pop_60e+",
                    "pop_total", "mx_0a14", "mx_15a29", "mx_30a44",
                    "mx_45a59", "mx_60e+", "mx_total",
                ],
                [
                    ["3550308", 2024, 0, 1, 2, 3, 4, 0, 10, 100, 200, 200, 200, 300, 1000, 0, 5, 10, 15, "13,3", 10],
                    ["3500105", 2024, 1, 1, 1, 1, 1, 0, 5, 100, 100, 100, 100, 100, 500, 10, 10, 10, 10, 10, 10],
                    ["3500000", 2024, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, "", "", "", "", "", ""],
                ],
            )
            self._write(
                source / "obitosinfantis_periodo.csv",
                ["cod_ibge", "ano", "obitos menores de 1 Ano", "obitos menores de 7 dias", "obitos de 7 a 27 dias", "obitos de 28 dias a 364 dias", "nascidos vivos (por local de residência)"],
                [["3550308", 2024, 1, 1, 0, 0, 100]],
            )
            self._write(
                source / "obitosinfantis_principais_causas.csv",
                ["cod_ibge", "ano", "nascidos vivos", "perinatais", "malformação congenita", "doenças do aparelho respirtatorio", "infecciosas e parasitárias"],
                [["3550308", 2024, 100, 1, 0, 0, 0]],
            )
            self._write(
                source / "codigos_municipios_regioes.csv",
                ["cod_ibge", "municipio", "area_km", "cod_ra", "ra", "cod_rm", "rm", "cod_drs", "drs", "cod_r_saude", "r_saude"],
                [
                    ["3550308", "São Paulo", 1, "RA1", "RA", "RM1", "RM", "DRS1", "DRS", "RS1", "RS"],
                    ["3500105", "Município Teste", 1, "RA1", "RA", "RM1", "RM", "DRS1", "DRS", "RS1", "RS"],
                    ["3500000", "Sem especificação", 0, "", "", "", "", "", "", "", ""],
                ],
            )
            self._write(
                source / "obitos_gerais_esp_periodo.csv",
                ["codIBGE", "municipio", "ano", "obitos_gerais"],
                [
                    ["3550308", "São Paulo", 2024, 10],
                    ["3500105", "Município Teste", 2024, 5],
                    ["3500000", "Sem especificação", 2024, 1],
                ],
            )
            self._write(
                source / "obitos_sexo_idade_periodo.csv",
                ["codIBGE", "ano", "sexo", "idade", "obitos"],
                [
                    ["3550308", 2024, "Total", "Total", 10],
                    ["3500105", 2024, "Total", "Total", 5],
                    ["3500000", 2024, "Total", "Idade Igmorada", 1],
                ],
            )
            self._write(
                source / "obitos_esp_mes_ocorrencia_area_periodo.csv",
                ["ano", "codIBGE", "mes", "obitos"],
                [
                    [2024, "3550308", "Janeiro", 10],
                    [2024, "3500105", "Janeiro", 5],
                    [2024, "3500000", "Janeiro", 1],
                ],
            )
            self._write(
                source / "d_obitos_gerais_periodo.csv",
                ["cod_distrito", "periodos", "descricao_do_distrito", "obitos"],
                [["00001", 2024, "Distrito Teste", 10]],
            )
            self._write(
                source / "d_obitos_sexo_idade_periodo.csv",
                ["cod_distrito", "ano", "sexo", "Idade", "obito"],
                [["00001", 2024, "Total", "Total", 10]],
            )
            self._write(
                source / "d_obitos_meses_periodo.csv",
                ["cod_distrito", "ano", "mes", "obito"],
                [["00001", 2024, "Janeiro", 10]],
            )
            self._write(
                source / "obitos_mes_anoatual.csv",
                ["codibge", "ano", "mes", "obito"],
                [
                    ["3550308", 2025, "Janeiro", 11],
                    ["3500105", 2025, "Janeiro", 5],
                    ["3500000", 2025, "Janeiro", 1],
                ],
            )
            self._write(
                source / "msp_obitos_mes_anoatual.csv",
                ["cod_distrito", "ano", "mes", "obito"],
                [["00001", 2025, "Janeiro", 11]],
            )

            result = seade.main(["--offline-dir", str(source), "--root", str(root)])
            self.assertEqual(result, 0)

            state_path = root / "data/processed/seade_mortalidade_estado_ano.csv"
            quality_path = root / "data/raw/seade/mortalidade/quality_report.json"
            manifest_path = root / "data/raw/seade/mortalidade/manifest.json"
            self.assertTrue(state_path.exists())
            self.assertTrue(quality_path.exists())
            self.assertTrue(manifest_path.exists())

            with state_path.open(encoding="utf-8", newline="") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(int(row["obitos_total"]), 16)
            self.assertEqual(int(row["obitos_municipio_sp"]), 10)
            self.assertEqual(int(row["populacao_total"]), 1500)

            quality = json.loads(quality_path.read_text(encoding="utf-8"))
            self.assertEqual(quality["errors"], [])
            self.assertEqual(quality["checks"]["fontes_anuais"]["difference_count"], 0)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["resources"]["geral"]["acquisition"], "offline")
            self.assertEqual(manifest["resources"]["geral"]["rows"], 3)

    @staticmethod
    def _write(path: Path, fields: list[str], rows: list[list[object]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter=";", lineterminator="\n")
            writer.writerow(fields)
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
