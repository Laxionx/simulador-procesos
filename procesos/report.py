"""Tabla de corrientes (CSV o Excel) y balances de masa por elemento y por equipo."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook

from .flowsheet import Flowsheet, Solution
from .stream import element_flows, mix
from .thermo import stream_enthalpy
from .units import Heater, Reactor


@dataclass(frozen=True)
class BalanceRow:
    name: str
    inflow: float
    outflow: float

    @property
    def relative_error(self) -> float:
        return abs(self.outflow - self.inflow) / max(abs(self.inflow), 1e-12)


def stream_table(flowsheet: Flowsheet, solution: Solution) -> list[list[object]]:
    """Filas: especies, total, temperatura y presión; columnas: corrientes en orden de cálculo."""
    names = list(flowsheet.feeds) + [o for u in flowsheet.order for o in u.outputs]
    streams = [solution.streams[n] for n in names]
    rows: list[list[object]] = [["Especie (kg/h)", *names]]
    rows += [[s, *(st.flow(s) for st in streams)] for s in flowsheet.catalog.names]
    rows.append(["Total (kg/h)", *(st.total for st in streams)])
    rows.append(["Temperatura (°C)", *(st.temperature for st in streams)])
    rows.append(["Presión (kPa)", *(st.pressure for st in streams)])
    return rows


def write_csv(rows: list[list[object]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        csv.writer(handle, delimiter=";").writerows(rows)
    return path


def write_xlsx(rows: list[list[object]], path: Path, title: str = "Corrientes") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = title[:31]
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    return path


def element_balance(flowsheet: Flowsheet, solution: Solution) -> list[BalanceRow]:
    """Cada elemento que entra por las alimentaciones debe salir por los productos."""
    inflow = element_flows(mix(list(flowsheet.feeds.values())), flowsheet.catalog)
    products = [solution.streams[n] for n in flowsheet.products]
    outflow = element_flows(mix(products), flowsheet.catalog) if products else {}
    elements = sorted(set(inflow) | set(outflow))
    return [BalanceRow(e, inflow.get(e, 0.0), outflow.get(e, 0.0)) for e in elements]


def unit_balance(flowsheet: Flowsheet, solution: Solution) -> list[BalanceRow]:
    """Masa total que entra y sale de cada equipo."""
    return [
        BalanceRow(
            unit.name,
            sum(solution.streams[n].total for n in unit.inputs),
            sum(solution.streams[n].total for n in unit.outputs),
        )
        for unit in flowsheet.units
    ]


@dataclass(frozen=True)
class EnergyRow:
    """Balance de energía de un equipo (kW): entra + calor agregado = sale."""

    name: str
    inflow: float
    duty: float
    outflow: float

    @property
    def relative_error(self) -> float:
        scale = max(abs(self.inflow), abs(self.outflow), abs(self.duty), 1e-9)
        return abs(self.inflow + self.duty - self.outflow) / scale


def energy_balance(flowsheet: Flowsheet, solution: Solution) -> list[EnergyRow]:
    """Entalpía que entra y sale de cada equipo y el calor que recibe (fase 2)."""
    catalog = flowsheet.catalog
    if catalog.thermo is None:
        return []

    def h(name: str) -> float:
        s = solution.streams[name]
        return stream_enthalpy(s.flows, s.temperature, catalog)

    rows = []
    for unit in flowsheet.units:
        inputs = [solution.streams[n] for n in unit.inputs]
        duty = (
            unit.heat_duty(inputs, catalog)
            if isinstance(unit, Heater)
            or (isinstance(unit, Reactor) and unit.temperature is not None)
            else 0.0
        )
        rows.append(
            EnergyRow(
                unit.name,
                sum(h(n) for n in unit.inputs),
                duty,
                sum(h(n) for n in unit.outputs),
            )
        )
    return rows


def worst_closure(flowsheet: Flowsheet, solution: Solution) -> float:
    """Peor error relativo de cierre: elementos, masa por equipo y, si hay, energía."""
    rows = element_balance(flowsheet, solution) + unit_balance(flowsheet, solution)
    mass = max((r.relative_error for r in rows if r.inflow > 0), default=0.0)
    energy = max((r.relative_error for r in energy_balance(flowsheet, solution)), default=0.0)
    return max(mass, energy)
