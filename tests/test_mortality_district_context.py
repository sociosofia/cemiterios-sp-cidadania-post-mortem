from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import pandas as pd

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "analyze_district_mortality_context.py"
spec = importlib.util.spec_from_file_location("district_mortality", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class DistrictMortalityTests(unittest.TestCase):
    def test_district_code_conversion(self) -> None:
        self.assertEqual(module.district_seade_code("355030801"), "80001")
        self.assertEqual(module.district_seade_code("355030896"), "80096")

    def test_age_group_mapping(self) -> None:
        self.assertEqual(module.death_age_group("35 a 39"), "30 a 39")
        self.assertEqual(module.death_age_group("90 e mais"), "70 e mais")
        self.assertIsNone(module.death_age_group("Idade Ignorada"))

    def test_direct_standardization(self) -> None:
        population = pd.DataFrame({
            "cod_distrito": ["80001", "80001"],
            "NM_DIST": ["Teste", "Teste"],
            "populacao_grupo_etario": [1000.0, 1000.0],
            "grupo_etario": ["00 a 04", "70 e mais"],
        })
        deaths = pd.DataFrame({
            "cod_distrito": ["80001", "80001"],
            "ano": [2022, 2022],
            "grupo_etario": ["00 a 04", "70 e mais"],
            "obito": [1.0, 9.0],
        })
        weights = pd.Series({"00 a 04": 0.5, "70 e mais": 0.5})
        result = module.direct_standardized_rates(deaths, population, weights, [2022], "teste")
        self.assertAlmostEqual(result.loc[0, "taxa_padronizada_teste_100mil"], 500.0)
        self.assertAlmostEqual(result.loc[0, "taxa_padronizada_menos70_teste_100mil"], 50.0)


if __name__ == "__main__":
    unittest.main()
