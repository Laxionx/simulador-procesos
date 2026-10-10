"""Los 3 casos de verificación de la fase 1 (detalle de las cuentas en docs/casos-validacion.md).

Cada caso compara contra un resultado calculado APARTE del simulador: una solución analítica o un
cálculo a mano con su propia tabla de pesos atómicos. Si el simulador se equivoca, fallan.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from procesos import load_plant, solve_with_controllers
from procesos.report import worst_closure

EXAMPLES = Path(__file__).resolve().parents[1] / "ejemplos"


def test_caso_1_reciclo_coincide_con_la_solucion_exacta() -> None:
    plant = load_plant(EXAMPLES / "reciclo_simple.yaml")
    solution = plant.flowsheet.solve()
    s = {"SiO2": 0.6, "H2O": 0.2}
    feed = {"SiO2": 100.0, "H2O": 50.0}
    r = 0.7
    for species in feed:
        mixed = feed[species] / (1.0 - r * (1.0 - s[species]))
        expected = {
            "Mezcla": mixed,
            "Producto": s[species] * mixed,
            "Reciclo": r * (1.0 - s[species]) * mixed,
            "Purga": (1.0 - r) * (1.0 - s[species]) * mixed,
        }
        for stream, value in expected.items():
            assert solution.streams[stream].flow(species) == pytest.approx(
                value, rel=1e-9, abs=1e-12
            )
    # En estado estacionario todo lo que entra sale por el producto o la purga.
    for species, value in feed.items():
        out = solution.streams["Producto"].flow(species) + solution.streams["Purga"].flow(species)
        assert out == pytest.approx(value, rel=1e-12)


# Pesos atómicos tipeados aquí, independientes de procesos/elements.py.
CU, OX, H, S, CA, C = 63.546, 15.999, 1.008, 32.06, 40.078, 12.011


def test_caso_2_lixiviacion_coincide_con_el_calculo_a_mano() -> None:
    m_cuo = CU + OX
    m_h2so4 = 2 * H + S + 4 * OX
    m_cuso4 = CU + S + 4 * OX
    m_h2o = 2 * H + OX
    m_caco3 = CA + C + 3 * OX
    m_caso4 = CA + S + 4 * OX
    m_co2 = C + 2 * OX

    cu_reacted = 0.90 * 1500.0 / m_cuo  # kmol/h de CuO que reaccionan
    caco3_reacted = 1.0 * 800.0 / m_caco3
    water_out = 150000.0 + (cu_reacted + caco3_reacted) * m_h2o
    free_acid = 5.0 / 1000.0 * water_out  # 5 g de H2SO4 por kg de agua
    acid_feed = (cu_reacted + caco3_reacted) * m_h2so4 + free_acid

    plant = load_plant(EXAMPLES / "lixiviacion_oxidos_cu.yaml")
    result = solve_with_controllers(plant.flowsheet, plant.controllers)
    discharge = result.solution.streams["Descarga"]

    assert result.values["Acidez libre"] == pytest.approx(acid_feed, rel=1e-6)
    assert discharge.flow("H2SO4") == pytest.approx(free_acid, rel=1e-6)
    assert discharge.flow("H2O") == pytest.approx(water_out, rel=1e-9)
    assert discharge.flow("CuSO4") == pytest.approx(cu_reacted * m_cuso4, rel=1e-9)
    assert discharge.flow("CuO") == pytest.approx(0.10 * 1500.0, rel=1e-9)
    assert discharge.flow("CaCO3") == pytest.approx(0.0, abs=1e-9)
    assert discharge.flow("CaSO4") == pytest.approx(caco3_reacted * m_caso4, rel=1e-9)
    assert discharge.flow("CO2") == pytest.approx(caco3_reacted * m_co2, rel=1e-9)
    assert worst_closure(result.flowsheet, result.solution) < 1e-12


def test_caso_3_concentradora_cumple_reciclo_y_formula_de_dos_productos() -> None:
    plant = load_plant(EXAMPLES / "concentradora_cu.yaml")
    solution = plant.flowsheet.solve()
    feed = solution.streams["Mineral"]
    concentrate = solution.streams["Concentrado final"]
    tailing = solution.streams["Relave final"]

    rougher = {"CuFeS2": 0.92, "SiO2": 0.08, "H2O": 0.15}
    cleaner = {"CuFeS2": 0.95, "SiO2": 0.15, "H2O": 0.40}
    for species, rr in rougher.items():
        rc = cleaner[species]
        overall = rr * rc / (1.0 - rr * (1.0 - rc))
        assert concentrate.flow(species) / feed.flow(species) == pytest.approx(overall, rel=1e-9)

    # Fórmula de dos productos sobre sólidos secos (Wills y Finch, cap. 3).
    m_cufes2 = CU + 55.845 + 2 * S

    def solids(stream):
        return stream.flow("CuFeS2") + stream.flow("SiO2")

    def grade(stream):
        return stream.flow("CuFeS2") * CU / m_cufes2 / solids(stream)

    f, c, t = grade(feed), grade(concentrate), grade(tailing)
    assert solids(concentrate) / solids(feed) == pytest.approx((f - t) / (c - t), rel=1e-9)
    recovery_from_grades = c * (f - t) / (f * (c - t))
    assert recovery_from_grades == pytest.approx(
        concentrate.flow("CuFeS2") / feed.flow("CuFeS2"), rel=1e-9
    )
    assert worst_closure(plant.flowsheet, solution) < 1e-12
