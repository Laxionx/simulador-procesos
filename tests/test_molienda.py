"""Molienda conectada a simulador-conminucion. Tolerancias fijadas ANTES de correr (brief 11-10):

1. Identidad: lo que entrega el equipo es lo mismo que correr conminucion por separado (1e-12):
   energía de Bond, P80, carga circulante y potencia.
2. A través de la conexión se mantienen las validaciones de conminucion (mismas tolerancias que
   en ese proyecto): Bougainville contra MODSIM 3.6.24, carga circulante y P80 ±5 %; los 14
   muestreos de Constancia contra la columna «modelo» del reporte, ±5 %.
3. Guardas: la composición no cambia, cierre por elemento y de energía, y el costo de la
   electricidad es la potencia por el precio.
"""

from __future__ import annotations

import pytest

pytest.importorskip("conminucion")

from conminucion.bond import bond_energy  # noqa: E402
from conminucion.plantas_reales import (  # noqa: E402
    BOUGAINVILLE_ALIM_TPH,
    CONSTANCIA,
    MODSIM_BOUGAINVILLE,
    bougainville_config,
    simular_bougainville,
    tamano_estilo_modsim,
)

from procesos import Catalog, Flowsheet, Grinding, Stream, load_plant, make_species  # noqa: E402
from procesos.costs import operating_cost  # noqa: E402
from procesos.molienda import template  # noqa: E402
from procesos.report import element_balance, energy_balance, grinding_report  # noqa: E402
from procesos.thermo_data import DEFAULT_THERMO  # noqa: E402

SPECIES = [("CuFeS2", "s"), ("SiO2", "s"), ("H2O", "l")]


CATALOG = Catalog([make_species(n, phase=p) for n, p in SPECIES])


def _ore(t_h: float, water_t_h: float = 0.0) -> Stream:
    return Stream({"CuFeS2": 29.0 * t_h, "SiO2": 971.0 * t_h, "H2O": 1000.0 * water_t_h})


def _bond(**kw) -> Grinding:
    args = {"wi": 16.4, "f80_um": 1068.0, "p80_um": 188.0}
    args.update(kw)
    return Grinding("Molienda", ("Mineral",), ("Pulpa",), **args)


def _circuit(power_kw: float | None = None) -> Grinding:
    return Grinding("Molienda", ("Mineral",), ("Pulpa",), 14.0, circuit="cerrado_directo",
                    config=template("bougainville", power_kw))  # fmt: skip


# ------------------------------------------------------------------ identidad


@pytest.mark.parametrize("m", CONSTANCIA, ids=lambda m: f"muestreo{m.numero}")
def test_bond_igual_a_conminucion_y_a_constancia(m):
    unit = _bond(wi=m.wi_kwh_t, f80_um=m.f80_um, p80_um=m.p80_um)
    result = unit.solve([_ore(100.0, 50.0)], CATALOG)
    assert result.bond_kwh_t == pytest.approx(bond_energy(m.wi_kwh_t, m.f80_um, m.p80_um),
                                              rel=1e-12)  # fmt: skip
    assert result.power_kw == pytest.approx(result.bond_kwh_t * 100.0, rel=1e-12)
    assert result.bond_kwh_t == pytest.approx(m.energia_modelo, rel=0.05)


@pytest.fixture(scope="module")
def bougainville():
    unit = _circuit()
    return unit.solve([_ore(BOUGAINVILLE_ALIM_TPH)], CATALOG), simular_bougainville()


def test_circuito_igual_a_conminucion(bougainville):
    ours, theirs = bougainville
    product = theirs.streams["overflow"]
    assert ours.p80_um == pytest.approx(product.p80, rel=1e-12)
    assert ours.circulating_load == pytest.approx(theirs.circulating_load, rel=1e-12)
    assert ours.bond_kwh_t == pytest.approx(theirs.bond_kwh_t, rel=1e-12)
    assert ours.power_kw == bougainville_config().mill.power_kw
    assert ours.power_basis == "molino"
    assert ours.water_added_t_h == pytest.approx(product.water, rel=1e-12)


def test_circuito_escala_la_alimentacion_y_el_agua():
    """A 100 t/h con 150 t/h de agua: igual a escalar la plantilla a mano en conminucion."""
    from dataclasses import replace

    from conminucion.circuits import simulate

    config = bougainville_config()
    fresh = config.fresh.scaled(100.0 / config.fresh.total_solids).with_water(150.0)
    theirs = simulate("cerrado_directo", replace(config, fresh=fresh, bond_wi=14.0), tol=1e-10)
    ours = _circuit().solve([_ore(100.0, 150.0)], CATALOG)
    product = theirs.streams["overflow"]
    assert ours.solids_t_h == pytest.approx(100.0, rel=1e-12)
    assert ours.p80_um == pytest.approx(product.p80, rel=1e-12)
    assert ours.circulating_load == pytest.approx(theirs.circulating_load, rel=1e-12)
    assert ours.water_added_t_h == pytest.approx(product.water - 150.0, abs=1e-9)


def test_circuito_mantiene_la_validacion_contra_modsim(bougainville):
    ours, _ = bougainville
    ref = MODSIM_BOUGAINVILLE
    assert ours.circulating_load == pytest.approx(ref["underflow_tph"] / BOUGAINVILLE_ALIM_TPH,
                                                  rel=0.05)  # fmt: skip
    assert tamano_estilo_modsim(ours.product, 0.8) == pytest.approx(ref["p80_um"], rel=0.05)


# ------------------------------------------------------------------ guardas


def test_no_cambia_la_composicion_y_cierra():
    sheet = Flowsheet(CATALOG, [_bond()], {"Mineral": _ore(100.0, 60.0)})
    solution = sheet.solve()
    assert dict(solution.streams["Pulpa"].flows) == dict(_ore(100.0, 60.0).flows)
    assert all(r.relative_error < 1e-12 for r in element_balance(sheet, solution))


def test_cierra_la_energia_con_la_potencia_del_molino():
    # La base térmica no trae calcopirita: el mineral es solo sílice.
    catalog = Catalog([make_species("SiO2", phase="s"), make_species("H2O", phase="l")],
                      DEFAULT_THERMO)  # fmt: skip
    ore = Stream({"SiO2": 100_000.0, "H2O": 60_000.0}, 25.0)
    sheet = Flowsheet(catalog, [_bond()], {"Mineral": ore})
    (row,) = energy_balance(sheet, sheet.solve())
    assert row.power == pytest.approx(bond_energy(16.4, 1068.0, 188.0) * 100.0, rel=1e-12)
    assert row.relative_error < 1e-9


def test_rechaza_datos_imposibles():
    with pytest.raises(ValueError):
        _bond(f80_um=100.0, p80_um=188.0)  # F80 < P80
    with pytest.raises(ValueError):
        Grinding("M", ("A",), ("B",), 14.0)  # ni Bond ni circuito
    with pytest.raises(ValueError):
        _bond(wi=-1.0)
    with pytest.raises(ValueError):
        template("otro")
    with pytest.raises(ValueError):
        _bond().solve([Stream({"H2O": 1000.0})], CATALOG)


def test_parametros_ajustables():
    assert _bond().with_parameter("p80", 150.0).p80_um == 150.0
    assert _circuit().with_parameter("potencia_kw", 4000.0).config.mill.power_kw == 4000.0
    with pytest.raises(KeyError):
        _bond().with_parameter("potencia_kw", 1.0)


# ------------------------------------------------------------------ ejemplo


def test_ejemplo_concentradora_con_molienda():
    plant = load_plant("ejemplos/concentradora_con_molienda.yaml")
    sheet = plant.flowsheet
    solution = sheet.solve()
    (_, mo), = grinding_report(sheet, solution)  # fmt: skip
    assert mo.power_basis == "molino" and mo.circulating_load > 0
    (line,) = operating_cost(sheet, solution, plant.costs).lines
    assert line.cost_per_h == pytest.approx(mo.power_kw * 0.08, rel=1e-12)
    assert all(r.relative_error < 1e-9 for r in element_balance(sheet, solution))
