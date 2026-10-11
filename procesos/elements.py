"""Pesos atómicos estándar y lectura de fórmulas químicas.

Pesos atómicos: valores abreviados de la IUPAC (Prohaska et al., *Standard atomic weights of
the elements 2021*, Pure Appl. Chem. 94, 2022), redondeados como en las tablas de uso general.
"""

from __future__ import annotations

import re

ATOMIC_WEIGHTS: dict[str, float] = {
    "H": 1.008,
    "He": 4.0026,
    "Li": 6.94,
    "Be": 9.0122,
    "B": 10.81,
    "C": 12.011,
    "N": 14.007,
    "O": 15.999,
    "F": 18.998,
    "Na": 22.990,
    "Mg": 24.305,
    "Al": 26.982,
    "Si": 28.085,
    "P": 30.974,
    "S": 32.06,
    "Cl": 35.45,
    "K": 39.098,
    "Ca": 40.078,
    "Ti": 47.867,
    "V": 50.942,
    "Cr": 51.996,
    "Mn": 54.938,
    "Fe": 55.845,
    "Co": 58.933,
    "Ni": 58.693,
    "Cu": 63.546,
    "Zn": 65.38,
    "Ga": 69.723,
    "Ge": 72.630,
    "As": 74.922,
    "Se": 78.971,
    "Br": 79.904,
    "Rb": 85.468,
    "Sr": 87.62,
    "Zr": 91.224,
    "Nb": 92.906,
    "Mo": 95.95,
    "Ag": 107.87,
    "Cd": 112.41,
    "In": 114.82,
    "Sn": 118.71,
    "Sb": 121.76,
    "Te": 127.60,
    "I": 126.90,
    "Ba": 137.33,
    "La": 138.91,
    "Ce": 140.12,
    "W": 183.84,
    "Pt": 195.08,
    "Au": 196.97,
    "Hg": 200.59,
    "Tl": 204.38,
    "Pb": 207.2,
    "Bi": 208.98,
    "U": 238.03,
}

_PHASE_SUFFIX = re.compile(r"\((aq|s|l|g|org)\)$")
_CHARGE_SUFFIX = re.compile(r"([+-])(\d*)$")
_TOKEN = re.compile(r"([A-Z][a-z]?)|(\d+(?:\.\d+)?)|([(\[])|([)\]])")


def strip_phase(text: str) -> tuple[str, str | None]:
    """Separa el sufijo de fase: ``'CuSO4(aq)'`` → ``('CuSO4', 'aq')``."""
    match = _PHASE_SUFFIX.search(text)
    return (text[: match.start()], match.group(1)) if match else (text, None)


def split_charge(formula: str) -> tuple[str, int]:
    """Separa la carga iónica final: ``'SO4-2'`` → ``('SO4', -2)``; ``'OH-'`` → ``('OH', -1)``."""
    match = _CHARGE_SUFFIX.search(formula)
    if not match:
        return formula, 0
    magnitude = int(match.group(2)) if match.group(2) else 1
    return formula[: match.start()], magnitude if match.group(1) == "+" else -magnitude


def _parse_group(text: str) -> dict[str, float]:
    tokens = list(_TOKEN.finditer(text))
    if "".join(t.group(0) for t in tokens) != text:
        raise ValueError(f"Fórmula con caracteres no reconocidos: {text!r}")
    stack: list[dict[str, float]] = [{}]
    i = 0
    while i < len(tokens):
        element, number, opening, closing = tokens[i].groups()
        if element:
            if element not in ATOMIC_WEIGHTS:
                raise ValueError(f"Elemento desconocido {element!r} en {text!r}")
            count = 1.0
            if i + 1 < len(tokens) and tokens[i + 1].group(2):
                count = float(tokens[i + 1].group(2))
                i += 1
            stack[-1][element] = stack[-1].get(element, 0.0) + count
        elif opening:
            stack.append({})
        elif closing:
            if len(stack) == 1:
                raise ValueError(f"Paréntesis sin abrir en {text!r}")
            group = stack.pop()
            factor = 1.0
            if i + 1 < len(tokens) and tokens[i + 1].group(2):
                factor = float(tokens[i + 1].group(2))
                i += 1
            for key, value in group.items():
                stack[-1][key] = stack[-1].get(key, 0.0) + value * factor
        elif number:
            raise ValueError(f"Número sin elemento en {text!r}")
        i += 1
    if len(stack) != 1:
        raise ValueError(f"Paréntesis sin cerrar en {text!r}")
    return stack[0]


def parse_formula(formula: str) -> dict[str, float]:
    """Composición elemental de una fórmula: átomos de cada elemento por unidad de fórmula.

    Admite paréntesis y corchetes (``Ca(OH)2``), hidratos con ``·`` o ``*`` (``CuSO4·5H2O``),
    subíndices decimales (``Fe0.95S``), carga final (``Cu+2``, ``SO4-2``) y sufijo de fase
    (``(aq)``), que no alteran la composición.
    """
    body, _ = strip_phase(formula.strip())
    body, _ = split_charge(body)
    if not body:
        raise ValueError(f"Fórmula vacía: {formula!r}")
    composition: dict[str, float] = {}
    for part in re.split(r"[·*]", body):
        multiplier_match = re.match(r"^(\d+(?:\.\d+)?)", part)
        multiplier = float(multiplier_match.group(1)) if multiplier_match else 1.0
        group = part[multiplier_match.end() :] if multiplier_match else part
        for element, count in _parse_group(group).items():
            composition[element] = composition.get(element, 0.0) + count * multiplier
    if not composition:
        raise ValueError(f"La fórmula no tiene elementos: {formula!r}")
    return composition


def molar_mass(composition: dict[str, float]) -> float:
    """Masa molar en kg/kmol (numéricamente igual a g/mol)."""
    return sum(ATOMIC_WEIGHTS[element] * count for element, count in composition.items())
