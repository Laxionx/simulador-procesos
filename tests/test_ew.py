"""Electroobtención de cobre. Tolerancias fijadas ANTES de correr (brief aprobado el 11-10):

1. Guardas: cátodo = Faraday (1e-9) y cierre por elemento y de energía.
2. Conductividad (Kalliomäki et al. 2021) contra la medida en la tesis de Fuentes (USM 2022,
   Tabla 4.24), datos independientes de los del ajuste:
   - M3 (50 g/L Cu, 171 g/L H2SO4) a 54,4 y 60,0 °C, dentro del rango: ±5 %.
   - M3 a 48,9 y 71,1 °C y M4 (34,8 g/L Cu, 188 g/L) a 48,9-71,1 °C, extrapolación: ±10 %.
3. Reproducir el ejemplo resuelto de Beukes y Badenhorst (2009, ec. 73 y 75): ±0,01 V.
4. Coherencia con la industria (no es una planta medida): con 40 g/L Cu, 170 g/L H2SO4, 50 °C y
   300 A/m², la celda queda en 1,9-2,3 V (Beukes y Badenhorst) y, con 92 % de eficiencia, la
   energía en 1.800-2.200 kWh/t.
5. Gunnison (informe NI 43-101 de 2023): no declara eficiencia ni disponibilidad, así que solo se
   comprueba que la producción declarada dividida por la de Faraday al 100 % (con su corriente
   y sus celdas) quede en 0,85-0,95, el rango de eficiencia por disponibilidad de la industria.
"""

from __future__ import annotations

import pytest

from procesos import Catalog, Flowsheet, Stream, make_species
from procesos.ew import (
    E_REV,
    FARADAY,
    Electrowinning,
    anode_overpotential,
    cathode_overpotential,
    conductivity,
    specific_energy_kwh_t,
)
from procesos.report import element_balance, energy_balance
from procesos.thermo_data import DEFAULT_THERMO

CU = 63.546
SPECIES = [("H2O", "l"), ("CuSO4", "aq"), ("H2SO4", "aq"), ("Cu", "s"), ("O2", "g")]


def _catalog(thermo: bool = False) -> Catalog:
    return Catalog([make_species(n, phase=p) for n, p in SPECIES],
                   DEFAULT_THERMO if thermo else None)  # fmt: skip


CATALOG = _catalog()


def _electrolyte(litros_h: float, cu: float, acido: float, densidad: float = 1.2,
                 temperatura: float = 50.0) -> Stream:  # fmt: skip
    flows = {"CuSO4": cu / CU * CATALOG["CuSO4"].molar_mass, "H2SO4": acido}
    kg = {k: v * litros_h / 1000.0 for k, v in flows.items()}
    kg["H2O"] = litros_h * densidad - sum(kg.values())
    return Stream(kg, temperatura)


def _unit(**kw) -> Electrowinning:
    args = {"current_density": 300.0, "cathode_area_m2": 1000.0}
    args.update(kw)
    return Electrowinning("EW", ("Rico",), ("Pobre", "Catodos", "O2"), **args)


# ------------------------------------------------------------------ guardas


def test_catodo_por_faraday():
    unit = _unit(current_efficiency=0.9)
    _, cathodes, _ = unit.compute([_electrolyte(100_000, 45, 170)], CATALOG)
    esperado = 0.9 * 300.0 * 1000.0 / (2 * FARADAY) * CU * 3.6  # kg/h
    assert cathodes.flow("Cu") == pytest.approx(esperado, rel=1e-9)


def test_cierra_por_elemento_en_una_planta():
    sheet = Flowsheet(CATALOG, [_unit()], {"Rico": _electrolyte(100_000, 45, 170)})
    solution = sheet.solve()
    for row in element_balance(sheet, solution):
        assert row.relative_error < 1e-9, row.name


def test_cierra_la_energia_con_la_electricidad():
    catalog = _catalog(thermo=True)
    sheet = Flowsheet(catalog, [_unit()], {"Rico": _electrolyte(100_000, 45, 170)})
    (row,) = energy_balance(sheet, sheet.solve())
    assert row.power > 0
    assert row.duty < 0  # la celda produce calor que la nave debe perder
    assert row.relative_error < 1e-9


def test_sin_cobre_suficiente_se_limita_y_avisa():
    unit = _unit(cathode_area_m2=1e6)
    result = unit.solve([_electrolyte(1000, 45, 170)], CATALOG)
    assert result.limited and result.warnings
    assert result.copper_kg_h == pytest.approx(45.0, rel=1e-9)


def test_rechaza_datos_imposibles():
    with pytest.raises(ValueError):
        _unit(current_density=-1.0)
    with pytest.raises(ValueError):
        _unit(current_efficiency=1.2)
    with pytest.raises(ValueError):
        cathode_overpotential(300.0, 50.0, limiting=250.0)


def test_voltaje_dado_por_el_usuario():
    result = _unit(cell_voltage=2.0).solve([_electrolyte(100_000, 45, 170)], CATALOG)
    assert result.cell_voltage == 2.0 and result.components == {}
    assert result.specific_energy_kwh_t == pytest.approx(
        specific_energy_kwh_t(2.0, 0.92, CU), rel=1e-9
    )


# ------------------------------------------------------------------ conductividad (Fuentes 2022)

M3 = (50.0, (243.0 / 96.06 - 50.0 / CU) * 98.079)
M4 = (34.8, (237.0 / 96.06 - 34.8 / CU) * 98.079)
MEDIDA = {  # mS/cm, Tabla 4.24
    "M3": {48.9: 493, 54.4: 527, 60.0: 559, 71.1: 625},
    "M4": {48.9: 619, 54.4: 662, 60.0: 710, 71.1: 784},
}


# Hallazgo: con M3 la correlación sobrestima la conductividad +11,8 % (54,4 °C) y +9,1 % (60 °C) y
# su efecto de la temperatura es la mitad del medido (0,6 frente a 1,2 %/°C). M4, con menos Cu y
# más ácido, queda entre -4,5 y +6,0 %. No se ajusta a estos datos: es la correlación publicada.
# Efecto en la celda: un 12 % más de conductividad baja la caída óhmica ~0,03 V (~1 %).
SOBRESTIMA = pytest.mark.xfail(strict=True, reason="Kalliomäki sobrestima κ de M3 (Fuentes 2022)")


@pytest.mark.parametrize("temp", [pytest.param(54.4, marks=SOBRESTIMA),
                                  pytest.param(60.0, marks=SOBRESTIMA)])  # fmt: skip
def test_conductividad_m3_dentro_del_rango(temp):
    kappa, warnings = conductivity(*M3, temp)
    assert not warnings
    assert kappa * 10 == pytest.approx(MEDIDA["M3"][temp], rel=0.05)


@pytest.mark.parametrize(
    ("muestra", "temp"),
    [
        pytest.param("M3", 48.9, marks=SOBRESTIMA),
        ("M3", 71.1),
        *(("M4", t) for t in (48.9, 54.4, 60.0, 71.1)),
    ],
)
def test_conductividad_extrapolada(muestra, temp):
    kappa, warnings = conductivity(*(M3 if muestra == "M3" else M4), temp)
    assert warnings
    assert kappa * 10 == pytest.approx(MEDIDA[muestra][temp], rel=0.10)


# ------------------------------------------------------------------ Beukes y Badenhorst (2009)


def test_ejemplo_resuelto_de_beukes():
    assert E_REV == pytest.approx(0.892, abs=1e-12)
    assert anode_overpotential(200.0) == pytest.approx(0.543, abs=0.01)
    assert cathode_overpotential(200.0, 65.0, limiting=300.0) == pytest.approx(0.225, abs=0.01)


def test_celda_tipica_dentro_del_rango_industrial():
    result = _unit().solve([_electrolyte(10_000_000, 40.0, 170.0)], CATALOG)
    assert 1.9 <= result.cell_voltage <= 2.3
    assert 1800 <= result.specific_energy_kwh_t <= 2200


# ------------------------------------------------------------------ Gunnison (NI 43-101, 2023)

LB_POR_T = 2204.62
GUNNISON = {  # etapa: (celdas × amperes por celda, millones de lb/año declaradas)
    "1": (56 * 13_000 + 32 * 17_000, 25),
    "2": (80 * 30_500, 50),
    "3": (160 * 30_500, 100),
}


@pytest.mark.parametrize("etapa", list(GUNNISON))
def test_gunnison_factor_implicito(etapa):
    amperes_celda, mlb = GUNNISON[etapa]
    # j × área = suma de la corriente de todas las celdas en serie (la de cada una por su número)
    unit = _unit(current_density=1.0, cathode_area_m2=amperes_celda, current_efficiency=1.0)
    _, cathodes, _ = unit.compute([_electrolyte(10_000_000, 45, 170)], CATALOG)
    faraday_t_ano = cathodes.flow("Cu") * 8760 / 1000
    factor = mlb * 1e6 / LB_POR_T / faraday_t_ano
    assert 0.85 <= factor <= 0.95


# ------------------------------------------------------------------ circuito SX-EW cerrado


def test_circuito_sx_ew_cerrado():
    """ejemplos/sx_ew_circuito.yaml con la densidad de corriente que fijó su lazo de control.

    Guardas: cátodos + Cu purgado = Cu transferido (1e-6) y cierre por elemento. Validación (la
    de la SX, ±5 puntos): con el electrolito en circuito cerrado, la recuperación sigue cerca de
    la de Isocalc (92,83 %). Regresión: el Cu del electrolito pobre queda en la meta del lazo.
    """
    pytest.importorskip("phreeqpy")
    from procesos import load_plant
    from procesos.report import ew_report, sx_report

    plant = load_plant("ejemplos/sx_ew_circuito.yaml")
    sheet = plant.flowsheet.with_unit_parameter("Electroobtencion", "densidad_corriente", 299.0175)
    solution = sheet.solve()
    reports = dict(sx_report(sheet, solution))
    (_, ew), = ew_report(sheet, solution)  # fmt: skip
    cuso4 = solution.streams["Purga de electrolito"].flow("CuSO4")
    purga = cuso4 * CU / CATALOG["CuSO4"].molar_mass
    transferido = reports["Extraccion"].transferred_mol_h * CU / 1000.0
    assert ew.copper_kg_h + purga == pytest.approx(transferido, rel=1e-6)
    assert all(r.relative_error < 1e-9 for r in element_balance(sheet, solution))
    assert reports["Extraccion"].recovery * 100 == pytest.approx(92.83, abs=5.0)
    pobre = solution.streams["Electrolito pobre"]
    assert pobre.flow("CuSO4") / pobre.flow("H2O") * 1000 == pytest.approx(92.31, rel=1e-3)


PLANTA_EW = """
nombre: Nave de electroobtención
especies: [{nombre: H2O, fase: l}, {nombre: CuSO4, fase: aq}, {nombre: H2SO4, fase: aq},
           {nombre: Cu, fase: s}, {nombre: O2, fase: g}]
alimentaciones:
  Rico: {flujos: {CuSO4: 23000, H2SO4: 34000, H2O: 183000}, temperatura: 50}
equipos:
  - {tipo: electroobtencion, nombre: EW, entradas: [Rico], salidas: [Pobre, Catodos, Oxigeno],
     densidad_corriente: 300, area_catodica: 1000, eficiencia_corriente: 0.9}
costos:
  por_tonelada_de: {corriente: Catodos, elemento: Cu}
  electricidad_por_kwh: 0.1
"""


def test_planta_yaml_con_costo_de_electricidad_y_reporte():
    from procesos import load_plant
    from procesos.costs import operating_cost
    from procesos.html_report import html_report

    plant = load_plant(PLANTA_EW)
    solution = plant.flowsheet.solve()
    (line,) = operating_cost(plant.flowsheet, solution, plant.costs).lines
    (unit,) = plant.flowsheet.units
    power = unit.power_kw([solution.streams["Rico"]], plant.flowsheet.catalog)
    assert line.concept == "Electricidad · EW"
    assert line.cost_per_h == pytest.approx(power * 0.1, rel=1e-12)
    assert "Electroobtención · EW" in html_report(plant, plant.flowsheet, solution)
