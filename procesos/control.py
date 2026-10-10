"""Lazos de control: ajustar una variable de la planta hasta que una propiedad llegue a su meta.

Es el equivalente de los «controladores» de los simuladores comerciales: por ejemplo, ajustar el
ácido que entra hasta tener la acidez libre deseada a la salida del reactor. Un lazo se resuelve
con Brent (siempre converge si la meta está dentro de los límites); varios, en conjunto con el
método híbrido de Powell sobre variables normalizadas.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import numpy as np
from scipy.optimize import brentq, root

from .flowsheet import Flowsheet, Solution
from .stream import Stream

PROPERTIES = ("flujo", "total", "fraccion_masica", "g_por_kg_agua", "temperatura")
WATER = "H2O"


class ControlError(RuntimeError):
    """La meta no se puede alcanzar dentro de los límites o el ajuste no convergió."""


@dataclass(frozen=True)
class Manipulated:
    """Qué se ajusta: el flujo de una especie en una alimentación, o un parámetro de un equipo."""

    kind: str  # "alimentacion" o "equipo"
    target: str  # nombre de la alimentación o del equipo
    key: str  # especie (alimentación) o clave del parámetro (equipo)
    lower: float
    upper: float

    def __post_init__(self) -> None:
        if self.kind not in ("alimentacion", "equipo"):
            raise ValueError(f"Tipo de variable inválido: {self.kind!r}")
        if not (
            math.isfinite(self.lower) and math.isfinite(self.upper) and self.lower < self.upper
        ):
            raise ValueError(
                f"Límites inválidos para {self.target}/{self.key}: {self.lower}..{self.upper}"
            )

    def apply(self, flowsheet: Flowsheet, value: float) -> Flowsheet:
        if self.kind == "alimentacion":
            return flowsheet.with_feed_flow(self.target, self.key, value)
        return flowsheet.with_unit_parameter(self.target, self.key, value)


@dataclass(frozen=True)
class Goal:
    """Qué se mide: una propiedad de una corriente y el valor buscado."""

    stream: str
    prop: str
    value: float
    species: str | None = None

    def __post_init__(self) -> None:
        if self.prop not in PROPERTIES:
            raise ValueError(f"Propiedad desconocida {self.prop!r}; use una de {PROPERTIES}")
        if self.prop not in ("total", "temperatura") and not self.species:
            raise ValueError(f"La propiedad {self.prop!r} necesita una especie")
        if not math.isfinite(self.value):
            raise ValueError(f"Meta no finita: {self.value}")

    def measure(self, stream: Stream) -> float:
        if self.prop == "total":
            return stream.total
        if self.prop == "temperatura":
            return stream.temperature
        assert self.species is not None
        if self.prop == "flujo":
            return stream.flow(self.species)
        if self.prop == "fraccion_masica":
            return stream.mass_fraction(self.species)
        water = stream.flow(WATER)
        if water <= 0:
            raise ControlError(f"La corriente {self.stream} no tiene agua para medir g/kg de agua")
        return 1000.0 * stream.flow(self.species) / water


@dataclass(frozen=True)
class Controller:
    name: str
    manipulated: Manipulated
    goal: Goal


@dataclass(frozen=True)
class ControlledSolution:
    solution: Solution
    flowsheet: Flowsheet
    values: Mapping[str, float]
    """Valor final de cada variable ajustada, por nombre de controlador."""
    evaluations: int


def _check(flowsheet: Flowsheet, controllers: Sequence[Controller]) -> None:
    if not controllers:
        raise ValueError("No hay controladores que resolver")
    names = [c.name for c in controllers]
    if len(set(names)) != len(names):
        raise ValueError(f"Controladores con nombre repetido: {names}")
    known = set(flowsheet.feeds) | {o for u in flowsheet.units for o in u.outputs}
    for c in controllers:
        if c.goal.stream not in known:
            raise ValueError(f"{c.name}: la corriente {c.goal.stream!r} no existe")
        if c.goal.species and c.goal.species not in flowsheet.catalog:
            raise ValueError(f"{c.name}: la especie {c.goal.species!r} no está en el catálogo")
        # Probar la variable en su límite inferior detecta nombres o claves inválidos de una vez.
        c.manipulated.apply(flowsheet, c.manipulated.lower)


def solve_with_controllers(
    flowsheet: Flowsheet,
    controllers: Sequence[Controller],
    tol: float = 1e-9,
    max_evaluations: int = 200,
    **solve_options: Any,
) -> ControlledSolution:
    _check(flowsheet, controllers)
    evaluations = 0
    last: dict[str, object] = {}

    def run(values: Sequence[float]) -> np.ndarray:
        nonlocal evaluations
        evaluations += 1
        if evaluations > max_evaluations:
            raise ControlError(f"Se superaron {max_evaluations} evaluaciones de la planta")
        current = flowsheet
        for controller, value in zip(controllers, values, strict=True):
            current = controller.manipulated.apply(current, float(value))
        solution = current.solve(**solve_options)
        last.update(flowsheet=current, solution=solution, values=list(values))
        return np.array(
            [
                (c.goal.measure(solution.streams[c.goal.stream]) - c.goal.value)
                / max(abs(c.goal.value), 1.0)
                for c in controllers
            ]
        )

    if len(controllers) == 1:
        variable = controllers[0].manipulated
        low, high = run([variable.lower])[0], run([variable.upper])[0]
        if low == 0 or high == 0:
            value = variable.lower if low == 0 else variable.upper
        elif np.sign(low) == np.sign(high):
            raise ControlError(
                f"{controllers[0].name}: la meta no se alcanza entre {variable.lower:g} y "
                f"{variable.upper:g} (desvíos relativos {low:+.4g} y {high:+.4g}); "
                "amplíe los límites"
            )
        else:
            span = variable.upper - variable.lower
            value = brentq(
                lambda v: run([v])[0],
                variable.lower,
                variable.upper,
                xtol=tol * max(span, 1.0),
                rtol=4 * np.finfo(float).eps,
            )
        residual = run([value])
    else:
        lows = np.array([c.manipulated.lower for c in controllers])
        spans = np.array([c.manipulated.upper - c.manipulated.lower for c in controllers])
        result = root(
            lambda u: run(lows + np.clip(u, 0.0, 1.0) * spans),
            x0=np.full(len(controllers), 0.5),
            method="hybr",
            tol=tol,
        )
        unit = np.clip(result.x, 0.0, 1.0)
        residual = run(lows + unit * spans)
        if not result.success and np.max(np.abs(residual)) > 1e3 * tol:
            raise ControlError(f"Los controladores no convergieron: {result.message}")
    if np.max(np.abs(residual)) > 1e3 * tol:
        raise ControlError(
            f"Desvío final {np.max(np.abs(residual)):.3e} sobre la tolerancia {tol:g}"
        )
    values = dict(zip((c.name for c in controllers), map(float, last["values"]), strict=True))
    return ControlledSolution(
        solution=last["solution"],  # type: ignore[arg-type]
        flowsheet=last["flowsheet"],  # type: ignore[arg-type]
        values=MappingProxyType(values),
        evaluations=evaluations,
    )
