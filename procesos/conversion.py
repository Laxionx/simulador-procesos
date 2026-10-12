"""Convertidor Peirce-Smith (fase 4b): balance de masa y de calor por etapa de soplado.

- Soplado a escoria: el aire oxida el FeS de la mata a FeO y Fe3O4, que con la sílice forman la
  escoria; el azufre sale como SO2. Termina cuando el metal blanco (Cu2S) llega al Fe pedido.
- Soplado a cobre: el Cu2S se oxida a cobre blíster y SO2 hasta el S pedido en el blíster; el Fe
  que quede pasa a la escoria como magnetita y el Cu de esa escoria, como Cu2O.

Cada etapa es un balance lineal por elemento (Cu, Fe, S, O) con metas que se miden en planta: el
Fe del metal blanco o el S del blíster (fin de etapa), el Cu de la escoria (atrapado como Cu2S en
el soplado a escoria) y la fracción del Fe de la escoria que es magnetita. El cobre metálico que
entra (carga fría) no se oxida en el soplado a escoria. La sílice y la ganga pasan a la escoria.

El aire sale del O2 que reacciona y de la eficiencia de oxígeno (O2 que reacciona / O2 soplado):
    aire = (O2 que reacciona / eficiencia − O2 puro) / 0,21   [Nm³]
El calor compara lo que entra (cada carga a su temperatura, aire a 25 °C) con lo que sale a la
temperatura del baño; la diferencia es la pérdida del convertidor o el calor que queda para fundir
más carga fría. Ver docs/conversion.md.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from .elements import ATOMIC_WEIGHTS, molar_mass, parse_formula
from .thermo import KELVIN, ThermoDatabase
from .thermo_data import DEFAULT_THERMO

NM3_PER_KMOL = 22.414
O2_IN_AIR = 0.21
ELEMENTS = ("Cu", "Fe", "S", "O")
INERT = ("SiO2", "Al2O3")  # pasan a la escoria sin reaccionar
FEED_SPECIES = ("Cu2S", "FeS", "Fe3O4", "FeO", "Cu", "Cu2O") + INERT
# Fase de cada especie en una corriente caliente (mata, escoria, metal) y en una fría (25 °C).
HOT = {"Cu2S": "l", "FeS": "l", "Fe3O4": "s", "FeO": "l", "Cu": "l", "Cu2O": "l", "SiO2": "l",
       "Al2O3": "s", "SO2": "g", "N2": "g", "O2": "g"}  # fmt: skip
# A 25 °C no hay ficha de FeO sólido: una carga fría con FeO falla en el balance de calor.
COLD = {k: v for k, v in (HOT | {"Cu2S": "s", "FeS": "s", "Cu2O": "s", "SiO2": "s"}).items()
        if k != "FeO"}  # fmt: skip
COLD_LIMIT_C = 200.0
CU2S_GRADE = 100 * 2 * ATOMIC_WEIGHTS["Cu"] / molar_mass(parse_formula("Cu2S"))


class ConversionError(ValueError):
    """La carga no admite las metas pedidas."""


def _mm(formula: str) -> float:
    return molar_mass(parse_formula(formula))


def _h(formula: str, temp_c: float, thermo: ThermoDatabase) -> float:
    """Entalpía absoluta (kJ/mol = MJ/kmol). La ficha «Cu líquido» cubre también el sólido."""
    phase = (COLD if temp_c <= COLD_LIMIT_C else HOT)[formula]
    return thermo.by_key(formula, phase).enthalpy(temp_c + KELVIN)


@dataclass(frozen=True)
class Feed:
    """Una carga al convertidor: toneladas por especie y su temperatura."""

    name: str
    tonnes: Mapping[str, float]
    temp_c: float = 25.0

    def __post_init__(self) -> None:
        unknown = sorted(set(self.tonnes) - set(FEED_SPECIES))
        if unknown:
            raise ConversionError(f"{self.name}: especies sin modelo: {', '.join(unknown)}")
        if any(v < 0 for v in self.tonnes.values()):
            raise ConversionError(f"{self.name}: toneladas negativas")

    def kmol(self) -> dict[str, float]:
        return {s: 1000.0 * t / _mm(s) for s, t in self.tonnes.items() if t > 0}


def matte(name: str, tonnes: float, cu_pct: float, fe3o4_pct: float = 0.0,
          temp_c: float = 1200.0) -> Feed:  # fmt: skip
    """Mata de Cu2S + FeS (+ Fe3O4) con la ley publicada."""
    if not 0 < cu_pct <= CU2S_GRADE * (1 - fe3o4_pct / 100):
        raise ConversionError(f"{name}: ley {cu_pct} % imposible para Cu2S + FeS")
    cu2s = tonnes * cu_pct / CU2S_GRADE
    fe3o4 = tonnes * fe3o4_pct / 100
    return Feed(name, {"Cu2S": cu2s, "Fe3O4": fe3o4, "FeS": tonnes - cu2s - fe3o4}, temp_c)


def oxide_slag(name: str, tonnes: float, cu_pct: float, fe_pct: float, sio2_pct: float,
               temp_c: float = 25.0) -> Feed:  # fmt: skip
    """Escoria reciclada: Cu como Cu2O, Fe como Fe3O4, SiO2, y el resto como ganga inerte."""
    cu2o = cu_pct * _mm("Cu2O") / (2 * ATOMIC_WEIGHTS["Cu"])
    fe3o4 = fe_pct * _mm("Fe3O4") / (3 * ATOMIC_WEIGHTS["Fe"])
    rest = 100.0 - cu2o - fe3o4 - sio2_pct
    if rest < 0:
        raise ConversionError(f"{name}: el análisis suma más de 100 %")
    pct = {"Cu2O": cu2o, "Fe3O4": fe3o4, "SiO2": sio2_pct, "Al2O3": rest}
    return Feed(name, {s: tonnes * p / 100 for s, p in pct.items()}, temp_c)


@dataclass(frozen=True)
class Stage:
    """Resultado de una etapa. ``products`` en kmol por «fase:especie»."""

    name: str
    feeds: tuple[Feed, ...]
    products: dict[str, float]
    o2_reacted: float  # kmol
    efficiency: float
    pure_o2_nm3: float
    bath_c: float

    def mass_t(self, phase: str) -> float:
        return sum(n * _mm(k.split(":")[1]) for k, n in self.products.items()
                   if k.startswith(phase + ":")) / 1000.0  # fmt: skip

    def percent(self, phase: str, element: str) -> float:
        kg = sum(n * parse_formula(k.split(":")[1]).get(element, 0.0) * ATOMIC_WEIGHTS[element]
                 for k, n in self.products.items() if k.startswith(phase + ":"))  # fmt: skip
        return kg / (10.0 * self.mass_t(phase))

    @property
    def air_nm3(self) -> float:
        """Aire que pide el balance con la eficiencia dada."""
        o2_blown = self.o2_reacted / self.efficiency * NM3_PER_KMOL
        return (o2_blown - self.pure_o2_nm3) / O2_IN_AIR

    def elements(self) -> tuple[dict[str, float], dict[str, float]]:
        inn, out = dict.fromkeys(ELEMENTS, 0.0), dict.fromkeys(ELEMENTS, 0.0)
        for feed in self.feeds:
            for s, n in feed.kmol().items():
                if s not in INERT:
                    for el, k in parse_formula(s).items():
                        inn[el] += n * k
        inn["O"] += 2 * self.o2_reacted
        for key, n in self.products.items():
            s = key.split(":")[1]
            if s not in INERT:
                for el, k in parse_formula(s).items():
                    out[el] += n * k
        return inn, out

    def heat_balance(self, air_nm3: float | None = None,
                     thermo: ThermoDatabase = DEFAULT_THERMO) -> tuple[float, float]:  # fmt: skip
        """Entalpía que entra y que sale (MJ), con el aire medido si se da (si no, el del
        balance). El O2 que no reacciona sale caliente con el N2."""
        air = self.air_nm3 if air_nm3 is None else air_nm3
        o2_blown = (air * O2_IN_AIR + self.pure_o2_nm3) / NM3_PER_KMOL
        n2 = air * (1 - O2_IN_AIR) / NM3_PER_KMOL
        h_in = sum(n * _h(s, f.temp_c, thermo) for f in self.feeds for s, n in f.kmol().items())
        h_in += o2_blown * _h("O2", 25.0, thermo) + n2 * _h("N2", 25.0, thermo)
        h_out = sum(n * _h(k.split(":")[1], self.bath_c, thermo) for k, n in self.products.items())
        h_out += (o2_blown - self.o2_reacted) * _h("O2", self.bath_c, thermo)
        h_out += n2 * _h("N2", self.bath_c, thermo)
        return h_in, h_out

    def cold_copper_capacity_t(self, heat_loss_mj: float, air_nm3: float | None = None,
                               thermo: ThermoDatabase = DEFAULT_THERMO) -> float:  # fmt: skip
        """Cobre frío (t, a 25 °C) que el calor sobrante de la etapa alcanza a fundir."""
        h_in, h_out = self.heat_balance(air_nm3, thermo)
        per_kmol = _h("Cu", self.bath_c, thermo) - _h("Cu", 25.0, thermo)
        return (h_in - h_out - heat_loss_mj) / per_kmol * _mm("Cu") / 1000.0


class _System:
    """Sistema lineal por nombre de incógnita."""

    def __init__(self, unknowns: Sequence[str]) -> None:
        self.ix = {u: i for i, u in enumerate(unknowns)}
        self.rows: list[np.ndarray] = []
        self.rhs: list[float] = []

    def add(self, coefs: Mapping[str, float], value: float) -> None:
        row = np.zeros(len(self.ix))
        for name, c in coefs.items():
            row[self.ix[name]] += c
        self.rows.append(row)
        self.rhs.append(value)

    def element_rows(self, feeds_el: Mapping[str, float]) -> None:
        for el in ELEMENTS:
            coefs = {u: parse_formula(u.split(":")[1]).get(el, 0.0) for u in self.ix
                     if u != "O2" and u.split(":")[1] not in INERT}  # fmt: skip
            if el == "O":
                coefs["O2"] = -2.0
            add = {u: c for u, c in coefs.items() if c}
            self.add(add, feeds_el[el])

    def solve(self) -> dict[str, float]:
        x = np.linalg.solve(np.vstack(self.rows), np.asarray(self.rhs))
        return dict(zip(self.ix, map(float, x), strict=True))


def _feed_elements(feeds: Sequence[Feed]) -> tuple[dict[str, float], float, dict[str, float]]:
    """kmol de cada elemento reactivo, kmol de Cu metálico y toneladas inertes por especie."""
    el = dict.fromkeys(ELEMENTS, 0.0)
    metal, inert = 0.0, dict.fromkeys(INERT, 0.0)
    for f in feeds:
        for s, n in f.kmol().items():
            if s in INERT:
                inert[s] += n
                continue
            for e, k in parse_formula(s).items():
                el[e] += n * k
            if s == "Cu":
                metal += n
    return el, metal, inert


def _check(products: Mapping[str, float], stage: str) -> None:
    negative = sorted(k for k, v in products.items() if v < -1e-9)
    if negative:
        raise ConversionError(f"{stage}: imposible con esas metas ({', '.join(negative)} < 0)")


def slag_blow(
    feeds: Sequence[Feed],
    *,
    end_fe_pct: float,
    slag_cu_pct: float,
    magnetite_fe: float,
    efficiency: float,
    pure_o2_nm3: float = 0.0,
    bath_c: float = 1200.0,
    slag_sio2_pct: float | None = None,
    name: str = "soplado a escoria",
) -> Stage:
    """Soplado a escoria hasta que el metal blanco tenga ``end_fe_pct`` % de Fe. La escoria
    lleva ``slag_cu_pct`` % de Cu (Cu2S atrapado) y ``magnetite_fe`` de su Fe como Fe3O4. Con
    ``slag_sio2_pct``, el fundente (SiO2 a 25 °C) se calcula para llegar a esa sílice."""
    _validate(efficiency, magnetite_fe, slag_cu_pct)
    el, metal, inert = _feed_elements(feeds)
    unknowns = ("metal:Cu2S", "metal:FeS", "metal:Cu", "escoria:FeO", "escoria:Fe3O4",
                "escoria:Cu2S", "gas:SO2", "O2")  # fmt: skip
    if slag_sio2_pct is not None:
        if not 0 < slag_sio2_pct < 100:
            raise ConversionError("La sílice de la escoria debe estar entre 0 y 100 %")
        unknowns += ("fundente:SiO2",)
    sys_ = _System(unknowns)
    sys_.element_rows(el)
    sys_.add({"metal:Cu": 1.0}, metal)
    sys_.add({"escoria:Fe3O4": 3 * (1 - magnetite_fe), "escoria:FeO": -magnetite_fe}, 0.0)
    inert_kg = sum(n * _mm(sp) for sp, n in inert.items())
    slag_kg = {u: _mm(u.split(":")[1]) for u in unknowns if u.startswith(("escoria:", "fundente:"))}
    c = slag_cu_pct / 100
    cu_row = {u: -c * m for u, m in slag_kg.items()}
    cu_row["escoria:Cu2S"] += 2 * ATOMIC_WEIGHTS["Cu"]
    sys_.add(cu_row, c * inert_kg)
    if slag_sio2_pct is not None:  # SiO2 total = meta × masa de escoria
        x = slag_sio2_pct / 100
        si_row = {u: -x * m for u, m in slag_kg.items()}
        si_row["fundente:SiO2"] += _mm("SiO2")
        sys_.add(si_row, x * inert_kg - inert["SiO2"] * _mm("SiO2"))
    e = end_fe_pct / 100
    wm = {u: -e * _mm(u.split(":")[1]) for u in unknowns if u.startswith("metal:")}
    wm["metal:FeS"] += ATOMIC_WEIGHTS["Fe"]
    sys_.add(wm, 0.0)
    sol = sys_.solve()
    o2 = sol.pop("O2")
    flux = sol.pop("fundente:SiO2", 0.0)
    _check(sol | {"O2": o2, "fundente:SiO2": flux}, name)
    inert_out = dict(inert, SiO2=inert["SiO2"] + flux)
    products = sol | {f"escoria:{sp}": n for sp, n in inert_out.items() if n > 0}
    all_feeds = tuple(feeds) + ((Feed("fundente", {"SiO2": flux * _mm("SiO2") / 1000}),)
                                if flux > 0 else ())  # fmt: skip
    return Stage(name, all_feeds, products, o2, efficiency, pure_o2_nm3, bath_c)


def copper_blow(
    feeds: Sequence[Feed],
    *,
    blister_s_pct: float,
    slag_cu_pct: float,
    efficiency: float,
    pure_o2_nm3: float = 0.0,
    bath_c: float = 1200.0,
    name: str = "soplado a cobre",
) -> Stage:
    """Soplado a cobre hasta ``blister_s_pct`` % de S en el blíster. Todo el Fe pasa a la escoria
    como Fe3O4 y el Cu de la escoria (``slag_cu_pct`` %) es Cu2O."""
    _validate(efficiency, 0.0, slag_cu_pct)
    el, _metal, inert = _feed_elements(feeds)
    unknowns = ("blister:Cu", "blister:Cu2S", "escoria:Fe3O4", "escoria:Cu2O", "gas:SO2", "O2")
    sys_ = _System(unknowns)
    sys_.element_rows(el)
    s = blister_s_pct / 100
    sys_.add({"blister:Cu2S": ATOMIC_WEIGHTS["S"] - s * _mm("Cu2S"),
              "blister:Cu": -s * _mm("Cu")}, 0.0)  # fmt: skip
    inert_kg = sum(n * _mm(sp) for sp, n in inert.items())
    c = slag_cu_pct / 100
    sys_.add({"escoria:Cu2O": 2 * ATOMIC_WEIGHTS["Cu"] - c * _mm("Cu2O"),
              "escoria:Fe3O4": -c * _mm("Fe3O4")}, c * inert_kg)  # fmt: skip
    x = sys_.solve()
    o2 = x.pop("O2")
    products = x | {f"escoria:{sp}": n for sp, n in inert.items() if n > 0}
    _check(products | {"O2": o2}, name)
    return Stage(name, tuple(feeds), products, o2, efficiency, pure_o2_nm3, bath_c)


def _validate(efficiency: float, magnetite_fe: float, slag_cu_pct: float) -> None:
    if not 0 < efficiency <= 1:
        raise ConversionError("La eficiencia de oxígeno debe estar entre 0 y 1")
    if not 0 <= magnetite_fe <= 1:
        raise ConversionError("La fracción de Fe como magnetita debe estar entre 0 y 1")
    if not 0 <= slag_cu_pct < 100:
        raise ConversionError("El Cu de la escoria debe estar entre 0 y 100 %")


def carry_over(stage: Stage, phase: str, fraction: float, temp_c: float, name: str) -> Feed:
    """Lo que de una fase de ``stage`` pasa a la etapa siguiente (p. ej. metal blanco, o la
    escoria que queda tras escoriar), como carga a ``temp_c``."""
    tonnes = {k.split(":")[1]: fraction * n * _mm(k.split(":")[1]) / 1000.0
              for k, n in stage.products.items() if k.startswith(phase + ":")}  # fmt: skip
    return Feed(name, tonnes, temp_c)


def skimmed_slag_from_iron(feeds_t: Sequence[tuple[float, float, float]], end_cu_pct: float,
                           end_fe_pct: float, slag_cu_pct: float, slag_fe_pct: float,
                           initial_slag_t: float = 0.0) -> float:  # fmt: skip
    """Escoria de los soplados a escoria (t) por balance de Fe y Cu con análisis medidos.
    ``feeds_t``: (t, % Cu, % Fe) de cada carga. El Fe que sale de la mata va a la escoria; el
    Cu se reparte entre la escoria (a su ley) y la mata final. La escoria inicial se suma."""
    cu = sum(t * c / 100 for t, c, _ in feeds_t)
    fe = sum(t * f / 100 for t, _, f in feeds_t)
    # Incógnitas: masa de mata final M y de escoria nueva E.
    #   Cu: c_m M + c_s E = cu ;  Fe: f_m M + f_s E = fe
    a = np.array([[end_cu_pct, slag_cu_pct], [end_fe_pct, slag_fe_pct]]) / 100
    _m, slag = np.linalg.solve(a, np.array([cu, fe]))
    if slag < 0 or _m < 0:
        raise ConversionError("Los análisis no cierran: masa negativa")
    return float(slag) + initial_slag_t
