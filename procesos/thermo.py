"""Entalpía por especie y temperatura de una corriente (fase 2: balance de calor).

La entalpía molar es la de formación a 298,15 K más el calor sensible:

    h(T) = ΔfH°(298,15) + ∫ Cp dT   (kJ/mol)

Así, una misma suma de entalpías cierra a la vez el calor sensible y el de reacción. Los
datos y sus fuentes están en `procesos/thermo_data.py`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq

from .elements import strip_phase
from .species import Catalog, Species

T_REF = 298.15  # K
KELVIN = 273.15
EXTRAPOLATION_K = 30.0  # se admite extrapolar hasta 30 K bajo el primer tramo (agua a 20 °C)


@dataclass(frozen=True)
class Shomate:
    """Ecuación de Shomate del NIST Chemistry WebBook, con t = T/1000:
    Cp = A + B t + C t² + D t³ + E/t²  [J/(mol·K)];
    h - h298 = A t + B t²/2 + C t³/3 + D t⁴/4 - E/t + F - H  [kJ/mol]."""

    tmin: float
    tmax: float
    a: float
    b: float
    c: float
    d: float
    e: float
    f: float
    g: float  # término de la entropía; no se usa en la entalpía
    h: float

    def cp(self, temp_k: float) -> float:
        t = temp_k / 1000.0
        return self.a + self.b * t + self.c * t**2 + self.d * t**3 + self.e / t**2

    def dh(self, temp_k: float) -> float:
        t = temp_k / 1000.0
        return (
            self.a * t
            + self.b * t**2 / 2
            + self.c * t**3 / 3
            + self.d * t**4 / 4
            - self.e / t
            + self.f
            - self.h
        )


@dataclass(frozen=True)
class MaierKelley:
    """Forma de Robie y Hemingway (1995): Cp = A1 + A2 T + A3/T² + A4/√T + A5 T² [J/(mol·K)]."""

    tmin: float
    tmax: float
    a1: float
    a2: float = 0.0
    a3: float = 0.0
    a4: float = 0.0
    a5: float = 0.0

    def cp(self, temp_k: float) -> float:
        t = temp_k
        return self.a1 + self.a2 * t + self.a3 / t**2 + self.a4 / math.sqrt(t) + self.a5 * t**2

    def _integral(self, t: float) -> float:
        return (
            self.a1 * t
            + self.a2 * t**2 / 2
            - self.a3 / t
            + 2 * self.a4 * math.sqrt(t)
            + self.a5 * t**3 / 3
        )

    def dh(self, temp_k: float) -> float:
        return (self._integral(temp_k) - self._integral(T_REF)) / 1000.0


@dataclass(frozen=True)
class ConstantCp:
    """Cp constante [J/(mol·K)]; se usa para solutos en dilución infinita (Cp aproximado a 0)."""

    cp_value: float = 0.0
    tmin: float = KELVIN
    tmax: float = KELVIN + 100.0

    def cp(self, temp_k: float) -> float:
        return self.cp_value

    def dh(self, temp_k: float) -> float:
        return self.cp_value * (temp_k - T_REF) / 1000.0


@dataclass(frozen=True)
class EnthalpyPolynomial:
    """Forma del US Bureau of Mines (p. ej. RI 8305): h - h298 = a T + b T² + c/T + d en kcal/mol,
    con la constante d de cada tramo incluyendo las transiciones anteriores."""

    tmin: float
    tmax: float
    a: float
    b: float = 0.0
    c: float = 0.0
    d: float = 0.0

    def cp(self, temp_k: float) -> float:
        return (self.a + 2 * self.b * temp_k - self.c / temp_k**2) * 4184.0

    def dh(self, temp_k: float) -> float:
        t = temp_k
        return (self.a * t + self.b * t**2 + self.c / t + self.d) * 4.184


CpModel = Shomate | MaierKelley | ConstantCp | EnthalpyPolynomial


@dataclass(frozen=True)
class ApparentEnthalpy:
    """Entalpía molal aparente relativa ΦL(m) de un soluto (kJ por mol de soluto), tabulada
    contra √m y con interpolación monótona (PCHIP). Es lo que el soluto lleva de más frente a
    la dilución infinita: al diluir, la diferencia de ΦL sale como calor."""

    sqrt_m: tuple[float, ...]
    phi_kj: tuple[float, ...]
    source: str = ""

    def _spline(self):
        from scipy.interpolate import PchipInterpolator

        return PchipInterpolator(np.asarray(self.sqrt_m), np.asarray(self.phi_kj))

    @property
    def max_molality(self) -> float:
        return self.sqrt_m[-1] ** 2

    def __call__(self, molality: float) -> float:
        if molality < 0 or molality > self.max_molality * (1 + 1e-9):
            raise ValueError(
                f"Molalidad {molality:.4g} fuera de la tabla de ΦL (0 a {self.max_molality:.4g})"
            )
        return float(self._spline()(math.sqrt(molality)))

    def partial(self, molality: float) -> float:
        """Entalpía molal parcial relativa del soluto, L2 = ΦL + (√m/2) dΦL/d√m."""
        x = math.sqrt(molality)
        spline = self._spline()
        return float(spline(x) + x / 2.0 * spline.derivative()(x))


@dataclass(frozen=True)
class ThermoRecord:
    dfh298: float  # kJ/mol
    ranges: tuple[CpModel, ...]
    source: str
    apparent: ApparentEnthalpy | None = None

    def model(self, temp_k: float) -> CpModel:
        first, last = self.ranges[0], self.ranges[-1]
        if not first.tmin - EXTRAPOLATION_K <= temp_k <= last.tmax:
            raise ValueError(
                f"{temp_k - KELVIN:.1f} °C fuera del rango de los datos "
                f"({first.tmin - EXTRAPOLATION_K - KELVIN:.0f} a {last.tmax - KELVIN:.0f} °C)"
            )
        return next((r for r in self.ranges if temp_k <= r.tmax), last)

    def cp(self, temp_k: float) -> float:
        return self.model(temp_k).cp(temp_k)

    def enthalpy(self, temp_k: float) -> float:
        """kJ/mol, referida a los elementos a 298,15 K."""
        return self.dfh298 + self.model(temp_k).dh(temp_k)

    @property
    def limits_k(self) -> tuple[float, float]:
        return self.ranges[0].tmin - EXTRAPOLATION_K, self.ranges[-1].tmax


class ThermoDatabase:
    """Fichas por (fórmula sin fase, fase), p. ej. ("H2O", "l") o ("CuSO4", "aq")."""

    def __init__(self, records: Mapping[tuple[str, str], ThermoRecord]) -> None:
        self._records = dict(records)

    @staticmethod
    def key(species: Species) -> tuple[str, str]:
        return strip_phase(species.formula)[0], species.phase

    def record(self, species: Species) -> ThermoRecord:
        try:
            return self._records[self.key(species)]
        except KeyError:
            raise KeyError(
                f"Sin datos termodinámicos para {species.name} (fase {species.phase})"
            ) from None

    def by_key(self, formula: str, phase: str) -> ThermoRecord:
        try:
            return self._records[(formula, phase)]
        except KeyError:
            raise KeyError(f"Sin datos termodinámicos para {formula} (fase {phase})") from None

    def missing(self, species: list[Species] | tuple[Species, ...]) -> list[str]:
        return [s.name for s in species if self.key(s) not in self._records]

    def __contains__(self, key: object) -> bool:
        return key in self._records


def _liquid_water_kg(flows: Mapping[str, float], catalog: Catalog) -> float:
    return sum(
        f
        for n, f in flows.items()
        if catalog[n].phase == "l" and strip_phase(catalog[n].formula)[0] == "H2O"
    )


def stream_enthalpy(flows: Mapping[str, float], temperature: float, catalog: Catalog) -> float:
    """Entalpía de una corriente en kW: Σ (kg/h ÷ kg/kmol) · kJ/mol · 1000 / 3600. Los solutos
    con ΦL suman su entalpía aparente a la molalidad de la corriente (calor de dilución)."""
    thermo = _thermo(catalog)
    temp_k = temperature + KELVIN
    total = 0.0
    water = None
    for name, flow in flows.items():
        if flow <= 0:
            continue
        record = thermo.record(catalog[name])
        kmol = flow / catalog[name].molar_mass
        h = record.enthalpy(temp_k)
        if record.apparent is not None:
            water = _liquid_water_kg(flows, catalog) if water is None else water
            if water <= 0:
                raise ValueError(f"{name}: un soluto con calor de dilución necesita agua líquida")
            h += record.apparent(kmol * 1000.0 / water)
        total += kmol * h / 3.6
    return total


def temperature_for(
    flows: Mapping[str, float], target_kw: float, catalog: Catalog, default: float
) -> float:
    """Temperatura (°C) a la que la corriente tiene la entalpía buscada."""
    present = [catalog[n] for n, f in flows.items() if f > 0]
    if not present:
        return default
    thermo = _thermo(catalog)
    low = max(thermo.record(s).limits_k[0] for s in present) - KELVIN
    high = min(thermo.record(s).limits_k[1] for s in present) - KELVIN

    def gap(t: float) -> float:
        return stream_enthalpy(flows, t, catalog) - target_kw

    g_low, g_high = gap(low), gap(high)
    if g_low > 0 or g_high < 0:
        raise ValueError(
            f"La entalpía pedida ({target_kw:.1f} kW) queda fuera de lo que admiten los datos "
            f"entre {low:.0f} y {high:.0f} °C "
            f"({g_low + target_kw:.1f} a {g_high + target_kw:.1f} kW)"
        )
    return float(brentq(gap, low, high, xtol=1e-9, rtol=1e-12))


def _thermo(catalog: Catalog) -> ThermoDatabase:
    if catalog.thermo is None:
        raise ValueError("Esta planta no tiene activado el balance de calor")
    return catalog.thermo
