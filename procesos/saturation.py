"""Curva de saturación del agua, IAPWS-IF97 región 4 (Wagner et al. 2000; norma pública IAPWS).

Válida entre 273,15 K y el punto crítico (647,096 K, 22,064 MPa).
"""

from __future__ import annotations

import math

KELVIN = 273.15
T_CRIT = 647.096  # K
P_CRIT = 22.064  # MPa
P_TRIPLE = 611.212677e-6  # MPa
_N = (
    0.11670521452767e4,
    -0.72421316598433e6,
    -0.17073846940092e2,
    0.12020824702470e5,
    -0.32325550322333e7,
    0.14915108613530e2,
    -0.48232657361591e4,
    0.40511340542057e6,
    -0.23855557567849,
    0.65017534844798e3,
)


def psat_kpa(temperature_c: float) -> float:
    """Presión de saturación (kPa) a la temperatura dada (°C)."""
    t = temperature_c + KELVIN
    if not KELVIN <= t <= T_CRIT:
        raise ValueError(f"{temperature_c} °C fuera de la curva de saturación (0 a 373,946 °C)")
    n = _N
    theta = t + n[8] / (t - n[9])
    a = theta**2 + n[0] * theta + n[1]
    b = n[2] * theta**2 + n[3] * theta + n[4]
    c = n[5] * theta**2 + n[6] * theta + n[7]
    return 1000.0 * (2.0 * c / (-b + math.sqrt(b * b - 4.0 * a * c))) ** 4


def tsat_c(pressure_kpa: float) -> float:
    """Temperatura de saturación (°C) a la presión dada (kPa)."""
    p = pressure_kpa / 1000.0
    if not P_TRIPLE <= p <= P_CRIT:
        raise ValueError(f"{pressure_kpa} kPa fuera de la curva de saturación (0,611 a 22 064 kPa)")
    n = _N
    beta = p**0.25
    e = beta**2 + n[2] * beta + n[5]
    f = n[0] * beta**2 + n[3] * beta + n[6]
    g = n[1] * beta**2 + n[4] * beta + n[7]
    d = 2.0 * g / (-f - math.sqrt(f * f - 4.0 * e * g))
    t = (n[9] + d - math.sqrt((n[9] + d) ** 2 - 4.0 * (n[8] + n[9] * d))) / 2.0
    return t - KELVIN
