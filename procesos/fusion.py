"""Horno de fusión flash de cobre (fase 4a): balance de masa y de calor por tonelada de carga.

Dada la mineralogía de la carga y dos metas que la planta mide —la ley de la mata y la sílice de
la escoria—, el horno reparte el Cu, Fe, Zn y S entre mata, escoria y gases, y devuelve el
oxígeno, el nitrógeno y el fundente con que cierra el balance de calor sin combustible (fusión
autógena):

- Mata: Cu2S, FeS y ZnS. Escoria: FeO, SiO2, ZnO, ZnS, Cu2O, Cu2S y la ganga inerte (Al2O3).
  Gases: SO2 y el N2 del aire; sin O2 ni SO3 libres.
- El Cu de la escoria sale del coeficiente de distribución mata/escoria; su Cu2S, de la relación
  molar mata/escoria; el resto del Cu de la escoria es Cu2O. El zinc se reparte con su coeficiente
  escoria/mata y la relación ZnO/ZnS de la escoria (Bacedoni et al. 2020, calculados con FactSage).
- Calor: entalpías absolutas (ΔfH + calor sensible) de `thermo_piro`. Entran la carga y el
  fundente a 25 °C y el aire a 227 °C; salen los productos a 1.300 °C más la pérdida del horno.

Todas las ecuaciones son lineales en los kmol salvo el reparto del zinc (una relación de
concentraciones), que se resuelve por sustitución sucesiva sobre la razón escoria/mata.
Ver docs/fusion.md.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from .elements import ATOMIC_WEIGHTS, molar_mass, parse_formula
from .fusion_datos import CU2S_MATTE_SLAG, D_CU_MATTE_SLAG, D_ZN_SLAG_MATTE, ZNO_ZNS_SLAG
from .thermo import KELVIN, T_REF, ThermoDatabase
from .thermo_data import DEFAULT_THERMO

NM3_PER_KMOL = 22.414
INERT = "Al2O3"  # ganga no listada en la mineralogía
CU2S_GRADE = 100 * 2 * ATOMIC_WEIGHTS["Cu"] / molar_mass(parse_formula("Cu2S"))  # 79,85 %
ELEMENTS = ("Cu", "Fe", "Zn", "S", "O", "Si")

# Mineral -> sustancias cuyo ΔfH lo representa (fórmula, fase, moles por mol de mineral).
_PROXY = {
    "CuFeO2": (("Cu2O", "s", 0.5), ("Fe2O3", "s", 0.5)),  # delafosita
    "Cu2OSO4": (("CuO", "s", 1.0), ("CuSO4", "s", 1.0)),  # dolerofanita
}
FEED_MINERALS = (
    "CuFeS2", "FeS2", "Cu5FeS4", "Cu2S", "CuS", "ZnS", "FeS", "Fe2SiO4", "Fe3O4", "Fe2O3", "Cu",
    "CuSO4", "ZnSO4", "CuFeO2", "Cu2OSO4", "Cu2O", "CuO", "SiO2", INERT,
)  # fmt: skip

# Incógnitas (kmol por t de carga): los productos, el O2 y el N2 del aire y el SiO2 del fundente.
PRODUCTS = (
    ("mata", "Cu2S", "l"),
    ("mata", "FeS", "l"),
    ("mata", "ZnS", "s"),
    ("escoria", "FeO", "l"),
    ("escoria", "SiO2", "l"),
    ("escoria", "ZnO", "s"),
    ("escoria", "ZnS", "s"),
    ("escoria", "Cu2O", "l"),
    ("escoria", "Cu2S", "l"),
    ("gas", "SO2", "g"),
)
UNKNOWNS = tuple(f"{p}:{f}" for p, f, _ in PRODUCTS) + ("aire:O2", "aire:N2", "fundente:SiO2")
_IX = {name: i for i, name in enumerate(UNKNOWNS)}
_ZN_TOL, _ZN_ITER = 1e-12, 100


class SmeltingError(ValueError):
    """La carga no admite la mata, la escoria o el balance de calor pedidos."""


def _mm(formula: str) -> float:
    return molar_mass(parse_formula(formula))


def feed_enthalpy(mineral: str, thermo: ThermoDatabase = DEFAULT_THERMO) -> float:
    """Entalpía de un mineral de la carga a 25 °C (kJ/mol = MJ/kmol)."""
    parts = _PROXY.get(mineral, ((mineral, "s", 1.0),))
    return sum(n * thermo.by_key(f, ph).enthalpy(T_REF) for f, ph, n in parts)


@dataclass(frozen=True)
class SmeltResult:
    """Balance por tonelada de carga seca. ``kmol`` tiene las incógnitas de ``UNKNOWNS``."""

    feed_kmol: dict[str, float]
    kmol: dict[str, float]
    products_k: float
    air_k: float
    heat_loss_mj_t: float

    def _mass(self, phase: str) -> float:
        total = sum(n * _mm(k.split(":")[1]) for k, n in self.kmol.items() if k.startswith(phase))
        if phase == "escoria":
            total += self.feed_kmol.get(INERT, 0.0) * _mm(INERT)
        return total

    @property
    def matte_kg(self) -> float:
        return self._mass("mata:")

    @property
    def slag_kg(self) -> float:
        return self._mass("escoria")

    @property
    def matte_grade(self) -> float:
        return 100 * 2 * ATOMIC_WEIGHTS["Cu"] * self.kmol["mata:Cu2S"] / self.matte_kg

    @property
    def slag_sio2(self) -> float:
        return 100 * self.kmol["escoria:SiO2"] * _mm("SiO2") / self.slag_kg

    @property
    def oxygen_nm3_t(self) -> float:
        return self.kmol["aire:O2"] * NM3_PER_KMOL

    @property
    def enrichment_pct(self) -> float:
        o2, n2 = self.kmol["aire:O2"], self.kmol["aire:N2"]
        return 100 * o2 / (o2 + n2)

    @property
    def flux_pct(self) -> float:
        return self.kmol["fundente:SiO2"] * _mm("SiO2") / 10.0  # kg por t -> % de la carga

    @property
    def so2_kg(self) -> float:
        return self.kmol["gas:SO2"] * _mm("SO2")

    def elements(self) -> tuple[dict[str, float], dict[str, float]]:
        """kmol de cada elemento que entra y que sale (la ganga inerte no cuenta)."""
        inn = dict.fromkeys(ELEMENTS, 0.0)
        out = dict.fromkeys(ELEMENTS, 0.0)
        streams = [(m, n, inn) for m, n in self.feed_kmol.items() if m != INERT]
        for key, n in self.kmol.items():
            formula = key.split(":")[1]
            streams.append((formula, n, inn if key.startswith(("aire", "fundente")) else out))
        for formula, n, side in streams:
            for el, k in parse_formula(formula).items():
                if el in side:
                    side[el] += n * k
        return inn, out

    def enthalpies(self, thermo: ThermoDatabase = DEFAULT_THERMO) -> tuple[float, float]:
        """Entalpía que entra y que sale (MJ por t), sin la pérdida del horno."""
        h_in = sum(n * feed_enthalpy(m, thermo) for m, n in self.feed_kmol.items())
        h_in += self.kmol["fundente:SiO2"] * thermo.by_key("SiO2", "s").enthalpy(T_REF)
        for gas in ("O2", "N2"):
            h_in += self.kmol[f"aire:{gas}"] * thermo.by_key(gas, "g").enthalpy(self.air_k)
        h_out = sum(
            self.kmol[f"{p}:{f}"] * thermo.by_key(f, ph).enthalpy(self.products_k)
            for p, f, ph in PRODUCTS
        )
        h_out += self.kmol["aire:N2"] * thermo.by_key("N2", "g").enthalpy(self.products_k)
        h_out += self.feed_kmol.get(INERT, 0.0) * thermo.by_key(INERT, "s").enthalpy(
            self.products_k
        )
        return h_in, h_out


def feed_from_mineralogy(mineralogy: Mapping[str, float]) -> dict[str, float]:
    """kmol de cada mineral por t de carga; la masa que falta hasta 100 % entra como inerte."""
    unknown = sorted(set(mineralogy) - set(FEED_MINERALS))
    if unknown:
        raise SmeltingError(f"Minerales sin datos: {', '.join(unknown)}")
    if any(v < 0 for v in mineralogy.values()):
        raise SmeltingError("La mineralogía no admite porcentajes negativos")
    total = sum(mineralogy.values())
    if total > 100.0 + 1e-6:
        raise SmeltingError(f"La mineralogía suma {total:.2f} %, más de 100 %")
    mass = dict(mineralogy)
    mass[INERT] = mass.get(INERT, 0.0) + max(100.0 - total, 0.0)
    return {m: 10.0 * pct / _mm(m) for m, pct in mass.items() if pct > 0}


def _system(
    feed: dict[str, float],
    grade: float,
    sio2: float,
    loss: float,
    products_k: float,
    air_k: float,
    slag_to_matte: float,
    thermo: ThermoDatabase,
) -> tuple[np.ndarray, np.ndarray]:
    n = len(UNKNOWNS)
    rows: list[np.ndarray] = []
    rhs: list[float] = []

    def add(coefs: Mapping[str, float], value: float) -> None:
        row = np.zeros(n)
        for name, c in coefs.items():
            row[_IX[name]] += c
        rows.append(row)
        rhs.append(value)

    # Balances de elementos: salidas - entradas desconocidas = carga.
    feed_el = dict.fromkeys(ELEMENTS, 0.0)
    for m, kmol in feed.items():
        if m != INERT:
            for el, k in parse_formula(m).items():
                feed_el[el] += kmol * k
    for el in ELEMENTS:
        coefs = {}
        for name in UNKNOWNS:
            k = parse_formula(name.split(":")[1]).get(el, 0.0)
            if k:
                coefs[name] = -k if name.startswith(("aire", "fundente")) else k
        add(coefs, feed_el[el])

    inert_kg = feed.get(INERT, 0.0) * _mm(INERT)
    slag = {f"escoria:{f}": _mm(f) for p, f, _ in PRODUCTS if p == "escoria"}
    matte = {f"mata:{f}": _mm(f) for p, f, _ in PRODUCTS if p == "mata"}
    cu = ATOMIC_WEIGHTS["Cu"]

    # Ley de mata: masa de Cu en la mata = ley × masa de mata.
    add(
        {k: -grade * v for k, v in matte.items()}
        | {"mata:Cu2S": 2 * cu - grade * matte["mata:Cu2S"]},
        0.0,
    )
    # SiO2 de la escoria = meta × masa de escoria (la ganga inerte también es escoria).
    add(
        {k: -sio2 * v for k, v in slag.items()} | {"escoria:SiO2": (1 - sio2) * _mm("SiO2")},
        sio2 * inert_kg,
    )
    # Cu de la escoria = (ley / D) × masa de escoria.
    c_slag = grade / D_CU_MATTE_SLAG
    coefs = {k: -c_slag * v for k, v in slag.items()}
    for f in ("Cu2O", "Cu2S"):
        coefs[f"escoria:{f}"] += 2 * cu
    add(coefs, c_slag * inert_kg)
    add({"mata:Cu2S": 1.0, "escoria:Cu2S": -CU2S_MATTE_SLAG}, 0.0)
    add({"escoria:ZnO": 1.0, "escoria:ZnS": -ZNO_ZNS_SLAG}, 0.0)
    # Zn: (Zn escoria / masa escoria) = D × (Zn mata / masa mata), con la razón de masas fija.
    add({"escoria:ZnO": 1.0, "escoria:ZnS": 1.0, "mata:ZnS": -D_ZN_SLAG_MATTE * slag_to_matte}, 0.0)

    # Calor: H(productos) + pérdida = H(carga) + H(fundente) + H(aire).
    coefs = {f"{p}:{f}": thermo.by_key(f, ph).enthalpy(products_k) for p, f, ph in PRODUCTS}
    coefs["aire:O2"] = -thermo.by_key("O2", "g").enthalpy(air_k)
    coefs["aire:N2"] = thermo.by_key("N2", "g").enthalpy(products_k) - thermo.by_key(
        "N2", "g"
    ).enthalpy(air_k)
    coefs["fundente:SiO2"] = -thermo.by_key("SiO2", "s").enthalpy(T_REF)
    h_feed = sum(kmol * feed_enthalpy(m, thermo) for m, kmol in feed.items())
    h_inert = feed.get(INERT, 0.0) * thermo.by_key(INERT, "s").enthalpy(products_k)
    add(coefs, h_feed - loss - h_inert)
    return np.vstack(rows), np.asarray(rhs)


def smelt(
    mineralogy: Mapping[str, float],
    matte_grade: float,
    slag_sio2: float,
    heat_loss_mj_t: float,
    *,
    products_c: float = 1300.0,
    air_c: float = 227.0,
    thermo: ThermoDatabase = DEFAULT_THERMO,
) -> SmeltResult:
    """Balance del horno por t de carga. ``matte_grade`` y ``slag_sio2`` en % en masa;
    ``heat_loss_mj_t`` es la pérdida térmica del horno (MJ por t de carga, positiva)."""
    if not 0 < matte_grade < CU2S_GRADE:
        raise SmeltingError(f"La ley de mata debe estar entre 0 y {CU2S_GRADE:.2f} %")
    if not 0 < slag_sio2 < 100:
        raise SmeltingError("La sílice de la escoria debe estar entre 0 y 100 %")
    if heat_loss_mj_t < 0:
        raise SmeltingError("La pérdida térmica del horno no puede ser negativa")
    feed = feed_from_mineralogy(mineralogy)
    products_k, air_k = products_c + KELVIN, air_c + KELVIN
    ratio = 1.0
    for _ in range(_ZN_ITER):
        a, b = _system(
            feed, matte_grade / 100, slag_sio2 / 100, heat_loss_mj_t, products_k, air_k, ratio,
            thermo,
        )  # fmt: skip
        x = np.linalg.solve(a, b)
        result = SmeltResult(
            feed, dict(zip(UNKNOWNS, map(float, x), strict=True)), products_k, air_k, heat_loss_mj_t
        )
        new_ratio = result.slag_kg / result.matte_kg if result.matte_kg > 0 else ratio
        if abs(new_ratio - ratio) < _ZN_TOL * max(1.0, ratio):
            break
        ratio = new_ratio
    else:
        raise SmeltingError("El reparto del zinc no converge")
    _check(result)
    return result


def _check(result: SmeltResult) -> None:
    negative = [k for k, v in result.kmol.items() if v < -1e-12]
    if not negative:
        return
    hints = {
        "aire:N2": "el calor no alcanza para fundir sin combustible: falta energía",
        "fundente:SiO2": "la carga ya trae más sílice que la que pide la escoria",
        "aire:O2": "la carga trae más oxígeno que el necesario para esa ley",
    }
    detail = "; ".join(hints.get(k, f"{k} sale negativo") for k in negative)
    raise SmeltingError(f"Balance imposible con esas metas: {detail}")
