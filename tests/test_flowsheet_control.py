"""Planta, cortes automáticos, convergencia y lazos de control."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from procesos import (
    Catalog,
    ControlError,
    Controller,
    ConvergenceError,
    Flowsheet,
    Goal,
    Manipulated,
    Mixer,
    Reaction,
    Reactor,
    Separator,
    Splitter,
    Stream,
    load_plant,
    make_species,
    parse_equation,
    solve_with_controllers,
)
from procesos.flowsheet import with_tears

EXAMPLES = Path(__file__).resolve().parents[1] / "ejemplos"


def _catalog() -> Catalog:
    return Catalog([make_species(n) for n in ["SiO2", "H2O", "CuO", "H2SO4", "CuSO4"]])


def _recycle(**kwargs) -> Flowsheet:
    units = [
        Mixer("Cajón", ("F", "R"), ("M",)),
        Separator("Sep", ("M",), ("P", "Fondo"), {"SiO2": 0.6, "H2O": 0.2}),
        Splitter("Div", ("Fondo",), ("R", "Purga"), (0.7, 0.3)),
    ]
    return Flowsheet(_catalog(), units, {"F": Stream({"SiO2": 100.0, "H2O": 50.0})}, **kwargs)


# ---------------------------------------------------------------- validación
@pytest.mark.parametrize(
    ("units", "feeds", "message"),
    [
        ([Mixer("A", ("F",), ("X",)), Mixer("A", ("X",), ("Y",))], {"F": Stream()}, "repetido"),
        ([Mixer("A", ("F",), ("X",)), Mixer("B", ("F",), ("X",))], {"F": Stream()}, "único origen"),
        ([Mixer("A", ("F",), ("F2",))], {"F": Stream(), "F2": Stream()}, "único origen"),
        ([Mixer("A", ("F", "Z"), ("X",))], {"F": Stream()}, "nadie produce"),
        ([Mixer("A", ("F",), ("X",))], {"F": Stream({"Au": 1.0})}, "fuera del catálogo"),
        ([Separator("S", ("F",), ("X", "Y"), {"Au": 0.5})], {"F": Stream()}, "fuera del catálogo"),
        ([Mixer("A", ("F",), ("X",))], {"F": Stream(), "G": Stream()}, "ningún equipo usa"),
        (
            [Reactor("R", ("F",), ("X",), (Reaction(parse_equation("CuO -> CuSO4"), "CuO", 1.0),))],
            {"F": Stream()},
            "desbalanceada",
        ),
    ],
)
def test_planta_invalida(units: list, feeds: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Flowsheet(_catalog(), units, feeds)


def test_cortes_automaticos_y_manuales() -> None:
    auto = _recycle()
    assert auto.tears == ("R",)
    assert auto.products == ("P", "Purga")
    manual = with_tears(auto, ["Fondo"])
    assert manual.tears == ("Fondo",)
    np.testing.assert_allclose(
        manual.solve().streams["P"].flow("SiO2"), auto.solve().streams["P"].flow("SiO2"), rtol=1e-9
    )
    with pytest.raises(ValueError, match="sin corriente de corte"):
        _recycle(tears=[])
    with pytest.raises(ValueError, match="ningún equipo produce"):
        _recycle(tears=["F"])


def test_wegstein_acelera_y_sin_cortes_es_un_paso() -> None:
    accelerated = _recycle().solve()
    plain = _recycle().solve(accelerate=False)
    assert accelerated.converged and plain.converged
    assert accelerated.iterations < plain.iterations
    with pytest.raises(ConvergenceError, match="No convergió"):
        _recycle().solve(accelerate=False, max_iter=3)
    exact = _recycle().solve(initial={"R": accelerated.streams["R"], "Ignorada": Stream()})
    assert exact.iterations <= 2
    straight = Flowsheet(_catalog(), [Mixer("A", ("F",), ("X",))], {"F": Stream({"H2O": 1.0})})
    solution = straight.solve()
    assert solution.iterations == 1 and solution.tears == ()


def test_copias_modificadas_y_busquedas() -> None:
    plant = _recycle()
    assert plant.with_feed_flow("F", "SiO2", 200.0).feeds["F"].flow("SiO2") == 200.0
    assert plant.feeds["F"].flow("SiO2") == 100.0  # la original no cambia
    assert plant.with_unit_parameter("Div", "fraccion:R", 0.5).unit("Div").fractions == (0.5, 0.5)
    for call in [
        lambda: plant.with_feed_flow("Z", "SiO2", 1.0),
        lambda: plant.with_feed_flow("F", "Au", 1.0),
        lambda: plant.with_unit_parameter("Z", "x", 1.0),
        lambda: plant.unit("Z"),
    ]:
        with pytest.raises(KeyError):
            call()


# ---------------------------------------------------------------- control
def test_meta_y_variable_invalidas() -> None:
    for kwargs in [
        {"stream": "X", "prop": "otra", "value": 1.0},
        {"stream": "X", "prop": "flujo", "value": 1.0},
        {"stream": "X", "prop": "total", "value": float("inf")},
    ]:
        with pytest.raises(ValueError):
            Goal(**kwargs)
    with pytest.raises(ValueError):
        Manipulated("otro", "F", "SiO2", 0.0, 1.0)
    with pytest.raises(ValueError):
        Manipulated("alimentacion", "F", "SiO2", 1.0, 1.0)


def test_mediciones() -> None:
    stream = Stream({"H2SO4": 5.0, "H2O": 1000.0})
    assert Goal("X", "total", 0.0).measure(stream) == 1005.0
    assert Goal("X", "flujo", 0.0, "H2SO4").measure(stream) == 5.0
    assert Goal("X", "fraccion_masica", 0.0, "H2O").measure(stream) == pytest.approx(1000 / 1005)
    assert Goal("X", "g_por_kg_agua", 0.0, "H2SO4").measure(stream) == pytest.approx(5.0)
    with pytest.raises(ControlError):
        Goal("X", "g_por_kg_agua", 0.0, "H2SO4").measure(Stream({"H2SO4": 5.0}))


def _leaching():
    return load_plant(EXAMPLES / "lixiviacion_oxidos_cu.yaml")


def test_criterio_de_muerte_el_lazo_de_acido_converge_en_todo_el_rango() -> None:
    """Brief de la fase 1: si el lazo no converge de forma confiable, se cambia de enfoque."""
    plant = _leaching()
    base = plant.controllers[0]
    for target in np.linspace(0.5, 40.0, 20):
        goal = Goal(base.goal.stream, base.goal.prop, float(target), base.goal.species)
        result = solve_with_controllers(
            plant.flowsheet, [Controller(base.name, base.manipulated, goal)]
        )
        measured = goal.measure(result.solution.streams[goal.stream])
        assert measured == pytest.approx(target, rel=1e-6)


def test_meta_inalcanzable_avisa_con_numeros() -> None:
    plant = _leaching()
    base = plant.controllers[0]
    goal = Goal(base.goal.stream, base.goal.prop, 500.0, base.goal.species)
    with pytest.raises(ControlError, match="amplíe los límites"):
        solve_with_controllers(plant.flowsheet, [Controller("Alto", base.manipulated, goal)])


def test_lazo_sobre_un_parametro_de_equipo() -> None:
    controller = Controller(
        "Purga", Manipulated("equipo", "Div", "fraccion:R", 0.0, 0.95), Goal("Purga", "total", 30.0)
    )
    result = solve_with_controllers(_recycle(), [controller])
    assert result.solution.streams["Purga"].total == pytest.approx(30.0, rel=1e-6)
    assert 0.0 < result.values["Purga"] < 0.95


def test_dos_lazos_a_la_vez_acido_y_agua() -> None:
    plant = _leaching()
    acid = plant.controllers[0]
    water = Controller(
        "Agua",
        Manipulated("alimentacion", "Agua", "H2O", 50000.0, 400000.0),
        Goal("Descarga", "fraccion_masica", 0.6, "H2O"),
    )
    result = solve_with_controllers(plant.flowsheet, [acid, water])
    discharge = result.solution.streams["Descarga"]
    assert acid.goal.measure(discharge) == pytest.approx(5.0, rel=1e-6)
    assert discharge.mass_fraction("H2O") == pytest.approx(0.6, rel=1e-6)


def test_controladores_mal_definidos() -> None:
    plant = _leaching()
    acid = plant.controllers[0]
    bad_cases = [
        [],
        [acid, acid],
        [Controller("X", acid.manipulated, Goal("NoExiste", "total", 1.0))],
        [Controller("X", acid.manipulated, Goal("Descarga", "flujo", 1.0, "Au"))],
        [Controller("X", Manipulated("alimentacion", "Acido", "Au", 0.0, 1.0), acid.goal)],
    ]
    for controllers in bad_cases:
        with pytest.raises((ValueError, KeyError)):
            solve_with_controllers(plant.flowsheet, controllers)
    with pytest.raises(ControlError, match="evaluaciones"):
        solve_with_controllers(plant.flowsheet, [acid], max_evaluations=3)
