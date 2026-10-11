"""Extracción por solventes (SX) de cobre. Tolerancias fijadas ANTES de correr.

Modelo: Cu²⁺ + 2 RH ⇌ CuR₂ + 2 H⁺ con Kex = D·[H⁺]²/[RH]² (Devi y Nayak 2014, J. SAIMM 114, 937,
ec. 3). [RH] es la oxima libre en mol/L. Su capacidad sale del factor de carga máxima del reactivo
(g/L de Cu por %v/v): 0,56 para el LIX 984N de Devi (cota inferior que exige su punto de 2,8 g/L
con 5 %v/v; ese punto queda fuera de la validación) y 0,52 para la mezcla 50/50 de Mitshabu. Con
esa convención, Kex = 5,05 es la media geométrica de los 8 puntos de su Tabla III (2,8 a 8,7).

Supuestos declarados:
- El H⁺ se calcula con la asociación ideal del HSO₄⁻ (pKa₂ 1,99). Si se conoce el pH medido de
  la alimentación acuosa, la constante se calibra con él (dato de entrada, no de salida).
- Embudos de laboratorio (Devi): etapas en equilibrio (eficiencia 1).
- Caso Isocalc (Mitshabu): eficiencias típicas de la patente US 7635457 (E1 92 %, E2 95 %) y
  S1 95 %. Las razones O/A no se publican: salen del balance de sus propios resultados.

Controles:
1. Kremser (isoterma lineal, eficiencia 1, orgánico sin cobre): x_N/x_0 = (S-1)/(S^(N+1)-1),
   S = m·O/A. Tolerancia 1e-9.
2. Cierre de elementos del equipo y de la planta: 1e-9. Con eficiencia 1 cada etapa cumple el
   equilibrio a 1e-9.
3. Devi, Figura 3 (un contacto O:A 1:1, 0,1 M Cu, pH inicial 3,95): Cu extraído con 10, 15, 20
   y 25 %v/v de 4,5; 5,6; 5,95 y 6,27 g/L (los tres primeros leídos del gráfico): ±15 %.
4. Devi, Tabla IV (2 etapas a contracorriente, O:A 3:4, 20 %v/v): orgánico cargado 8,4 g/L ±5 %;
   refino 0,03 g/L dentro de un factor 2; pH del refino 0,9 ± 0,2.
5. Devi, Tabla V (despojo en 3 etapas, O:A 3:1, H2SO4 15 %v/v = 270,5 g/L): electrolito
   25,1 g/L ±3 %; orgánico despojado ≤ 0,05 g/L (medido 0,002).
6. Mitshabu (SAIMM Copper-Cobalt 2023, Isocalc, 2E-1S, mezcla 50/50, 21 %v/v): recuperación
   92,83 % ± 5 puntos; transferencia neta 0,26 g/L por %v/v ±20 %; orgánico cargado al 78,6 % de
   la carga máxima ± 10 puntos.
"""

from __future__ import annotations

import math

import pytest

from procesos import Catalog, Flowsheet, Stream, make_species
from procesos.report import element_balance
from procesos.sx import KEX_LIX984N, SolventExtraction

CU, ACID, SO4 = 63.546, 98.079, 96.06
ORG_DENSITY = 0.81  # kg/L


def _catalog() -> Catalog:
    species = [
        make_species("H2O", phase="l"),
        make_species("CuSO4", phase="aq"),
        make_species("H2SO4", phase="aq"),
        make_species("NiSO4", phase="aq"),
        make_species("MgSO4", phase="aq"),
        make_species("RH", formula="C16H25NO2", phase="org"),
        make_species("CuR2", formula="Cu(C16H24NO2)2", phase="org"),
        make_species("Diluyente", formula="C12H26", phase="org"),
    ]
    return Catalog(species)


CATALOG = _catalog()


def _aqueous(litros_h: float, cu: float, acido: float = 0.0, otros: dict | None = None,
             densidad: float = 1.0) -> Stream:  # fmt: skip
    """Acuosa desde g/L: Cu como CuSO4, ácido libre como H2SO4, otros sulfatos en g/L de sal."""
    flows = {"CuSO4": cu / CU * CATALOG["CuSO4"].molar_mass, "H2SO4": acido}
    flows.update(otros or {})
    kg = {k: v * litros_h / 1000.0 for k, v in flows.items()}
    kg["H2O"] = litros_h * densidad - sum(kg.values())
    return Stream(kg)


def _organic(litros_h: float, vol_pct: float, cu: float, carga_maxima: float) -> Stream:
    """Orgánica desde %v/v y g/L de Cu cargado; la oxima total sale de la carga máxima."""
    oxima = 2.0 * carga_maxima * vol_pct / CU  # mol/L
    complejo = cu / CU  # mol/L
    kg = {
        "RH": (oxima - 2 * complejo) * litros_h * CATALOG["RH"].molar_mass / 1e3,
        "CuR2": complejo * litros_h * CATALOG["CuR2"].molar_mass / 1e3,
    }
    kg["Diluyente"] = litros_h * ORG_DENSITY - sum(kg.values())
    return Stream(kg)


def _unit(stages: int = 1, **kw) -> SolventExtraction:
    return SolventExtraction("SX", ("A", "O"), ("Refino", "Cargado"), stages=stages, **kw)


# ------------------------------------------------------------------ 1. Kremser


@pytest.mark.parametrize("n", [1, 2, 3, 4])
@pytest.mark.parametrize("s", [0.5, 1.5, 3.0])
def test_contracorriente_igual_a_kremser(n, s):
    a, o = 100.0, 80.0
    m = s * a / o
    unit = _unit(stages=n, distribution=m)
    feed = _aqueous(a, 5.0)
    barren = _organic(o, 20, 0.0, 0.56)
    result = unit.solve([feed, barren], CATALOG)
    expected = (s - 1.0) / (s ** (n + 1) - 1.0)
    assert result.raffinate_g_l / 5.0 == pytest.approx(expected, rel=1e-9)


# ------------------------------------------------------------------ 2. Cierre y equilibrio


def test_cierre_de_elementos_y_equilibrio_por_etapa():
    unit = SolventExtraction("SX", ("PLS", "Org"), ("Refino", "Cargado"), stages=3)
    sheet = Flowsheet(CATALOG, [unit], {"PLS": _aqueous(100, 6.0, 5.0),
                                        "Org": _organic(110, 20, 1.0, 0.56)})  # fmt: skip
    solution = sheet.solve()
    for row in element_balance(sheet, solution):
        assert row.relative_error < 1e-9, row.name
    result = unit.solve([solution.streams["PLS"], solution.streams["Org"]], CATALOG)
    for x, y, ph, free in zip(result.aqueous_mol_l, result.organic_mol_l, result.ph,
                              result.free_extractant_mol_l, strict=True):  # fmt: skip
        assert y * 10 ** (-2 * ph) == pytest.approx(KEX_LIX984N * x * free**2, rel=1e-9)


# ------------------------------------------------------------------ 3. Devi, Figura 3

FIGURA_3 = {10: 4.5, 15: 5.6, 20: 5.95, 25: 6.27}  # %v/v -> g/L de Cu extraído


@pytest.mark.parametrize("vol_pct", list(FIGURA_3))
def test_devi_un_contacto_segun_concentracion_de_extractante(vol_pct):
    feed = _aqueous(100, 6.35, acido=0.5 * 10**-3.95 * ACID, otros={})
    result = _unit().solve([feed, _organic(100, vol_pct, 0.0, 0.56)], CATALOG)
    assert result.loaded_g_l == pytest.approx(FIGURA_3[vol_pct], rel=0.15)


# ------------------------------------------------------------------ 4 y 5. Devi, Tablas IV y V


def test_devi_extraccion_dos_etapas_a_contracorriente():
    ni = {"NiSO4": 0.58 / 58.693 * 154.75}
    feed = _aqueous(80, 6.35, acido=0.5 * 10**-3.95 * ACID, otros=ni)
    result = _unit(stages=2).solve([feed, _organic(60, 20, 0.0, 0.56)], CATALOG)
    assert result.loaded_g_l == pytest.approx(8.4, rel=0.05)
    assert 0.015 <= result.raffinate_g_l <= 0.060
    assert result.ph[-1] == pytest.approx(0.9, abs=0.2)


# Hallazgo: el despojo es el límite anunciado. Con ácido concentrado el modelo trata el H⁺ como
# ideal y su actividad real es mucho mayor: despoja de menos. En Devi deja 0,119 g/L en el orgánico
# (medido 0,002); en el caso Isocalc, 5,0 g/L (Isocalc 3,1), y el circuito recupera 70,4 % en vez
# de 92,8 % con una transferencia neta de 0,198. Fallos esperados y estrictos.
DESPOJO_IDEAL = pytest.mark.xfail(strict=True, reason="H⁺ ideal en ácido concentrado")


def _despojo_devi():
    acido = 0.15 * 1.84 * 0.98 * 1000.0  # 15 %v/v de ácido al 98 %, densidad 1,84
    strip = _aqueous(20, 0.0, acido=acido, densidad=1.17)
    loaded = _organic(60, 20, 8.4, 0.56)
    unit = SolventExtraction("S", ("Acido", "Cargado"), ("Electrolito", "Despojado"), stages=3,
                             density_aq=1.17)  # fmt: skip
    return unit.solve([strip, loaded], CATALOG)


def test_devi_despojo_electrolito():
    assert _despojo_devi().raffinate_g_l == pytest.approx(25.1, rel=0.03)


@DESPOJO_IDEAL
def test_devi_despojo_organico_despojado():
    assert _despojo_devi().loaded_g_l <= 0.05


# ------------------------------------------------------------------ 6. Mitshabu / Isocalc

VOL, ML, CU_PLS = 21.0, 0.52, 7.02
NT = 0.26 * VOL  # g/L
LO = 0.786 * ML * VOL
SO = LO - NT
OA_EXT = CU_PLS * 0.9283 / NT
OA_STRIP = (46.29 - 33.67) / NT


def _pls() -> Stream:
    otros = {"MgSO4": (30.0 - CU_PLS / CU * SO4 - 3.90 / ACID * SO4) / SO4 * 120.37}
    return _aqueous(1000, CU_PLS, acido=3.90, otros=otros)


def _extraccion() -> SolventExtraction:
    return SolventExtraction("E", ("PLS", "OrgD"), ("Refino", "OrgC"), stages=2,
                             efficiency=(0.92, 0.95), feed_ph=1.46)  # fmt: skip


@pytest.fixture(scope="module")
def isocalc():
    spent = _aqueous(1000 / OA_STRIP * OA_EXT, 33.67, acido=199.3, densidad=1.2)
    extraccion = _extraccion()
    despojo = SolventExtraction("S", ("Spent", "OrgC"), ("Advance", "OrgD"), stages=1,
                                efficiency=(0.95,), density_aq=1.2)  # fmt: skip
    guess = {"OrgD": _organic(1000 * OA_EXT, VOL, SO, ML)}
    sheet = Flowsheet(CATALOG, [extraccion, despojo], {"PLS": _pls(), "Spent": spent},
                      tears=("OrgD",), initial=guess)  # fmt: skip
    solution = sheet.solve()
    e = extraccion.solve([solution.streams["PLS"], solution.streams["OrgD"]], CATALOG)
    s = despojo.solve([solution.streams["Spent"], solution.streams["OrgC"]], CATALOG)
    return e, s


@DESPOJO_IDEAL
def test_isocalc_recuperacion(isocalc):
    assert isocalc[0].recovery * 100 == pytest.approx(92.83, abs=5.0)


@DESPOJO_IDEAL
def test_isocalc_transferencia_neta(isocalc):
    e, s = isocalc
    assert (e.loaded_g_l - s.loaded_g_l) / VOL == pytest.approx(0.26, rel=0.20)


def test_isocalc_carga_del_organico(isocalc):
    assert isocalc[0].loaded_g_l / (ML * VOL) * 100 == pytest.approx(78.6, abs=10.0)


def test_isocalc_solo_extraccion_con_su_organico_despojado():
    """POSTERIOR al resultado: se agregó para aislar la causa del fallo del circuito. Con el
    orgánico despojado que informa Isocalc (3,12 g/L), la extracción sola debe recuperar
    92,83 % ± 5 puntos. No es una validación ciega."""
    result = _extraccion().solve([_pls(), _organic(1000 * OA_EXT, VOL, SO, ML)], CATALOG)
    assert result.recovery * 100 == pytest.approx(92.83, abs=5.0)


# ------------------------------------------------------------------ errores


def test_errores():
    feed, org = _aqueous(100, 5.0), _organic(100, 20, 0.0, 0.56)
    with pytest.raises(ValueError, match="orgánic"):
        _unit().solve([feed, Stream({"H2O": 1.0})], CATALOG)
    with pytest.raises(ValueError, match="acuos"):
        _unit().solve([org, org], CATALOG)
    with pytest.raises(ValueError):
        _unit(stages=0)
    with pytest.raises(ValueError):
        _unit(stages=2, efficiency=(1.0,))
    with pytest.raises(ValueError):
        _unit(efficiency=(1.5,))
    with pytest.raises(ValueError, match="pH"):
        _unit(feed_ph=0.5).solve([_aqueous(100, 5.0, acido=0.1), org], CATALOG)
    assert _unit().with_parameter("kex", 3.0).kex == 3.0
    assert _unit(stages=2).with_parameter("eficiencia", 0.9).efficiency == (0.9, 0.9)
    with pytest.raises(KeyError):
        _unit().with_parameter("otra", 1.0)
    assert math.isfinite(KEX_LIX984N)


def test_planta_yaml_con_organico_en_circuito_cerrado(capsys):
    from pathlib import Path

    from procesos import load_plant
    from procesos.cli import main
    from procesos.report import sx_report, worst_closure

    path = Path(__file__).resolve().parents[1] / "ejemplos" / "sx_2e1s.yaml"
    plant = load_plant(path)
    solution = plant.flowsheet.solve()
    assert worst_closure(plant.flowsheet, solution) < 1e-9
    (_, extraccion), (_, despojo) = sx_report(plant.flowsheet, solution)
    # en régimen el orgánico deja en el despojo todo lo que cargó en la extracción
    assert extraccion.transferred_mol_h == pytest.approx(-despojo.transferred_mol_h, rel=1e-6)
    assert main(["resolver", str(path)]) == 0
    assert "SX «Extracción»" in capsys.readouterr().out


def test_estimacion_inicial_solo_para_cortes():
    from procesos import load_plant
    from procesos.plant_io import PlantFileError

    text = """
especies: [{nombre: H2O, fase: l}]
alimentaciones: {A: {flujos: {H2O: 1.0}}}
estimaciones: {B: {flujos: {H2O: 1.0}}}
equipos: [{tipo: mezclador, nombre: M, entradas: [A], salidas: [B]}]
"""
    with pytest.raises(PlantFileError, match="corte"):
        load_plant(text)


@pytest.mark.parametrize("eff", [0.5, 0.8, 1.0])
def test_eficiencia_de_murphree_analitica(eff):
    # una etapa, isoterma lineal y* = m·x y orgánico sin cobre: y = E·m·x y x = x0 - r·y
    a, o, m = 100.0, 80.0, 2.0
    feed = _aqueous(a, 5.0)
    result = _unit(distribution=m, efficiency=(eff,)).solve(
        [feed, _organic(o, 20, 0.0, 0.56)], CATALOG
    )
    r = result.organic_l_h / result.aqueous_l_h
    assert result.raffinate_g_l == pytest.approx(5.0 / (1.0 + r * eff * m), rel=1e-9)
