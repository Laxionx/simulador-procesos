"""Flotación cinética: primer orden por especie, en celdas de mezcla perfecta en serie.

Modelos de la distribución de constantes f(k) (García-Zúñiga 1935; Klimpel 1980):
- ``primer_orden``: una sola constante k.
- ``rectangular``: k repartida uniforme entre 0 y kmax (Klimpel); k media = kmax/2.
- ``kelsall``: dos componentes, una fracción rápida y una lenta (Kelsall 1961); la cinética de
  cada especie es (φ lenta, k rápida, k lenta), sin R∞:
      batch:     (1 - φ)(1 - e^(-kf t)) + φ (1 - e^(-ks t))
      N celdas:  (1 - φ)(1 - (1 + kf τ)^-N) + φ (1 - (1 + ks τ)^-N)

Recuperación en batch (tiempo t) y en N celdas en serie de mezcla perfecta (τ por celda):

    primer orden:  R∞·(1 - e^(-k t))                R∞·(1 - (1 + kτ)^-N)
    rectangular:   R∞·(1 - (1 - e^(-kmax t))/(kmax t))
                   N = 1:  R∞·(1 - ln(1 + kmax τ)/(kmax τ))
                   N > 1:  R∞·(1 - (1 - (1 + kmax τ)^(1-N)) / (kmax τ (N - 1)))

Las formas continuas son las de Vinnett et al. (2022, Physicochem. Probl. Miner. Process. 58(5),
152420) bajo mezcla perfecta. El factor de escalamiento divide las k: k_planta = k_lab / factor.
Ver docs/flotacion.md.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from types import MappingProxyType

import numpy as np
from scipy.optimize import least_squares

from .species import Catalog
from .stream import Stream
from .units import _check_fraction, _check_ports, _mixed

MODELS = ("primer_orden", "rectangular")
KELSALL = "kelsall"
ALL_MODELS = (*MODELS, KELSALL)
WATER_DENSITY = 1.0  # t/m³


def _check_model(model: str, allowed: tuple[str, ...] = MODELS) -> None:
    if model not in allowed:
        raise ValueError(f"modelo de flotación desconocido {model!r}; use uno de {allowed}")


def kelsall_recovery(phi: float, kf: float, ks: float, t: float, cells: int | None = None) -> float:
    """Kelsall de dos componentes: batch de t minutos (``cells`` None) o N celdas de τ = t."""

    def part(k: float) -> float:
        if k <= 0 or t <= 0:
            return 0.0
        return -math.expm1(-k * t) if cells is None else 1.0 - (1.0 + k * t) ** -cells

    if cells is not None and cells < 1:
        raise ValueError("se necesita al menos una celda")
    return (1.0 - phi) * part(kf) + phi * part(ks)


def batch_recovery(model: str, r_inf: float, k: float, t: float) -> float:
    """Recuperación (fracción) en una prueba batch de t minutos."""
    _check_model(model)
    if t <= 0 or k <= 0:
        return 0.0
    if model == "primer_orden":
        return r_inf * -math.expm1(-k * t)
    return r_inf * (1.0 + math.expm1(-k * t) / (k * t))


def cells_recovery(model: str, r_inf: float, k: float, tau: float, cells: int) -> float:
    """Recuperación (fracción) en ``cells`` celdas de mezcla perfecta con τ minutos cada una."""
    _check_model(model)
    if cells < 1:
        raise ValueError("se necesita al menos una celda")
    x = k * tau
    if x <= 0:
        return 0.0
    if model == "primer_orden":
        return r_inf * (1.0 - (1.0 + x) ** -cells)
    if cells == 1:
        return r_inf * (1.0 - math.log1p(x) / x)
    return r_inf * (1.0 - (1.0 - (1.0 + x) ** (1 - cells)) / (x * (cells - 1)))


@dataclass(frozen=True)
class KineticFit:
    model: str
    r_inf: float  # fracción
    k: float  # 1/min (kmax en el rectangular)
    rmse: float  # fracción
    points: int

    @property
    def k_mean(self) -> float:
        return self.k if self.model == "primer_orden" else self.k / 2.0


def fit_kinetics(
    x: Sequence[float],
    recoveries: Sequence[float],
    model: str = "primer_orden",
    tau: float | None = None,
) -> KineticFit:
    """Ajusta R∞ (0-1) y k por mínimos cuadrados en la recuperación.

    Sin ``tau``, ``x`` son tiempos de una prueba batch (min). Con ``tau``, ``x`` son números de
    celdas de mezcla perfecta en serie con τ minutos cada una (perfil de un banco).
    """
    _check_model(model)
    xs, ys = np.asarray(x, dtype=float), np.asarray(recoveries, dtype=float)
    if xs.shape != ys.shape or xs.size < 3:
        raise ValueError("se necesitan al menos 3 puntos, con un x por cada recuperación")
    if np.any(ys < 0) or np.any(ys > 1):
        raise ValueError("las recuperaciones van como fracción entre 0 y 1")

    def predict(params: np.ndarray) -> np.ndarray:
        r_inf, k = params
        if tau is None:
            return np.array([batch_recovery(model, r_inf, k, t) for t in xs])
        return np.array([cells_recovery(model, r_inf, k, tau, int(n)) for n in xs])

    scale = float(xs.max()) if tau is None else float(tau * xs.max())
    guess = np.array([min(max(ys.max(), 0.05), 1.0), 2.0 / scale])
    result = least_squares(lambda p: predict(p) - ys, guess, bounds=([0.0, 1e-9], [1.0, np.inf]),
                           xtol=1e-14, ftol=1e-14, gtol=1e-14)  # fmt: skip
    rmse = float(np.sqrt(np.mean(result.fun**2)))
    return KineticFit(model, float(result.x[0]), float(result.x[1]), rmse, int(xs.size))


@dataclass(frozen=True)
class FlotationResult:
    tau_min: float  # por celda
    cells: int
    recoveries: Mapping[str, float]  # fracción por especie al concentrado


@dataclass(frozen=True)
class Flotation:
    """Salidas: (concentrado, relave). Las especies con cinética se recuperan según el modelo; las
    demás, con la recuperación fija de ``fixed`` (o ``default``), como en el separador.

    El τ por celda se da directo (``tau_min``) o sale del volumen de celda: τ = V·(1 - aire)/Q,
    con Q el caudal de pulpa (sólidos a ``solids_density`` y agua a 1 t/m³)."""

    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    kinetics: Mapping[str, tuple[float, ...]]  # especie -> (R∞, k o kmax), o (φ, kf, ks)
    cells: int
    model: str = "primer_orden"
    tau_min: float | None = None
    cell_volume_m3: float | None = None
    air_fraction: float = 0.15
    solids_density: float = 2.7
    scale_up: float = 1.0
    fixed: Mapping[str, float] = MappingProxyType({})
    default: float = 0.0
    water: str = "H2O"

    def __post_init__(self) -> None:
        _check_ports(self.name, self.inputs, self.outputs, 2)
        _check_model(self.model, ALL_MODELS)
        if self.cells < 1:
            raise ValueError(f"{self.name}: se necesita al menos una celda")
        if (self.tau_min is None) == (self.cell_volume_m3 is None):
            raise ValueError(f"{self.name}: dé el tiempo de residencia o el volumen de celda")
        for label, value in (("τ", self.tau_min), ("volumen", self.cell_volume_m3)):
            if value is not None and not (math.isfinite(value) and value > 0):
                raise ValueError(f"{self.name}: {label} debe ser positivo: {value}")
        if not (self.scale_up > 0 and self.solids_density > 0):
            raise ValueError(f"{self.name}: factor de escalamiento y densidad positivos")
        _check_fraction(self.air_fraction, f"{self.name}: fracción de aire")
        kinetics = {}
        for species, params in self.kinetics.items():
            kinetics[species] = self._check_kinetics(species, tuple(params))
        fixed = {n: _check_fraction(v, f"{self.name}: recuperación de {n}")
                 for n, v in self.fixed.items()}  # fmt: skip
        object.__setattr__(self, "kinetics", MappingProxyType(kinetics))
        object.__setattr__(self, "fixed", MappingProxyType(fixed))
        object.__setattr__(self, "default", _check_fraction(self.default, f"{self.name}: defecto"))

    def _check_kinetics(self, species: str, params: tuple[float, ...]) -> tuple[float, ...]:
        if self.model == KELSALL:
            if len(params) != 3:
                raise ValueError(f"{self.name}: Kelsall pide (φ, kf, ks) para {species}")
            phi, kf, ks = params
            if not all(math.isfinite(k) and k >= 0 for k in (kf, ks)) or kf + ks <= 0:
                raise ValueError(f"{self.name}: kf y ks de {species} no negativas y no ambas 0")
            return (_check_fraction(phi, f"{self.name}: φ de {species}"), kf, ks)
        if len(params) != 2:
            raise ValueError(f"{self.name}: el modelo {self.model} pide (R∞, k) para {species}")
        r_inf, k = params
        if not (math.isfinite(k) and k > 0):
            raise ValueError(f"{self.name}: k de {species} debe ser positiva: {k}")
        return (_check_fraction(r_inf, f"{self.name}: R∞ de {species}"), k)

    def tau(self, feed: Stream, catalog: Catalog) -> float:
        if self.tau_min is not None:
            return float(self.tau_min)
        solids = sum(f for n, f in feed.flows.items() if catalog[n].phase == "s")
        liquid = sum(f for n, f in feed.flows.items() if catalog[n].phase != "s")
        q_m3_min = (solids / self.solids_density + liquid / WATER_DENSITY) / 1000.0 / 60.0
        if q_m3_min <= 0:
            raise ValueError(f"{self.name}: no entra pulpa a la flotación")
        return float(self.cell_volume_m3) * (1.0 - self.air_fraction) / q_m3_min

    def solve(self, inputs: Sequence[Stream], catalog: Catalog) -> FlotationResult:
        feed = _mixed(inputs, catalog)
        tau = self.tau(feed, catalog)
        recoveries = {}
        for species in feed.flows:
            if species in self.kinetics and self.model == KELSALL:
                phi, kf, ks = self.kinetics[species]
                recoveries[species] = kelsall_recovery(phi, kf / self.scale_up, ks / self.scale_up,
                                                       tau, self.cells)  # fmt: skip
            elif species in self.kinetics:
                r_inf, k = self.kinetics[species]
                recoveries[species] = cells_recovery(self.model, r_inf, k / self.scale_up, tau,
                                                     self.cells)  # fmt: skip
            else:
                recoveries[species] = self.fixed.get(species, self.default)
        return FlotationResult(tau, self.cells, MappingProxyType(recoveries))

    def compute(self, inputs: Sequence[Stream], catalog: Catalog) -> tuple[Stream, ...]:
        feed = _mixed(inputs, catalog)
        recoveries = self.solve(inputs, catalog).recoveries
        first = {n: v * recoveries[n] for n, v in feed.flows.items()}
        second = {n: v - first[n] for n, v in feed.flows.items()}
        return (
            Stream(first, feed.temperature, feed.pressure),
            Stream(second, feed.temperature, feed.pressure),
        )

    def with_parameter(self, key: str, value: float) -> Flotation:
        """Claves: ``tiempo_residencia``, ``factor_escalamiento`` o ``k:<especie>``."""
        if key == "tiempo_residencia" and self.tau_min is not None:
            return replace(self, tau_min=value)
        if key == "factor_escalamiento":
            return replace(self, scale_up=value)
        kind, _, species = key.partition(":")
        if kind == "k" and species in self.kinetics:  # en Kelsall, la k rápida
            kinetics = dict(self.kinetics)
            params = list(kinetics[species])
            params[1] = value
            kinetics[species] = tuple(params)
            return replace(self, kinetics=kinetics)
        raise KeyError(f"{self.name}: parámetro desconocido {key!r}")
