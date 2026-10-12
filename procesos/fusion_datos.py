"""Datos publicados para la fusión de cobre (fase 4a). Todos de acceso abierto.

Bacedoni, Moreno-Ventas y Ríos (2020), «Copper Flash Smelting Process Balance Modeling»,
Metals 10(9), 1229, CC BY (horno flash de Atlantic Copper, Huelva):
- Tabla 9: mineralogía de cuatro mezclas (% en masa).
- Tablas 1 y 2: coeficientes de distribución y relaciones molares que el artículo calculó con
  FactSage; aquí entran como datos publicados.
- Tabla 13: operación industrial (entradas y salidas medidas) y la pérdida térmica del horno.
- Tabla 14: resultados del propio modelo del artículo (solo como referencia).

González, Patiño y Salinas (2001), Rev. Soc. Quím. Méx. 45(1), 13-16 (SciELO México):
contenido calórico de matas Cu2S-FeS medido con calorímetro de gota a 1.473 K.
"""

from __future__ import annotations

ATLANTIC = "Bacedoni, Moreno-Ventas y Ríos (2020), Metals 10(9) 1229, CC BY"
SCIELO_MATTE = "González, Patiño y Salinas (2001), Rev. Soc. Quím. Méx. 45(1) 13"

# Tabla 9 (% en masa). Minerales con Pb, As, Sn o Sb (galena, anglesita, tenantita, estannita y
# tetraedrita; < 0,5 %) y la masa no listada se tratan como ganga inerte (Al2O3).
BLENDS = {
    "Mezcla 1": {"CuFeS2": 49.22, "FeS2": 15.83, "Cu5FeS4": 2.34, "Cu2S": 5.41, "CuS": 1.21,
                 "ZnS": 0.80, "FeS": 0.00, "Fe2SiO4": 2.85, "Fe3O4": 3.80, "Cu": 0.03,
                 "CuSO4": 0.85, "ZnSO4": 2.86, "CuFeO2": 0.76, "Cu2OSO4": 1.16, "Cu2O": 0.24,
                 "SiO2": 7.32},
    "Mezcla 2": {"CuFeS2": 37.42, "FeS2": 20.95, "Cu5FeS4": 8.41, "Cu2S": 2.92, "CuS": 4.04,
                 "ZnS": 0.03, "FeS": 0.00, "Fe2SiO4": 2.85, "Fe3O4": 3.80, "Cu": 0.03,
                 "CuSO4": 0.85, "ZnSO4": 2.86, "CuFeO2": 0.76, "Cu2OSO4": 1.16, "Cu2O": 0.24,
                 "SiO2": 9.56},
    "Mezcla 3": {"CuFeS2": 56.47, "FeS2": 13.66, "Cu5FeS4": 2.34, "Cu2S": 1.77, "CuS": 1.21,
                 "ZnS": 1.33, "FeS": 0.26, "Fe2SiO4": 2.85, "Fe3O4": 3.80, "Cu": 0.03,
                 "CuSO4": 0.85, "ZnSO4": 2.86, "CuFeO2": 0.76, "Cu2OSO4": 1.16, "Cu2O": 0.24,
                 "SiO2": 6.30},
    "Mezcla 4": {"CuFeS2": 53.07, "FeS2": 15.75, "Cu5FeS4": 2.34, "Cu2S": 3.42, "CuS": 1.21,
                 "ZnS": 0.86, "FeS": 0.00, "Fe2SiO4": 2.85, "Fe3O4": 3.80, "Cu": 0.03,
                 "CuSO4": 0.85, "ZnSO4": 2.86, "CuFeO2": 0.76, "Cu2OSO4": 1.16, "Cu2O": 0.24,
                 "SiO2": 5.91},
}  # fmt: skip

# Tabla 13: operación medida. Ley de mata y sílice en escoria son salidas medidas (aquí, metas);
# OC, enriquecimiento y fundente son lo que se compara. Pérdida térmica en MJ por t de carga.
# mezcla: (OC Nm3/t, O2 vol.%, fundente %, ley de mata %, SiO2 escoria %, pérdida MJ/t)
INDUSTRIAL = {
    "Mezcla 1": (186.0, 50.1, 8.26, 63.7, 29.0, 205.5),
    "Mezcla 2": (188.0, 51.0, 5.24, 62.7, 28.5, 211.9),
    "Mezcla 3": (193.0, 53.4, 10.6, 66.6, 27.5, 205.5),
    "Mezcla 4": (186.0, 53.8, 10.0, 62.6, 30.0, 218.7),
}
PAPER_MODEL = {  # Tabla 14: (OC, O2 vol.%, fundente %), modelo del artículo con HSC y FactSage
    "Mezcla 1": (161.8, 50.1, 5.9),
    "Mezcla 2": (154.0, 55.1, 2.8),
    "Mezcla 3": (163.3, 52.9, 7.8),
    "Mezcla 4": (157.6, 59.5, 6.9),
}
D_CU_MATTE_SLAG = 63.45  # Tabla 1: % Cu en mata / % Cu en escoria
CU2S_MATTE_SLAG = 1900.28  # texto: relación molar Cu2S mata / Cu2S escoria
D_ZN_SLAG_MATTE = 1.95  # Tabla 1: % Zn en escoria / % Zn en mata
ZNO_ZNS_SLAG = 24.18  # Tabla 2: relación molar en la escoria
T_PRODUCTS_C, T_AIR_C, T_FEED_C = 1300.0, 227.0, 25.0  # Tabla 3

# SciELO: contenido calórico H(1473 K) - H(298 K) de matas (J/g) por % de Cu2S en masa.
MATTE_HEAT_1473 = {0: 1253.0, 25: 1134.0, 50: 1008.0, 75: 879.0, 100: 756.0}
