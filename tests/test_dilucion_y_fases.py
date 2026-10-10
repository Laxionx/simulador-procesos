"""B1: calor de dilución del H2SO4 y cambio de fase del agua. Tolerancias fijadas ANTES de correr:

- ΔfH(H2SO4 en n H2O) = ΔfH∞ (CODATA) + ΦL (Wu y Young 1980) vs NBS 1982, n de 7 a 150 000
  (fuera del tramo donde el modelo usa la propia NBS): ±0,15 kJ/mol.
- L2 = ΦL + (√m/2) dΦL/d√m vs la columna L2 de Wu y Young: ±3 %.
- Calor de disolución del H2SO4 líquido hasta 100 H2O vs NBS: ±0,5 %.
- Ajustes propios a JANAF (H2SO4 líquido, vapor de agua) vs la columna H - H298: ±0,3 %.
- Saturación IAPWS-IF97: valores de verificación de la norma 1e-8; vs IAPWS-95 (NIST) ±0,05 %.
- Calor latente (vapor ideal JANAF menos líquido NIST) vs IAPWS-95: ±1,5 %.
- Evaporador: cierre de energía 1e-9; mitad evaporada con el calor calculado a mano 1e-6.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from procesos import (
    DEFAULT_THERMO,
    Catalog,
    Evaporator,
    Flowsheet,
    Stream,
    make_species,
    stream_enthalpy,
)
from procesos.report import energy_balance
from procesos.saturation import psat_kpa, tsat_c
from procesos.thermo import KELVIN
from procesos.thermo_data import WATER_MOL_PER_KG

ACID_AQ = DEFAULT_THERMO.record(make_species("H2SO4", phase="aq"))
ACID_L = DEFAULT_THERMO.record(make_species("H2SO4", phase="l"))
STEAM = DEFAULT_THERMO.record(make_species("H2O", phase="g"))
WATER = DEFAULT_THERMO.record(make_species("H2O", phase="l"))

# NBS 1982 (Wagman et al.), «H2SO4 in n H2O», ΔfH en kJ/mol (pp. 2-58 y 2-59)
NBS = {
    7.0: -876.372, 8.0: -878.075, 9.0: -879.435, 10: -880.527, 12: -882.134, 15: -883.623,
    20: -884.916, 25: -885.585, 30: -885.983, 40: -886.460, 50: -886.774, 75: -887.292,
    100: -887.636, 150: -888.188, 200: -888.627, 300: -889.372, 400: -889.974, 500: -890.493,
    700: -891.359, 1000: -892.343, 2000: -894.476, 5000: -897.970, 10000: -900.752,
    20000: -903.326, 50000: -906.024, 150000: -907.807,
}  # fmt: skip


# Hallazgo: con n = 7 (m = 7,9) Wu y Young y la NBS difieren en 0,18 kJ/mol: fuera de ±0,15.
@pytest.mark.parametrize(
    "n",
    [
        pytest.param(n, marks=pytest.mark.xfail(strict=True, reason="Wu-Young vs NBS cerca de m=8"))
        if n == 7.0
        else n
        for n in NBS
    ],
)
def test_entalpia_del_acido_diluido_vs_nbs(n):
    ours = ACID_AQ.dfh298 + ACID_AQ.apparent(WATER_MOL_PER_KG / n)
    assert ours == pytest.approx(NBS[n], abs=0.15)


# Wu y Young (1980), Tabla 5, columna L2 (cal/mol)
L2 = {
    0.10: 3540, 0.20: 4605, 0.30: 4990, 0.40: 5184, 0.50: 5303, 0.60: 5382, 0.80: 5506,
    1.00: 5634, 1.20: 5822, 1.40: 6086, 1.60: 6500, 1.80: 7056, 2.00: 7737, 2.20: 8536,
    2.40: 9366, 2.60: 10196,
}  # fmt: skip


@pytest.mark.parametrize("x", list(L2))
def test_entalpia_parcial_derivada_de_phi_l(x):
    assert ACID_AQ.apparent.partial(x**2) == pytest.approx(L2[x] * 4.184e-3, rel=0.03)


def test_calor_de_disolucion_del_acido_concentrado():
    ours = ACID_AQ.dfh298 + ACID_AQ.apparent(WATER_MOL_PER_KG / 100) - ACID_L.dfh298
    assert ours == pytest.approx(-887.636 - (-813.989), rel=0.005)


JANAF_ACID = {400: 15.112, 500: 31.903}
JANAF_STEAM = {200: -3.282, 400: 3.452, 500: 6.925, 600: 10.501, 700: 14.192}


def test_ajustes_a_janaf():
    for temp, h in JANAF_ACID.items():
        assert ACID_L.enthalpy(temp) - ACID_L.enthalpy(298.15) == pytest.approx(h, rel=0.003)
    assert ACID_L.cp(298.15) == pytest.approx(138.584, rel=0.003)
    for temp, h in JANAF_STEAM.items():
        assert STEAM.enthalpy(temp) - STEAM.enthalpy(298.15) == pytest.approx(h, rel=0.003)


# IAPWS-IF97, Tablas 35 y 36: valores de verificación de la norma
@pytest.mark.parametrize(("t_k", "p_mpa"), [(300, 0.353658941e-2), (500, 0.263889776e1),
                                              (600, 0.123443146e2)])  # fmt: skip
def test_if97_presion_de_saturacion(t_k, p_mpa):
    assert psat_kpa(t_k - KELVIN) / 1000 == pytest.approx(p_mpa, rel=1e-8)


@pytest.mark.parametrize(("p_mpa", "t_k"), [(0.1, 0.372755919e3), (1.0, 0.453035632e3),
                                              (10.0, 0.584149488e3)])  # fmt: skip
def test_if97_temperatura_de_saturacion(p_mpa, t_k):
    assert tsat_c(p_mpa * 1000) + KELVIN == pytest.approx(t_k, rel=1e-8)


# NIST WebBook (IAPWS-95): T (°C) -> (P kPa, h líquido, h vapor en kJ/kg)
IAPWS95 = {
    74.1740: (37.2809, 310.565, 2633.20),
    99.7263: (100.431, 418.011, 2675.14),
    102.219: (109.718, 428.531, 2679.06),
    150.208: (478.821, 633.075, 2746.17),
    200.689: (1577.46, 855.379, 2792.42),
}


@pytest.mark.parametrize("t_c", list(IAPWS95))
def test_presion_de_saturacion_vs_iapws95(t_c):
    assert psat_kpa(t_c) == pytest.approx(IAPWS95[t_c][0], rel=5e-4)


# Hallazgo: el vapor es gas ideal (JANAF). Cerca de 1 atm el calor latente sale a +0,6 % o menos;
# a 4,8 y 15,8 bar (150 y 200 °C) el vapor real se aparta del ideal: +1,8 % y +4,6 %.
VAPOR_REAL = pytest.mark.xfail(
    strict=True, reason="vapor real a presión: falta IAPWS-IF97 región 2"
)


@pytest.mark.parametrize(
    "t_c", [pytest.param(t, marks=VAPOR_REAL) if t > 120 else t for t in IAPWS95]
)
def test_calor_latente_vs_iapws95(t_c):
    _, h_l, h_v = IAPWS95[t_c]
    m = make_species("H2O", phase="l").molar_mass
    latent = (STEAM.enthalpy(t_c + KELVIN) - WATER.enthalpy(t_c + KELVIN)) / m * 1000
    assert latent == pytest.approx(h_v - h_l, rel=0.015)


def _catalog() -> Catalog:
    species = [make_species("H2O", phase="l"), make_species("Vapor", formula="H2O", phase="g")]
    return Catalog(species, DEFAULT_THERMO)


def test_evaporador_mitad_del_agua_con_calor_a_mano():
    catalog = _catalog()
    feed = Stream({"H2O": 3600.0}, 25.0)
    t_sat = tsat_c(101.325)
    h_in = stream_enthalpy(feed.flows, 25.0, catalog)
    h_half = stream_enthalpy({"H2O": 1800.0, "Vapor": 1800.0}, t_sat, catalog)
    unit = Evaporator("Evaporador", ("Agua",), ("Liquido", "Vapor"), h_half - h_in)
    sheet = Flowsheet(catalog, [unit], {"Agua": feed})
    solution = sheet.solve()
    assert solution.streams["Vapor"].flow("Vapor") == pytest.approx(1800.0, rel=1e-6)
    assert solution.streams["Liquido"].temperature == pytest.approx(t_sat)
    (row,) = energy_balance(sheet, solution)
    assert row.relative_error < 1e-9


def test_evaporador_sin_hervir_y_sobrecalentado():
    catalog = _catalog()
    feed = Stream({"H2O": 3600.0}, 25.0)
    liq, vap = Evaporator("E", ("A",), ("L", "V"), 100.0).compute([feed], catalog)
    assert vap.flow("Vapor") == 0.0 and 25.0 < liq.temperature < 99.0
    liq, vap = Evaporator("E", ("A",), ("L", "V"), 3000.0).compute([feed], catalog)
    assert vap.flow("Vapor") == pytest.approx(3600.0) and vap.temperature > 101.0
    low_p, _ = Evaporator("E", ("A",), ("L", "V"), 1000.0, pressure_kpa=20.0).compute(
        [feed], catalog
    )
    assert low_p.temperature == pytest.approx(tsat_c(20.0))  # a 20 kPa hierve a ~60 °C


def test_errores_del_evaporador_y_de_la_dilucion():
    plain = Catalog([make_species("H2O", phase="l"), make_species("V", formula="H2O", phase="g")])
    with pytest.raises(ValueError, match="balance de calor"):
        Evaporator("E", ("A",), ("L", "V")).compute([Stream({"H2O": 1.0})], plain)
    only_liquid = Catalog([make_species("H2O", phase="l")], DEFAULT_THERMO)
    with pytest.raises(ValueError, match="vapor"):
        Evaporator("E", ("A",), ("L", "V")).compute([Stream({"H2O": 1.0})], only_liquid)
    with pytest.raises(ValueError):
        Evaporator("E", ("A",), ("L",))
    acid = Catalog([make_species("H2SO4", phase="aq"), make_species("H2O", phase="l")],
                   DEFAULT_THERMO)  # fmt: skip
    with pytest.raises(ValueError, match="agua líquida"):
        stream_enthalpy({"H2SO4": 98.0}, 25.0, acid)
    with pytest.raises(ValueError, match="fuera de la tabla"):
        ACID_AQ.apparent(80.0)
    with pytest.raises(ValueError):
        psat_kpa(400.0)
    with pytest.raises(ValueError):
        tsat_c(0.1)
    unit = Evaporator("E", ("A",), ("L", "V"))
    assert unit.with_parameter("calor_kw", 5.0).duty_kw == 5.0
    assert unit.with_parameter("presion_kpa", 50.0).pressure_kpa == 50.0
    with pytest.raises(KeyError):
        unit.with_parameter("otro", 1.0)


def test_evaporar_solucion_acida_y_no_secarla():
    from procesos import load_plant

    plant = load_plant(Path(__file__).resolve().parents[1] / "ejemplos" / "evaporacion.yaml")
    solution = plant.flowsheet.solve()
    (row,) = energy_balance(plant.flowsheet, solution)
    assert row.relative_error < 1e-9
    concentrate = solution.streams["Concentrado"]
    assert solution.streams["Vahos"].flow("Vapor") > 0
    assert concentrate.temperature == pytest.approx(tsat_c(101.325))
    catalog = plant.flowsheet.catalog
    too_much = Evaporator("E", ("A",), ("L", "V"), 1e5)
    with pytest.raises(ValueError, match="datos de dilución"):
        too_much.compute([Stream({"H2O": 10000.0, "H2SO4": 500.0}, 40.0)], catalog)
