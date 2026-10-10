"""Planta: equipos conectados por corrientes, resuelta en forma secuencial-modular.

Los reciclos se rompen en corrientes de corte (elegidas automáticamente si no se indican) y se
iteran por sustitución directa acelerada con Wegstein (q acotado en [-5, 0]), igual que en el
simulador de conminución del mismo autor.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np

from .reactions import check_balance
from .species import Catalog
from .stream import STANDARD_PRESSURE, STANDARD_TEMPERATURE, Stream
from .units import Reactor, Unit, unit_species


class ConvergenceError(RuntimeError):
    """El reciclo no convergió dentro del máximo de iteraciones."""


@dataclass(frozen=True)
class Solution:
    streams: Mapping[str, Stream]
    iterations: int
    converged: bool
    residuals: tuple[float, ...] = field(default_factory=tuple)
    tears: tuple[str, ...] = ()


class Flowsheet:
    def __init__(
        self,
        catalog: Catalog,
        units: Sequence[Unit],
        feeds: Mapping[str, Stream],
        tears: Sequence[str] | None = None,
    ) -> None:
        self.catalog = catalog
        self.units = tuple(units)
        self.feeds = MappingProxyType(dict(feeds))
        self._validate()
        self.order, self.tears = self._sequence(None if tears is None else tuple(tears))

    # ------------------------------------------------------------------ validación
    def _validate(self) -> None:
        names = [u.name for u in self.units]
        if len(set(names)) != len(names):
            raise ValueError(
                f"Equipos con nombre repetido: {sorted({n for n in names if names.count(n) > 1})}"
            )
        produced = [o for u in self.units for o in u.outputs]
        repeated = sorted(
            {o for o in produced if produced.count(o) > 1} | (set(produced) & set(self.feeds))
        )
        if repeated:
            raise ValueError(f"Cada corriente debe tener un único origen; repetidas: {repeated}")
        known = set(produced) | set(self.feeds)
        for unit in self.units:
            missing = sorted(set(unit.inputs) - known)
            if missing:
                raise ValueError(f"{unit.name} usa corrientes que nadie produce: {missing}")
            unknown = sorted(unit_species(unit) - set(self.catalog.names))
            if unknown:
                raise ValueError(f"{unit.name} menciona especies fuera del catálogo: {unknown}")
            if isinstance(unit, Reactor):
                for reaction in unit.reactions:
                    check_balance(reaction, self.catalog)
        consumed = {i for u in self.units for i in u.inputs}
        unused = sorted(set(self.feeds) - consumed)
        if unused:
            raise ValueError(f"Alimentaciones que ningún equipo usa: {unused}")
        for name, stream in self.feeds.items():
            outside = sorted(set(stream.flows) - set(self.catalog.names))
            if outside:
                raise ValueError(
                    f"La alimentación {name} trae especies fuera del catálogo: {outside}"
                )

    # ------------------------------------------------------------------ orden de cálculo
    def _sequence(self, tears: tuple[str, ...] | None) -> tuple[tuple[Unit, ...], tuple[str, ...]]:
        produced = {o for u in self.units for o in u.outputs}
        chosen = list(tears or ())
        unknown = sorted(set(chosen) - produced)
        if unknown:
            raise ValueError(f"Corrientes de corte que ningún equipo produce: {unknown}")
        available = set(self.feeds) | set(chosen)
        pending, order = list(self.units), []
        while pending:
            ready = [u for u in pending if set(u.inputs) <= available]
            if not ready:
                if tears is not None:
                    stuck = [u.name for u in pending]
                    raise ValueError(f"Ciclo sin corriente de corte; equipos atascados: {stuck}")
                # Corte automático: abre el ciclo el equipo pendiente con menos entradas
                # desconocidas.
                opener = min(pending, key=lambda u: len(set(u.inputs) - available))
                new = sorted(set(opener.inputs) - available)
                chosen.extend(new)
                available |= set(new)
                continue
            for unit in ready:
                order.append(unit)
                pending.remove(unit)
                available |= set(unit.outputs)
        return tuple(order), tuple(chosen)

    @property
    def products(self) -> tuple[str, ...]:
        """Corrientes que salen de la planta: producidas y no consumidas por ningún equipo."""
        consumed = {i for u in self.units for i in u.inputs}
        return tuple(o for u in self.units for o in u.outputs if o not in consumed)

    def unit(self, name: str) -> Unit:
        for unit in self.units:
            if unit.name == name:
                return unit
        raise KeyError(f"Equipo desconocido: {name!r}")

    # ------------------------------------------------------------------ copias modificadas
    def with_feed_flow(self, feed: str, species: str, value: float) -> Flowsheet:
        if feed not in self.feeds:
            raise KeyError(f"Alimentación desconocida: {feed!r}")
        if species not in self.catalog:
            raise KeyError(f"Especie desconocida: {species!r}")
        feeds = dict(self.feeds)
        feeds[feed] = feeds[feed].with_flow(species, value)
        return Flowsheet(self.catalog, self.units, feeds, self.tears)

    def with_unit_parameter(self, unit_name: str, key: str, value: float) -> Flowsheet:
        units = [u.with_parameter(key, value) if u.name == unit_name else u for u in self.units]
        if all(u.name != unit_name for u in self.units):
            raise KeyError(f"Equipo desconocido: {unit_name!r}")
        return Flowsheet(self.catalog, units, self.feeds, self.tears)

    # ------------------------------------------------------------------ cálculo
    def _encode(self, streams: Mapping[str, Stream]) -> np.ndarray:
        parts = []
        for name in self.tears:
            s = streams[name]
            parts.append([s.flow(n) for n in self.catalog.names] + [s.temperature, s.pressure])
        return np.asarray(parts, dtype=float).ravel()

    def _decode(self, x: np.ndarray) -> dict[str, Stream]:
        width = len(self.catalog) + 2
        result = {}
        for i, name in enumerate(self.tears):
            block = x[i * width : (i + 1) * width]
            flows = dict(zip(self.catalog.names, np.maximum(block[:-2], 0.0), strict=True))
            result[name] = Stream(flows, float(block[-2]), float(block[-1]))
        return result

    def _pass(self, x: np.ndarray) -> tuple[dict[str, Stream], dict[str, Stream]]:
        streams: dict[str, Stream] = dict(self.feeds)
        streams.update(self._decode(x))
        produced: dict[str, Stream] = {}
        for unit in self.order:
            outputs = unit.compute([streams[n] for n in unit.inputs], self.catalog)
            for name, stream in zip(unit.outputs, outputs, strict=True):
                (produced if name in self.tears else streams)[name] = stream
        return streams, produced

    def solve(
        self,
        tol: float = 1e-10,
        max_iter: int = 1000,
        accelerate: bool = True,
        initial: Mapping[str, Stream] | None = None,
    ) -> Solution:
        if not self.tears:
            streams, _ = self._pass(np.zeros(0))
            return Solution(MappingProxyType(streams), 1, True, (0.0,), ())
        guess = {t: Stream({}, STANDARD_TEMPERATURE, STANDARD_PRESSURE) for t in self.tears}
        guess.update({k: v for k, v in (initial or {}).items() if k in self.tears})
        x = self._encode(guess)
        width = len(self.catalog) + 2
        flow_mask = np.tile(np.r_[np.ones(width - 2, bool), False, False], len(self.tears))
        x_prev = g_prev = None
        residuals: list[float] = []
        for iteration in range(1, max_iter + 1):
            streams, produced = self._pass(x)
            g = self._encode(produced)
            error = float(np.max(np.abs(g - x) / (1.0 + np.abs(g))))
            residuals.append(error)
            if error <= tol:
                streams.update(produced)
                return Solution(
                    MappingProxyType(streams), iteration, True, tuple(residuals), self.tears
                )
            if accelerate and g_prev is not None:
                dx = x - x_prev
                moving = np.abs(dx) > 1e-14
                slope = np.where(moving, (g - g_prev) / np.where(moving, dx, 1.0), 0.0)
                with np.errstate(divide="ignore", invalid="ignore"):
                    q = np.clip(np.nan_to_num(slope / (slope - 1.0)), -5.0, 0.0)
                x_new = q * x + (1.0 - q) * g
            else:
                x_new = g
            x_prev, g_prev = x, g
            x = np.where(flow_mask, np.maximum(x_new, 0.0), x_new)
        raise ConvergenceError(
            f"No convergió en {max_iter} iteraciones (error {residuals[-1]:.3e} > {tol:g}); "
            f"cortes: {list(self.tears)}"
        )


def with_tears(flowsheet: Flowsheet, tears: Sequence[str]) -> Flowsheet:
    """Copia de la planta con corrientes de corte fijadas a mano."""
    return Flowsheet(flowsheet.catalog, flowsheet.units, flowsheet.feeds, tears)


__all__ = ["ConvergenceError", "Flowsheet", "Solution", "with_tears"]
