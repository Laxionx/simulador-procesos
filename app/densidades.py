"""Densidades de las fases líquidas de la fundición, SOLO para dibujar las capas del horno flash
y del convertidor (altura o área de capa = masa ÷ densidad). No entran a ningún modelo.

Valores a ~1200 °C y sus fuentes (notas de verificación del autor):
- Cu2S líquido 5,18 g/cm³ y FeS líquido 3,80 g/cm³: Nagamori (1968, Trans. AIME), citado en
  Tesfaye Firdu y Taskinen (2010), Aalto University TKK-MT-215, Tabla 9. Davenport et al.
  (*Extractive Metallurgy of Copper*) dan 5,20 y 3,90.
- Mata y metal blanco: mezcla ideal de volúmenes específicos de Cu2S y FeS (±10 %: Davenport y
  Partelpoeg dan 4,30 g/cm³ para 50 % Cu a 1500 K y la mezcla ideal 4,56; Azuma y Tatebe dan
  Cu2S 5,70).
- Blíster = cobre líquido: Assael et al. (2010), J. Phys. Chem. Ref. Data 39, 033105, ec. 1,
  ρ = 7997 − 0,819·(T − 1357,77 K) kg/m³ (±1,3 %).
- Escoria: 3,7 g/cm³ constante, aproximada (~3,7 a 1300 °C, Metall. Mater. Trans. B 2025,
  s11663-025-03828-w; 3,81 a 1200 °C en horno SKS, Wang et al. 2017, Trans. Nonferrous Met. Soc.
  China 27:946). La del convertidor, con magnetita, es más densa.
"""

from __future__ import annotations

CU2S_G_CM3 = 5.18
FES_G_CM3 = 3.80
CU_IN_CU2S_PCT = 79.85  # % de Cu en Cu2S
SLAG_G_CM3 = 3.7  # aproximada
MATTE_UNCERTAINTY = 0.10  # ±10 %
CU_MELT_K = 1357.77
KELVIN = 273.15
ASSAEL_RHO_MELT = 7997.0  # kg/m³ en el punto de fusión
ASSAEL_SLOPE = 0.819  # kg/(m³·K)

SOURCES = {
    "mata": "Nagamori (1968) vía Tesfaye Firdu y Taskinen (2010), Aalto TKK-MT-215, Tabla 9; "
    "mezcla ideal, ±10 %",
    "blíster": "Assael et al. (2010), J. Phys. Chem. Ref. Data 39, 033105, ec. 1 (cobre líquido)",
    "escoria": "3,7 g/cm³, aproximada (la del convertidor, con magnetita, es más densa)",
}


def matte_density_g_cm3(cu_pct: float) -> float:
    """Mata o metal blanco de `cu_pct` % de Cu: 1/ρ = w_Cu2S/5,18 + w_FeS/3,80, con w acotado
    a [0, 1]."""
    w = min(1.0, max(0.0, cu_pct / CU_IN_CU2S_PCT))
    return 1.0 / (w / CU2S_G_CM3 + (1.0 - w) / FES_G_CM3)


def copper_density_g_cm3(temp_c: float) -> float:
    """Cobre líquido (blíster) a `temp_c` °C, en g/cm³."""
    return (ASSAEL_RHO_MELT - ASSAEL_SLOPE * (temp_c + KELVIN - CU_MELT_K)) / 1000.0


def slag_density_g_cm3() -> float:
    return SLAG_G_CM3
