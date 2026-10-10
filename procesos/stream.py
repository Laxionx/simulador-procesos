"""Corrientes de proceso: flujo másico por especie (kg/h), temperatura y presión.

En la fase 1 la temperatura y la presión se transportan pero no se balancean: un mezclador
promedia la temperatura por masa como aproximación hasta que exista el balance de calor.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from .elements import ATOMIC_WEIGHTS
from .species import Catalog

STANDARD_TEMPERATURE = 25.0
STANDARD_PRESSURE = 101.325


@dataclass(frozen=True)
class Stream:
    flows: Mapping[str, float] = field(default_factory=dict)
    temperature: float = STANDARD_TEMPERATURE
    pressure: float = STANDARD_PRESSURE

    def __post_init__(self) -> None:
        clean: dict[str, float] = {}
        for name, value in self.flows.items():
            value = float(value)
            if not math.isfinite(value):
                raise ValueError(f"Flujo no finito para {name!r}: {value}")
            if value < 0:
                raise ValueError(f"Flujo negativo para {name!r}: {value} kg/h")
            if value > 0:
                clean[name] = value
        if not math.isfinite(self.temperature) or self.temperature < -273.15:
            raise ValueError(f"Temperatura imposible: {self.temperature} °C")
        if not math.isfinite(self.pressure) or self.pressure <= 0:
            raise ValueError(f"Presión imposible: {self.pressure} kPa")
        object.__setattr__(self, "flows", MappingProxyType(clean))

    @property
    def total(self) -> float:
        return sum(self.flows.values())

    def flow(self, name: str) -> float:
        return self.flows.get(name, 0.0)

    def mass_fraction(self, name: str) -> float:
        total = self.total
        return self.flow(name) / total if total > 0 else 0.0

    def with_flow(self, name: str, value: float) -> Stream:
        flows = dict(self.flows)
        flows[name] = value
        return Stream(flows, self.temperature, self.pressure)


def mix(streams: Sequence[Stream]) -> Stream:
    """Suma de flujos; temperatura promediada por masa y la menor presión de entrada."""
    if not streams:
        raise ValueError("No hay corrientes que mezclar")
    flows: dict[str, float] = {}
    for stream in streams:
        for name, value in stream.flows.items():
            flows[name] = flows.get(name, 0.0) + value
    total = sum(s.total for s in streams)
    temperature = (
        sum(s.temperature * s.total for s in streams) / total
        if total > 0
        else streams[0].temperature
    )
    return Stream(flows, temperature, min(s.pressure for s in streams))


def moles(stream: Stream, catalog: Catalog) -> dict[str, float]:
    """Flujo molar por especie en kmol/h."""
    return {name: value / catalog[name].molar_mass for name, value in stream.flows.items()}


def element_flows(stream: Stream, catalog: Catalog) -> dict[str, float]:
    """Flujo másico de cada elemento en kg/h."""
    result: dict[str, float] = {}
    for name, kmol in moles(stream, catalog).items():
        for element, count in catalog[name].composition.items():
            result[element] = result.get(element, 0.0) + kmol * count * ATOMIC_WEIGHTS[element]
    return result
