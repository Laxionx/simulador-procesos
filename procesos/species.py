"""Especies químicas y catálogo de la planta."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from .elements import molar_mass, parse_formula, split_charge, strip_phase

PHASES = ("s", "l", "aq", "g")


@dataclass(frozen=True)
class Species:
    """Una especie: nombre único en la planta, fórmula, fase y propiedades derivadas."""

    name: str
    formula: str
    phase: str
    composition: Mapping[str, float]
    molar_mass: float
    charge: int


def make_species(name: str, formula: str | None = None, phase: str | None = None) -> Species:
    """Crea una especie. La fórmula por defecto es el nombre sin sufijo de fase.

    La fase se toma, en orden, del argumento, del sufijo del nombre (``'CuSO4(aq)'``) o se asume
    líquida para el agua y sólida para el resto.
    """
    if not name or not name.strip():
        raise ValueError("La especie necesita un nombre")
    base, suffix_phase = strip_phase(name.strip())
    formula = (formula or base).strip()
    phase = phase or suffix_phase or ("l" if strip_phase(formula)[0] == "H2O" else "s")
    if phase not in PHASES:
        raise ValueError(f"Fase {phase!r} inválida para {name!r}; use una de {PHASES}")
    composition = parse_formula(formula)
    _, charge = split_charge(strip_phase(formula)[0])
    return Species(
        name=name.strip(),
        formula=formula,
        phase=phase,
        composition=MappingProxyType(composition),
        molar_mass=molar_mass(composition),
        charge=charge,
    )


class Catalog:
    """Catálogo ordenado de especies; el orden fija la codificación de las corrientes."""

    def __init__(self, species: Sequence[Species]) -> None:
        names = [s.name for s in species]
        duplicated = sorted({n for n in names if names.count(n) > 1})
        if duplicated:
            raise ValueError(f"Especies repetidas en el catálogo: {duplicated}")
        if not species:
            raise ValueError("El catálogo necesita al menos una especie")
        self._species = {s.name: s for s in species}
        self.names: tuple[str, ...] = tuple(names)

    def __getitem__(self, name: str) -> Species:
        try:
            return self._species[name]
        except KeyError:
            raise KeyError(f"Especie desconocida: {name!r}") from None

    def __contains__(self, name: object) -> bool:
        return name in self._species

    def __iter__(self) -> Iterator[Species]:
        return iter(self._species.values())

    def __len__(self) -> int:
        return len(self._species)

    def elements(self) -> tuple[str, ...]:
        """Elementos presentes en alguna especie, en orden alfabético."""
        return tuple(sorted({e for s in self for e in s.composition}))
