"""Electrorrefinación (fase 4c). Tolerancias fijadas ANTES de correr (brief aprobado el 12-10):

1. Conductividad κER.2 (Kalliomäki et al. 2021) contra la medida por Fuentes (USM 2022, Tabla
   4.24), datos independientes: M3 a 54,4 y 60 °C (dentro del rango) ±5 %; M3 a 48,9 y 71,1 °C y
   M4 (Cu 34,8 g/L, fuera del rango) ±10 %. Corte: falla si quedan fuera más de 4 de las 8.
2. Coherencia de planta, Mount Isa (compendio IsaKidd 2020): eficiencia × disponibilidad
   implícita por Faraday entre 0,85 y 0,98.
3. Coherencia del voltaje con la Tabla II del compendio (refinería típica, 300 A/m², paso de
   100 mm): caída en el electrolito por cosecha ±30 % y total por cosecha entre 280 y 385 mV.
4. Guardas: cierre por elemento, Faraday exacto, desplazamiento del Cu por el Ni, Cu2O disuelto,
   purga que deja el Ni en el límite (en un circuito con reciclo) y liberadoras que retiran justo
   el Cu ganado.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from procesos import Catalog, Flowsheet, Stream, make_species
from procesos.cli import main
from procesos.control import solve_with_controllers
from procesos.elements import molar_mass, parse_formula
from procesos.er import (
    CONTACTS_V,
    KAPPA_ER2,
    Electrorefining,
    conductivity,
    gap_from_geometry,
)
from procesos.er_datos import (
    CATHODE_BLADE_M,
    FUENTES_CU_G_L,
    FUENTES_KAPPA,
    FUENTES_SULFATE_G_L,
    ISAKIDD_ELECTROLYTE_MV,
    ISAKIDD_J,
    ISAKIDD_TOTAL_MV,
    MOUNT_ISA,
    TANKHOUSE3,
)
from procesos.ew import FARADAY, Electrowinning
from procesos.html_report import html_report
from procesos.plant_io import load_plant
from procesos.report import worst_closure
from procesos.units import Mixer, Splitter

EXAMPLE = Path(__file__).parents[1] / "ejemplos" / "refineria_atlantic_mount_isa.yaml"
CU, NI = 63.546, 58.693


def _mm(formula: str) -> float:
    return molar_mass(parse_formula(formula))


SPECIES = [("H2O", "l"), ("CuSO4", "aq"), ("H2SO4", "aq"), ("NiSO4", "aq"), ("Cu", "s"),
           ("Cu2O", "s"), ("Ni", "s"), ("Ag", "s"), ("O2", "g")]  # fmt: skip
CATALOG = Catalog([make_species(n, phase=p) for n, p in SPECIES])


def _electrolyte(m3_h: float, cu: float = 45.0, acid: float = 170.0, ni: float = 0.0) -> Stream:
    litres = 1000.0 * m3_h
    kg = {"CuSO4": cu * _mm("CuSO4") / CU, "H2SO4": acid, "NiSO4": ni * _mm("NiSO4") / NI}
    flows = {s: g_l * litres / 1000 for s, g_l in kg.items() if g_l > 0}
    flows["H2O"] = 1.2 * litres - sum(flows.values())
    return Stream(flows, 60.0)


def _unit(**kw) -> Electrorefining:
    args = {"current_density": 300.0, "cathode_area_m2": 100.0, "current_efficiency": 0.95,
            "gap_m": 0.03}  # fmt: skip
    args.update(kw)
    ports = ("Sale", "Catodos", "Barro", "Chatarra")
    return Electrorefining("ER", ("Anodos", "Electrolito"), ports, **args)


# ------------------------------------------------------------------ 1. conductividad medida
def _fuentes_acid(sample: str) -> float:
    cu = FUENTES_CU_G_L[sample]
    return (FUENTES_SULFATE_G_L[sample] / 96.06 - cu / CU) * 98.079


IN_RANGE = {("M3", 54.4), ("M3", 60.0)}
CASES = [(s, t) for s in FUENTES_KAPPA for t in FUENTES_KAPPA[s]]


def _kappa_error(sample: str, temp: float) -> float:
    model, _ = conductivity(FUENTES_CU_G_L[sample], _fuentes_acid(sample), 0.0, 0.0, temp)
    return 10.0 * model / FUENTES_KAPPA[sample][temp] - 1  # S/m → mS/cm


def _inside(sample: str, temp: float) -> bool:
    tol = 0.05 if (sample, temp) in IN_RANGE else 0.10
    return abs(_kappa_error(sample, temp)) <= tol


SOBRESTIMA = pytest.mark.xfail(strict=True, reason="κER.2 sobrestima M3 de Fuentes, como κEW")
FAILS_K = {("M3", 48.9): SOBRESTIMA, ("M3", 54.4): SOBRESTIMA, ("M3", 60.0): SOBRESTIMA}


@pytest.mark.parametrize(
    ("sample", "temp"),
    [pytest.param(s, t, marks=FAILS_K.get((s, t), ()), id=f"{s}-{t}") for s, t in CASES],
)
def test_conductividad_contra_fuentes(sample, temp):
    assert _inside(sample, temp)


def test_corte_conductividad():
    outside = [c for c in CASES if not _inside(*c)]
    assert len(outside) <= 4, outside


def test_conductividad_a_mano():
    # Un punto calculado término a término desde la Tabla 4 del artículo.
    cu, a, ni, arsenic, t = 45.0, 170.0, 15.0, 5.0, 60.0
    log_k = (2.446 - 6.089e-4 * cu + 1.553e-3 * a - 2.117e-3 * ni + 1.398e-4 * arsenic
             + 9.518e-4 * t - 7.753e-6 * cu * a - 1.235e-5 * cu * ni - 8.915e-6 * cu * arsenic
             - 4.930e-6 * a * arsenic + 1.030e-5 * a * t + 1.019e-5 * t * arsenic)  # fmt: skip
    model, warnings = conductivity(cu, a, ni, arsenic, t)
    assert model == pytest.approx(10**log_k / 10, rel=1e-12) and not warnings
    assert len(KAPPA_ER2) == 12
    assert conductivity(30.0, a, ni, arsenic, 80.0)[1]  # fuera de rango: avisa


# ------------------------------------------------------------------ 2. Mount Isa
def _mount_isa_area() -> float:
    m = MOUNT_ISA
    return m["celdas"] * m["catodos_por_celda"] * 2 * m["area_por_cara_m2"]


def test_mount_isa_faraday_coherente():
    current = MOUNT_ISA["densidad_corriente"] * _mount_isa_area()
    faraday_t_y = current / (2 * FARADAY) * CU * 8760 * 3600 / 1e6
    implied = MOUNT_ISA["capacidad_t_a"] / faraday_t_y
    assert 0.85 <= implied <= 0.98


# ------------------------------------------------------------------ 3. voltaje (coherencia)
def _crop_gaps() -> list[float]:
    """Distancia media por cosecha: el ánodo de 320 kg (cara de 0,82 m², 8,9 t/m³) pierde por
    Faraday lo que la corriente disuelve en su ciclo; el cátodo lleva medio depósito."""
    m = MOUNT_ISA
    j, area, eff = m["densidad_corriente"], m["area_por_cara_m2"], m["eficiencia"]
    per_anode = j * 2 * area * m["ciclo_anodo_d"] * 86400 / (2 * FARADAY) * CU / 1000 * eff
    consumed = per_anode / m["masa_anodo_kg"]
    t0 = m["masa_anodo_kg"] / (8900 * area)
    crop_s = m["ciclo_anodo_d"] / m["cosechas"] * 86400
    deposit = j * area * crop_s / (2 * FARADAY) * CU / 1000 * eff / (8960 * area)
    return [
        gap_from_geometry(
            m["paso_m"],
            t0 * (1 - consumed * (k - 0.5) / m["cosechas"]),
            CATHODE_BLADE_M,
            deposit / 2,
        )  # fmt: skip
        for k in (1, 2, 3)
    ]


def _crop_drop_mv(k: int) -> float:
    t3 = TANKHOUSE3
    kappa, _ = conductivity(t3["Cu"], t3["H2SO4"], t3["Ni"], t3["As"], t3["T"])
    return 1000 * ISAKIDD_J * _crop_gaps()[k] / kappa


CAIDA_BAJA = pytest.mark.xfail(strict=True, reason="j·L/κ da ~1/3 menos que la Tabla II")


@pytest.mark.parametrize("k", [pytest.param(k, marks=CAIDA_BAJA) for k in range(3)])
def test_caida_en_electrolito_vs_compendio(k):
    assert _crop_drop_mv(k) == pytest.approx(ISAKIDD_ELECTROLYTE_MV[k], rel=0.30)


@pytest.mark.parametrize("k", [pytest.param(k, marks=CAIDA_BAJA) for k in range(3)])
def test_voltaje_total_en_rango_del_compendio(k):
    total = _crop_drop_mv(k) + 1000 * CONTACTS_V
    assert min(ISAKIDD_TOTAL_MV) <= total <= max(ISAKIDD_TOTAL_MV)


def test_geometria_a_mano():
    assert gap_from_geometry(0.1, 0.04, 0.003, 0.002) == pytest.approx(0.05 - 0.02 - 0.0015 - 0.002)
    with pytest.raises(ValueError):
        gap_from_geometry(0.05, 0.05, 0.003)


# ------------------------------------------------------------------ 4. guardas
def _anode(cu: float, cu2o: float = 0.0, ni: float = 0.0, ag: float = 0.0) -> Stream:
    return Stream(
        {k: v for k, v in {"Cu": cu, "Cu2O": cu2o, "Ni": ni, "Ag": ag}.items() if v}, 60.0
    )


def test_faraday_y_reparto_del_anodo():
    unit = _unit()
    anode = _anode(2000.0, ag=5.0)
    out, cathodes, slimes, scrap = unit.compute([anode, _electrolyte(50.0)], CATALOG)
    deposited = 0.95 * 30_000 / (2 * FARADAY) * 3.6 * CU
    assert cathodes.flow("Cu") == pytest.approx(deposited, rel=1e-12)
    phi = deposited / 2000.0
    assert scrap.flow("Cu") == pytest.approx((1 - phi) * 2000.0, rel=1e-12)
    assert slimes.flow("Ag") == pytest.approx(phi * 5.0, rel=1e-12)
    assert scrap.flow("Ag") == pytest.approx((1 - phi) * 5.0, rel=1e-12)
    feed = _electrolyte(50.0)
    assert out.flow("CuSO4") == pytest.approx(feed.flow("CuSO4"), rel=1e-12)  # Cu entra y sale


def test_niquel_desplaza_cobre_sin_consumir_acido():
    unit = _unit()
    feed = _electrolyte(50.0)
    out, cathodes, _s, _c = unit.compute([_anode(2000.0, ni=40.0), feed], CATALOG)
    result = unit.solve([_anode(2000.0, ni=40.0), feed], CATALOG)
    ni_kmol = result.anode_consumed * 40.0 / NI
    assert out.flow("H2SO4") == pytest.approx(feed.flow("H2SO4"), rel=1e-12)
    cu_lost = (feed.flow("CuSO4") - out.flow("CuSO4")) / _mm("CuSO4")
    assert cu_lost == pytest.approx(ni_kmol, rel=1e-9)
    assert result.nickel_gain_kg_h == pytest.approx(ni_kmol * NI, rel=1e-9)
    assert cathodes.flow("Cu") == pytest.approx(0.95 * 30_000 / (2 * FARADAY) * 3.6 * CU, rel=1e-12)


def test_cu2o_se_disuelve_y_consume_acido():
    unit = _unit()
    feed = _electrolyte(50.0)
    inputs = [_anode(2000.0, cu2o=30.0), feed]
    out, _cat, slimes, _scrap = unit.compute(inputs, CATALOG)
    result = unit.solve(inputs, CATALOG)
    n = result.anode_consumed * 30.0 / _mm("Cu2O")
    assert feed.flow("H2SO4") - out.flow("H2SO4") == pytest.approx(n * _mm("H2SO4"), rel=1e-9)
    assert slimes.flow("Cu") == pytest.approx(n * CU, rel=1e-9)
    assert result.copper_gain_kg_h == pytest.approx(n * CU, rel=1e-9)
    assert result.acid_consumed_kg_h == pytest.approx(n * _mm("H2SO4"), rel=1e-9)


def test_anodo_insuficiente_avisa():
    # La corriente disuelve ~33,8 kg/h de Cu: con 20 kg/h de ánodo, se consume entero.
    result = _unit().solve([_anode(20.0), _electrolyte(50.0)], CATALOG)
    assert result.limited and result.anode_consumed == 1.0
    assert result.copper_kg_h == pytest.approx(20.0)
    assert "ánodo" in result.warnings[0]


def test_parametros_invalidos():
    for bad in ({"current_efficiency": 1.2}, {"gap_m": 0.0}, {"nickel_to_electrolyte": -0.1},
                {"contacts_v": -1.0}):  # fmt: skip
        with pytest.raises(ValueError):
            _unit(**bad)
    with pytest.raises(ValueError, match="entradas"):
        Electrorefining("ER", ("Solo",), ("a", "b", "c", "d"), 300, 100, 0.95, 0.03)


def test_purga_deja_el_niquel_en_el_limite():
    # Circuito con reciclo: la reposición (sin Ni) entra con la masa que sale por la purga. En
    # estado estacionario el Ni que sale con la purga es el que entra con los ánodos.
    limit, density = 15.0, 1.2
    unit = _unit(nickel_limit_g_l=limit)
    anode = _anode(2000.0, ni=40.0)
    probe = unit.solve([anode, _electrolyte(20.0)], CATALOG)
    bleed_kg = probe.nickel_bleed_m3_h(limit) * 1000 * density
    phi_ni = probe.anode_consumed * 40.0 / NI
    delta_mass = phi_ni * (NI - CU)  # el Ni desplaza Cu en el electrolito
    unit_makeup = _electrolyte(1.0)
    scale = (bleed_kg - delta_mass) / unit_makeup.total
    makeup = Stream({s: v * scale for s, v in unit_makeup.flows.items()}, 60.0)
    sheet = Flowsheet(
        CATALOG,
        [
            Mixer("Mezcla", ("Reposicion", "Recirculado"), ("Electrolito",)),
            Electrorefining("ER", ("Anodos", "Electrolito"),
                            ("Sale", "Catodos", "Barro", "Chatarra"), 300.0, 100.0, 0.95, 0.03),
            Splitter("Purga", ("Sale",), ("Purga", "Recirculado"), (0.2, 0.8)),
        ],
        {"Reposicion": makeup, "Anodos": anode},
    )  # fmt: skip
    solution = sheet.solve(initial={"Recirculado": _electrolyte(4.0, ni=limit)})
    out = solution.streams["Sale"]
    ni_g_l = 1000 * out.flow("NiSO4") / _mm("NiSO4") * NI / (out.total / density)
    assert ni_g_l == pytest.approx(limit, rel=1e-6)


def test_liberadoras_retiran_justo_el_cobre_ganado():
    unit = _unit(liberator_efficiency=0.85)
    feed = _electrolyte(50.0)
    inputs = [_anode(2000.0, cu2o=30.0), feed]
    current = unit.solve(inputs, CATALOG).liberator_current_a(0.85)
    sheet = Flowsheet(
        CATALOG,
        [
            Electrorefining("ER", ("Anodos", "Electrolito"),
                            ("Sale", "Catodos", "Barro", "Chatarra"), 300.0, 100.0, 0.95, 0.03),
            Splitter("A liberadoras", ("Sale",), ("Lib", "Directo"), (0.3, 0.7)),
            Electrowinning("Liberadoras", ("Lib",), ("Decobrizado", "Cat lib", "O2"),
                           current_density=current / 100.0, cathode_area_m2=100.0,
                           current_efficiency=0.85),
            Mixer("Retorno", ("Directo", "Decobrizado"), ("Final",)),
        ],
        {"Anodos": inputs[0], "Electrolito": feed},
    )  # fmt: skip
    final = sheet.solve().streams["Final"]
    for species in ("CuSO4", "H2SO4", "H2O"):
        assert final.flow(species) == pytest.approx(feed.flow(species), rel=1e-12), species


def test_sin_balance_de_calor():
    from procesos.thermo_data import DEFAULT_THERMO

    with_data = [("H2O", "l"), ("CuSO4", "aq"), ("H2SO4", "aq"), ("Cu", "s")]
    hot = Catalog([make_species(n, phase=p) for n, p in with_data], DEFAULT_THERMO)
    with pytest.raises(ValueError, match="balance de calor"):
        _unit().compute([_anode(2000.0), _electrolyte(50.0)], hot)


def test_ejemplo_cierra_y_las_liberadoras_cuadran():
    plant = load_plant(EXAMPLE)
    controlled = solve_with_controllers(plant.flowsheet, plant.controllers)
    assert worst_closure(controlled.flowsheet, controlled.solution) < 1e-9
    unit = next(u for u in controlled.flowsheet.units if isinstance(u, Electrorefining))
    result = unit.solve([controlled.solution.streams[n] for n in unit.inputs],
                        controlled.flowsheet.catalog)  # fmt: skip
    assert result.cell_voltage == pytest.approx(sum(result.components.values()))
    assert result.specific_energy_kwh_t == pytest.approx(
        result.cell_voltage * 2 * FARADAY / (0.975 * CU * 3.6), rel=1e-9
    )
    assert math.isfinite(result.nickel_bleed_m3_h(18.9))
    text = html_report(plant, controlled.flowsheet, controlled.solution)
    assert "Electrorrefinación · Nave de refinacion" in text and "contactos y placas" in text


def test_cli_imprime_la_nave(capsys):
    assert main(["resolver", str(EXAMPLE)]) == 0
    out = capsys.readouterr().out
    assert "ER «Nave de refinacion»" in out and "Purga para 18.9 g/L de Ni" in out


# ------------------------------------------------------------------ guardas a mano (mutaciones)
def test_concentraciones_y_caida_ohmica_a_mano():
    # Ánodo de Cu puro: el electrolito sale con la composición con que entró.
    unit = _unit(gap_m=0.03)
    result = unit.solve([_anode(2000.0), _electrolyte(50.0, cu=45.0, acid=170.0)], CATALOG)
    assert result.electrolyte_g_l["Cu"] == pytest.approx(45.0, rel=1e-9)
    assert result.electrolyte_g_l["H2SO4"] == pytest.approx(170.0, rel=1e-9)
    assert result.electrolyte_m3_h == pytest.approx(50.0, rel=1e-9)
    kappa, _ = conductivity(45.0, 170.0, 0.0, 0.0, 60.0)
    assert result.components["electrolito"] == pytest.approx(300.0 * 0.03 / kappa, rel=1e-9)


def test_niquel_parte_al_barro():
    unit = _unit(nickel_to_electrolyte=0.6)
    inputs = [_anode(2000.0, ni=40.0), _electrolyte(50.0)]
    _out, _cat, slimes, _scrap = unit.compute(inputs, CATALOG)
    result = unit.solve(inputs, CATALOG)
    ni_consumed = result.anode_consumed * 40.0
    assert result.nickel_gain_kg_h == pytest.approx(0.6 * ni_consumed, rel=1e-9)
    assert slimes.flow("Ni") == pytest.approx(0.4 * ni_consumed, rel=1e-9)


def test_liberadoras_descuentan_el_cobre_que_ya_sale():
    result = _unit().solve([_anode(2000.0, cu2o=30.0), _electrolyte(50.0)], CATALOG)
    full = result.liberator_current_a(0.9)
    half = result.liberator_current_a(0.9, copper_removed_kg_h=result.copper_gain_kg_h / 2)
    assert half == pytest.approx(full / 2, rel=1e-12)
    assert result.liberator_current_a(0.9, copper_removed_kg_h=1e9) == 0.0
