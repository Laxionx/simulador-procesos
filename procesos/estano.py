"""Fundición de estaño en dos etapas (fase 4d): balance de masa por el reparto Sn/Fe.

- Etapa 1, fusión del concentrado: SnO2 y Fe2O3 se reducen con carbono a estaño crudo (con el Fe
  pedido) y a una escoria rica en SnO y FeO; una fracción del Sn se volatiliza como SnO.
- Etapa 2, reducción de la escoria: da una aleación Sn-Fe (hardhead) y la escoria de desecho (con
  el Sn pedido); una fracción del Sn se volatiliza.
- El hardhead y los humos vuelven a la etapa 1 (lazo); a régimen, el Sn solo sale con el crudo y
  con la escoria de desecho.

El reparto entre metal y escoria sigue el coeficiente de distribución de la reacción
SnO (escoria) + Fe (metal) = Sn (metal) + FeO (escoria):
    D = (%Sn/%Fe)metal × (%Fe/%Sn)escoria
(Kandalam et al. 2023, Metals 13, 1742): 150-400 en la fusión, 20-50 en la reducción. El carbono
sale del O que se retira (SnO2 → Sn o SnO; Fe2O3 → FeO o Fe) con la razón CO/(CO + CO2) dada; la
caliza, de la basicidad CaO/SiO2 pedida. Sin balance de calor. Ver docs/estano.md.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq

from .elements import ATOMIC_WEIGHTS, molar_mass, parse_formula

SN, FE, OX, C = (ATOMIC_WEIGHTS[e] for e in ("Sn", "Fe", "O", "C"))
REDUCIBLE = ("SnO2", "SnO", "Sn", "Fe2O3", "FeO", "Fe")
INERT = ("SiO2", "CaO", "Al2O3", "MgO", "TiO2", "otros")  # pasan a la escoria
SPECIES = REDUCIBLE + INERT
_TOL, _ITER = 1e-12, 500


class TinSmeltingError(ValueError):
    """La carga no admite las metas pedidas."""


def _mm(formula: str) -> float:
    return molar_mass(parse_formula(formula))


def _element_t(tonnes: Mapping[str, float], element: str) -> float:
    return sum(t * parse_formula(s).get(element, 0.0) * ATOMIC_WEIGHTS[element] / _mm(s)
               for s, t in tonnes.items() if s != "otros")  # fmt: skip


def feed(tonnes: float, composition: Mapping[str, float]) -> dict[str, float]:
    """Toneladas por especie a partir de un análisis en % en masa (debe sumar 100)."""
    unknown = sorted(set(composition) - set(SPECIES))
    if unknown:
        raise TinSmeltingError(f"Especies sin modelo: {', '.join(unknown)}")
    total = sum(composition.values())
    if abs(total - 100.0) > 1e-6 or any(v < 0 for v in composition.values()):
        raise TinSmeltingError(f"El análisis debe sumar 100 % sin negativos (suma {total:.3f})")
    return {s: tonnes * pct / 100.0 for s, pct in composition.items() if pct > 0}


def _add(*streams: Mapping[str, float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for stream in streams:
        for s, t in stream.items():
            out[s] = out.get(s, 0.0) + t
    return out


def _carbon(o_removed_t: float, co_fraction: float) -> dict[str, float]:
    """C (t) y gases (t) para retirar ese O: cada C se lleva 2 - r átomos de O."""
    kmol_c = o_removed_t / OX / (2 - co_fraction)
    return {"C": kmol_c * C, "CO": co_fraction * kmol_c * _mm("CO"),
            "CO2": (1 - co_fraction) * kmol_c * _mm("CO2")}  # fmt: skip


@dataclass(frozen=True)
class Stage:
    metal: dict[str, float]  # t de Sn y Fe
    slag: dict[str, float]  # t por especie (SnO, FeO e inertes)
    fume_sno_t: float
    carbon: dict[str, float]

    @property
    def metal_t(self) -> float:
        return sum(self.metal.values())

    @property
    def slag_t(self) -> float:
        return sum(self.slag.values())

    def metal_pct(self, element: str) -> float:
        return 100.0 * self.metal.get(element, 0.0) / self.metal_t

    def slag_pct(self, element: str) -> float:
        return 100.0 * _element_t(self.slag, element) / self.slag_t


def smelting_stage(charge: Mapping[str, float], d: float, crude_fe_pct: float, fume: float,
                   co_fraction: float) -> Stage:  # fmt: skip
    """Etapa 1: estaño crudo con ``crude_fe_pct`` % de Fe y escoria según D."""
    sn, fe = _element_t(charge, "Sn"), _element_t(charge, "Fe")
    sn_fume = fume * sn
    e = crude_fe_pct / 100.0
    k = (1 - e) / e / d  # t de Sn en escoria por t de Fe en escoria
    # (1 - e) M + k F = Sn disponible ;  e M + F = Fe
    metal_t, fe_slag = np.linalg.solve(np.array([[1 - e, k], [e, 1.0]]), [sn - sn_fume, fe])
    if metal_t <= 0 or fe_slag < 0:
        raise TinSmeltingError("Fusión imposible: la carga no da crudo con ese Fe y ese D")
    sn_slag = k * fe_slag
    slag = {"SnO": sn_slag / SN * _mm("SnO"), "FeO": fe_slag / FE * _mm("FeO")}
    slag |= {s: t for s, t in charge.items() if s in INERT}
    o_out = _element_t({"SnO": slag["SnO"] + sn_fume / SN * _mm("SnO"), "FeO": slag["FeO"]}, "O")
    o_in = _element_t({s: t for s, t in charge.items() if s in REDUCIBLE}, "O")
    metal = {"Sn": (1 - e) * metal_t, "Fe": e * metal_t}
    return Stage(metal, slag, sn_fume / SN * _mm("SnO"), _carbon(o_in - o_out, co_fraction))


def reduction_stage(slag: Mapping[str, float], d: float, discard_sn_pct: float, fume: float,
                    co_fraction: float) -> Stage:  # fmt: skip
    """Etapa 2: hardhead y escoria de desecho con ``discard_sn_pct`` % de Sn, según D."""
    sn_in, fe_in = _element_t(slag, "Sn"), _element_t(slag, "Fe")
    sn_fume = fume * sn_in
    sn_av = sn_in - sn_fume
    x = discard_sn_pct / 100.0
    a, b = _mm("SnO") / SN, _mm("FeO") / FE
    inert = sum(t for s, t in slag.items() if s in INERT)

    def sn_discard(fe_d: float) -> float:  # Sn de la escoria = x × masa de escoria
        return x * (b * fe_d + inert) / (1 - x * a)

    def gap(fe_d: float) -> float:  # (Sn/Fe)hardhead = D (Sn/Fe)escoria
        return (sn_av - sn_discard(fe_d)) * fe_d - d * sn_discard(fe_d) * (fe_in - fe_d)

    if sn_av <= sn_discard(fe_in) or gap(fe_in * 1e-12) >= 0:
        raise TinSmeltingError("Reducción imposible: la escoria ya está bajo esa ley de Sn")
    fe_d = brentq(gap, fe_in * 1e-12, fe_in, xtol=1e-14, rtol=1e-14)
    sn_d = sn_discard(fe_d)
    discard = {"SnO": sn_d * a, "FeO": fe_d * b} | {s: t for s, t in slag.items() if s in INERT}
    o_in = _element_t({s: t for s, t in slag.items() if s in ("SnO", "FeO")}, "O")
    o_out = _element_t({"SnO": discard["SnO"] + sn_fume * a, "FeO": discard["FeO"]}, "O")
    metal = {"Sn": sn_av - sn_d, "Fe": fe_in - fe_d}
    return Stage(metal, discard, sn_fume * a, _carbon(o_in - o_out, co_fraction))


@dataclass(frozen=True)
class TinResult:
    fresh: dict[str, float]  # concentrado + otras cargas + caliza (t por especie)
    limestone_t: float
    stage1: Stage
    stage2: Stage
    iterations: int

    @property
    def sn_fed_t(self) -> float:
        return _element_t(self.fresh, "Sn")

    @property
    def recovery(self) -> float:
        """Fracción del Sn de las cargas que sale en el estaño crudo."""
        return self.stage1.metal["Sn"] / self.sn_fed_t

    @property
    def carbon_t(self) -> float:
        return self.stage1.carbon["C"] + self.stage2.carbon["C"]

    def elements(self) -> tuple[dict[str, float], dict[str, float]]:
        """t de cada elemento que entra (cargas, caliza y carbono) y sale (crudo, escoria de
        desecho y gases); el hardhead y los humos son internos."""
        names = ("Sn", "Fe", "O", "C", "Ca", "Si", "Al", "Mg", "Ti")
        inputs = _add(self.fresh, {"CaCO3": self.limestone_t, "C": self.carbon_t})
        gases = [
            {k: v for k, v in st.carbon.items() if k != "C"} for st in (self.stage1, self.stage2)
        ]
        calcination = {"CO2": self.limestone_t / _mm("CaCO3") * _mm("CO2")}
        outputs = _add(self.stage1.metal, self.stage2.slag, *gases, calcination)
        return ({e: _element_t(inputs, e) for e in names},
                {e: _element_t(outputs, e) for e in names})  # fmt: skip


def smelt_tin(
    feeds: Mapping[str, float],
    *,
    crude_fe_pct: float,
    discard_sn_pct: float,
    d1: float,
    d2: float,
    basicity: float | None = None,
    fume1: float = 0.0,
    fume2: float = 0.0,
    co_fraction: float = 0.5,
) -> TinResult:
    """Dos etapas con reciclo del hardhead y de los humos. ``feeds``: t por especie de todas las
    cargas frescas. Con ``basicity`` se agrega caliza hasta CaO/SiO2 = basicity."""
    if not 0 < crude_fe_pct < 100 or not 0 < discard_sn_pct < 100:
        raise TinSmeltingError("Fe del crudo y Sn de la escoria deben estar entre 0 y 100 %")
    if d1 <= 0 or d2 <= 0 or not 0 <= fume1 < 1 or not 0 <= fume2 < 1:
        raise TinSmeltingError("D positivos y fracciones de humo entre 0 y 1")
    if not 0 <= co_fraction <= 1:
        raise TinSmeltingError("La fracción de CO debe estar entre 0 y 1")
    fresh = dict(feeds)
    charge = dict(fresh)
    limestone = 0.0
    if basicity is not None:
        cao_needed = basicity * fresh.get("SiO2", 0.0) - fresh.get("CaO", 0.0)
        limestone = max(cao_needed, 0.0) / _mm("CaO") * _mm("CaCO3")
        charge = _add(charge, {"CaO": limestone / _mm("CaCO3") * _mm("CaO")})
    recycle: dict[str, float] = {}
    for iteration in range(1, _ITER + 1):
        s1 = smelting_stage(_add(charge, recycle), d1, crude_fe_pct, fume1, co_fraction)
        s2 = reduction_stage(s1.slag, d2, discard_sn_pct, fume2, co_fraction)
        new = _add(s2.metal, {"SnO": s1.fume_sno_t + s2.fume_sno_t})
        change = max(abs(new.get(k, 0.0) - recycle.get(k, 0.0)) for k in new)
        recycle = new
        if change < _TOL * max(1.0, sum(new.values())):
            return TinResult(fresh, limestone, s1, s2, iteration)
    raise TinSmeltingError("El reciclo del hardhead no converge")
