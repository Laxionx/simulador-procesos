"""Reacciones con estequiometría y conversión de un componente clave."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .species import Catalog

_ARROW = re.compile(r"\s*(?:->|=>|=)\s*")
_SEPARATOR = re.compile(r"\s+\+\s+")
_COEFFICIENT = re.compile(r"^(\d+(?:\.\d+)?)\s+(.+)$")


@dataclass(frozen=True)
class Reaction:
    """Coeficientes negativos = reactivos, positivos = productos.

    La conversión es la fracción del componente clave que reacciona (0 a 1). Si otro reactivo
    se agota antes, el avance se limita a él (ver :class:`procesos.units.Reactor`).
    """

    stoichiometry: Mapping[str, float]
    key: str
    conversion: float
    equation: str = ""

    def __post_init__(self) -> None:
        if not self.stoichiometry:
            raise ValueError("La reacción no tiene especies")
        if any(not math.isfinite(c) or c == 0 for c in self.stoichiometry.values()):
            raise ValueError(f"Coeficientes inválidos en {self.label}")
        if self.stoichiometry.get(self.key, 0.0) >= 0:
            raise ValueError(f"El componente clave {self.key!r} debe ser reactivo en {self.label}")
        if not 0.0 <= self.conversion <= 1.0:
            raise ValueError(f"Conversión fuera de 0..1 en {self.label}: {self.conversion}")
        object.__setattr__(self, "stoichiometry", MappingProxyType(dict(self.stoichiometry)))

    @property
    def label(self) -> str:
        return self.equation or " + ".join(self.stoichiometry)

    @property
    def reactants(self) -> dict[str, float]:
        return {n: -c for n, c in self.stoichiometry.items() if c < 0}


def parse_equation(text: str) -> dict[str, float]:
    """``'CuO + H2SO4 -> CuSO4 + H2O'`` → coeficientes con signo.

    Los términos se separan con `` + `` (con espacios, para no confundir la carga de un ion como
    ``Fe+3``) y el coeficiente va antes del nombre con un espacio: ``'2 FeSO4'``.
    """
    sides = _ARROW.split(text.strip())
    if len(sides) != 2 or not all(side.strip() for side in sides):
        raise ValueError(f"La ecuación necesita reactivos -> productos: {text!r}")
    result: dict[str, float] = {}
    for side, sign in zip(sides, (-1.0, 1.0), strict=True):
        for term in _SEPARATOR.split(side.strip()):
            match = _COEFFICIENT.match(term.strip())
            coefficient, name = (float(match.group(1)), match.group(2)) if match else (1.0, term)
            name = name.strip()
            result[name] = result.get(name, 0.0) + sign * coefficient
    return {name: c for name, c in result.items() if c != 0}


def check_balance(reaction: Reaction, catalog: Catalog, tolerance: float = 1e-9) -> None:
    """Verifica que la reacción conserve cada elemento y la carga; si no, lanza ``ValueError``."""
    unknown = [n for n in reaction.stoichiometry if n not in catalog]
    if unknown:
        raise ValueError(f"Especies fuera del catálogo en {reaction.label}: {unknown}")
    atoms: dict[str, float] = {}
    charge = 0.0
    for name, coefficient in reaction.stoichiometry.items():
        species = catalog[name]
        charge += coefficient * species.charge
        for element, count in species.composition.items():
            atoms[element] = atoms.get(element, 0.0) + coefficient * count
    unbalanced = {e: round(v, 9) for e, v in atoms.items() if abs(v) > tolerance}
    if unbalanced:
        raise ValueError(f"Reacción desbalanceada {reaction.label}: sobran/faltan {unbalanced}")
    if abs(charge) > tolerance:
        raise ValueError(f"Reacción con carga desbalanceada {reaction.label}: {charge:+g}")
