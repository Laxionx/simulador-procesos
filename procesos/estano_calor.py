"""Balance de calor de la fundición de estaño en dos etapas (fase 4d): gas natural por etapa.

Toma el balance de masa de `estano.smelt_tin` y cierra el calor de cada etapa con gas natural
quemado con el aire justo (CH4 + 2 O2 + 7,52 N2 → CO2 + 2 H2O + 7,52 N2):
- Etapa 1: entran a 25 °C las cargas, la caliza (CaCO3), el carbono, el hardhead y los humos
  reciclados; salen a T1 el crudo, la escoria, los gases de la reducción y de la calcinación, los
  humos y los gases de combustión.
- Etapa 2: la escoria de la etapa 1 entra caliente (a T1) con el carbono a 25 °C; salen a T2 el
  hardhead, la escoria de desecho, los gases y los humos.
La pérdida de cada horno es un dato. Si el calor sobra, el gas es cero y se informa el sobrante.

Entalpías: `thermo_piro` (USGS B2131, JANAF, CODATA). El SnO líquido de la escoria no está en esas
fuentes: se toma de Takeda et al. (1990, ec. 5), ΔG°(SnO, l) = −274.500 + 93,3·T J, es decir
h(SnO, l) = h(Sn, l) + ½ h(O2) − 274,5 kJ/mol (medido a 1.366-1.573 K). El humo de SnO se trata
como SnO líquido (sin el calor de vaporización) y la ganga «otros», como SiO2. Ver docs/estano.md.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .elements import molar_mass, parse_formula
from .estano import TinResult
from .thermo import KELVIN, T_REF, ThermoDatabase
from .thermo_data import DEFAULT_THERMO

SNO_FORMATION_LIQUID = -274.5  # kJ/mol, Takeda et al. (1990), ec. 5
N2_PER_O2 = 79.0 / 21.0
# Fase de cada especie a 25 °C y caliente; «otros» como SiO2.
COLD = {"SnO2": ("SnO2", "s"), "SnO": ("SnO", "s"), "Sn": ("Sn", "l"), "Fe": ("Fe", "s"),
        "Fe2O3": ("Fe2O3", "s"), "SiO2": ("SiO2", "s"), "CaO": ("CaO", "s"),
        "Al2O3": ("Al2O3", "s"), "MgO": ("MgO", "s"), "TiO2": ("TiO2", "s"),
        "otros": ("SiO2", "s"), "CaCO3": ("CaCO3", "s"), "C": ("C", "s"), "CH4": ("CH4", "g"),
        "O2": ("O2", "g"), "N2": ("N2", "g")}  # fmt: skip
HOT = {"Sn": ("Sn", "l"), "Fe": ("Fe", "s"), "FeO": ("FeO", "l"), "SiO2": ("SiO2", "l"),
       "CaO": ("CaO", "s"), "Al2O3": ("Al2O3", "s"), "MgO": ("MgO", "s"),
       "TiO2": ("TiO2", "s"), "otros": ("SiO2", "l"), "CO": ("CO", "g"), "CO2": ("CO2", "g"),
       "H2O": ("H2O", "g"), "N2": ("N2", "g")}  # fmt: skip


def _mm(species: str) -> float:
    return molar_mass(parse_formula("SiO2" if species == "otros" else species))


def _h(species: str, temp_k: float, thermo: ThermoDatabase, hot: bool) -> float:
    """kJ/mol. El SnO caliente sale de Takeda; el resto, de las fichas."""
    if hot and species == "SnO":
        sn = thermo.by_key("Sn", "l").enthalpy(temp_k)
        return sn + 0.5 * thermo.by_key("O2", "g").enthalpy(temp_k) + SNO_FORMATION_LIQUID
    formula, phase = (HOT if hot else COLD)[species]
    return thermo.by_key(formula, phase).enthalpy(temp_k)


def enthalpy_mj(tonnes: Mapping[str, float], temp_c: float, thermo: ThermoDatabase = DEFAULT_THERMO,
                hot: bool = True) -> float:  # fmt: skip
    """Entalpía (MJ) de una mezcla dada en toneladas por especie."""
    temp_k = temp_c + KELVIN
    return sum(1000.0 * t / _mm(s) * _h(s, temp_k, thermo, hot) for s, t in tonnes.items() if t)


def combustion_mj_per_kmol(temp_c: float, thermo: ThermoDatabase = DEFAULT_THERMO) -> float:
    """Calor que deja un kmol de CH4 quemado con el aire justo a 25 °C, con los humos a temp_c."""
    t_hot = temp_c + KELVIN
    reactants = (_h("CH4", T_REF, thermo, False) + 2 * _h("O2", T_REF, thermo, False)
                 + 2 * N2_PER_O2 * _h("N2", T_REF, thermo, False))  # fmt: skip
    products = (_h("CO2", t_hot, thermo, True) + 2 * _h("H2O", t_hot, thermo, True)
                + 2 * N2_PER_O2 * _h("N2", t_hot, thermo, True))  # fmt: skip
    return reactants - products


@dataclass(frozen=True)
class StageHeat:
    h_in_mj: float  # sin el gas
    h_out_mj: float  # sin los gases de combustión
    loss_mj: float
    temp_c: float
    ch4_kmol: float

    @property
    def deficit_mj(self) -> float:
        """Calor que falta (positivo) o que sobra (negativo) antes de quemar gas."""
        return self.h_out_mj + self.loss_mj - self.h_in_mj

    @property
    def ch4_t(self) -> float:
        return self.ch4_kmol * _mm("CH4") / 1000.0


def _stage(h_in: float, h_out: float, loss: float, temp_c: float,
           thermo: ThermoDatabase) -> StageHeat:  # fmt: skip
    deficit = h_out + loss - h_in
    ch4 = max(deficit, 0.0) / combustion_mj_per_kmol(temp_c, thermo)
    return StageHeat(h_in, h_out, loss, temp_c, ch4)


@dataclass(frozen=True)
class TinHeat:
    stage1: StageHeat
    stage2: StageHeat
    co2_process_t: float  # carbono reductor + caliza
    co2_fuel_t: float

    @property
    def ch4_t(self) -> float:
        return self.stage1.ch4_t + self.stage2.ch4_t

    @property
    def co2_t(self) -> float:
        return self.co2_process_t + self.co2_fuel_t


def tin_heat(result: TinResult, *, t1_c: float = 1200.0, t2_c: float = 1400.0,
             loss1_mj: float = 0.0, loss2_mj: float = 0.0,
             thermo: ThermoDatabase = DEFAULT_THERMO) -> TinHeat:  # fmt: skip
    """Gas natural de cada etapa del balance de masa ``result`` (masas en t)."""
    if loss1_mj < 0 or loss2_mj < 0:
        raise ValueError("Las pérdidas no pueden ser negativas")
    s1, s2 = result.stage1, result.stage2
    recycle = {"Sn": s2.metal["Sn"], "Fe": s2.metal["Fe"]}
    fume_in = {"SnO": s1.fume_sno_t + s2.fume_sno_t}
    cold_in = dict(result.fresh) | {"CaCO3": result.limestone_t, "C": s1.carbon["C"]}
    h_in1 = (enthalpy_mj(cold_in, 25.0, thermo, hot=False)
             + enthalpy_mj(recycle, 25.0, thermo, hot=False)
             + enthalpy_mj(fume_in, 25.0, thermo, hot=False))  # fmt: skip
    calcination = {"CO2": result.limestone_t / _mm("CaCO3") * _mm("CO2")}
    gases1 = {k: v for k, v in s1.carbon.items() if k != "C"}
    h_out1 = (enthalpy_mj(s1.metal, t1_c, thermo) + enthalpy_mj(s1.slag, t1_c, thermo)
              + enthalpy_mj(_add(gases1, calcination), t1_c, thermo)
              + enthalpy_mj({"SnO": s1.fume_sno_t}, t1_c, thermo))  # fmt: skip
    h_in2 = enthalpy_mj(s1.slag, t1_c, thermo) + enthalpy_mj({"C": s2.carbon["C"]}, 25.0, thermo,
                                                               hot=False)  # fmt: skip
    gases2 = {k: v for k, v in s2.carbon.items() if k != "C"}
    h_out2 = (enthalpy_mj(s2.metal, t2_c, thermo) + enthalpy_mj(s2.slag, t2_c, thermo)
              + enthalpy_mj(gases2, t2_c, thermo)
              + enthalpy_mj({"SnO": s2.fume_sno_t}, t2_c, thermo))  # fmt: skip
    st1 = _stage(h_in1, h_out1, loss1_mj, t1_c, thermo)
    st2 = _stage(h_in2, h_out2, loss2_mj, t2_c, thermo)
    c_kmol = (s1.carbon["C"] + s2.carbon["C"]) * 1000.0 / _mm("C")
    process = (c_kmol + result.limestone_t * 1000.0 / _mm("CaCO3")) * _mm("CO2") / 1000.0
    fuel = (st1.ch4_kmol + st2.ch4_kmol) * _mm("CO2") / 1000.0
    return TinHeat(st1, st2, process, fuel)


def _add(*parts: Mapping[str, float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for part in parts:
        for k, v in part.items():
            out[k] = out.get(k, 0.0) + v
    return out
