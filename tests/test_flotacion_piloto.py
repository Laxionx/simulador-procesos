"""Flotación de laboratorio a piloto (Minerals 16(7), 726, 2026). Tolerancias fijadas ANTES de
correr (brief aprobado el 12-10), con estos supuestos declarados también antes de correr:
- Alimentación: la de la Tabla 1 (0,85 % Cu; 0,14 % Zn; 2,36 % S) con la regla del artículo
  (Cu → Ccp, Zn → Sp, el S que sobra → Py, el resto Qtz).
- Cinética de Kelsall de dos componentes (Tablas 4-6), la que usaron los autores.
- Rougher y scavenger de 2 celdas con 14 min cada una (28 min por etapa: 50 L a ~111 L/h).
- Cleaner de 17 L con el τ que da su caudal de sólidos a 200 g/L (densidad del cleaner de
  laboratorio); el artículo no publica el τ del cleaner.

1. Reproducir la simulación de los autores (HSC SIM, Tabla 8): composiciones ±2 puntos.
2. Contra el piloto medido (promedio de 60-180 min): Cu del concentrado (9,27 %) ±15 % relativo;
   minerales del concentrado ±5 puntos; minerales del relave ±0,5 puntos. Corte: falla si quedan
   fuera más de la mitad (más de 4 de 9).
"""

from __future__ import annotations

import math
import runpy
from pathlib import Path

import pytest

from procesos.flotacion import KELSALL, Flotation, kelsall_recovery
from procesos.flotacion_datos import (
    FEED_KG_H,
    HSC_CONCENTRATE,
    HSC_TAILINGS,
    MINERALS,
    PILOT_CONCENTRATE,
    PILOT_CU_PCT,
    PILOT_TAILINGS,
    composition,
    feed_mineralogy,
    solve_pilot,
)
from procesos.plant_io import PlantFileError, load_plant

CU_IN_CCP = 63.546 / 183.511


@pytest.fixture(scope="module")
def pilot():
    solution, tau = solve_pilot()
    conc = composition(solution.streams["Concentrado final"])
    tails = composition(solution.streams["Relave final"])
    return solution, tau, conc, tails


# ------------------------------------------------------------------ 1. simulación de los autores
NO_REPRODUCE = pytest.mark.xfail(
    strict=True, reason="la simulación HSC parece usar otra alimentación"
)
HSC_FAILS = {("concentrado", "Ccp"), ("concentrado", "Py"), ("concentrado", "Qtz")}
HSC_CASES = [(p, m) for p in ("concentrado", "relave") for m in MINERALS]


@pytest.mark.parametrize(
    ("product", "mineral"),
    [pytest.param(p, m, marks=NO_REPRODUCE if (p, m) in HSC_FAILS else (), id=f"{p}-{m}")
     for p, m in HSC_CASES],
)  # fmt: skip
def test_reproduce_simulacion_hsc(pilot, product, mineral):
    _s, _t, conc, tails = pilot
    model = (conc if product == "concentrado" else tails)[mineral]
    published = (HSC_CONCENTRATE if product == "concentrado" else HSC_TAILINGS)[mineral]
    assert model == pytest.approx(published, abs=2.0)


# ------------------------------------------------------------------ 2. piloto medido
def _pilot_checks(conc: dict, tails: dict) -> dict[str, bool]:
    checks = {"Cu": abs(conc["Ccp"] * CU_IN_CCP / PILOT_CU_PCT - 1) <= 0.15}
    checks |= {f"concentrado {m}": abs(conc[m] - PILOT_CONCENTRATE[m]) <= 5.0 for m in MINERALS}
    checks |= {f"relave {m}": abs(tails[m] - PILOT_TAILINGS[m]) <= 0.5 for m in MINERALS}
    return checks


PILOTO_FALLA = pytest.mark.xfail(strict=True, reason="pirita y ganga no siguen al piloto")
PILOT_FAILS = {"concentrado Py", "concentrado Qtz", "relave Ccp", "relave Py", "relave Qtz"}
PILOT_NAMES = ["Cu"] + [f"{p} {m}" for p in ("concentrado", "relave") for m in MINERALS]


@pytest.mark.parametrize(
    "name", [pytest.param(n, marks=PILOTO_FALLA if n in PILOT_FAILS else (), id=n)
             for n in PILOT_NAMES],
)  # fmt: skip
def test_contra_el_piloto(pilot, name):
    _s, _t, conc, tails = pilot
    assert _pilot_checks(conc, tails)[name]


@pytest.mark.xfail(strict=True, reason="5 de 9 fuera: no pasa el corte")
def test_corte_piloto(pilot):
    _s, _t, conc, tails = pilot
    assert sum(not ok for ok in _pilot_checks(conc, tails).values()) <= 4


# ------------------------------------------------------------------ guardas
def test_alimentacion_reproduce_la_quimica():
    feed = feed_mineralogy()
    assert sum(feed.values()) == pytest.approx(100.0)
    assert feed["Ccp"] * CU_IN_CCP == pytest.approx(0.85, rel=1e-9)
    s = (
        feed["Ccp"] * 2 * 32.06 / 183.511
        + feed["Sp"] * 32.06 / 97.45
        + feed["Py"] * 2 * 32.06 / 119.98
    )
    assert s == pytest.approx(2.36, rel=1e-3)


def test_circuito_cierra_y_tau_del_cleaner(pilot):
    solution, tau, _c, _t = pilot
    out = solution.streams["Concentrado final"].total + solution.streams["Relave final"].total
    assert out == pytest.approx(FEED_KG_H, rel=1e-9)
    solids = solution.streams["Concentrado rougher"].total
    assert tau == pytest.approx(17.0 * 0.2 / solids * 60.0, rel=1e-8)


def test_kelsall_a_mano():
    # Rougher de laboratorio, Ccp: a 15 min, 0,731 de fracción rápida casi entera y 0,269 lenta.
    batch = kelsall_recovery(0.269, 0.892, 0.027, 15.0)
    expected = 0.731 * (1 - math.exp(-0.892 * 15)) + 0.269 * (1 - math.exp(-0.027 * 15))
    assert batch == pytest.approx(expected, rel=1e-12)
    assert 0.80 < batch < 0.84  # la Figura 7a del artículo marca ~81 % a 15 min
    cells = kelsall_recovery(0.269, 0.892, 0.027, 14.0, cells=2)
    assert cells == pytest.approx(
        0.731 * (1 - (1 + 0.892 * 14) ** -2) + 0.269 * (1 - (1 + 0.027 * 14) ** -2)
    )
    many = kelsall_recovery(0.269, 0.892, 0.027, 15.0 / 4000, cells=4000)
    assert many == pytest.approx(batch, rel=1e-3)  # muchas celdas en serie tienden al batch


def test_kelsall_valida_parametros():
    for bad in ((0.3, 0.5), (1.2, 0.5, 0.1), (0.3, -0.5, 0.1), (0.3, 0.0, 0.0)):
        with pytest.raises(ValueError):
            Flotation("F", ("a",), ("b", "c"), {"X": bad}, 1, KELSALL, tau_min=5.0)
    with pytest.raises(ValueError):
        Flotation("F", ("a",), ("b", "c"), {"X": (0.3, 0.5, 0.1)}, 1, "primer_orden", tau_min=5.0)


def test_kelsall_desde_yaml(tmp_path):
    text = """nombre: Kelsall
especies:
  - {nombre: CuFeS2, fase: s}
  - {nombre: SiO2, fase: s}
alimentaciones:
  Alimentacion: {flujos: {CuFeS2: 2.0, SiO2: 98.0}}
equipos:
  - tipo: flotacion
    nombre: Rougher
    entradas: [Alimentacion]
    salidas: [Concentrado, Relave]
    celdas: 2
    tiempo_residencia_min: 14
    modelo: kelsall
    cinetica:
      CuFeS2: {phi: 0.269, kf: 0.892, ks: 0.027}
"""
    path = tmp_path / "k.yaml"
    path.write_text(text, encoding="utf-8")
    sheet = load_plant(path).flowsheet
    conc = sheet.solve().streams["Concentrado"]
    assert conc.flow("CuFeS2") == pytest.approx(
        2.0 * kelsall_recovery(0.269, 0.892, 0.027, 14.0, 2)
    )
    bad = path.with_name("malo.yaml")
    bad.write_text(text.replace("phi: 0.269, kf: 0.892, ks: 0.027", "phi: 0.269"), encoding="utf-8")
    with pytest.raises(PlantFileError):
        load_plant(bad)


def test_ejemplo_corre(capsys):
    runpy.run_path(str(Path(__file__).parents[1] / "ejemplos" / "flotacion_piloto.py"))
    assert "piloto" in capsys.readouterr().out


def test_kelsall_con_factor_de_escalamiento():
    from procesos import Catalog, Stream, make_species

    catalog = Catalog([make_species("CuFeS2", phase="s")])
    unit = Flotation("F", ("a",), ("b", "c"), {"CuFeS2": (0.3, 0.8, 0.05)}, 2, KELSALL,
                     tau_min=10.0, scale_up=2.0)  # fmt: skip
    got = unit.solve([Stream({"CuFeS2": 1.0})], catalog).recoveries["CuFeS2"]
    assert got == pytest.approx(kelsall_recovery(0.3, 0.4, 0.025, 10.0, 2), rel=1e-12)
