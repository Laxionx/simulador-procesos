"""Equipos de la planta: mezclador, divisor, separador por especie y reactor.

Cada equipo es inmutable; ``with_parameter`` devuelve una copia con un parámetro cambiado, que
es lo que usan los lazos de control para manipular la planta.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Protocol

from .reactions import Reaction
from .species import Catalog
from .stream import Stream, mix, moles


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
        return (mix(inputs),)

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
        feed = mix(inputs)
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
        feed = mix(inputs)
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
    """Aplica las reacciones en orden sobre la mezcla de sus entradas."""

    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    reactions: tuple[Reaction, ...]

    def __post_init__(self) -> None:
        _check_ports(self.name, self.inputs, self.outputs, 1)
        if not self.reactions:
            raise ValueError(f"{self.name}: el reactor necesita al menos una reacción")

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
        return (Stream(flows, feed.temperature, feed.pressure),)

    def with_parameter(self, key: str, value: float) -> Reactor:
        """``'conversion:<n>'``, con n desde 1 en el orden de las reacciones."""
        kind, _, index_text = key.partition(":")
        if kind != "conversion" or not index_text.isdigit():
            raise KeyError(f"{self.name}: parámetro desconocido {key!r}; use 'conversion:<n>'")
        index = int(index_text) - 1
        if not 0 <= index < len(self.reactions):
            raise KeyError(f"{self.name}: no existe la reacción {index + 1}")
        reactions = list(self.reactions)
        reactions[index] = replace(reactions[index], conversion=value)
        return replace(self, reactions=tuple(reactions))


def unit_species(unit: Unit) -> set[str]:
    """Especies que un equipo menciona en sus parámetros (para validar contra el catálogo)."""
    if isinstance(unit, Separator):
        return set(unit.recoveries)
    if isinstance(unit, Reactor):
        return {name for r in unit.reactions for name in r.stoichiometry}
    return set()
