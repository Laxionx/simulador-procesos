# ruff: noqa: E501  (tabla de coeficientes: una fila por tramo de temperatura)
"""Datos termodinámicos públicos para la pirometalurgia del cobre (fase 4a).

Entalpías de formación a 298,15 K: USGS Bulletin 2131 (Robie y Hemingway 1995), un solo juego
para reactivos y productos, para que el calor de reacción no dependa de mezclar fuentes. El calor
sensible a alta temperatura sale de:
- NIST-JANAF (Chase 1998, vía NIST WebBook): FeS, FeO, SiO2 líquido, Cu2O y SO2. En cada tramo el
  parámetro H de Shomate se reemplaza por el ΔfH del sólido de JANAF, para que la fusión entre en
  el calor sensible: h(T) = ΔfH(USGS) + [Σ Shomate + F - H_sólido(JANAF)].
- US Bureau of Mines RI 8305 (Ferrante, Stuve, Daut y Pankratz 1978, dominio público): Cu2S
  sólido (α, β, γ) y líquido, en kcal/mol; los saltos entre tramos reproducen las transiciones
  publicadas (0,865; 0,280 y 3,070 de fusión).
- USGS Bulletin 2131, ecuaciones de Cp: ZnS (esfalerita, 298-1.300 K; extrapolada a 1.600 K) y ZnO.
- Tablas NIST-JANAF (janaf.nist.gov, columna H-H298) interpoladas: Cu sólido y líquido (Cu-001)
  y magnetita (Fe-032), para el convertidor (fase 4b).

Escoria fundida: el FeO y el SiO2 bajo su punto de fusión se tratan como líquidos subenfriados
(Shomate del sólido más el calor de fusión de JANAF). Los minerales de la alimentación entran a
25 °C: solo se usa su ΔfH. Ver docs/fusion.md.
"""

from __future__ import annotations

from .thermo import (
    ConstantCp,
    EnthalpyPolynomial,
    MaierKelley,
    Shomate,
    TabulatedEnthalpy,
    ThermoRecord,
)

NIST_USGS = "ΔfH de USGS B2131; calor sensible de NIST-JANAF (Chase 1998)"
USBM = "ΔfH de USGS B2131; calor sensible de USBM RI 8305 (Ferrante et al. 1978)"
USGS_CP = "USGS Bulletin 2131 (ΔfH y ecuación de Cp)"
ONLY_25C = "USGS Bulletin 2131, solo ΔfH (entra a 25 °C)"


def _shomate(
    h_ref: float, *ranges: tuple[float, ...], fusion: float = 0.0, upto: float | None = None
) -> tuple[Shomate, ...]:
    """Tramos de Shomate con H = h_ref; ``fusion`` (kJ/mol) se suma a F de los tramos que terminan
    hasta ``upto`` (sólido usado como líquido subenfriado)."""
    out = []
    for r in ranges:
        tmin, tmax, a, b, c, d, e, f, g, _h = r
        extra = fusion if upto is not None and tmax <= upto else 0.0
        out.append(Shomate(tmin, tmax, a, b, c, d, e, f + extra, g, h_ref))
    return tuple(out)


def _at25(dfh: float) -> ThermoRecord:
    return ThermoRecord(dfh, (ConstantCp(0.0),), ONLY_25C)


def shomate_absolute(r: tuple[float, ...], temp_k: float) -> float:
    """Entalpía absoluta de un tramo de Shomate (kJ/mol, referida a sus elementos)."""
    t = temp_k / 1000.0
    _tmin, _tmax, a, b, c, d, e, f, _g, _h = r
    return a * t + b * t**2 / 2 + c * t**3 / 3 + d * t**4 / 4 - e / t + f


# fmt: off
_FES = (  # JANAF, troilita y líquido
    (298.0, 411.0, 9240.570, -55016.80, 121502.0, -93187.10, -99.35930, -1634.010, 22510.20, -101.6710),
    (411.0, 598.0, 72.36830, -0.060653, 0.120490, -0.079265, -0.000018, -122.1360, 149.9740, -101.6710),
    (598.0, 1463.0, 95.82780, -85.56150, 48.72030, -0.000101, 0.000071, -123.9460, 205.1350, -101.6710),
    (1463.0, 3800.0, 62.55080, 0.000002, -6.720620e-07, 6.411921e-08, -4.303011e-07, -84.51170, 166.2660, -68.81140),
)
FEO_SOLID = (298.0, 1650.0, 45.75120, 18.78553, -5.952201, 0.852779, -0.081265, -286.7429, 110.3120, -272.0441)
FEO_LIQUID = (1650.0, 5000.0, 68.19920, -4.501232e-10, 1.195227e-10, -1.064302e-11, -3.092680e-10, -281.4326, 137.8377, -249.5321)
_SIO2_S = (  # los mismos tramos que ("SiO2", "s") en thermo_data
    (298.0, 847.0, -6.076591, 251.6755, -324.7964, 168.5604, 0.002548, -917.6893, -27.96962, -910.8568),
    (847.0, 1996.0, 58.7534, 10.27925, -0.131384, 0.02521, 0.025601, -929.3292, 105.8092, -910.8568),
)
_SIO2_L = (1996.0, 4500.0, 85.77200, -0.000016, 0.000004, -3.809081e-07, -0.000017, -952.8700, 113.3440, -902.6610)
CU2O_JANAF = (
    (298.0, 1100.0, 59.42033, 37.84767, -26.45083, 11.07609, -0.542180, -191.7109, 151.0177, -170.7072),
    (1100.0, 1516.7, 28.82153, 39.81603, 1.459388, -0.256110, 11.30291, -156.7167, 144.7999, -170.7072),
    (1517.0, 2000.0, 95.39980, 4.892490, -1.982781, 0.284974, 1.522601, -155.9270, 213.9270, -111.9950),
)
_SO2 = (
    (298.0, 1200.0, 21.43049, 74.35094, -57.75217, 16.35534, 0.086731, -305.7688, 254.8872, -296.8422),
    (1200.0, 6000.0, 57.48188, 1.009328, -0.076290, 0.005174, -4.045401, -324.4140, 302.7798, -296.8422),
)
# fmt: on

# Calores de fusión de JANAF a la temperatura de fusión (líquido - sólido), kJ/mol.
FUSION_FEO = shomate_absolute(FEO_LIQUID, 1650.0) - shomate_absolute(FEO_SOLID, 1650.0)
FUSION_SIO2 = shomate_absolute(_SIO2_L, 1996.0) - shomate_absolute(_SIO2_S[1], 1996.0)

# JANAF, H-H298 en kJ/mol. Cu-001: el sólido llega a 1.358 K y el líquido parte de ahí con el
# calor de fusión (13,138 kJ/mol). Fe-032: la transición λ de la magnetita (900 K) es continua.
_CU_JANAF = (
    TabulatedEnthalpy(
        (298.15, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1358),
        (0.0, 0.045, 2.539, 5.105, 7.725, 10.399, 13.123, 15.899, 18.733, 21.638, 24.633,
         27.762, 29.660),
    ),
    TabulatedEnthalpy(
        (1358, 1400, 1500, 1600, 1700, 1800, 1900, 2000),
        (42.798, 44.177, 47.462, 50.746, 54.031, 57.315, 60.600, 63.884),
    ),
)  # fmt: skip
_FE3O4_JANAF = TabulatedEnthalpy(
    (298.15, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
     1800),
    (0.0, 0.273, 16.240, 34.424, 54.671, 76.934, 101.214, 127.510, 147.594, 167.677, 187.760,
     207.843, 227.927, 248.010, 268.093, 288.176, 308.259),
)  # fmt: skip
JANAF_TABLE = "ΔfH de USGS B2131; calor sensible de la tabla NIST-JANAF interpolada"

# RI 8305, h - h298 en kcal/mol: α, β, γ y líquido.
_CU2S = (
    EnthalpyPolynomial(298.15, 376.0, 5.24e-3, 17.72e-6, -2.29e2, -2.369),
    EnthalpyPolynomial(376.0, 720.0, 25.24e-3, -3.12e-6, -1.58e2, -6.267),
    EnthalpyPolynomial(720.0, 1400.0, 20.38e-3, -0.37e-6, 0.15e2, -4.153),
    EnthalpyPolynomial(1400.0, 1600.0, 21.43e-3, 0.0, 0.0, -3.266),
)

PIRO = {
    # Productos (mata, escoria y gases a 1.300 °C)
    ("Cu2S", "l"): ThermoRecord(-83.9, _CU2S, USBM),
    ("FeS", "l"): ThermoRecord(-101.0, _shomate(-101.6710, *_FES), NIST_USGS),
    ("FeO", "l"): ThermoRecord(
        -272.0,
        _shomate(-272.0441, FEO_SOLID, fusion=FUSION_FEO, upto=1650.0)
        + _shomate(-272.0441, FEO_LIQUID),
        NIST_USGS,
    ),
    ("SiO2", "l"): ThermoRecord(
        -910.8568,
        _shomate(-910.8568, *_SIO2_S, fusion=FUSION_SIO2, upto=1996.0)
        + _shomate(-910.8568, _SIO2_L),
        NIST_USGS,
    ),
    ("Cu2O", "l"): ThermoRecord(-170.6, _shomate(-170.7072, *CU2O_JANAF), NIST_USGS),
    ("ZnS", "s"): ThermoRecord(
        -204.1, (MaierKelley(298.15, 1600.0, 61.51, 7.631e-4, -7.963e4, -260.4),), USGS_CP
    ),
    ("ZnO", "s"): ThermoRecord(
        -350.46, (MaierKelley(298.15, 1800.0, 43.50, 7.658e-3, -7.573e5, 54.56),), USGS_CP
    ),
    ("Cu", "l"): ThermoRecord(0.0, _CU_JANAF, JANAF_TABLE),
    ("Fe3O4", "s"): ThermoRecord(-1115.7, (_FE3O4_JANAF,), JANAF_TABLE),
    ("SO2", "g"): ThermoRecord(
        -296.8422, _shomate(-296.8422, *_SO2), "NIST WebBook, Shomate (Chase 1998)"
    ),
    # Minerales de la alimentación (a 25 °C)
    ("CuFeS2", "s"): _at25(-194.9),
    ("FeS2", "s"): _at25(-171.5),
    ("Cu5FeS4", "s"): _at25(-371.6),
    ("Cu2S", "s"): _at25(-83.9),
    ("CuS", "s"): _at25(-54.6),
    ("FeS", "s"): _at25(-101.0),
    ("Fe2SiO4", "s"): _at25(-1478.2),
    ("Fe2O3", "s"): _at25(-826.2),
    ("CuSO4", "s"): _at25(-771.4),
    ("ZnSO4", "s"): _at25(-980.1),
    ("Cu2O", "s"): _at25(-170.6),
}
