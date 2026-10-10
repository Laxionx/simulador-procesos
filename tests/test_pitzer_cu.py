"""B2: soluciones concentradas con Pitzer (base pitzer_cu.dat). Tolerancias fijadas ANTES de correr:

- Consistencia de la base con Justel et al. (2020), ACS Omega 5, 29150, Tabla 6: CuSO4 1,39 mol/kg
  a 25 °C da γ± 0,0368 y a_w 0,9753. γ± ±2 %, a_w ±0,002 y |SI| de la calcantita ≤ 0,01.
- Calcantita en agua a 25 °C vs Bell y Taber (1908), en Seidell (1919), p. 276: 18,47 g de CuSO4
  por 100 g de solución saturada: ±5 %. Medición independiente de la de Justel.
- Calcantita en H2SO4 de 1,5 a 9,8 mol/kg a 25 °C, misma tabla (5 puntos): ±10 %.
- Yeso en agua (Nordstrom, 0,01528 mol/kg): ±5 %. Yeso en H2SO4 de 0,1 a 3 mol/kg vs Shen et al.
  (2020): ±10 %. Esta tolerancia NO es ciega: con pitzer.dat sin cobre ya se había visto -0,1 % a
  -5,4 %.
- Cierre de elementos del reactor con la base pitzer_cu.dat: 1e-9.
"""

from __future__ import annotations

import pytest

pytest.importorskip("phreeqpy")

from procesos import Catalog, Flowsheet, Stream, make_species  # noqa: E402
from procesos.equilibrium import EquilibriumReactor, _engine, database_path  # noqa: E402
from procesos.report import element_balance  # noqa: E402

PITZER = database_path("pitzer_cu.dat")
CHALCANTHITE = "CuSO4·5H2O"
GYPSUM = "CaSO4·2H2O"
M_ACID = make_species("H2SO4", phase="aq").molar_mass
M_CUSO4 = make_species("CuSO4", phase="aq").molar_mass


def _catalog() -> Catalog:
    names = [
        ("H2O", "l"),
        ("H2SO4", "aq"),
        ("CuSO4", "aq"),
        ("CaSO4", "aq"),
        (CHALCANTHITE, "s"),
        (GYPSUM, "s"),
    ]
    return Catalog([make_species(n, phase=p) for n, p in names])


def _reactor(minerals: dict[str, str]) -> EquilibriumReactor:
    return EquilibriumReactor("Equilibrio", ("Entrada",), ("Salida",), minerals, 25.0, PITZER)


def test_base_consistente_con_justel_2020():
    engine = _engine(PITZER)
    engine.run_string(
        "\n".join(
            [
                "SOLUTION 1",
                "  temp 25",
                "  pH 7 charge",
                "  units mol/kgw",
                "  Cu 1.39",
                "  S(6) 1.39",
                "USER_PUNCH",
                "  -headings aw gCu gSO4 si",
                '  10 PUNCH ACT("H2O"), GAMMA("Cu+2"), GAMMA("SO4-2"), SI("Chalcanthite")',
                "SELECTED_OUTPUT",
                "  -reset false",
                "END",
            ]
        )
    )
    table = engine.get_selected_output_array()
    row = dict(zip(table[0], table[-1], strict=True))
    gamma = (row["gCu"] * row["gSO4"]) ** 0.5
    assert gamma == pytest.approx(0.0368, rel=0.02)
    assert row["aw"] == pytest.approx(0.9753, abs=0.002)
    assert abs(row["si"]) <= 0.01


# Bell y Taber (1908) y Foote (1915), en Seidell (1919), p. 276: g por 100 g de solución saturada,
# fase sólida CuSO4·5H2O a 25 °C. (H2SO4, CuSO4)
BELL_TABER = [(0.0, 18.47), (11.14, 12.62), (25.53, 5.92), (36.77, 3.25), (42.15, 2.63),
              (47.66, 2.59)]  # fmt: skip


def _molal(w_acid: float, w_cu: float) -> tuple[float, float]:
    water_kg = (100.0 - w_acid - w_cu) / 1000.0
    return w_acid / M_ACID / water_kg, w_cu / M_CUSO4 / water_kg


def _chalcanthite_solubility(acid: float) -> float:
    """Cu disuelto (mol/kg) en equilibrio con calcantita en exceso, a esa molalidad FINAL de ácido.

    La calcantita al disolverse aporta 5 H2O por Cu: se ajusta el agua de la entrada hasta que la
    salida tenga exactamente 1.000 kg/h de agua.
    """
    catalog = _catalog()
    reactor = _reactor({"Chalcanthite": CHALCANTHITE})
    water = 1000.0
    for _ in range(20):
        feed = Stream({"H2O": water, "H2SO4": acid * M_ACID, CHALCANTHITE: 800.0}, 25.0)
        result = reactor.solve([feed], catalog)
        if abs(result.flows["H2O"] - 1000.0) < 1e-9:
            break
        water += 1000.0 - result.flows["H2O"]
    assert result.flows[CHALCANTHITE] > 0  # queda sólido: está saturada
    return result.flows["CuSO4"] / M_CUSO4 / (result.flows["H2O"] / 1000.0)


def test_calcantita_en_agua():
    _, cu = _molal(*BELL_TABER[0])
    assert _chalcanthite_solubility(0.0) == pytest.approx(cu, rel=0.05)


# Hallazgo: con ácido la base sobreestima la solubilidad: +14, +80, +113, +92 y +18 % con 1,5;
# 3,8; 6,3; 7,8 y 9,8 mol/kg de H2SO4. Mandan el término Cu-HSO4 y los ternarios, ajustados por sus
# autores con OTRO modelo del H2SO4. Con el H2SO4 de Justel completo tampoco pasa (+25 a +126 %).
NO_VALIDADO = pytest.mark.xfail(strict=True, reason="Cu con ácido: parámetros no transferibles")


@pytest.mark.parametrize("point", [pytest.param(p, marks=NO_VALIDADO) for p in BELL_TABER[1:]])
def test_calcantita_en_acido_sulfurico(point):
    acid, cu = _molal(*point)
    assert _chalcanthite_solubility(acid) == pytest.approx(cu, rel=0.10)


def _gypsum_solubility(acid: float) -> float:
    catalog = _catalog()
    feed = Stream({"H2O": 1000.0, "H2SO4": acid * M_ACID, GYPSUM: 20.0}, 25.0)
    result = _reactor({"Gypsum": GYPSUM}).solve([feed], catalog)
    return result.flows["CaSO4"] / catalog["CaSO4"].molar_mass / (result.flows["H2O"] / 1000.0)


def test_yeso_en_agua():
    assert _gypsum_solubility(0.0) == pytest.approx(0.01528, rel=0.05)


SHEN_2020 = {0.1: 0.01583, 0.2: 0.01713, 0.4: 0.01866, 0.6: 0.01942, 0.8: 0.01973, 1.0: 0.01971,
             1.5: 0.01867, 2.0: 0.01677, 2.5: 0.01451, 3.0: 0.01227}  # fmt: skip


@pytest.mark.parametrize("acid", list(SHEN_2020))
def test_yeso_en_acido_sulfurico_concentrado(acid):
    assert _gypsum_solubility(acid) == pytest.approx(SHEN_2020[acid], rel=0.10)


def test_cierre_de_elementos_con_cobre_y_acido():
    catalog = _catalog()
    feed = Stream(
        {"H2O": 1000.0, "H2SO4": 150.0, "CuSO4": 200.0, CHALCANTHITE: 50.0, GYPSUM: 10.0}, 25.0
    )
    reactor = _reactor({"Chalcanthite": CHALCANTHITE, "Gypsum": GYPSUM})
    sheet = Flowsheet(catalog, [reactor], {"Entrada": feed})
    solution = sheet.solve()
    for row in element_balance(sheet, solution):
        assert row.relative_error < 1e-9, row.name


def test_avisos_de_validez_segun_la_base():
    from procesos.equilibrium import DEFAULT_DATABASE

    catalog = _catalog()
    chalcanthite = {"Chalcanthite": CHALCANTHITE}
    water = Stream({"H2O": 1000.0, CHALCANTHITE: 800.0}, 25.0)
    assert _reactor(chalcanthite).solve([water], catalog).warnings == ()
    acid = Stream({"H2O": 1000.0, "H2SO4": 150.0, CHALCANTHITE: 800.0}, 25.0)
    (note,) = _reactor(chalcanthite).solve([acid], catalog).warnings
    assert "ácido libre" in note
    hot = EquilibriumReactor("E", ("a",), ("b",), chalcanthite, 40.0, PITZER)
    assert any("25 °C" in w for w in hot.solve([water], catalog).warnings)
    # sin cobre, la base de Pitzer no avisa aunque la fuerza iónica sea alta
    gypsum = Stream({"H2O": 1000.0, "H2SO4": 2.0 * M_ACID, GYPSUM: 20.0}, 25.0)
    result = _reactor({"Gypsum": GYPSUM}).solve([gypsum], catalog)
    assert result.ionic_strength > 0.5 and result.warnings == ()
    # la de Debye-Hückel sí
    minteq = EquilibriumReactor("E", ("a",), ("b",), {"Gypsum": GYPSUM}, 25.0,
                                str(DEFAULT_DATABASE))  # fmt: skip
    assert "Debye-Hückel" in minteq.solve([gypsum], catalog).warnings[0]
