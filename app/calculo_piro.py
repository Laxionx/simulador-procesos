"""Cálculo del horno flash y del convertidor Peirce-Smith para la app, sin Streamlit: llama a
`procesos.fusion` y `procesos.conversion` y le suma el volumen de cada fase (masa ÷ densidad, ver
`densidades.py`) que usan los esquemas. Los números del balance son los de los modelos."""

from __future__ import annotations

from dataclasses import dataclass

from densidades import (
    copper_density_g_cm3,
    matte_density_g_cm3,
    slag_density_g_cm3,
)

from procesos.conversion import carry_over, copper_blow, matte, slag_blow
from procesos.conversion_datos import ILO_MAGNETITE_FE, ILO_SLAG
from procesos.fusion import SmeltResult, smelt
from procesos.fusion_datos import BLENDS, INDUSTRIAL, T_PRODUCTS_C

SO2_MOLAR_MASS = 64.058
O2_MOLAR_MASS = 31.998

# ------------------------------------------------------------------ horno flash
BLEND_NAMES = tuple(BLENDS)  # «Mezcla 1» a «Mezcla 4»


@dataclass(frozen=True)
class FlashParams:
    blend: int = 1  # 1 a 4
    matte_grade: float = 63.7  # % Cu (Tabla 13 de Bacedoni et al. 2020, mezcla 1)
    slag_sio2: float = 29.0  # % SiO2 de la escoria
    heat_loss_mj_t: float = 205.5  # MJ por t de carga
    products_c: float = T_PRODUCTS_C


@dataclass(frozen=True)
class FlashView:
    params: FlashParams
    result: SmeltResult
    matte_density: float  # g/cm³
    slag_density: float

    @property
    def matte_kg_t(self) -> float:
        return self.result.matte_kg

    @property
    def slag_kg_t(self) -> float:
        return self.result.slag_kg

    @property
    def matte_m3_t(self) -> float:
        """Volumen de mata por t de concentrado: kg/t ÷ (kg/m³)."""
        return self.matte_kg_t / (self.matte_density * 1000.0)

    @property
    def slag_m3_t(self) -> float:
        return self.slag_kg_t / (self.slag_density * 1000.0)

    @property
    def plant(self) -> tuple[float, float, float, float, float, float]:
        """Operación industrial publicada de la mezcla elegida (Tabla 13)."""
        return INDUSTRIAL[BLEND_NAMES[self.params.blend - 1]]


def run_flash(p: FlashParams) -> FlashView:
    """Lanza `SmeltingError` (ValueError) si el balance es imposible con esas metas."""
    result = smelt(BLENDS[BLEND_NAMES[p.blend - 1]], p.matte_grade, p.slag_sio2, p.heat_loss_mj_t,
                   products_c=p.products_c)  # fmt: skip
    return FlashView(p, result, matte_density_g_cm3(result.matte_grade), slag_density_g_cm3())


# ------------------------------------------------------------------ convertidor
MATTE_T = 100.0  # t de mata por carga (como ejemplos/conversion_ilo.py)
END_FE_PCT = 0.4  # Fe del metal blanco al fin del soplado a escoria (Rönnskär, Lennartsson 2013)
BLISTER_S_PCT = 0.023
CB_SLAG_CU_PCT = 28.3  # Cu de la escoria del soplado a cobre (Rönnskär)


@dataclass(frozen=True)
class ConverterParams:
    matte_grade: float = 62.0  # % Cu (Southern Copper, SEC 2007)
    eff_slag: float = 0.62  # eficiencia de O2 en el soplado a escoria (Flin Flon, Kyllo 1995)
    eff_copper: float = 0.77  # ídem, soplado a cobre
    bath_c: float = 1200.0


@dataclass(frozen=True)
class BathState:
    """Una foto del baño: fase de abajo (más densa) y escoria encima, con sus volúmenes."""

    name: str
    lower_name: str
    lower_t: float
    lower_g_cm3: float
    slag_t: float
    slag_g_cm3: float
    air_nm3: float  # aire del soplado que llevó a este estado (0 en la carga)
    so2_t: float
    o2_t: float = 0.0  # O₂ que reacciona en ese soplado

    @property
    def lower_m3(self) -> float:
        return self.lower_t / self.lower_g_cm3

    @property
    def slag_m3(self) -> float:
        return self.slag_t / self.slag_g_cm3


@dataclass(frozen=True)
class ConverterView:
    params: ConverterParams
    states: tuple[BathState, BathState, BathState]
    flux_t: float
    slag_blow_so2_t: float
    copper_blow_so2_t: float

    @property
    def so2_t(self) -> float:
        return self.slag_blow_so2_t + self.copper_blow_so2_t


def run_converter(p: ConverterParams) -> ConverterView:
    """Lanza `ConversionError` (ValueError) si la carga no admite las metas."""
    slag_g = slag_density_g_cm3()
    sb = slag_blow(
        [matte("mata", MATTE_T, p.matte_grade)], end_fe_pct=END_FE_PCT,
        slag_cu_pct=ILO_SLAG["Cu"], magnetite_fe=ILO_MAGNETITE_FE,
        slag_sio2_pct=ILO_SLAG["SiO2"], efficiency=p.eff_slag, bath_c=p.bath_c,
    )  # fmt: skip
    cb = copper_blow(
        [carry_over(sb, "metal", 1.0, p.bath_c, "metal blanco")], blister_s_pct=BLISTER_S_PCT,
        slag_cu_pct=CB_SLAG_CU_PCT, efficiency=p.eff_copper, bath_c=p.bath_c,
    )  # fmt: skip
    so2 = {s: s_.products["gas:SO2"] * SO2_MOLAR_MASS / 1000.0 for s, s_ in (("a", sb), ("b", cb))}
    states = (
        BathState("Carga: mata", "mata", MATTE_T, matte_density_g_cm3(p.matte_grade), 0.0, slag_g,
                  0.0, 0.0, 0.0),
        BathState("Fin del soplado a escoria", "metal blanco", sb.mass_t("metal"),
                  matte_density_g_cm3(sb.percent("metal", "Cu")), sb.mass_t("escoria"), slag_g,
                  sb.air_nm3, so2["a"], sb.o2_reacted * O2_MOLAR_MASS / 1000.0),
        BathState("Fin del soplado a cobre", "blíster", cb.mass_t("blister"),
                  copper_density_g_cm3(p.bath_c), cb.mass_t("escoria"), slag_g, cb.air_nm3,
                  so2["b"], cb.o2_reacted * O2_MOLAR_MASS / 1000.0),
    )  # fmt: skip
    flux = sum(f.tonnes.get("SiO2", 0.0) for f in sb.feeds if f.name == "fundente")
    return ConverterView(p, states, flux, so2["a"], so2["b"])
