"""Equipos de la planta: mezclador, divisor, separador por especie, reactor y calentador.

Cada equipo es inmutable; ``with_parameter`` devuelve una copia con un parámetro cambiado, que
es lo que usan los lazos de control para manipular la planta. Si el catálogo trae datos
termodinámicos (fase 2), la temperatura de cada salida sale del balance de entalpía.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Protocol

from scipy.optimize import brentq

from .elements import strip_phase
from .reactions import Reaction
from .saturation import tsat_c
from .species import Catalog
from .stream import Stream, mix, moles
from .thermo import stream_enthalpy, temperature_for

DEFAULT_LIMIT_C = 500.0  # °C: tope de búsqueda para vapor sobrecalentado


class Unit(Protocol):
    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]

    def compute(self, inputs: Sequence[Stream], catalog: Catalog) -> tuple[Stream, ...]: ...

    def with_parameter(self, key: str, value: float) -> Unit: ...


def _check_fraction(value: float, label: str) -> float:
    value = float(value)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} debe estar entre 0 y 1: {value}")
    return value


def _check_temperature(value: float | None, label: str) -> float | None:
    if value is None:
        return None
    value = float(value)
    if not math.isfinite(value) or value <= -273.15:
        raise ValueError(f"{label}: temperatura imposible ({value} °C)")
    return value


def inlet_enthalpy(inputs: Sequence[Stream], catalog: Catalog) -> float:
    """Entalpía total que entra (kW)."""
    return sum(stream_enthalpy(s.flows, s.temperature, catalog) for s in inputs)


def _mixed(inputs: Sequence[Stream], catalog: Catalog) -> Stream:
    """Mezcla; con balance de calor, la temperatura es la que conserva la entalpía."""
    feed = mix(inputs)
    if catalog.thermo is None or len(inputs) < 2:
        return feed
    t = temperature_for(feed.flows, inlet_enthalpy(inputs, catalog), catalog, feed.temperature)
    return Stream(feed.flows, t, feed.pressure)


def _check_ports(
    name: str, inputs: tuple[str, ...], outputs: tuple[str, ...], n_out: int | None
) -> None:
    if not name:
        raise ValueError("El equipo necesita un nombre")
    if not inputs:
        raise ValueError(f"{name}: necesita al menos una entrada")
    if n_out is not None and len(outputs) != n_out:
        raise ValueError(f"{name}: necesita exactamente {n_out} salida(s), tiene {len(outputs)}")
    if len(set(outputs)) != len(outputs) or set(inputs) & set(outputs):
        raise ValueError(f"{name}: salidas repetidas o iguales a una entrada")


@dataclass(frozen=True)
class Mixer:
    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]

    def __post_init__(self) -> None:
        _check_ports(self.name, self.inputs, self.outputs, 1)

    def compute(self, inputs: Sequence[Stream], catalog: Catalog) -> tuple[Stream, ...]:
        return (_mixed(inputs, catalog),)

    def with_parameter(self, key: str, value: float) -> Mixer:
        raise KeyError(f"{self.name}: el mezclador no tiene parámetros ajustables ({key!r})")


@dataclass(frozen=True)
class Splitter:
    """Reparte la corriente mezclada en fracciones fijas, iguales para todas las especies."""

    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    fractions: tuple[float, ...]

    def __post_init__(self) -> None:
        _check_ports(self.name, self.inputs, self.outputs, None)
        if len(self.outputs) < 2 or len(self.fractions) != len(self.outputs):
            raise ValueError(f"{self.name}: una fracción por cada salida (al menos 2)")
        fractions = tuple(_check_fraction(f, f"{self.name}: fracción") for f in self.fractions)
        if abs(sum(fractions) - 1.0) > 1e-9:
            raise ValueError(f"{self.name}: las fracciones deben sumar 1 (suman {sum(fractions)})")
        object.__setattr__(self, "fractions", fractions)

    def compute(self, inputs: Sequence[Stream], catalog: Catalog) -> tuple[Stream, ...]:
        feed = _mixed(inputs, catalog)
        return tuple(
            Stream({n: v * f for n, v in feed.flows.items()}, feed.temperature, feed.pressure)
            for f in self.fractions
        )

    def with_parameter(self, key: str, value: float) -> Splitter:
        """``'fraccion:<salida>'``: fija esa fracción y reparte el resto en proporción."""
        kind, _, output = key.partition(":")
        if kind != "fraccion" or output not in self.outputs:
            raise KeyError(f"{self.name}: parámetro desconocido {key!r}; use 'fraccion:<salida>'")
        value = _check_fraction(value, f"{self.name}: fracción de {output}")
        index = self.outputs.index(output)
        others = [f for i, f in enumerate(self.fractions) if i != index]
        rest = sum(others)
        scaled = (
            [f / rest * (1 - value) for f in others]
            if rest > 0
            else [(1 - value) / len(others)] * len(others)
        )
        scaled.insert(index, value)
        return replace(self, fractions=tuple(scaled))


@dataclass(frozen=True)
class Separator:
    """Envía a la primera salida una fracción de cada especie (recuperación); el resto a la segunda.

    Modela flotación, espesamiento, filtración o lavado mientras no haya un modelo físico.
    """

    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    recoveries: Mapping[str, float]
    default: float = 0.0

    def __post_init__(self) -> None:
        _check_ports(self.name, self.inputs, self.outputs, 2)
        clean = {
            n: _check_fraction(v, f"{self.name}: recuperación de {n}")
            for n, v in self.recoveries.items()
        }
        object.__setattr__(self, "recoveries", MappingProxyType(clean))
        object.__setattr__(self, "default", _check_fraction(self.default, f"{self.name}: defecto"))

    def recovery(self, species: str) -> float:
        return self.recoveries.get(species, self.default)

    def compute(self, inputs: Sequence[Stream], catalog: Catalog) -> tuple[Stream, ...]:
        feed = _mixed(inputs, catalog)
        first = {n: v * self.recovery(n) for n, v in feed.flows.items()}
        second = {n: v - first[n] for n, v in feed.flows.items()}
        return (
            Stream(first, feed.temperature, feed.pressure),
            Stream(second, feed.temperature, feed.pressure),
        )

    def with_parameter(self, key: str, value: float) -> Separator:
        """``'recuperacion:<especie>'`` o ``'recuperacion_por_defecto'``."""
        if key == "recuperacion_por_defecto":
            return replace(self, default=value)
        kind, _, species = key.partition(":")
        if kind != "recuperacion" or not species:
            raise KeyError(
                f"{self.name}: parámetro desconocido {key!r}; use 'recuperacion:<especie>'"
            )
        recoveries = dict(self.recoveries)
        recoveries[species] = value
        return replace(self, recoveries=recoveries)


@dataclass(frozen=True)
class ReactionExtent:
    reaction: Reaction
    extent: float
    """Avance en kmol/h (moles de reacción)."""
    achieved_conversion: float
    limited_by: str | None
    """Reactivo que se agotó antes que el componente clave, si lo hubo."""


@dataclass(frozen=True)
class Reactor:
    """Aplica las reacciones en orden sobre la mezcla de sus entradas.

    Con balance de calor: si `temperature` (°C) está fijada, el reactor es isotérmico y
    `heat_duty` da el calor que hay que agregar (kW; negativo = hay que retirar); si no, es
    adiabático y la temperatura de salida sale del balance.
    """

    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    reactions: tuple[Reaction, ...]
    temperature: float | None = None

    def __post_init__(self) -> None:
        _check_ports(self.name, self.inputs, self.outputs, 1)
        if not self.reactions:
            raise ValueError(f"{self.name}: el reactor necesita al menos una reacción")
        object.__setattr__(self, "temperature", _check_temperature(self.temperature, self.name))

    def extents(self, inputs: Sequence[Stream], catalog: Catalog) -> list[ReactionExtent]:
        amounts = moles(mix(inputs), catalog)
        result: list[ReactionExtent] = []
        for reaction in self.reactions:
            key_coefficient = -reaction.stoichiometry[reaction.key]
            key_available = amounts.get(reaction.key, 0.0)
            wanted = reaction.conversion * key_available / key_coefficient
            extent, limited_by = wanted, None
            for species, coefficient in reaction.reactants.items():
                possible = amounts.get(species, 0.0) / coefficient
                if possible < extent:
                    extent, limited_by = possible, species
            for species, coefficient in reaction.stoichiometry.items():
                amounts[species] = max(amounts.get(species, 0.0) + coefficient * extent, 0.0)
            achieved = extent * key_coefficient / key_available if key_available > 0 else 0.0
            result.append(ReactionExtent(reaction, extent, achieved, limited_by))
        return result

    def compute(self, inputs: Sequence[Stream], catalog: Catalog) -> tuple[Stream, ...]:
        feed = mix(inputs)
        amounts = moles(feed, catalog)
        for item in self.extents(inputs, catalog):
            for species, coefficient in item.reaction.stoichiometry.items():
                amounts[species] = max(amounts.get(species, 0.0) + coefficient * item.extent, 0.0)
        flows = {n: kmol * catalog[n].molar_mass for n, kmol in amounts.items()}
        if self.temperature is not None:
            t = self.temperature
        elif catalog.thermo is not None:
            t = temperature_for(flows, inlet_enthalpy(inputs, catalog), catalog, feed.temperature)
        else:
            t = feed.temperature
        return (Stream(flows, t, feed.pressure),)

    def heat_duty(self, inputs: Sequence[Stream], catalog: Catalog) -> float:
        """Calor agregado (kW): entalpía que sale menos la que entra (0 si es adiabático)."""
        (out,) = self.compute(inputs, catalog)
        h_out = stream_enthalpy(out.flows, out.temperature, catalog)
        return h_out - inlet_enthalpy(inputs, catalog)

    def with_parameter(self, key: str, value: float) -> Reactor:
        """``'conversion:<n>'`` (n desde 1, en orden) o ``'temperatura'``."""
        if key == "temperatura":
            return replace(self, temperature=value)
        kind, _, index_text = key.partition(":")
        if kind != "conversion" or not index_text.isdigit():
            raise KeyError(f"{self.name}: parámetro desconocido {key!r}; use 'conversion:<n>'")
        index = int(index_text) - 1
        if not 0 <= index < len(self.reactions):
            raise KeyError(f"{self.name}: no existe la reacción {index + 1}")
        reactions = list(self.reactions)
        reactions[index] = replace(reactions[index], conversion=value)
        return replace(self, reactions=tuple(reactions))


@dataclass(frozen=True)
class Heater:
    """Calentador o enfriador: fija la temperatura de salida (°C) o agrega un calor (kW;
    negativo = enfría). Con temperatura fija, `heat_duty` da el calor necesario."""

    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    temperature: float | None = None
    duty_kw: float | None = None

    def __post_init__(self) -> None:
        _check_ports(self.name, self.inputs, self.outputs, 1)
        if (self.temperature is None) == (self.duty_kw is None):
            raise ValueError(f"{self.name}: indique temperatura o calor, no ambos ni ninguno")
        object.__setattr__(self, "temperature", _check_temperature(self.temperature, self.name))
        if self.duty_kw is not None and not math.isfinite(float(self.duty_kw)):
            raise ValueError(f"{self.name}: calor no finito")

    def compute(self, inputs: Sequence[Stream], catalog: Catalog) -> tuple[Stream, ...]:
        feed = _mixed(inputs, catalog)
        if self.temperature is not None:
            return (Stream(feed.flows, self.temperature, feed.pressure),)
        if catalog.thermo is None:
            raise ValueError(f"{self.name}: dar un calor exige activar el balance de calor")
        target = inlet_enthalpy(inputs, catalog) + float(self.duty_kw or 0.0)
        t = temperature_for(feed.flows, target, catalog, feed.temperature)
        return (Stream(feed.flows, t, feed.pressure),)

    def heat_duty(self, inputs: Sequence[Stream], catalog: Catalog) -> float:
        if self.duty_kw is not None:
            return float(self.duty_kw)
        (out,) = self.compute(inputs, catalog)
        h_out = stream_enthalpy(out.flows, out.temperature, catalog)
        return h_out - inlet_enthalpy(inputs, catalog)

    def with_parameter(self, key: str, value: float) -> Heater:
        """``'temperatura'`` o ``'calor_kw'``."""
        if key == "temperatura":
            return replace(self, temperature=value, duty_kw=None)
        if key == "calor_kw":
            return replace(self, temperature=None, duty_kw=value)
        raise KeyError(
            f"{self.name}: parámetro desconocido {key!r}; use 'temperatura' o 'calor_kw'"
        )


@dataclass(frozen=True)
class Evaporator:
    """Evaporador o flash a presión fija (fase 2b). Agrega un calor (kW) y reparte el agua entre
    líquido y vapor según la saturación IAPWS-IF97. Salidas: (líquido, vapor). Los gases van al
    vapor; sólidos y solutos, al líquido. No modela la elevación del punto de ebullición por los
    solutos ni la presión parcial de otros gases."""

    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    duty_kw: float = 0.0
    pressure_kpa: float = 101.325

    def __post_init__(self) -> None:
        _check_ports(self.name, self.inputs, self.outputs, 2)
        if not math.isfinite(float(self.duty_kw)) or not self.pressure_kpa > 0:
            raise ValueError(f"{self.name}: calor finito y presión positiva")

    def _water_names(self, catalog: Catalog) -> tuple[str, str]:
        liquid = vapor = None
        for sp in catalog:
            if strip_phase(sp.formula)[0] == "H2O":
                if sp.phase == "l":
                    liquid = sp.name
                elif sp.phase == "g":
                    vapor = sp.name
        if liquid is None or vapor is None:
            raise ValueError(f"{self.name}: el catálogo necesita agua líquida y vapor (fase g)")
        return liquid, vapor

    def compute(self, inputs: Sequence[Stream], catalog: Catalog) -> tuple[Stream, ...]:
        if catalog.thermo is None:
            raise ValueError(f"{self.name}: el evaporador exige activar el balance de calor")
        liquid_name, vapor_name = self._water_names(catalog)
        feed = _mixed(inputs, catalog)
        target = inlet_enthalpy(inputs, catalog) + float(self.duty_kw)
        water = feed.flow(liquid_name) + feed.flow(vapor_name)
        gases = {n: f for n, f in feed.flows.items() if catalog[n].phase == "g" and n != vapor_name}
        rest = {n: f for n, f in feed.flows.items() if catalog[n].phase != "g" and n != liquid_name}

        def split(v: float) -> tuple[dict[str, float], dict[str, float]]:
            liq = dict(rest)
            liq[liquid_name] = water - v
            vap = dict(gases)
            vap[vapor_name] = v
            return liq, vap

        def enthalpy(t: float, v: float) -> float:
            liq, vap = split(v)
            return stream_enthalpy(liq, t, catalog) + stream_enthalpy(vap, t, catalog)

        # Agua mínima que debe quedar: la que mantiene a los solutos con ΦL dentro de su tabla.
        keep = 0.0
        for n, f in rest.items():
            apparent = catalog.thermo.record(catalog[n]).apparent
            if apparent is not None and f > 0:
                keep += f / catalog[n].molar_mass * 1000.0 / apparent.max_molality
        v_max = max(water - keep, 0.0)
        t_sat = tsat_c(self.pressure_kpa)
        if enthalpy(t_sat, 0.0) >= target:  # no llega a hervir
            liq, vap = split(0.0)
            t = temperature_for({**liq, **vap}, target, catalog, feed.temperature)
        elif enthalpy(t_sat, v_max) >= target:  # hierve en parte, a la temperatura de saturación
            v = brentq(lambda x: enthalpy(t_sat, x) - target, 0.0, v_max, xtol=1e-12, rtol=1e-14)
            liq, vap = split(v)
            t = t_sat
        elif v_max < water:
            raise ValueError(
                f"{self.name}: el calor concentraría los solutos más allá de sus datos de "
                "dilución; baje el calor (además, no se modela la subida del punto de ebullición)"
            )
        else:  # todo el agua se evapora y el vapor se sobrecalienta
            liq, vap = split(water)
            high = min(
                DEFAULT_LIMIT_C,
                *(
                    catalog.thermo.record(catalog[n]).limits_k[1] - 273.15
                    for n, f in {**liq, **vap}.items()
                    if f > 0
                ),
            )
            t = brentq(lambda x: enthalpy(x, water) - target, t_sat, high, xtol=1e-9)
        return (
            Stream(liq, t, self.pressure_kpa),
            Stream(vap, t, self.pressure_kpa),
        )

    def heat_duty(self, inputs: Sequence[Stream], catalog: Catalog) -> float:
        return float(self.duty_kw)

    def with_parameter(self, key: str, value: float) -> Evaporator:
        """``'calor_kw'`` o ``'presion_kpa'``."""
        if key == "calor_kw":
            return replace(self, duty_kw=value)
        if key == "presion_kpa":
            return replace(self, pressure_kpa=value)
        raise KeyError(
            f"{self.name}: parámetro desconocido {key!r}; use 'calor_kw' o 'presion_kpa'"
        )


def unit_species(unit: Unit) -> set[str]:
    """Especies que un equipo menciona en sus parámetros (para validar contra el catálogo)."""
    from .equilibrium import EquilibriumReactor
    from .ew import Electrowinning
    from .molienda import Grinding

    if isinstance(unit, EquilibriumReactor):
        return set(unit.minerals.values())
    if isinstance(unit, Electrowinning):
        return {unit.copper, unit.acid, unit.water, unit.metal, unit.oxygen}
    if isinstance(unit, Grinding):
        return {unit.water}
    if isinstance(unit, Separator):
        return set(unit.recoveries)
    if isinstance(unit, Reactor):
        return {name for r in unit.reactions for name in r.stoichiometry}
    return set()
