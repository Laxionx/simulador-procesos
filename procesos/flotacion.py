"""Flotación cinética: primer orden por especie, en celdas de mezcla perfecta en serie.

Modelos de la distribución de constantes f(k) (García-Zúñiga 1935; Klimpel 1980):
- ``primer_orden``: una sola constante k.
- ``rectangular``: k repartida uniforme entre 0 y kmax (Klimpel); k media = kmax/2.

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
WATER_DENSITY = 1.0  # t/m³


def _check_model(model: str) -> None:
    if model not in MODELS:
        raise ValueError(f"modelo de flotación desconocido {model!r}; use uno de {MODELS}")


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
    kinetics: Mapping[str, tuple[float, float]]  # especie -> (R∞, k o kmax)
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
        _check_model(self.model)
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
        for species, (r_inf, k) in self.kinetics.items():
            if not (math.isfinite(k) and k > 0):
                raise ValueError(f"{self.name}: k de {species} debe ser positiva: {k}")
            kinetics[species] = (_check_fraction(r_inf, f"{self.name}: R∞ de {species}"), k)
        fixed = {n: _check_fraction(v, f"{self.name}: recuperación de {n}")
                 for n, v in self.fixed.items()}  # fmt: skip
        object.__setattr__(self, "kinetics", MappingProxyType(kinetics))
        object.__setattr__(self, "fixed", MappingProxyType(fixed))
        object.__setattr__(self, "default", _check_fraction(self.default, f"{self.name}: defecto"))

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
            if species in self.kinetics:
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
        if kind == "k" and species in self.kinetics:
            kinetics = dict(self.kinetics)
            kinetics[species] = (kinetics[species][0], value)
            return replace(self, kinetics=kinetics)
        raise KeyError(f"{self.name}: parámetro desconocido {key!r}")
