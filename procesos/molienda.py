"""Molienda: conecta con el proyecto hermano simulador-conminucion (extra opcional ``molienda``).

El equipo no cambia la composición (moler no reacciona): entrega el P80, la energía específica,
la potencia y, si se simula el circuito, la carga circulante. La potencia entra al costo como
electricidad y, con balance de calor, al balance de energía. Dos modos:

- **Bond** (``wi``, ``f80_um``, ``p80_um``): W = 10·Wi·(1/√P80 − 1/√F80), con la función de
  conminucion. Es el cálculo de diseño; conminucion lo validó con los 14 muestreos de Constancia.
- **Circuito** (``circuit`` y ``config``): simula con conminucion el circuito de molino y
  clasificador. La alimentación de la plantilla (``config.fresh``) se escala a los sólidos de la
  planta, con su agua. Con un molino de energía (``EnergyBallMill``), la potencia es la del
  molino; con un molino por tiempo de residencia, la de Bond con el P80 que resulta.

El agua que agrega el circuito (cajón, descarga del molino) se informa, pero no se suma a la
corriente: si importa, se agrega como una alimentación de agua. Ver docs/molienda.md.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Any

from .species import Catalog
from .stream import Stream
from .thermo import stream_enthalpy
from .units import _check_ports, _mixed, inlet_enthalpy

CIRCUITS = ("abierto", "cerrado_directo", "cerrado_inverso")
CASES = ("bougainville",)


def _conminucion() -> Any:
    try:
        import conminucion.bond
        import conminucion.circuits
        import conminucion.mill
    except ImportError as error:
        raise ImportError(
            "la molienda necesita simulador-conminucion: pip install -e '.[molienda]'"
        ) from error
    return conminucion


def template(case: str, power_kw: float | None = None) -> Any:
    """Configuración de circuito de conminucion validada contra MODSIM (``CASES``)."""
    if case not in CASES:
        raise ValueError(f"caso de molienda desconocido {case!r}; use uno de {CASES}")
    _conminucion()
    from conminucion.plantas_reales import bougainville_config

    config = bougainville_config("modsim")
    if power_kw is not None:
        config = replace(config, mill=replace(config.mill, power_kw=float(power_kw)))
    return config


@dataclass(frozen=True)
class GrindResult:
    solids_t_h: float
    f80_um: float
    p80_um: float
    bond_kwh_t: float
    power_kw: float
    power_basis: str  # "molino" o "Bond"
    circulating_load: float | None = None
    water_added_t_h: float = 0.0
    product: Any = None  # corriente de conminucion (granulometría), solo en modo circuito

    @property
    def specific_kwh_t(self) -> float:
        return self.power_kw / self.solids_t_h if self.solids_t_h > 0 else 0.0


@lru_cache(maxsize=64)
def _simulate(circuit: str, config: Any, wi: float, solids: float, water: float) -> GrindResult:
    cm = _conminucion()
    fresh = config.fresh.scaled(solids / config.fresh.total_solids).with_water(water)
    result = cm.circuits.simulate(circuit, replace(config, fresh=fresh, bond_wi=wi), tol=1e-10)
    product = result.streams[result.product]
    if isinstance(config.mill, cm.mill.EnergyBallMill):
        power, basis = config.mill.power_kw, "molino"
    else:
        power, basis = result.bond_kwh_t * solids, "Bond"
    return GrindResult(
        solids, fresh.f80, product.p80, result.bond_kwh_t, power, basis,
        result.circulating_load, product.water - fresh.water, product,
    )  # fmt: skip


@dataclass(frozen=True)
class Grinding:
    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    wi: float  # kWh/t, índice de trabajo de Bond
    f80_um: float | None = None
    p80_um: float | None = None
    circuit: str | None = None
    config: Any = None  # CircuitConfig de conminucion (plantilla)
    water: str = "H2O"

    def __post_init__(self) -> None:
        _check_ports(self.name, self.inputs, self.outputs, 1)
        if not (math.isfinite(float(self.wi)) and self.wi > 0):
            raise ValueError(f"{self.name}: el índice de Bond debe ser positivo: {self.wi}")
        bond = self.f80_um is not None or self.p80_um is not None
        if bond == (self.circuit is not None):
            raise ValueError(f"{self.name}: dé F80 y P80 (Bond) o un circuito, no ambos")
        if bond and not (self.f80_um and self.p80_um and self.f80_um > self.p80_um > 0):
            raise ValueError(f"{self.name}: se necesita F80 > P80 > 0 (µm)")
        if self.circuit is not None and (self.circuit not in CIRCUITS or self.config is None):
            raise ValueError(f"{self.name}: circuito uno de {CIRCUITS} y su configuración")

    def compute(self, inputs: Sequence[Stream], catalog: Catalog) -> tuple[Stream, ...]:
        return (_mixed(inputs, catalog),)

    def solve(self, inputs: Sequence[Stream], catalog: Catalog) -> GrindResult:
        feed = _mixed(inputs, catalog)
        solids = sum(f for n, f in feed.flows.items() if catalog[n].phase == "s") / 1000.0
        if solids <= 0:
            raise ValueError(f"{self.name}: no entran sólidos a la molienda")
        if self.circuit is not None:
            return _simulate(self.circuit, self.config, float(self.wi), solids,
                             feed.flow(self.water) / 1000.0)  # fmt: skip
        energy = _conminucion().bond.bond_energy(self.wi, self.f80_um, self.p80_um)
        return GrindResult(solids, float(self.f80_um), float(self.p80_um), energy,
                           energy * solids, "Bond")  # fmt: skip

    def power_kw(self, inputs: Sequence[Stream], catalog: Catalog) -> float:
        return self.solve(inputs, catalog).power_kw

    def heat_duty(self, inputs: Sequence[Stream], catalog: Catalog) -> float:
        """Calor (kW) para salir a la temperatura de mezcla: la energía del molino se pierde."""
        (out,) = self.compute(inputs, catalog)
        h_out = stream_enthalpy(out.flows, out.temperature, catalog)
        return h_out - inlet_enthalpy(inputs, catalog) - self.power_kw(inputs, catalog)

    def with_parameter(self, key: str, value: float) -> Grinding:
        """Claves: ``wi``, ``p80`` (modo Bond) o ``potencia_kw`` (molino de energía)."""
        if key == "wi":
            return replace(self, wi=value)
        if key == "p80" and self.circuit is None:
            return replace(self, p80_um=value)
        if key == "potencia_kw" and self.circuit is not None:
            mill = replace(self.config.mill, power_kw=value)
            return replace(self, config=replace(self.config, mill=mill))
        raise KeyError(f"{self.name}: parámetro desconocido {key!r}; use wi, p80 o potencia_kw")
