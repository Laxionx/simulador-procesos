# ruff: noqa: E501  (tabla de coeficientes: una fila por tramo de temperatura)
"""Datos termodinámicos públicos de la fase 2, con su fuente.

- NIST: Shomate del NIST Chemistry WebBook (SRD 69), ajustes de Chase (1998), NIST-JANAF 4.ª ed.
  El parámetro H de Shomate es ΔfH°(298,15).
- USGS: Robie y Hemingway (1995), USGS Bulletin 2131 (dominio público). Coeficientes de Cp
  verificados reproduciendo la columna de Cp tabulada de cada mineral.
- CODATA: Cox, Wagman y Medvedev (1989), CODATA Key Values for Thermodynamics. Un soluto
  acuoso se arma con sus iones a dilución infinita; su Cp se toma como 0 (ver README).
"""

from __future__ import annotations

from .thermo import ConstantCp, MaierKelley, Shomate, ThermoDatabase, ThermoRecord

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

DEFAULT_THERMO = ThermoDatabase({**_NIST, **_USGS, **_CODATA})
