"""Datos publicados para la fundición de estaño (fase 4d). Todos de acceso abierto.

- Takeda, Yazawa, Chit y Ujiie (1990), «Equilibria between Liquid Tin and FeOx-CaO-SiO2 Slag»,
  Materials Transactions JIM 31(9), 793-801 (J-STAGE): Tabla 6, escorias y metal Sn-Fe en
  equilibrio a 1.573 K, en crisoles de magnesia.
- Kandalam, Reuter, Stelter, Reinmöller, Gräbner, Richter y Charitos (2023), «A Review of Top
  Submerged Lance (TSL) Processing - Part II», Metals 13(10), 1742, CC BY: rangos del
  coeficiente de distribución D por etapa y el piloto CSIRO de reducción de escoria.
- Fosu, Bartier, Diot y Kanari (2024), Materials 17, 3312, CC BY: concentrado de casiterita
  analizado (Tabla 1) y crudo con 98 % Sn y 2 % Fe.
- Minsur (2026), Memoria Integrada 2025, Tabla 11: indicadores de la planta de Pisco (Funsur).
"""

from __future__ import annotations

# Rangos de D = (%Sn/%Fe)metal × (%Fe/%Sn)escoria (revisión TSL, Parte II).
D_STAGE1 = (150.0, 400.0)  # fusión del concentrado, ~1.200 °C, crudo con < 2 % Fe
D_STAGE2 = (20.0, 50.0)  # reducción de la escoria, ~1.400 °C, hardhead de 10-60 % Fe
D_STAGE1_DEFAULT = 200.0  # el ejemplo de la revisión: D = 200 a 1.200 °C
D_STAGE2_DEFAULT = 35.0  # mitad del rango
CRUDE_FE_PCT = 2.0  # crudo de 98 % Sn y 2 % Fe (Materials 2024)
BASICITY_SMELTING = 0.3  # CaO/SiO2 de la fusión (ACS Omega 2024, Tabla 1)
STAGE2_FUME = (0.10, 0.25)  # fracción del Sn volatilizada como SnO, piloto CSIRO (revisión TSL)

# Concentrado de casiterita analizado (Materials 2024, Tabla 1, % en masa).
CASSITERITE_REF = {"SnO2": 75.85, "SiO2": 8.85, "TiO2": 3.54, "Fe2O3": 2.75, "Al2O3": 1.88,
                   "MgO": 1.85, "otros": 5.28}  # fmt: skip

# Funsur, planta de Pisco (Memoria Integrada 2025 de Minsur, Tabla 11).
FUNSUR = {  # año: (concentrado t, % Sn, escoria de horno rotatorio t, % Sn, refinado t, rec. %,
    #                 % Sn en escoria de desecho)
    2022: (74_372.0, 37.11, 1_350.0, 15.13, 26_706.0, 96.77, 0.54),
    2023: (69_994.0, 37.27, 1_242.0, 15.51, 25_374.0, 97.27, 0.59),
    2024: (81_177.0, 39.53, 931.0, 21.31, 30_926.0, 96.40, 0.56),
    2025: (87_527.0, 38.73, 1_091.0, 19.77, 32_981.0, 97.28, 0.55),
}

# Takeda et al. (1990), Tabla 6 (1.573 K): (ensayo, escoria % Sn, % CaO, % SiO2, % Fe total,
# metal % Fe, metal % Sn o None si no se informa). El Fe total de la escoria es Fe²⁺ + Fe³⁺, o
# el FeT que da la tabla. En las filas con dos fases metálicas (brecha de miscibilidad) la tabla
# da la composición de la fase rica en Fe.
TAKEDA_1573 = (
    ("A-S51", 2.4, 0.0, 34.3, 42.5 + 1.0, 61.1, 37.8),
    ("52", 5.0, 0.0, 34.2, 38.0 + 2.8, 9.1, None),
    ("53", 9.0, 0.0, 33.8, 36.5 + 2.5, 3.7, None),
    ("54", 14.6, 0.0, 31.3, 32.5 + 3.4, 2.0, None),
    ("55", 19.6, 0.0, 29.1, 28.9 + 4.0, 0.97, None),
    ("56", 29.5, 0.0, 25.5, 23.0 + 4.3, 0.64, None),
    ("57", 36.5, 0.0, 23.7, 19.1 + 5.1, 0.68, None),
    ("58", 45.8, 0.0, 19.3, 14.1 + 5.1, 0.60, None),
    ("59", 58.1, 0.0, 15.2, 5.8 + 6.3, 0.26, None),
    ("a-S60", 4.7, 0.0, 14.2, 52.2 + 6.8, 60.4, 40.0),
    ("61", 8.4, 0.0, 13.0, 48.8 + 6.9, 16.5, None),
    ("62", 9.8, 0.0, 12.3, 47.6 + 7.7, 8.5, None),
    ("63", 15.1, 0.0, 11.0, 43.5 + 8.1, 2.7, None),
    ("64", 35.0, 0.0, 8.1, 25.4 + 10.8, 0.93, None),
    ("65", 47.0, 0.0, 6.2, 15.2 + 14.0, 0.76, None),
    ("66", 55.7, 0.0, 3.0, 7.5 + 15.0, 0.34, None),
    ("B-S67", 0.45, 24.2, 49.4, 14.8 + 0.7, 62.4, 38.1),
    ("68", 0.80, 23.5, 48.9, 14.6 + 0.9, 10.6, None),
    ("69", 1.1, 23.0, 48.1, 13.5 + 0.5, 4.8, None),
    ("70", 1.5, 22.1, 48.4, 13.8 + 0.8, 5.0, None),
    ("71", 2.9, 21.9, 47.4, 10.8 + 0.8, 1.3, None),
    ("72", 6.8, 20.8, 46.0, 8.2 + 2.5, 0.50, None),
    ("73", 10.2, 20.1, 44.7, 7.6 + 2.9, 0.53, None),
    ("74", 9.3, 20.6, 47.2, 7.7 + 3.4, 0.25, None),
    ("75", 9.2, 20.3, 45.4, 9.0 + 2.7, 0.35, None),
    ("76", 15.3, 18.2, 41.7, 8.8 + 2.6, 0.21, None),
    ("77", 14.2, 19.7, 43.7, 7.1 + 3.7, 0.23, None),
    ("78", 28.8, 13.8, 35.8, 5.0 + 3.6, 0.10, None),
    ("79", 43.0, 8.2, 25.4, 4.2 + 4.3, 0.16, None),
    ("80", 30.5, 13.8, 33.0, 5.8 + 3.1, 0.25, None),
    ("81", 60.7, 4.2, 17.0, 4.5, 0.09, None),
    ("b-S82", 3.6, 8.5, 19.1, 50.2 + 0.9, 60.8, 41.3),
    ("83", 7.2, 7.3, 17.7, 43.0 + 5.6, 12.4, None),
    ("84", 7.7, 7.2, 17.5, 42.9 + 6.3, 9.5, None),
    ("85", 14.2, 5.5, 14.6, 34.4 + 9.5, 2.3, None),
    ("86", 27.2, 5.3, 12.6, 23.8 + 11.0, 0.81, None),
    ("87", 42.5, 3.3, 8.7, 17.2 + 10.2, 0.51, None),
    ("88", 49.8, 3.9, 8.9, 13.0 + 8.5, 0.14, None),
    ("E-S89", 1.4, 21.7, 31.3, 25.8 + 3.0, 56.2, 44.3),
    ("90", 2.6, 21.9, 31.6, 24.9 + 2.6, 12.3, None),
    ("91", 2.7, 21.3, 31.6, 24.5 + 2.5, 9.8, None),
    ("92", 3.5, 24.0, 29.5, 24.1 + 4.1, 6.7, None),
    ("93", 5.5, 24.0, 30.7, 19.8 + 4.5, 3.0, None),
    ("94", 7.6, 23.1, 29.7, 17.2 + 6.9, 1.7, None),
    ("95", 11.2, 21.9, 28.1, 16.4 + 5.8, 0.93, None),
    ("96", 15.6, 20.7, 27.1, 14.1 + 6.2, 0.61, None),
    ("97", 15.6, 19.0, 26.9, 14.3 + 6.9, 0.50, None),
    ("98", 26.9, 15.3, 24.4, 11.2 + 6.7, 0.40, None),
    ("99", 44.7, 8.6, 16.1, 5.6 + 8.8, 0.16, None),
    ("100", 64.2, 5.0, 9.6, 8.5, 0.05, None),
    ("C-S101", 0.86, 32.7, 36.0, 17.9 + 1.3, 55.0, 43.5),
    ("102", 1.3, 33.3, 36.4, 17.1 + 1.3, 7.7, None),
    ("103", 2.8, 32.4, 32.5, 17.9 + 2.5, 1.9, None),
    ("104", 8.4, 29.8, 34.6, 9.6 + 6.2, 0.61, None),
    ("105", 10.2, 27.2, 33.1, 10.4 + 6.0, 0.77, None),
    ("106", 19.1, 23.9, 30.9, 5.9 + 7.2, 0.33, None),
    ("107", 30.9, 19.0, 24.6, 4.4 + 6.0, 0.12, None),
    ("c-S108", 3.5, 15.6, 17.5, 41.7 + 6.4, 60.4, 40.8),
    ("109", 6.1, 15.5, 18.0, 37.0 + 6.7, 12.0, None),
    ("110", 7.4, 14.2, 16.3, 38.6 + 7.1, 8.7, None),
    ("111", 15.7, 10.8, 13.7, 30.1 + 9.7, 1.5, None),
    ("112", 28.2, 9.0, 11.2, 21.7 + 11.0, 0.98, None),
    ("113", 39.9, 7.5, 8.2, 18.1 + 8.3, 0.33, None),
    ("114", 51.2, 5.0, 6.3, 8.4 + 11.0, 0.37, None),
    ("D-S115", 4.7, 20.1, 0.0, 40.2 + 14.5, 58.0, 40.3),
    ("116", 8.8, 20.1, 0.0, 35.9 + 13.9, 13.9, None),
    ("117", 9.8, 20.5, 0.0, 34.3 + 14.7, 8.2, None),
    ("118", 13.9, 20.0, 0.0, 31.0 + 15.0, 3.9, None),
    ("119", 16.3, 16.2, 0.0, 27.2 + 19.4, 1.9, None),
    ("120", 21.3, 17.7, 0.0, 22.2 + 19.3, 1.4, None),
    ("121", 27.1, 15.7, 0.0, 18.5 + 19.0, 1.3, None),
    ("122", 33.5, 14.8, 0.0, 14.3 + 20.4, 0.78, None),
    ("123", 37.4, 13.7, 0.0, 13.2 + 17.6, 0.49, None),
    ("124", 57.2, 7.7, 0.0, 18.5, 0.36, None),
    ("d-S125", 5.2, 10.7, 0.0, 49.9 + 12.0, 61.2, 39.8),
    ("126", 8.4, 11.1, 0.0, 46.6 + 12.0, 13.4, None),
    ("127", 9.5, 11.2, 0.0, 45.5 + 12.1, 14.8, None),
    ("128", 11.6, 10.4, 0.0, 43.2 + 13.6, 4.8, None),
    ("129", 35.2, 7.0, 0.0, 22.1 + 17.0, 0.82, None),
    ("130", 44.8, 4.9, 0.0, 9.5 + 20.2, 0.62, None),
    ("131", 55.3, 2.0, 0.0, 23.9, 0.34, None),
)
