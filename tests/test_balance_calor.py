"""Fase 2: balance de calor. Tolerancias fijadas ANTES de correr.

Datos (fuentes distintas a las del simulador cuando se puede):
  - Shomate del NIST vs tablas NIST-JANAF (CO2 y O2, 400-1000 K): ±0,3 % en h - h298.
  - Agua líquida vs IAPWS-95 (NIST WebBook, 1 atm, 5-95 °C): ±0,5 % en h(T) - h(25 °C).
  - Calcita y anhidrita vs las tablas del USGS: Cp ±0,3 % y h - h298 ±0,5 %.
  - Cuarzo y CuO del NIST vs las tablas del USGS (otra fuente): h - h298 ±1 %.
Motor:
  - Mezcla de agua a 20 y 80 °C: temperatura de IAPWS ±0,1 °C; cierre de energía 1e-9.
  - Reactor isotérmico a 25 °C: calor = Σ avance · ΔrH calculado a mano, ±1e-4 relativo.
  - Calentador: temperatura ⇄ calor ida y vuelta 1e-9; un lazo lleva la salida a 60 °C.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from procesos import (
    DEFAULT_THERMO,
    Catalog,
    Flowsheet,
    Heater,
    Mixer,
    Reaction,
    Reactor,
    Stream,
    load_plant,
    make_species,
    parse_equation,
    solve_with_controllers,
    stream_enthalpy,
)
from procesos.control import Controller, Goal, Manipulated
from procesos.report import energy_balance, worst_closure
from procesos.thermo import KELVIN

EXAMPLES = Path(__file__).resolve().parents[1] / "ejemplos"


def _record(formula: str, phase: str):
    return DEFAULT_THERMO.record(make_species(formula, phase=phase))


def _dh(formula: str, phase: str, temp_k: float) -> float:
    r = _record(formula, phase)
    return r.enthalpy(temp_k) - r.enthalpy(298.15)


# ---------------------------------------------------------------------- datos
JANAF = {  # h - h298 (kJ/mol), tablas C-095 y O-029 de NIST-JANAF
    ("CO2", "g"): {400: 4.003, 600: 12.907, 800: 22.806, 1000: 33.397},
    ("O2", "g"): {400: 3.025, 600: 9.244, 800: 15.835, 1000: 22.703},
}


@pytest.mark.parametrize("key", list(JANAF))
def test_shomate_reproduce_janaf(key):
    for temp, expected in JANAF[key].items():
        assert _dh(*key, temp) == pytest.approx(expected, rel=0.003), temp


IAPWS = {5: 21.1200, 20: 84.0073, 25: 104.920, 50: 209.418, 80: 335.055, 95: 398.102}  # kJ/kg
IAPWS_60 = 251.249


def test_agua_liquida_reproduce_iapws():
    m = make_species("H2O", phase="l").molar_mass  # kg/kmol = g/mol
    for t_c, h in IAPWS.items():
        if t_c == 25:
            continue
        ours = _dh("H2O", "l", t_c + KELVIN) / m * 1000.0  # kJ/kg
        assert ours == pytest.approx(h - IAPWS[25], rel=0.005), t_c


# Robie y Hemingway (1995). Cp tabulado y (HT - H298)/T; en el texto extraído del PDF la
# columna (HT - H298)/T viene corrida una fila: se ubicó integrando el Cp de la misma tabla.
USGS = {
    ("CaCO3", "s"): {
        "cp": {298.15: 83.47, 400: 97.00, 500: 104.55, 700: 114.16, 1000: 124.48, 1200: 130.53},
        "h_t": {400: 23.18, 500: 38.75, 600: 50.18, 800: 66.15, 1000: 77.17, 1200: 85.57},
    },
    ("CaSO4", "s"): {
        "cp": {298.15: 101.23, 400: 116.68, 600: 135.03, 800: 147.55, 1000: 160.04},
        "h_t": {400: 27.87, 500: 46.74, 700: 71.90, 900: 88.71, 1000: 95.52},
    },
}


@pytest.mark.parametrize("key", list(USGS))
def test_minerales_del_usgs(key):
    r = _record(*key)
    for temp, cp in USGS[key]["cp"].items():
        assert r.cp(temp) == pytest.approx(cp, rel=0.003), temp
    for temp, h_over_t in USGS[key]["h_t"].items():
        assert _dh(*key, temp) * 1000.0 / temp == pytest.approx(h_over_t, rel=0.005), temp


CRUZADO = {  # tablas del USGS (h - h298)/T, frente a los Shomate del NIST
    ("SiO2", "s"): {400: 12.52, 500: 21.34, 600: 28.18, 700: 33.80, 800: 38.58},
    ("CuO", "s"): {400: 11.47, 500: 18.83, 600: 24.04, 800: 31.02, 1000: 35.64},
}


@pytest.mark.parametrize("key", list(CRUZADO))
def test_nist_y_usgs_coinciden(key):
    for temp, h_over_t in CRUZADO[key].items():
        assert _dh(*key, temp) * 1000.0 / temp == pytest.approx(h_over_t, rel=0.01), temp


# ---------------------------------------------------------------------- motor
def _water_catalog() -> Catalog:
    return Catalog([make_species("H2O", phase="l")], DEFAULT_THERMO)


def test_mezcla_de_agua_da_la_temperatura_de_iapws():
    catalog = _water_catalog()
    feeds = {"Fria": Stream({"H2O": 1000.0}, 20.0), "Caliente": Stream({"H2O": 1000.0}, 80.0)}
    sheet = Flowsheet(catalog, [Mixer("Cajón", ("Fria", "Caliente"), ("Mezcla",))], feeds)
    solution = sheet.solve()
    # IAPWS: h = (84,0073 + 335,055)/2 = 209,531 kJ/kg -> 50,027 °C (entre 50 y 55 °C)
    expected = 50.0 + (209.531 - 209.418) / (230.329 - 209.418) * 5.0
    assert solution.streams["Mezcla"].temperature == pytest.approx(expected, abs=0.1)
    (row,) = energy_balance(sheet, solution)
    assert row.duty == 0.0 and row.relative_error < 1e-9


# ΔfH° (kJ/mol) tipeados aquí, de las mismas fuentes: JANAF, CODATA y USGS.
DFH = {
    "CuO": -156.0632,
    "H2SO4": -909.34,
    "CuSO4": 64.9 - 909.34,
    "H2O": -285.8304,
    "CaCO3": -1207.4,
    "CaSO4": -1434.4,
    "CO2": -393.5224,
}


def _leach_catalog() -> Catalog:
    phases = {
        "CuO": "s",
        "CaCO3": "s",
        "SiO2": "s",
        "H2SO4": "aq",
        "H2O": "l",
        "CuSO4": "aq",
        "CaSO4": "s",
        "CO2": "g",
    }
    return Catalog([make_species(n, phase=p) for n, p in phases.items()], DEFAULT_THERMO)


def _leach_reactor(temperature: float | None) -> Reactor:
    eq1 = "CuO + H2SO4 -> CuSO4 + H2O"
    eq2 = "CaCO3 + H2SO4 -> CaSO4 + H2O + CO2"
    return Reactor(
        "Lixiviación",
        ("Pulpa",),
        ("Descarga",),
        (
            Reaction(parse_equation(eq1), "CuO", 0.9, eq1),
            Reaction(parse_equation(eq2), "CaCO3", 1.0, eq2),
        ),
        temperature,
    )


def test_reactor_isotermico_calor_de_reaccion_a_mano():
    catalog = _leach_catalog()
    feed = Stream({"CuO": 1500.0, "CaCO3": 800.0, "H2SO4": 3000.0, "H2O": 150000.0}, 25.0)
    reactor = _leach_reactor(25.0)
    duty = reactor.heat_duty([feed], catalog)
    xi_cu = 0.9 * 1500.0 / catalog["CuO"].molar_mass  # kmol/h
    xi_ca = 800.0 / catalog["CaCO3"].molar_mass
    dr_cu = DFH["CuSO4"] + DFH["H2O"] - DFH["CuO"] - DFH["H2SO4"]
    dr_ca = DFH["CaSO4"] + DFH["H2O"] + DFH["CO2"] - DFH["CaCO3"] - DFH["H2SO4"]
    expected = (xi_cu * dr_cu + xi_ca * dr_ca) / 3.6  # kmol/h · kJ/mol -> kW
    assert duty == pytest.approx(expected, rel=1e-4)
    assert duty < 0  # la lixiviación del CuO libera calor: hay que retirarlo para seguir a 25 °C


def test_reactor_adiabatico_cierra_y_calienta():
    catalog = _leach_catalog()
    feed = Stream({"CuO": 1500.0, "CaCO3": 800.0, "H2SO4": 3000.0, "H2O": 150000.0}, 25.0)
    sheet = Flowsheet(catalog, [_leach_reactor(None)], {"Pulpa": feed})
    solution = sheet.solve()
    (row,) = energy_balance(sheet, solution)
    assert row.duty == 0.0 and row.relative_error < 1e-9
    isothermal = _leach_reactor(25.0).heat_duty([feed], catalog)
    out = solution.streams["Descarga"]
    heat_capacity = sum(  # kW/K a 25 °C
        flow / catalog[n].molar_mass * DEFAULT_THERMO.record(catalog[n]).cp(298.15) / 3600.0
        for n, flow in out.flows.items()
    )
    assert out.temperature - 25.0 == pytest.approx(-isothermal / heat_capacity, rel=0.02)


def test_calentador_temperatura_y_calor_ida_y_vuelta():
    catalog = _water_catalog()
    feed = Stream({"H2O": 3600.0}, 20.0)
    heat = Heater("Intercambiador", ("Agua",), ("Caliente",), temperature=60.0)
    duty = heat.heat_duty([feed], catalog)
    back = Heater("Intercambiador", ("Agua",), ("Caliente",), duty_kw=duty)
    (out,) = back.compute([feed], catalog)
    assert out.temperature == pytest.approx(60.0, abs=1e-9)
    assert back.heat_duty([feed], catalog) == pytest.approx(duty)
    # 3,6 t/h = 1 kg/s de agua de 20 a 60 °C; IAPWS: h(60 °C) - h(20 °C) = H60 - 84,0073 kJ/kg
    assert duty == pytest.approx(IAPWS_60 - 84.0073, rel=0.005)


def test_lazo_de_control_lleva_la_salida_a_60_grados():
    catalog = _water_catalog()
    sheet = Flowsheet(
        catalog,
        [Heater("Intercambiador", ("Agua",), ("Caliente",), duty_kw=10.0)],
        {"Agua": Stream({"H2O": 3600.0}, 20.0)},
    )
    controller = Controller(
        "Temperatura de salida",
        Manipulated("equipo", "Intercambiador", "calor_kw", 0.0, 300.0),
        Goal("Caliente", "temperatura", 60.0),
    )
    result = solve_with_controllers(sheet, [controller])
    assert result.solution.streams["Caliente"].temperature == pytest.approx(60.0, abs=1e-6)
    assert worst_closure(result.flowsheet, result.solution) < 1e-9


def test_planta_yaml_con_balance_de_calor_y_errores():
    plant = load_plant(EXAMPLES / "lixiviacion_con_calor.yaml")
    result = solve_with_controllers(plant.flowsheet, plant.controllers)
    assert worst_closure(result.flowsheet, result.solution) < 1e-9
    rows = {r.name: r for r in energy_balance(result.flowsheet, result.solution)}
    assert rows["Calentador"].duty > 0
    assert rows["Lixiviación"].duty == 0.0
    assert result.solution.streams["PLS"].temperature == pytest.approx(30.0)
    with pytest.raises(ValueError, match="Sin datos termodinámicos"):
        Catalog([make_species("CuFeS2")], DEFAULT_THERMO)
    with pytest.raises(ValueError, match="fuera del rango"):
        _record("CaSO4", "s").enthalpy(2000.0)
    with pytest.raises(ValueError, match="temperatura o calor"):
        Heater("X", ("a",), ("b",))
    with pytest.raises(ValueError, match="balance de calor"):
        Heater("X", ("a",), ("b",), duty_kw=1.0).compute(
            [Stream({"H2O": 1.0})], Catalog([make_species("H2O", phase="l")])
        )
    plain = Catalog([make_species("H2O", phase="l")])
    with pytest.raises(ValueError, match="balance de calor"):
        stream_enthalpy({"H2O": 1.0}, 25.0, plain)
