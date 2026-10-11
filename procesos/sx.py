"""Extracción por solventes (SX) de cobre con una oxima: extracción y despojo en contracorriente.

Equilibrio (Devi y Nayak 2014, J. SAIMM 114, 937): Cu²⁺ + 2 RH(org) ⇌ CuR₂(org) + 2 H⁺, con
Kex = D·[H⁺]²/[RH]², donde D = [CuR₂]/[Cu²⁺] y [RH] es la oxima libre, todo en mol/L.

Para cada etapa i (la acuosa entra por la 1 y sale por la N; la orgánica, al revés):
- balance:    A·(x[i-1] - x[i]) = O·(y[i] - y[i+1])
- eficiencia: y[i] = y[i+1] + E[i]·(y*(x[i]) - y[i+1])   (Murphree, en la orgánica)
donde y* es el Cu orgánico en equilibrio con la acuosa que sale de la etapa. El H⁺ libre sale
del ácido total (el inicial más 2 H⁺ por Cu extraído) y de la asociación H⁺ + SO₄²⁻ ⇌ HSO₄⁻:
ideal (pKa₂ = 1,99) o calibrada con el pH medido de la alimentación acuosa.

En la planta el equipo aplica CuSO4 + 2 RH -> CuR2 + H2SO4 con el avance que da el equilibrio,
así que cierra por elemento. Extracción y despojo son el mismo equipo: el sentido lo decide el
equilibrio. Ver docs/sx.md.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace

import numpy as np
from scipy.optimize import least_squares, root

from .species import Catalog
from .stream import Stream

# Kex con la oxima total desde la carga máxima del reactivo (0,56 g/L de Cu por %v/v) y
# [H⁺] = 10^-pH: media geométrica de los 8 puntos de la Tabla III de Devi y Nayak (2014).
KEX_LIX984N = 5.05
PKA2_HSO4 = 1.99
WATER = "H2O"


class SXError(RuntimeError):
    """El cálculo por etapas no convergió a una solución física."""


@dataclass(frozen=True)
class SXResult:
    aqueous_mol_l: tuple[float, ...]  # Cu de la acuosa que sale de cada etapa
    organic_mol_l: tuple[float, ...]  # Cu (como CuR2) de la orgánica que sale de cada etapa
    free_extractant_mol_l: tuple[float, ...]  # oxima libre en esa orgánica
    ph: tuple[float, ...]  # -log10 [H⁺] de la acuosa que sale de cada etapa
    feed_aqueous_mol_l: float
    aqueous_l_h: float
    organic_l_h: float

    @property
    def transferred_mol_h(self) -> float:
        """Cu que pasa de la acuosa a la orgánica (negativo en el despojo)."""
        return self.aqueous_l_h * (self.feed_aqueous_mol_l - self.aqueous_mol_l[-1])

    @property
    def raffinate_g_l(self) -> float:
        """Cu en la acuosa que sale (refino, o electrolito cargado en el despojo)."""
        return self.aqueous_mol_l[-1] * _CU

    @property
    def loaded_g_l(self) -> float:
        """Cu en la orgánica que sale (cargada, o despojada en el despojo)."""
        return self.organic_mol_l[0] * _CU

    @property
    def recovery(self) -> float:
        """Fracción del Cu de la acuosa de entrada que pasa a la orgánica."""
        return 1.0 - self.aqueous_mol_l[-1] / self.feed_aqueous_mol_l


_CU = 63.546


def _free_h(total_h: float, total_s: float, ka: float) -> float:
    """[H⁺] libre con H⁺ + SO₄²⁻ ⇌ HSO₄⁻ (ka = constante de disociación del HSO₄⁻)."""
    total_h = max(total_h, 1e-12)
    b = ka + total_s - total_h
    return 0.5 * (-b + math.sqrt(b * b + 4.0 * total_h * ka))


@dataclass(frozen=True)
class SolventExtraction:
    """Entradas (acuosa, orgánica); salidas (acuosa, orgánica). Densidades en kg/L."""

    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    stages: int = 1
    kex: float = KEX_LIX984N
    efficiency: tuple[float, ...] | float = 1.0
    density_aq: float = 1.0
    density_org: float = 0.81
    feed_ph: float | None = None
    pka2: float = PKA2_HSO4
    distribution: float | None = None  # isoterma lineal y* = m·x (verificación)
    copper: str = "CuSO4"
    acid: str = "H2SO4"
    extractant: str = "RH"
    complex: str = "CuR2"

    def __post_init__(self) -> None:
        if not self.name or len(self.inputs) != 2 or len(self.outputs) != 2:
            raise ValueError(f"{self.name}: necesita (acuosa, orgánica) de entrada y de salida")
        if self.stages < 1:
            raise ValueError(f"{self.name}: necesita al menos una etapa")
        eff = self.efficiency
        eff = (float(eff),) * self.stages if isinstance(eff, int | float) else tuple(eff)
        if len(eff) != self.stages or not all(0.0 < e <= 1.0 for e in eff):
            raise ValueError(f"{self.name}: una eficiencia en (0, 1] por etapa ({self.stages})")
        object.__setattr__(self, "efficiency", tuple(float(e) for e in eff))
        if min(self.kex, self.density_aq, self.density_org) <= 0:
            raise ValueError(f"{self.name}: Kex y densidades deben ser positivos")

    # ---------------------------------------------------------------- entrada
    def _phases(self, inputs: Sequence[Stream], catalog: Catalog) -> tuple[Stream, Stream]:
        aqueous, organic = inputs
        org_in_aq = any(catalog[n].phase == "org" for n, f in aqueous.flows.items() if f > 0)
        if aqueous.flow(WATER) <= 0 or org_in_aq:
            raise ValueError(f"{self.name}: la entrada acuosa (la primera) debe traer agua y nada "
                             "orgánico")  # fmt: skip
        if not any(catalog[n].phase == "org" for n, f in organic.flows.items() if f > 0) or any(
            catalog[n].phase != "org" for n, f in organic.flows.items() if f > 0
        ):
            raise ValueError(f"{self.name}: la entrada orgánica (la segunda) debe traer solo "
                             "especies orgánicas")  # fmt: skip
        reac = {}
        for name, coef in ((self.copper, 1), (self.extractant, 2), (self.complex, -1),
                           (self.acid, -1)):  # fmt: skip
            for e, n in catalog[name].composition.items():
                reac[e] = reac.get(e, 0.0) + coef * n
        if any(abs(v) > 1e-9 for v in reac.values()):
            raise ValueError(f"{self.name}: las fórmulas no cierran {self.copper} + 2 "
                             f"{self.extractant} -> {self.complex} + {self.acid}")  # fmt: skip
        if catalog.thermo is not None:
            raise ValueError(f"{self.name}: la SX no tiene balance de calor")
        return aqueous, organic

    @staticmethod
    def _mol_h(stream: Stream, name: str, catalog: Catalog) -> float:
        return stream.flow(name) * 1000.0 / catalog[name].molar_mass

    # ---------------------------------------------------------------- cálculo
    def solve(self, inputs: Sequence[Stream], catalog: Catalog) -> SXResult:
        aqueous, organic = self._phases(inputs, catalog)
        a = aqueous.total / self.density_aq  # L/h
        o = organic.total / self.density_org
        x0 = self._mol_h(aqueous, self.copper, catalog) / a
        h0 = 2.0 * self._mol_h(aqueous, self.acid, catalog) / a
        s_total = (
            sum(
                f * 1000.0 / catalog[n].molar_mass * catalog[n].composition.get("S", 0.0)
                for n, f in aqueous.flows.items()
            )
            / a
        )
        y_feed = self._mol_h(organic, self.complex, catalog) / o
        hr_total = (self._mol_h(organic, self.extractant, catalog) + 2.0 * y_feed * o) / o
        ka = self._ka(h0, s_total)
        r = o / a
        n = self.stages

        def acid(x: float) -> float:
            return _free_h(h0 + 2.0 * (x0 - x), s_total, ka)

        def y_star(x: float) -> float:
            x = max(x, 0.0)
            if self.distribution is not None:
                return self.distribution * x
            k, h = self.kex * x, acid(x)
            b = 4.0 * k * hr_total + h * h
            disc = max(b * b - 16.0 * k * k * hr_total * hr_total, 0.0)
            return 2.0 * k * hr_total * hr_total / (b + math.sqrt(disc)) if k > 0 else 0.0

        def aqueous_profile(y: np.ndarray) -> np.ndarray:
            ys = np.append(y, y_feed)
            return x0 - r * np.cumsum(ys[:-1] - ys[1:])

        def residual(y: np.ndarray) -> np.ndarray:
            x = aqueous_profile(y)
            ys = np.append(y, y_feed)
            eff = np.asarray(self.efficiency)
            stars = np.array([y_star(xi) for xi in x])
            return ys[:-1] - ys[1:] - eff * (stars - ys[1:])

        y = self._stage_solve(residual, y_feed, y_star(x0), n, hr_total)
        x = aqueous_profile(y)
        if np.any(x < -1e-12 * max(x0, 1e-12)) or np.any(y < -1e-12):
            raise SXError(f"{self.name}: la solución por etapas no es física")
        x = np.maximum(x, 0.0)
        return SXResult(
            tuple(float(v) for v in x),
            tuple(float(v) for v in y),
            tuple(float(hr_total - 2.0 * v) for v in y),
            tuple(-math.log10(acid(float(v))) for v in x),
            x0,
            a,
            o,
        )

    def _ka(self, h0: float, s_total: float) -> float:
        if self.feed_ph is None:
            return 10.0 ** (-self.pka2)
        free = 10.0 ** (-self.feed_ph)
        bound = h0 - free  # H⁺ que está como HSO₄⁻
        if bound <= 0 or s_total <= bound:
            raise ValueError(
                f"{self.name}: el pH {self.feed_ph} de la alimentación no es compatible con su "
                f"ácido ({h0:.4g} mol/L de H⁺) y sulfato ({s_total:.4g} mol/L)"
            )
        return free * (s_total - bound) / bound

    def _stage_solve(self, residual, y_feed: float, y_eq: float, n: int, hr_total: float):
        start = y_feed + 0.5 * (y_eq - y_feed)
        guess = np.linspace(start, y_feed, n + 1)[:-1]
        sol = root(residual, guess, method="hybr", options={"xtol": 1e-15})
        scale = max(hr_total, 1e-12)
        if not sol.success or np.max(np.abs(residual(sol.x))) > 1e-12 * scale:
            fit = least_squares(residual, np.clip(guess, 0, hr_total / 2), bounds=(0, hr_total / 2),
                                xtol=1e-15, ftol=1e-15, gtol=1e-15)  # fmt: skip
            sol = root(residual, fit.x, method="hybr", options={"xtol": 1e-15})
            if np.max(np.abs(residual(sol.x))) > 1e-10 * scale:
                raise SXError(f"{self.name}: el cálculo por etapas no convergió")
        return sol.x

    # ---------------------------------------------------------------- interfaz de equipo
    def compute(self, inputs: Sequence[Stream], catalog: Catalog) -> tuple[Stream, ...]:
        aqueous, organic = inputs
        moved = self.solve(inputs, catalog).transferred_mol_h / 1000.0  # kmol/h
        mm = {s: catalog[s].molar_mass for s in (self.copper, self.acid, self.extractant,
                                                  self.complex)}  # fmt: skip
        aq = dict(aqueous.flows)
        aq[self.copper] = max(aq.get(self.copper, 0.0) - moved * mm[self.copper], 0.0)
        aq[self.acid] = aq.get(self.acid, 0.0) + moved * mm[self.acid]
        org = dict(organic.flows)
        org[self.complex] = max(org.get(self.complex, 0.0) + moved * mm[self.complex], 0.0)
        org[self.extractant] = org.get(self.extractant, 0.0) - 2.0 * moved * mm[self.extractant]
        return (
            Stream(aq, aqueous.temperature, aqueous.pressure),
            Stream(org, organic.temperature, organic.pressure),
        )

    def with_parameter(self, key: str, value: float) -> SolventExtraction:
        """``'kex'`` o ``'eficiencia'`` (la misma en todas las etapas)."""
        if key == "kex":
            return replace(self, kex=float(value))
        if key == "eficiencia":
            return replace(self, efficiency=(float(value),) * self.stages)
        raise KeyError(f"{self.name}: parámetro desconocido {key!r}; use 'kex' o 'eficiencia'")
