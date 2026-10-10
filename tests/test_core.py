"""Fórmulas, especies, corrientes, reacciones y equipos."""

from __future__ import annotations

import math

import pytest

from procesos import Catalog, Reaction, Stream, check_balance, make_species, mix, parse_equation
from procesos.elements import molar_mass, parse_formula, split_charge
from procesos.stream import element_flows, moles
from procesos.units import Mixer, Reactor, Separator, Splitter


# ---------------------------------------------------------------- fórmulas
@pytest.mark.parametrize(
    ("formula", "expected"),
    [
        ("H2O", {"H": 2, "O": 1}),
        ("CuSO4·5H2O", {"Cu": 1, "S": 1, "O": 9, "H": 10}),
        ("CuSO4*5H2O", {"Cu": 1, "S": 1, "O": 9, "H": 10}),
        ("Ca(OH)2", {"Ca": 1, "O": 2, "H": 2}),
        ("Fe2(SO4)3", {"Fe": 2, "S": 3, "O": 12}),
        ("[Cu(NH3)4]SO4", {"Cu": 1, "N": 4, "H": 12, "S": 1, "O": 4}),
        ("Fe0.95S", {"Fe": 0.95, "S": 1}),
        ("CuSO4(aq)", {"Cu": 1, "S": 1, "O": 4}),
        ("SO4-2", {"S": 1, "O": 4}),
    ],
)
def test_lee_formulas(formula: str, expected: dict[str, float]) -> None:
    assert parse_formula(formula) == pytest.approx(expected)


@pytest.mark.parametrize("bad", ["Xx2", "Cu(SO4", "CuSO4)", "", "Cu$", "2", "Cu)2("])
def test_rechaza_formulas_invalidas(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_formula(bad)


def test_cargas_y_masas_molares() -> None:
    assert split_charge("Cu+2") == ("Cu", 2)
    assert split_charge("SO4-2") == ("SO4", -2)
    assert split_charge("OH-") == ("OH", -1)
    assert split_charge("H2O") == ("H2O", 0)
    assert molar_mass(parse_formula("H2SO4")) == pytest.approx(2 * 1.008 + 32.06 + 4 * 15.999)
    assert molar_mass(parse_formula("CuO")) == pytest.approx(79.545)


# ---------------------------------------------------------------- especies
def test_especies_infieren_fase_y_formula() -> None:
    assert make_species("H2O").phase == "l"
    assert make_species("CuO").phase == "s"
    aqueous = make_species("CuSO4(aq)")
    assert (aqueous.phase, aqueous.formula) == ("aq", "CuSO4")
    ion = make_species("Fe+3", phase="aq")
    assert ion.charge == 3
    named = make_species("Calcopirita", formula="CuFeS2")
    assert named.composition == pytest.approx({"Cu": 1, "Fe": 1, "S": 2})


def test_especies_y_catalogo_invalidos() -> None:
    with pytest.raises(ValueError):
        make_species("CuO", phase="plasma")
    with pytest.raises(ValueError):
        make_species("  ")
    with pytest.raises(ValueError):
        Catalog([make_species("CuO"), make_species("CuO")])
    with pytest.raises(ValueError):
        Catalog([])
    catalog = Catalog([make_species("CuO"), make_species("H2O")])
    with pytest.raises(KeyError):
        catalog["Au"]
    assert "CuO" in catalog and len(catalog) == 2
    assert catalog.elements() == ("Cu", "H", "O")


# ---------------------------------------------------------------- corrientes
def test_corriente_valida_y_es_inmutable() -> None:
    stream = Stream({"CuO": 10.0, "H2O": 0.0})
    assert dict(stream.flows) == {"CuO": 10.0}
    assert stream.total == 10.0 and stream.mass_fraction("CuO") == 1.0
    assert Stream({}).mass_fraction("CuO") == 0.0
    with pytest.raises(TypeError):
        stream.flows["CuO"] = 1.0  # type: ignore[index]
    changed = stream.with_flow("H2O", 5.0)
    assert stream.flow("H2O") == 0.0 and changed.flow("H2O") == 5.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"flows": {"CuO": -1.0}},
        {"flows": {"CuO": math.nan}},
        {"flows": {}, "temperature": -300.0},
        {"flows": {}, "pressure": 0.0},
    ],
)
def test_corriente_rechaza_valores_imposibles(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        Stream(**kwargs)


def test_mezcla_promedia_temperatura_y_toma_la_menor_presion() -> None:
    hot = Stream({"H2O": 100.0}, temperature=80.0, pressure=200.0)
    cold = Stream({"H2O": 300.0}, temperature=20.0, pressure=150.0)
    mixed = mix([hot, cold])
    assert mixed.flow("H2O") == 400.0
    assert mixed.temperature == pytest.approx(35.0)
    assert mixed.pressure == 150.0
    assert mix([Stream({}, temperature=40.0)]).temperature == 40.0
    with pytest.raises(ValueError):
        mix([])


def test_moles_y_flujo_por_elemento() -> None:
    catalog = Catalog([make_species("CuSO4", phase="aq")])
    stream = Stream({"CuSO4": 159.602})
    assert moles(stream, catalog)["CuSO4"] == pytest.approx(1.0)
    assert element_flows(stream, catalog)["Cu"] == pytest.approx(63.546)


# ---------------------------------------------------------------- reacciones
def test_lee_ecuaciones_con_coeficientes_e_iones() -> None:
    assert parse_equation("CuO + H2SO4 -> CuSO4 + H2O") == {
        "CuO": -1,
        "H2SO4": -1,
        "CuSO4": 1,
        "H2O": 1,
    }
    assert parse_equation("2 Fe+3 + Cu = 2 Fe+2 + Cu+2") == {
        "Fe+3": -2,
        "Cu": -1,
        "Fe+2": 2,
        "Cu+2": 1,
    }
    assert parse_equation("A + B => B + C") == {"A": -1, "C": 1}
    with pytest.raises(ValueError):
        parse_equation("CuO + H2SO4")


@pytest.mark.parametrize(
    ("stoichiometry", "key", "conversion"),
    [
        ({}, "CuO", 0.5),
        ({"CuO": -1, "Cu": 0}, "CuO", 0.5),
        ({"CuO": 1}, "CuO", 0.5),
        ({"CuO": -1}, "CuO", 1.5),
    ],
)
def test_reaccion_invalida(stoichiometry: dict, key: str, conversion: float) -> None:
    with pytest.raises(ValueError):
        Reaction(stoichiometry, key, conversion)


def test_balance_de_reacciones() -> None:
    names = ["CuO", "H2SO4", "CuSO4", "H2O", "Cu"]
    catalog = Catalog(
        [make_species(n) for n in names]
        + [
            make_species("Fe+3", phase="aq"),
            make_species("Fe+2", phase="aq"),
            make_species("Cu+2", phase="aq"),
        ]
    )
    check_balance(Reaction(parse_equation("CuO + H2SO4 -> CuSO4 + H2O"), "CuO", 1.0), catalog)
    check_balance(Reaction(parse_equation("2 Fe+3 + Cu -> 2 Fe+2 + Cu+2"), "Cu", 1.0), catalog)
    with pytest.raises(ValueError, match="desbalanceada"):
        check_balance(Reaction(parse_equation("CuO + H2SO4 -> CuSO4"), "CuO", 1.0), catalog)
    with pytest.raises(ValueError, match="carga"):
        check_balance(Reaction(parse_equation("Fe+3 + Cu -> Fe+2 + Cu+2"), "Cu", 1.0), catalog)
    with pytest.raises(ValueError, match="fuera del catálogo"):
        check_balance(Reaction(parse_equation("Au + CuO -> Cu + AuO"), "Au", 1.0), catalog)


# ---------------------------------------------------------------- equipos
def _catalog() -> Catalog:
    return Catalog([make_species(n) for n in ["CuO", "H2SO4", "CuSO4", "H2O", "SiO2"]])


def test_mezclador_y_puertos_invalidos() -> None:
    mixer = Mixer("M", ("A", "B"), ("C",))
    (out,) = mixer.compute([Stream({"H2O": 1.0}), Stream({"H2O": 2.0})], _catalog())
    assert out.flow("H2O") == 3.0
    with pytest.raises(KeyError):
        mixer.with_parameter("x", 1.0)
    with pytest.raises(ValueError):
        Mixer("M", (), ("C",))
    with pytest.raises(ValueError):
        Mixer("M", ("A",), ("A",))
    with pytest.raises(ValueError):
        Mixer("M", ("A",), ("B", "C"))
    with pytest.raises(ValueError):
        Mixer("", ("A",), ("B",))


def test_divisor_reparte_y_renormaliza() -> None:
    splitter = Splitter("D", ("F",), ("A", "B", "C"), (0.5, 0.3, 0.2))
    outs = splitter.compute([Stream({"H2O": 100.0})], _catalog())
    assert [o.flow("H2O") for o in outs] == pytest.approx([50.0, 30.0, 20.0])
    changed = splitter.with_parameter("fraccion:A", 0.8)
    assert changed.fractions == pytest.approx((0.8, 0.12, 0.08))
    even = Splitter("D", ("F",), ("A", "B", "C"), (1.0, 0.0, 0.0)).with_parameter("fraccion:A", 0.4)
    assert even.fractions == pytest.approx((0.4, 0.3, 0.3))
    with pytest.raises(KeyError):
        splitter.with_parameter("fraccion:Z", 0.5)
    for fractions, outputs in [
        ((0.5, 0.4), ("A", "B")),
        ((1.0,), ("A",)),
        ((0.5, 0.5), ("A", "B", "C")),
    ]:
        with pytest.raises(ValueError):
            Splitter("D", ("F",), outputs, fractions)


def test_separador_por_especie() -> None:
    separator = Separator("S", ("F",), ("Conc", "Rel"), {"CuO": 0.9}, default=0.1)
    conc, tail = separator.compute([Stream({"CuO": 100.0, "SiO2": 1000.0})], _catalog())
    assert conc.flow("CuO") == pytest.approx(90.0) and conc.flow("SiO2") == pytest.approx(100.0)
    assert conc.total + tail.total == pytest.approx(1100.0)
    assert separator.with_parameter("recuperacion:CuO", 0.5).recovery("CuO") == 0.5
    assert separator.with_parameter("recuperacion_por_defecto", 0.0).recovery("SiO2") == 0.0
    with pytest.raises(KeyError):
        separator.with_parameter("otra", 0.5)
    with pytest.raises(ValueError):
        Separator("S", ("F",), ("Conc", "Rel"), {"CuO": 1.2})
    with pytest.raises(ValueError):
        Separator("S", ("F",), ("Conc",), {})


def test_reactor_convierte_y_se_limita_al_reactivo_que_falta() -> None:
    catalog = _catalog()
    reaction = Reaction(parse_equation("CuO + H2SO4 -> CuSO4 + H2O"), "CuO", 0.9)
    reactor = Reactor("R", ("F",), ("P",), (reaction,))
    m_cuo, m_acid = catalog["CuO"].molar_mass, catalog["H2SO4"].molar_mass
    feed = Stream({"CuO": 10 * m_cuo, "H2SO4": 100 * m_acid})
    (out,) = reactor.compute([feed], catalog)
    assert out.flow("CuO") == pytest.approx(1 * m_cuo)
    assert out.total == pytest.approx(feed.total)
    (extent,) = reactor.extents([feed], catalog)
    assert extent.limited_by is None and extent.achieved_conversion == pytest.approx(0.9)

    short = Stream({"CuO": 10 * m_cuo, "H2SO4": 4 * m_acid})
    (limited,) = reactor.extents([short], catalog)
    assert limited.limited_by == "H2SO4" and limited.achieved_conversion == pytest.approx(0.4)
    (out,) = reactor.compute([short], catalog)
    assert out.flow("H2SO4") == pytest.approx(0.0, abs=1e-9)
    assert all(v >= 0 for v in out.flows.values())

    (nothing,) = reactor.extents([Stream({"H2SO4": 1.0})], catalog)
    assert nothing.extent == 0.0 and nothing.achieved_conversion == 0.0

    assert reactor.with_parameter("conversion:1", 0.5).reactions[0].conversion == 0.5
    for bad in ["conversion:2", "conversion:x", "otra"]:
        with pytest.raises(KeyError):
            reactor.with_parameter(bad, 0.5)
    with pytest.raises(ValueError):
        Reactor("R", ("F",), ("P",), ())
