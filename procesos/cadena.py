"""Cadena de concentrado a cátodo, por tonelada de concentrado: fusión flash (4a), convertidor
Peirce-Smith (4b), horno de ánodos (4b) y electrorrefinación (4c).

- La mata de la fusión pasa al convertidor como Cu2S + FeS a la temperatura de los productos.
  El ZnS de la mata no lo modela el convertidor: se informa aparte y no sigue.
- El blíster pasa al horno de ánodos y los ánodos a la nave de refinación. A régimen la chatarra
  anódica vuelve al horno, así que la nave disuelve el ánodo entero (la corriente se fija para
  eso). Todo el O del ánodo entra como Cu2O y su S va al barro.
- No se recirculan las escorias del convertidor ni la de la fusión: su cobre se informa.
Ver docs/cadena.md.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .anodos import AnodeResult, refine
from .conversion import Feed, Stage, carry_over, copper_blow, slag_blow
from .conversion_datos import ILO_MAGNETITE_FE, ILO_SLAG
from .elements import ATOMIC_WEIGHTS, molar_mass, parse_formula
from .er import Electrorefining, ERResult
from .er_datos import TANKHOUSE3
from .ew import FARADAY
from .fusion import SmeltResult, smelt
from .species import Catalog, make_species
from .stream import Stream

CU, S = ATOMIC_WEIGHTS["Cu"], ATOMIC_WEIGHTS["S"]
ELECTROLYTE_M3_PER_T = 20.0  # m³ de electrolito por t de concentrado (solo es el medio)
_ER_SPECIES = [("H2O", "l"), ("CuSO4", "aq"), ("H2SO4", "aq"), ("NiSO4", "aq"), ("Cu", "s"),
               ("Cu2O", "s"), ("S", "s")]  # fmt: skip
ER_CATALOG = Catalog([make_species(n, phase=p) for n, p in _ER_SPECIES])


def _mm(formula: str) -> float:
    return molar_mass(parse_formula(formula))


def _element_kmol(products: Mapping[str, float], element: str, prefix: str = "") -> float:
    """kmol de un elemento en los productos (clave «fase:especie») que empiezan con prefix."""
    return sum(n * parse_formula(k.split(":")[1]).get(element, 0.0)
               for k, n in products.items() if k.startswith(prefix))  # fmt: skip


@dataclass(frozen=True)
class ChainResult:
    concentrate_cu_t: float
    concentrate_s_t: float
    smelting: SmeltResult
    excluded_zns_t: float
    slag_blow: Stage
    copper_blow: Stage
    anode: AnodeResult
    refining: ERResult
    slimes: Stream
    electrolyte_in: Stream
    electrolyte_out: Stream

    def copper_t(self) -> dict[str, float]:
        """Destino del Cu (t por t de concentrado)."""
        k = self.smelting.kmol
        cu_slag = 2 * (k["escoria:Cu2O"] + k["escoria:Cu2S"]) * CU / 1000
        er_gain = self.electrolyte_out.flow("CuSO4") - self.electrolyte_in.flow("CuSO4")
        sb = _element_kmol(self.slag_blow.products, "Cu", "escoria") * CU / 1000
        cb = _element_kmol(self.copper_blow.products, "Cu", "escoria") * CU / 1000
        return {
            "escoria de fusión": cu_slag,
            "escoria del soplado a escoria": sb,
            "escoria del soplado a cobre": cb,
            "cátodos": self.refining.copper_kg_h / 1000,
            "barro anódico": self.slimes.flow("Cu") / 1000,
            "electrolito": er_gain / _mm("CuSO4") * CU / 1000,
        }  # fmt: skip

    def sulfur_t(self) -> dict[str, float]:
        """Destino del S (t por t de concentrado)."""
        k = self.smelting.kmol
        return {
            "SO2 de fusión": k["gas:SO2"] * S / 1000,
            "escoria de fusión": (k["escoria:ZnS"] + k["escoria:Cu2S"]) * S / 1000,
            "ZnS de la mata (no sigue)": self.excluded_zns_t / _mm("ZnS") * S,
            "SO2 del convertidor": (self.slag_blow.products["gas:SO2"]
                                    + self.copper_blow.products["gas:SO2"]) * S / 1000,
            "escoria del convertidor": _element_kmol(self.slag_blow.products, "S", "escoria")
            * S
            / 1000,
            "SO2 del horno de ánodos": self.anode.so2_kg / _mm("SO2") * S / 1000,
            "barro anódico": self.slimes.flow("S") / 1000,
        }  # fmt: skip

    @property
    def potential_acid_t(self) -> float:
        """H2SO4 si todo el SO2 de fusión, convertidor y horno de ánodos se volviera ácido."""
        s = self.sulfur_t()
        so2_s = s["SO2 de fusión"] + s["SO2 del convertidor"] + s["SO2 del horno de ánodos"]
        return so2_s / S * _mm("H2SO4")

    @property
    def recovery(self) -> float:
        """Fracción del Cu del concentrado que llega a los cátodos (sin recircular escorias)."""
        return self.copper_t()["cátodos"] / self.concentrate_cu_t


def _concentrate(mineralogy: Mapping[str, float], element: str) -> float:
    return sum(pct * 10.0 * parse_formula(m).get(element, 0.0) * ATOMIC_WEIGHTS[element] / _mm(m)
               for m, pct in mineralogy.items() if m != "Al2O3") / 1000  # fmt: skip


def concentrate_to_cathode(
    mineralogy: Mapping[str, float],
    *,
    matte_grade: float,
    slag_sio2: float,
    heat_loss_mj_t: float,
    end_fe_pct: float = 0.4,
    converter_slag_cu_pct: float = ILO_SLAG["Cu"],
    converter_slag_sio2_pct: float = ILO_SLAG["SiO2"],
    magnetite_fe: float = ILO_MAGNETITE_FE,
    slag_blow_efficiency: float = 0.62,
    copper_blow_efficiency: float = 0.77,
    blister_s_pct: float = 0.023,
    copper_slag_cu_pct: float = 28.3,
    anode_s_pct: float = 0.003,
    er_current_density: float = 305.0,
    er_efficiency: float = 0.975,
    er_gap_m: float = 0.0322,
) -> ChainResult:
    """Una tonelada de concentrado de punta a punta. Los valores por defecto del convertidor son
    los del ejemplo de Ilo (4b) y los de la nave, los de Mount Isa (4c)."""
    sm = smelt(mineralogy, matte_grade, slag_sio2, heat_loss_mj_t)
    k = sm.kmol
    matte = Feed("mata", {"Cu2S": k["mata:Cu2S"] * _mm("Cu2S") / 1000,
                          "FeS": k["mata:FeS"] * _mm("FeS") / 1000},
                 temp_c=sm.products_k - 273.15)  # fmt: skip
    sb = slag_blow([matte], end_fe_pct=end_fe_pct, slag_cu_pct=converter_slag_cu_pct,
                   magnetite_fe=magnetite_fe, efficiency=slag_blow_efficiency,
                   slag_sio2_pct=converter_slag_sio2_pct)  # fmt: skip
    cb = copper_blow([carry_over(sb, "metal", 1.0, 1200.0, "metal blanco")],
                     blister_s_pct=blister_s_pct, slag_cu_pct=copper_slag_cu_pct,
                     efficiency=copper_blow_efficiency)  # fmt: skip
    anode = refine(cb.mass_t("blister"), cb.percent("blister", "S"), anode_s_pct=anode_s_pct)
    # Ánodo (kg): Cu, O como Cu2O y S; la corriente disuelve el ánodo entero.
    a_kg = 1000.0 * anode.anode_t
    o_kg, s_kg = a_kg * anode.anode_o_pct / 100, a_kg * anode.anode_s_pct / 100
    cu2o_kg = o_kg / ATOMIC_WEIGHTS["O"] * _mm("Cu2O")
    anode_stream = Stream({"Cu": a_kg - cu2o_kg - s_kg, "Cu2O": cu2o_kg, "S": s_kg}, 57.0)
    electrolyte = _tankhouse_electrolyte(ELECTROLYTE_M3_PER_T)
    cu_kmol = anode_stream.flow("Cu") / CU
    area = cu_kmol * 2 * FARADAY / 3.6 / (er_efficiency * er_current_density)
    ports = ("Sale", "Catodos", "Barro", "Chatarra")
    unit = Electrorefining(
        "Nave", ("Anodos", "Electrolito"), ports, er_current_density, area, er_efficiency, er_gap_m
    )
    out, _cathodes, slimes, _scrap = unit.compute([anode_stream, electrolyte], ER_CATALOG)
    er = unit.solve([anode_stream, electrolyte], ER_CATALOG)
    return ChainResult(
        concentrate_cu_t=_concentrate(mineralogy, "Cu"),
        concentrate_s_t=_concentrate(mineralogy, "S"),
        smelting=sm,
        excluded_zns_t=k["mata:ZnS"] * _mm("ZnS") / 1000,
        slag_blow=sb,
        copper_blow=cb,
        anode=anode,
        refining=er,
        slimes=slimes,
        electrolyte_in=electrolyte,
        electrolyte_out=out,
    )


def _tankhouse_electrolyte(m3: float) -> Stream:
    """Electrolito de la «Reference Tankhouse 3» (Kalliomäki 2021) sin Ni ni As, en kg."""
    litres = 1000.0 * m3
    kg = {"CuSO4": TANKHOUSE3["Cu"] * _mm("CuSO4") / CU * litres / 1000,
          "H2SO4": TANKHOUSE3["H2SO4"] * litres / 1000}  # fmt: skip
    kg["H2O"] = 1.2 * litres - sum(kg.values())
    return Stream(kg, TANKHOUSE3["T"])
