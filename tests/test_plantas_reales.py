"""Validación contra plantas reales publicadas (detalle en docs/VALIDACION_PLANTAS_REALES.md).

Tolerancias fijadas ANTES de correr:
  P1 Constancia (Hudbay): cobre en concentrado del simulador vs el reportado, ±2 % por periodo.
  P2 Marimaca (PEA 2020):
     - ácido por kg de Cu disuelto y ácido regenerado por kg de cátodo vs 1,54: ±0,01;
     - ácido de cada especie de la ganga (Tabla 13-18) vs el publicado: ±0,06 kg/t (la tabla
       redondea a 0,1); total 34,0 kg/t: ±0,1;
     - sulfato precipitado como CaSO4 y sulfato del ácido de reposición (Tabla 13-19): ±0,05 kg/t.
  P3 Puquios (PFS 2025): cátodos del simulador vs los del plan, ±2 % por año y en la vida de
     la mina; año de diseño (2,1 Mt/a, 0,542 % Cu, 78,98 %) vs 9.000 t/a, ±2 %.
"""

from __future__ import annotations

import pytest

from procesos import (
    Catalog,
    Flowsheet,
    Reaction,
    Reactor,
    Separator,
    Stream,
    element_flows,
    make_species,
    parse_equation,
)

ACID = "H2SO4(aq)"


def _catalog(*names: str) -> Catalog:
    phases = {"H2O": "l", "O2": "g", "CO2": "g"}
    return Catalog([make_species(n, phase=phases.get(n)) for n in names])


def _mineral_for_element(catalog: Catalog, mineral: str, element: str, mass: float) -> float:
    """Masa del mineral que contiene `mass` del elemento, con las masas molares del simulador."""
    sp = catalog[mineral]
    element_mass = element_flows(Stream({mineral: sp.molar_mass}), catalog)[element]
    return mass * sp.molar_mass / element_mass


# --------------------------------------------------------------------------------------
# P1 · Constancia (Hudbay Minerals). Formulario 6-K ante la SEC, exhibit 99.3, resultados
# del 4.º trimestre de 2019 (accession 0001062993-20-001139), tabla de operaciones de Perú.
# Los años 2018 y 2019 coinciden con la Tabla 6-1 del NI 43-101 de Constancia (2021).
# --------------------------------------------------------------------------------------

HUDBAY_PERU = {
    # periodo: (t molidas, % Cu, % recuperación, t de Cu en concentrado)
    "4T 2019": (7_474_136, 0.42, 85.6, 26_659),
    "3T 2019": (8_240_344, 0.44, 86.0, 31_091),
    "4T 2018": (7_657_943, 0.48, 84.8, 30_834),
    "Año 2019": (31_387_281, 0.42, 85.7, 113_825),
    "Año 2018": (31_282_610, 0.47, 82.6, 122_178),
}


def _concentradora(ore_t: float, grade_pct: float, recovery_pct: float) -> float:
    """Calcopirita + ganga -> flotación con la recuperación reportada. Devuelve t de Cu."""
    catalog = _catalog("CuFeS2", "SiO2")
    cpy = _mineral_for_element(catalog, "CuFeS2", "Cu", ore_t * grade_pct / 100.0)
    flotation = Separator(
        "Flotación",
        ("Mineral",),
        ("Concentrado", "Relave"),
        {"CuFeS2": recovery_pct / 100.0, "SiO2": 0.005},
    )
    feed = Stream({"CuFeS2": cpy, "SiO2": ore_t - cpy})
    sheet = Flowsheet(catalog, [flotation], {"Mineral": feed})
    concentrate = sheet.solve().streams["Concentrado"]
    return element_flows(concentrate, catalog)["Cu"]


@pytest.mark.parametrize("periodo", list(HUDBAY_PERU))
def test_p1_constancia_cobre_en_concentrado(periodo: str) -> None:
    ore, grade, recovery, published = HUDBAY_PERU[periodo]
    assert _concentradora(ore, grade, recovery) == pytest.approx(published, rel=0.02)


# --------------------------------------------------------------------------------------
# P2 · Marimaca (Marimaca Copper, Chile). NI 43-101 PEA, agosto 2020.
# Factor 1,54: p. 13-115 (PDF p. 128). Tabla 13-18: p. 13-124 (PDF p. 137).
# --------------------------------------------------------------------------------------

MARIMACA_GANGA = {
    # especie disuelta: (mineral supuesto, kg/t disueltos del elemento o ion, kg/t de ácido)
    "Fe": ("Fe2O3", "Fe", 4.374, 11.5),
    "Al": ("Al2O3", "Al", 1.175, 6.4),
    "Mg": ("MgO", "Mg", 0.470, 1.9),
    "Zn": ("ZnO", "Zn", 2.268, 3.4),
    "CO3": ("CaCO3", "C", 6.604, 10.8),
}
REACCIONES_GANGA = {
    "Fe2O3": "Fe2O3 + 3 H2SO4(aq) -> Fe2(SO4)3(aq) + 3 H2O",
    "Al2O3": "Al2O3 + 3 H2SO4(aq) -> Al2(SO4)3(aq) + 3 H2O",
    "MgO": "MgO + H2SO4(aq) -> MgSO4(aq) + H2O",
    "ZnO": "ZnO + H2SO4(aq) -> ZnSO4(aq) + H2O",
    "CaCO3": "CaCO3 + H2SO4(aq) -> CaSO4 + H2O + CO2",
}
MARIMACA_TOTAL_GANGA = 34.0
MARIMACA_REPOSICION = 34.222  # kg/t de H2SO4 (Tabla 13-19)
MARIMACA_SO4_REPOSICION = 33.524
MARIMACA_SO4_PRECIPITADO = 10.567
FACTOR_PUBLICADO = 1.54


def _ganga_catalog() -> Catalog:
    return _catalog(
        "Fe2O3",
        "Al2O3",
        "MgO",
        "ZnO",
        "CaCO3",
        ACID,
        "Fe2(SO4)3(aq)",
        "Al2(SO4)3(aq)",
        "MgSO4(aq)",
        "ZnSO4(aq)",
        "CaSO4",
        "H2O",
        "CO2",
    )


def _lixiviacion_ganga() -> tuple[dict[str, float], Catalog]:
    """Ácido consumido por cada mineral (kg/t) según el reactor del simulador."""
    catalog = _ganga_catalog()
    feed: dict[str, float] = {ACID: 100.0, "H2O": 1000.0}
    for mineral, element, dissolved, _ in MARIMACA_GANGA.values():
        if element == "C":  # el reporte da el ion carbonato (CO3 = C + 3 O), no el carbono
            calcite = element_flows(Stream({mineral: catalog[mineral].molar_mass}), catalog)
            feed[mineral] = dissolved * catalog[mineral].molar_mass / (calcite["C"] + calcite["O"])
        else:
            feed[mineral] = _mineral_for_element(catalog, mineral, element, dissolved)
    reactions = tuple(
        Reaction(parse_equation(eq), mineral, 1.0, eq) for mineral, eq in REACCIONES_GANGA.items()
    )
    reactor = Reactor("Pilas", ("Mineral",), ("PLS",), reactions)
    extents = reactor.extents([Stream(feed)], catalog)
    acid = {
        e.reaction.key: e.extent * e.reaction.reactants[ACID] * catalog[ACID].molar_mass
        for e in extents
    }
    assert all(e.limited_by is None for e in extents)  # el ácido está en exceso
    return acid, catalog


def test_p2_marimaca_acido_de_cada_especie_de_la_ganga() -> None:
    acid, _ = _lixiviacion_ganga()
    for mineral, _, _, published in MARIMACA_GANGA.values():
        assert acid[mineral] == pytest.approx(published, abs=0.06), mineral
    assert sum(acid.values()) == pytest.approx(MARIMACA_TOTAL_GANGA, abs=0.1)


def test_p2_marimaca_balance_de_sulfato() -> None:
    acid, catalog = _lixiviacion_ganga()
    gypsum_kmol = acid["CaCO3"] / catalog[ACID].molar_mass
    gypsum = element_flows(Stream({"CaSO4": gypsum_kmol * catalog["CaSO4"].molar_mass}), catalog)
    assert gypsum["S"] + gypsum["O"] == pytest.approx(MARIMACA_SO4_PRECIPITADO, abs=0.05)
    makeup = element_flows(Stream({ACID: MARIMACA_REPOSICION}), catalog)
    assert makeup["S"] + makeup["O"] == pytest.approx(MARIMACA_SO4_REPOSICION, abs=0.05)


def _acid_per_copper(equation: str, key: str) -> float:
    """kg de ácido consumido (o regenerado) por kg de cobre que cambia de especie."""
    reaction = Reaction(parse_equation(equation), key, 1.0, equation)
    catalog = _catalog(*reaction.stoichiometry)
    reactor = Reactor("R", ("A",), ("B",), (reaction,))
    feed = Stream({n: (100.0 if n == key else 10_000.0) for n in reaction.reactants})
    (item,) = reactor.extents([feed], catalog)
    assert item.limited_by is None and item.achieved_conversion == pytest.approx(1.0)
    out = reactor.compute([feed], catalog)[0]
    acid_change = out.flow(ACID) - feed.flow(ACID)
    cu_moved = element_flows(Stream({key: feed.flow(key) - out.flow(key)}), catalog)["Cu"]
    return abs(acid_change) / cu_moved


def test_p2_marimaca_factor_154_disolucion_y_electroobtencion() -> None:
    leach = _acid_per_copper("CuO + H2SO4(aq) -> CuSO4(aq) + H2O", "CuO")
    ew = _acid_per_copper("2 CuSO4(aq) + 2 H2O -> 2 Cu + 2 H2SO4(aq) + O2", "CuSO4(aq)")
    assert leach == pytest.approx(FACTOR_PUBLICADO, abs=0.01)
    assert ew == pytest.approx(FACTOR_PUBLICADO, abs=0.01)


def test_p2_hallazgo_el_154_no_vale_para_la_brocantita() -> None:
    """El reporte dice que 1,54 «se repite para la mayoría de las reacciones de disolución».
    Para la brocantita, nombrada en la columna C-37 (BROC/ATA), el simulador da 3/4 de eso."""
    broc = _acid_per_copper("Cu4(SO4)(OH)6 + 3 H2SO4(aq) -> 4 CuSO4(aq) + 6 H2O", "Cu4(SO4)(OH)6")
    assert broc == pytest.approx(0.75 * 98.072 / 63.546, rel=1e-4)
    assert broc < FACTOR_PUBLICADO - 0.3


# --------------------------------------------------------------------------------------
# P3 · Puquios (Camino Minerals, Chile). NI 43-101 PFS, abril 2025: lixiviación en pilas,
# SX-EW y cátodos. Plan minero Tabla 22-3 (PDF p. 317); año de diseño en PDF p. 39 y p. 228.
# --------------------------------------------------------------------------------------

PUQUIOS = {
    # año: (kt de mineral, % Cu, % recuperación, t de Cu en cátodos)
    1: (1472, 0.64, 81.52, 7714),
    2: (1544, 0.71, 81.92, 8999),
    3: (1034, 1.02, 85.77, 9001),
    4: (1577, 0.73, 77.95, 9000),
    5: (2100, 0.52, 76.75, 8319),
    6: (1750, 0.62, 83.03, 8993),
    7: (1560, 0.70, 82.38, 9000),
    8: (2100, 0.54, 78.97, 8989),
    9: (2100, 0.33, 75.32, 5295),
    10: (2100, 0.54, 77.83, 8781),
    11: (2100, 0.31, 73.77, 4804),
    12: (2100, 0.23, 68.93, 3400),
    13: (2100, 0.26, 63.33, 3398),
    14: (2100, 0.30, 78.89, 4901),
    15: (236, 0.18, 90.16, 391),
    "Vida de la mina": (25973, 0.49, 78.75, 100985),
}
PUQUIOS_DISENO = (2100, 0.542, 78.98, 9000)


def _pilas_sxew(ore_kt: float, grade_pct: float, recovery_pct: float) -> float:
    """Óxido de cobre -> lixiviación (la recuperación del plan) -> electroobtención -> cátodo."""
    catalog = _catalog("CuO", "SiO2", ACID, "CuSO4(aq)", "H2O", "Cu", "O2")
    ore_t = ore_kt * 1000.0
    cuo = _mineral_for_element(catalog, "CuO", "Cu", ore_t * grade_pct / 100.0)
    leach_eq = "CuO + H2SO4(aq) -> CuSO4(aq) + H2O"
    ew_eq = "2 CuSO4(aq) + 2 H2O -> 2 Cu + 2 H2SO4(aq) + O2"
    units = [
        Reactor(
            "Pilas",
            ("Mineral", "Refino"),
            ("PLS",),
            (Reaction(parse_equation(leach_eq), "CuO", recovery_pct / 100.0, leach_eq),),
        ),
        Reactor(
            "Electroobtención",
            ("PLS",),
            ("Celdas",),
            (Reaction(parse_equation(ew_eq), "CuSO4(aq)", 1.0, ew_eq),),
        ),
        Separator("Cosecha", ("Celdas",), ("Cátodos", "Electrolito y ripios"), {"Cu": 1.0}),
    ]
    feeds = {
        "Mineral": Stream({"CuO": cuo, "SiO2": ore_t - cuo}),
        "Refino": Stream({ACID: 2.0 * cuo, "H2O": 10.0 * ore_t}),
    }
    cathodes = Flowsheet(catalog, units, feeds).solve().streams["Cátodos"]
    return cathodes.flow("Cu")


# Hallazgo: en los años 12 y 15 la ley publicada con 2 decimales (0,23 % y 0,18 %) se aleja un
# 2 % de la real (cobre contenido / mineral = 0,2349 % y 0,1839 %). Fallan el ±2 % declarado
# por redondeo de la FUENTE; quedan marcados como fallo esperado y estricto para no ocultarlo.
REDONDEO_DE_LEY = {12, 15}
PUQUIOS_CONTENIDO_T = {
    1: 9463,
    2: 10985,
    3: 10494,
    4: 11546,
    5: 10839,
    6: 10830,
    7: 10925,
    8: 11382,
    9: 7030,
    10: 11282,
    11: 6513,
    12: 4932,
    13: 5366,
    14: 6212,
    15: 434,
    "Vida de la mina": 128234,
}


@pytest.mark.parametrize(
    "ano",
    [
        pytest.param(a, marks=pytest.mark.xfail(strict=True, reason="ley redondeada en la fuente"))
        if a in REDONDEO_DE_LEY
        else a
        for a in PUQUIOS
    ],
)
def test_p3_puquios_catodos_por_ano(ano: int | str) -> None:
    ore, grade, recovery, published = PUQUIOS[ano]
    assert _pilas_sxew(ore, grade, recovery) == pytest.approx(published, rel=0.02)


@pytest.mark.parametrize("ano", list(PUQUIOS))
def test_p3_puquios_ley_publicada_es_el_redondeo_del_contenido(ano: int | str) -> None:
    """Coherencia interna de la Tabla 22-3. Mineral (kt), contenido (t) y ley (%) vienen
    redondeados: el intervalo de ley que permiten los dos primeros debe tocar el de la ley."""
    ore, grade, _, _ = PUQUIOS[ano]
    contained = PUQUIOS_CONTENIDO_T[ano]
    low = 100.0 * (contained - 0.5) / ((ore + 0.5) * 1000.0)
    high = 100.0 * (contained + 0.5) / ((ore - 0.5) * 1000.0)
    assert low <= grade + 0.005 and high >= grade - 0.005


def test_p3_puquios_ano_de_diseno() -> None:
    ore, grade, recovery, published = PUQUIOS_DISENO
    assert _pilas_sxew(ore, grade, recovery) == pytest.approx(published, rel=0.02)
