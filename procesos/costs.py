"""Fase 4: costo operativo por hora y por tonelada, con los precios que da el usuario.

- Reactivos: lo que entra por las alimentaciones, en t/h, por su precio por tonelada.
- Energía: el calor de los calentadores, evaporadores y reactores isotérmicos. El que se agrega
  se cobra al precio del calor; el que se retira, al del frío. La electricidad de los equipos que
  la consumen (electroobtención), al precio de la electricidad.
- Un costo fijo por hora (mano de obra, mantención), si se da.

La base «por tonelada» es el flujo total de una corriente, o el de un elemento contenido en ella
(p. ej. USD por tonelada de Cu en el PLS). El costo de capital no se estima: no hay correlaciones
públicas validadas para estos equipos.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from .flowsheet import Flowsheet, Solution
from .report import energy_balance, unit_power
from .stream import element_flows


@dataclass(frozen=True)
class CostSpec:
    basis_stream: str
    prices_per_t: Mapping[str, float] = field(default_factory=dict)  # especie -> precio/t
    basis_element: str | None = None
    heat_per_kwh: float = 0.0
    cooling_per_kwh: float = 0.0
    fixed_per_h: float = 0.0
    currency: str = "USD"
    electricity_per_kwh: float = 0.0

    def __post_init__(self) -> None:
        prices = dict(self.prices_per_t)
        values = [
            *prices.values(),
            self.heat_per_kwh,
            self.cooling_per_kwh,
            self.fixed_per_h,
            self.electricity_per_kwh,
        ]
        if any(v < 0 for v in values):
            raise ValueError("costos: los precios no pueden ser negativos")
        object.__setattr__(self, "prices_per_t", MappingProxyType(prices))


@dataclass(frozen=True)
class CostLine:
    concept: str
    quantity: float
    unit: str  # unidad de la cantidad por hora: "t/h" o "kW"
    unit_price: float
    cost_per_h: float


@dataclass(frozen=True)
class CostReport:
    lines: tuple[CostLine, ...]
    total_per_h: float
    basis_t_h: float
    basis_label: str
    currency: str

    @property
    def per_tonne(self) -> float:
        return self.total_per_h / self.basis_t_h


def _basis(flowsheet: Flowsheet, solution: Solution, spec: CostSpec) -> tuple[float, str]:
    if spec.basis_stream not in solution.streams:
        raise ValueError(f"costos: la corriente base {spec.basis_stream!r} no existe")
    stream = solution.streams[spec.basis_stream]
    if spec.basis_element is None:
        amount, label = stream.total, spec.basis_stream
    else:
        amount = element_flows(stream, flowsheet.catalog).get(spec.basis_element, 0.0)
        label = f"{spec.basis_element} en {spec.basis_stream}"
    if amount <= 0:
        raise ValueError(f"costos: la base {label!r} no tiene flujo; no hay costo por tonelada")
    return amount / 1000.0, label


def operating_cost(flowsheet: Flowsheet, solution: Solution, spec: CostSpec) -> CostReport:
    fed = {s for stream in flowsheet.feeds.values() for s in stream.flows}
    missing = sorted(set(spec.prices_per_t) - fed)
    if missing:
        raise ValueError(f"costos: {missing} tienen precio pero no entran por ninguna alimentación")
    lines = []
    for species, price in spec.prices_per_t.items():
        t_h = sum(solution.streams[n].flow(species) for n in flowsheet.feeds) / 1000.0
        lines.append(CostLine(species, t_h, "t/h", price, t_h * price))
    for row in energy_balance(flowsheet, solution):
        if row.duty > 0 and spec.heat_per_kwh > 0:
            cost = row.duty * spec.heat_per_kwh
            lines.append(CostLine(f"Calor · {row.name}", row.duty, "kW", spec.heat_per_kwh, cost))
        elif row.duty < 0 and spec.cooling_per_kwh > 0:
            cost = -row.duty * spec.cooling_per_kwh
            lines.append(
                CostLine(f"Frío · {row.name}", -row.duty, "kW", spec.cooling_per_kwh, cost)
            )
    if spec.electricity_per_kwh > 0:
        for unit in flowsheet.units:
            inputs = [solution.streams[n] for n in unit.inputs]
            power = unit_power(unit, inputs, flowsheet.catalog)
            if power > 0:
                price = spec.electricity_per_kwh
                concept = f"Electricidad · {unit.name}"
                lines.append(CostLine(concept, power, "kW", price, power * price))
    if spec.fixed_per_h > 0:
        lines.append(CostLine("Fijo", 1.0, "h", spec.fixed_per_h, spec.fixed_per_h))
    basis_t_h, label = _basis(flowsheet, solution, spec)
    total = sum(line.cost_per_h for line in lines)
    return CostReport(tuple(lines), total, basis_t_h, label, spec.currency)
