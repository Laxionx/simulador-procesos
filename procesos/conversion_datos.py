"""Datos publicados para la conversión Peirce-Smith (fase 4b). Todos de acceso abierto.

- Lennartsson (2013), «Development of a Process Model for a Peirce-Smith Converter», tesis de
  licenciatura, Luleå University of Technology (DiVA; copia del Internet Archive de 2026):
  carga 860 de Boliden Rönnskär, Tablas 4, 5, 6, 9 y 10.
- Kyllo (1995), «A Kinetic Model of the Peirce-Smith Converter», tesis doctoral, University of
  British Columbia: cargas 586, 588 y 595 de Flin Flon (Hudson Bay), Tablas IV-I a IV-V y IV-XII.
- Morales, Palacios y Sánchez (2004), VII Int. Conf. on Molten Slags, SAIMM, 551-556: escorias de
  los convertidores de Ilo (Southern Peru), enero-mayo de 2000, Tabla I.
"""

from __future__ import annotations

LENNARTSSON = "Lennartsson (2013), tesis de licenciatura, Luleå University of Technology"
KYLLO = "Kyllo (1995), tesis doctoral, University of British Columbia"
MORALES = "Morales, Palacios y Sánchez (2004), Molten Slags VII, SAIMM, Tabla I"

# ---------------------------------------------------------------- Rönnskär, carga 860
# Tabla 4. El fin del primer soplado a escoria no se publica: los dos se tratan juntos.
RONNSKAR_MATTE = ((165.0, 59.0), (103.0, 52.0), (51.0, 59.0), (57.0, 52.0))  # (t, % Cu)
RONNSKAR_FLUX_T = 23.0 + 14.0
RONNSKAR_RECYCLED_SLAG_T = 14.0  # escoria de un soplado a cobre anterior
RONNSKAR_COLD_SLAG_BLOWS_T = 29.0 + 22.0
RONNSKAR_COLD_COPPER_BLOW_T = 115.0
RONNSKAR_AIR_SLAG_BLOWS = 78_800.0 + 69_700.0  # Nm3
RONNSKAR_O2_SLAG_BLOWS = 2_358.0  # Nm3 de O2 puro
RONNSKAR_AIR_COPPER_BLOW = 208_200.0
RONNSKAR_O2_COPPER_BLOW = 3_127.0
# Eficiencias que estima la planta (95 y 90 % en los soplados a escoria; 85 % en el de cobre).
# Los dos soplados a escoria juntos llevan el promedio simple.
RONNSKAR_EFF_SLAG = (0.95 + 0.90) / 2
RONNSKAR_EFF_COPPER = 0.85
RONNSKAR_SLAG = {"Fe": 31.2, "Cu": 6.1, "SiO2": 29.9, "t": 181.0}  # Tabla 5, planta
RONNSKAR_WHITE_METAL = {"Fe": 0.4, "Cu": 75.9, "S": 17.8}  # Tabla 6, planta
RONNSKAR_CB_SLAG = {"Fe": 20.4, "Cu": 28.3, "SiO2": 14.1, "t": 7.0}  # Tabla 9, planta
RONNSKAR_BLISTER = {"Cu": 98.9, "S": 0.023, "t": 322.0}  # Tabla 10, planta
RONNSKAR_THESIS_MODEL = {"escoria_t": 148.0, "blister_t": 358.0}  # Tablas 5 y 10, su modelo
RONNSKAR_SKIMMED = 0.95  # fracción de la escoria líquida que se escoria (estimación industrial)
RONNSKAR_CB_TEMP_K = 1450.0  # pirómetro IR durante el soplado a cobre (Figura 8, aproximado)

# ---------------------------------------------------------------- Flin Flon (Kyllo 1995)
# Análisis (% en masa): Cu, Fe, S, SiO2, Fe3O4.
FLINFLON_ASSAYS = {
    "586 inicial": (42.8, 25.2, 24.5, 0.21, 9.0),
    "586 traspaso": (65.6, 7.3, 17.9, 2.25, 11.0),
    "586 final": (74.7, 1.1, 19.8, 0.5, 1.2),  # mata 3, fin de los soplados a escoria
    "588 inicial": (42.2, 23.7, 25.1, 0.29, 8.0),
    "588 traspaso": (71.2, 2.88, 20.0, 0.31, 1.9),
    "588 final": (74.0, 1.43, 19.7, 0.25, 1.5),
    "595 inicial": (42.2, 20.8, 22.5, 0.53, 7.5),
    "595 final": (62.8, 4.39, 17.3, 2.55, 3.6),  # mata 11; el soplado a cobre no se siguió
    "escoria de cobre": (38.2, 21.8, 0.6, 12.1, 21.5),  # carga 586, reciclada en la 595
}
FLINFLON_FLUX = {"SiO2": 75.6, "Fe": 2.2, "CaO": 1.4, "Al2O3": 8.2, "H2O": 7.0}  # Tabla IV-V
# Por carga, solo los soplados a escoria (Tabla IV-I): mata (t, análisis), fundente (t),
# chatarra (t, cobre), escoria de cobre reciclada (t), escoria inicial (t), análisis final,
# Fe y Cu de las escorias muestreadas (%) y toneladas escoriadas.
FLINFLON = {
    "586": {
        "mata": ((32.0 + 16.0 + 32.0, "586 inicial"), (80.0, "586 traspaso")),
        "fundente_t": 5.5 + 7.7,
        "chatarra_t": 4.0,
        "escoria_cobre_t": 0.0,
        "escoria_inicial_t": 12.0,
        "final": "586 final",
        "escoria_fe": (41.6, 39.2, 37.4),
        "escoria_cu": (7.13, 6.46, 6.13),
        "escoriado_t": 31.25 + 37.5,
    },
    "588": {
        "mata": ((48.0 + 16.0 + 32.0, "588 inicial"), (72.0, "588 traspaso")),
        "fundente_t": 6.6 + 9.9,
        "chatarra_t": 4.0,
        "escoria_cobre_t": 0.0,
        "escoria_inicial_t": 8.0,
        "final": "588 final",
        "escoria_fe": (45.1, 36.5),
        "escoria_cu": (5.35, 7.04),
        "escoriado_t": 31.25 + 43.75,
    },
    "595": {
        "mata": ((48.0 + 16.0 + 48.0 + 32.0 + 32.0 + 32.0, "595 inicial"),),
        "fundente_t": 6.6 + 4.4 + 9.9 + 8.25,
        "chatarra_t": 4.0 + 12.0,
        "escoria_cobre_t": 25.0,
        "escoria_inicial_t": 8.0,
        "final": "595 final",
        "escoria_fe": (39.8, 38.3, 38.2, 40.6),
        "escoria_cu": (8.1, 12.4, 4.16, 3.52),
        "escoriado_t": 0.0 + 18.75 + 12.5 + 62.5 + 25.0,
    },
}
FLINFLON_EFFICIENCY = {  # Tabla IV-XII: soplados a escoria y a cobre (%)
    "586": (55.0, 82.0),
    "588": (63.0, 72.0),
    "595": (68.0, None),
}

# ---------------------------------------------------------------- Ilo (Morales et al. 2004)
ILO_SLAG = {"Cu": 2.85, "Fe": 46.48, "SiO2": 25.52, "Fe3O4": 16.46}  # promedio, Tabla I
ILO_MAGNETITE_FE = ILO_SLAG["Fe3O4"] * 3 * 55.845 / 231.533 / ILO_SLAG["Fe"]  # 0,256
