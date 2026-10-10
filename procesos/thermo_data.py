# ruff: noqa: E501  (tabla de coeficientes: una fila por tramo de temperatura)
"""Datos termodinámicos públicos de la fase 2, con su fuente.

- NIST: Shomate del NIST Chemistry WebBook (SRD 69), ajustes de Chase (1998), NIST-JANAF 4.ª ed.
  El parámetro H de Shomate es ΔfH°(298,15).
- USGS: Robie y Hemingway (1995), USGS Bulletin 2131 (dominio público). Coeficientes de Cp
  verificados reproduciendo la columna de Cp tabulada de cada mineral.
- CODATA: Cox, Wagman y Medvedev (1989), CODATA Key Values for Thermodynamics. Un soluto
  acuoso se arma con sus iones a dilución infinita; su Cp se toma como 0 (ver README).
- JANAF: ajuste propio Cp = A1 + A2 T + A3/T² a las tablas NIST-JANAF H-075 (H2SO4 líquido) y
  H-064 (vapor de agua); se comprueba contra la columna H - H298 de la misma tabla.
- ΦL del H2SO4 acuoso: Wu y Young (1980), J. Res. NBS 85, 11, Tabla 5 (hasta m = 9 mol/kg);
  por encima, tablas NBS de Wagman et al. (1982), «H2SO4 in n H2O», con ΔfH(ai) = -909,27.
"""

from __future__ import annotations

from .thermo import (
    ApparentEnthalpy,
    ConstantCp,
    MaierKelley,
    Shomate,
    ThermoDatabase,
    ThermoRecord,
)

NIST = "NIST WebBook, Shomate (Chase 1998)"
USGS = "USGS Bulletin 2131 (Robie y Hemingway 1995)"
CODATA = "CODATA Key Values (Cox et al. 1989), iones a dilución infinita"


def _nist(*ranges: tuple[float, ...]) -> ThermoRecord:
    models = tuple(Shomate(*r) for r in ranges)
    return ThermoRecord(models[0].h, models, NIST)


# (tmin, tmax, A, B, C, D, E, F, G, H) tal como los publica el WebBook
# fmt: off
_NIST = {
    ("H2O", "l"): _nist(
        (298.0, 500.0, -203.606, 1523.29, -3196.413, 2474.455, 3.855326, -256.5478, -488.7163, -285.8304),
    ),
    ("CO2", "g"): _nist(
        (298.0, 1200.0, 24.99735, 55.18696, -33.69137, 7.948387, -0.136638, -403.6075, 228.2431, -393.5224),
        (1200.0, 6000.0, 58.16639, 2.720074, -0.492289, 0.038844, -6.447293, -425.9186, 263.6125, -393.5224),
    ),
    ("O2", "g"): _nist(
        (100.0, 700.0, 31.32234, -20.23531, 57.86644, -36.50624, -0.007374, -8.903471, 246.7945, 0.0),
        (700.0, 2000.0, 30.03235, 8.772972, -3.988133, 0.788313, -0.741599, -11.32468, 236.1663, 0.0),
    ),
    ("N2", "g"): _nist(
        (100.0, 500.0, 28.98641, 1.853978, -9.647459, 16.63537, 0.000117, -8.671914, 226.4168, 0.0),
        (500.0, 2000.0, 19.50583, 19.88705, -8.598535, 1.369784, 0.527601, -4.935202, 212.39, 0.0),
    ),
    ("CuO", "s"): _nist(
        (298.0, 2000.0, 48.56494, 7.498607, -0.05598, 0.013851, -0.760082, -173.4272, 94.85128, -156.0632),
    ),
    ("Cu", "s"): _nist(
        (298.0, 1358.0, 17.72891, 28.0987, -31.25289, 13.97243, 0.068611, -6.056591, 47.89592, 0.0),
    ),
    ("SiO2", "s"): _nist(  # cuarzo alfa hasta 847 K, beta después
        (298.0, 847.0, -6.076591, 251.6755, -324.7964, 168.5604, 0.002548, -917.6893, -27.96962, -910.8568),
        (847.0, 1996.0, 58.7534, 10.27925, -0.131384, 0.02521, 0.025601, -929.3292, 105.8092, -910.8568),
    ),
    ("MgO", "s"): _nist(
        (298.0, 3105.0, 47.25995, 5.681621, -0.872665, 0.1043, -1.053955, -619.1316, 76.46176, -601.2408),
    ),
    ("Al2O3", "s"): _nist(  # corindón
        (298.0, 2327.0, 102.429, 38.7498, -15.9109, 2.628181, -3.007551, -1717.93, 146.997, -1675.69),
    ),
}
# fmt: on

_USGS = {
    ("CaCO3", "s"): ThermoRecord(  # calcita, 298-1200 K
        -1207.4, (MaierKelley(298.15, 1200.0, 99.72, 2.692e-02, -2.158e06),), USGS
    ),
    ("CaSO4", "s"): ThermoRecord(  # anhidrita, 298-1000 K
        -1434.4,
        (MaierKelley(298.15, 1000.0, 372.8, -0.1574, 1.695e06, -4330.8, 7.99e-05),),
        USGS,
    ),
}

# ΔfH° de iones acuosos (kJ/mol), CODATA Key Values.
IONES = {
    "H+": 0.0,
    "SO4-2": -909.34,
    "HSO4-": -886.9,
    "Cu+2": 64.9,
    "Ca+2": -543.0,
    "Mg+2": -467.0,
    "Zn+2": -153.39,
    "Al+3": -538.4,
    "CO3-2": -675.23,
}
_SOLUTOS = {  # soluto acuoso = suma de sus iones
    "H2SO4": {"H+": 2, "SO4-2": 1},
    "CuSO4": {"Cu+2": 1, "SO4-2": 1},
    "MgSO4": {"Mg+2": 1, "SO4-2": 1},
    "ZnSO4": {"Zn+2": 1, "SO4-2": 1},
    "Al2(SO4)3": {"Al+3": 2, "SO4-2": 3},
}
_CODATA = {
    (name, "aq"): ThermoRecord(
        sum(n * IONES[i] for i, n in ions.items()), (ConstantCp(0.0),), CODATA
    )
    for name, ions in _SOLUTOS.items()
}
_CODATA[("CO2", "aq")] = ThermoRecord(-413.26, (ConstantCp(0.0),), CODATA)

JANAF_FIT = "Ajuste propio a NIST-JANAF (Chase 1998)"
_JANAF = {
    ("H2SO4", "l"): ThermoRecord(  # H-075, 283-600 K
        -813.989, (MaierKelley(283.456, 600.0, 80.0059, 0.194857, 42715.4),), JANAF_FIT
    ),
    ("H2O", "g"): ThermoRecord(  # H-064, gas ideal, 200-800 K
        -241.826, (MaierKelley(200.0, 800.0, 29.1426, 0.0117234, 76507.8),), JANAF_FIT
    ),
}

# Wu y Young (1980), Tabla 5: √m (mol^1/2 kg^-1/2) -> ΦL (cal/mol)
_WU_YOUNG = (
    (0.0, 0),
    (0.005, 40),
    (0.01, 120),
    (0.02, 370),
    (0.03, 680),
    (0.04, 1015),
    (0.05, 1340),
    (0.06, 1640),
    (0.07, 1910),
    (0.08, 2160),
    (0.09, 2380),
    (0.10, 2585),
    (0.12, 2935),
    (0.14, 3220),
    (0.16, 3450),
    (0.18, 3650),
    (0.20, 3820),
    (0.22, 3965),
    (0.24, 4090),
    (0.26, 4200),
    (0.28, 4300),
    (0.30, 4370),
    (0.35, 4550),
    (0.40, 4690),
    (0.45, 4801),
    (0.50, 4892),
    (0.55, 4969),
    (0.60, 5031),
    (0.65, 5086),
    (0.70, 5133),
    (0.75, 5175),
    (0.80, 5214),
    (0.85, 5249),
    (0.90, 5282),
    (0.95, 5312),
    (1.00, 5342),
    (1.10, 5400),
    (1.20, 5460),
    (1.30, 5522),
    (1.40, 5589),
    (1.50, 5665),
    (1.60, 5752),
    (1.70, 5852),
    (1.80, 5967),
    (1.90, 6095),
    (2.00, 6237),
    (2.20, 6567),
    (2.40, 6958),
    (2.60, 7368),
    (3.00, 8267),
)
# NBS 1982 (Wagman et al.), «H2SO4 in n H2O», ΔfH en kJ/mol, para n < 6,17 (m > 9 mol/kg)
NBS_H2SO4_IN_N_H2O = {
    1.0: -841.791,
    1.5: -849.888,
    2.0: -855.440,
    2.5: -859.611,
    3.0: -862.912,
    3.5: -865.611,
    4.0: -867.879,
    4.5: -869.808,
    5.0: -871.477,
    5.5: -872.937,
    6.0: -874.222,
}
NBS_H2SO4_AI = -909.27
WATER_MOL_PER_KG = 1000.0 / 18.0153


def _h2so4_apparent() -> ApparentEnthalpy:
    points = [(x, cal * 4.184e-3) for x, cal in _WU_YOUNG]
    for n in sorted(NBS_H2SO4_IN_N_H2O, reverse=True):  # m crece al bajar n
        points.append(((WATER_MOL_PER_KG / n) ** 0.5, NBS_H2SO4_IN_N_H2O[n] - NBS_H2SO4_AI))
    return ApparentEnthalpy(
        tuple(x for x, _ in points), tuple(y for _, y in points), "Wu y Young 1980; NBS 1982"
    )


_CODATA[("H2SO4", "aq")] = ThermoRecord(
    _CODATA[("H2SO4", "aq")].dfh298,
    _CODATA[("H2SO4", "aq")].ranges,
    CODATA + "; ΦL de Wu y Young (1980) y NBS (1982)",
    _h2so4_apparent(),
)

DEFAULT_THERMO = ThermoDatabase({**_NIST, **_USGS, **_CODATA, **_JANAF})
