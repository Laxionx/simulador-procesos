"""Datos publicados para la electrorrefinación (fase 4c). Todos de acceso abierto.

- Glencore Technology (2020), «IsaKidd Compendium of Technical Papers»: la refinería de Mount Isa
  modernizada (Tabla I) y los componentes del voltaje de una refinería típica (Tabla II).
- Kalliomäki et al. (2021), Miner. Eng. 171, 107069, CC BY: electrolito de la «Reference
  Tankhouse 3» (Tabla 3, entradas).
- Fuentes (2022), tesis USM, Tabla 4.24: conductividad medida de dos electrolitos sin Ni ni As.
- Morales-Aragón, Sánchez-Rodas, Ríos y Moats (2025), Metals 15(2), 113, CC BY: ánodo comercial
  AC1 de Atlantic Copper (Tabla 1, g/t).
- Sahlman (Aalto): límite de 20 g/L de Ni en el electrolito.
"""

from __future__ import annotations

ISAKIDD = "Glencore Technology (2020), IsaKidd Compendium of Technical Papers"

# Mount Isa Copper Refinery modernizada (compendio, Tabla I y texto).
MOUNT_ISA = {
    "capacidad_t_a": 225_000.0,
    "celdas": 1320,
    "catodos_por_celda": 36,
    "area_por_cara_m2": 0.82,
    "densidad_corriente": 305.0,  # A/m²
    "paso_m": 0.100,  # entre cátodos
    "masa_anodo_kg": 320.0,  # máxima
    "ciclo_anodo_d": 18.0,
    "cosechas": 3,
    "eficiencia": 0.975,  # largo plazo tras la conversión (antes 85,9 %)
}
CATHODE_BLADE_M = 0.00325  # placa de acero inoxidable ISA (compendio)
# Tabla II: refinería típica, 300 A/m², paso de 100 mm; mV por cosecha 1, 2 y 3.
ISAKIDD_ELECTROLYTE_MV = (220.0, 270.0, 320.0)
ISAKIDD_TOTAL_MV = (280.0, 330.0, 385.0)
ISAKIDD_J = 300.0

# Reference Tankhouse 3 (Kalliomäki 2021, Tabla 3), punto medio de las entradas: g/L y °C.
TANKHOUSE3 = {"Cu": 45.4, "H2SO4": 173.0, "Ni": 18.9, "As": 6.55, "T": 57.0}
NICKEL_LIMIT_G_L = 20.0

# Ánodo comercial AC1 de Atlantic Copper (Metals 2025, Tabla 1), g/t.
ATLANTIC_AC1_G_T = {"Ni": 929, "Sn": 113, "Sb": 194, "As": 861, "O": 1545, "Ag": 300, "Bi": 250,
                    "Pb": 1106, "Se": 396, "Te": 60}  # fmt: skip

# Fuentes (2022), Tabla 4.24: mS/cm por temperatura (°C). M3 y M4 sin Ni ni As.
FUENTES_CU_G_L = {"M3": 50.0, "M4": 34.8}
FUENTES_SULFATE_G_L = {"M3": 243.0, "M4": 237.0}  # sulfato total
FUENTES_KAPPA = {
    "M3": {48.9: 493.0, 54.4: 527.0, 60.0: 559.0, 71.1: 625.0},
    "M4": {48.9: 619.0, 54.4: 662.0, 60.0: 710.0, 71.1: 784.0},
}
