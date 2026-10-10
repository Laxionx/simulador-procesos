"""Fase 3: reactor de equilibrio con PHREEQC (minteq.v4.dat). Tolerancias fijadas ANTES de correr:

- Yeso en agua a 25 °C vs Nordstrom (0,01528 mol/kg, citado por Hall, U. de Edimburgo): ±5 %.
- Yeso en H2SO4 0,1-1 mol/kg a 25 °C vs Shen et al. (2020), J. Chem. Eng. Data 65, 2310, tabla
  suplementaria (modelo de Pitzer evaluado, error medio 1,8 % contra los datos): ±15 %.
- pH de H2SO4 0,01 N, 0,1 N y 1 N vs PubChem/HSDB (2,1; 1,2; 0,3): ±0,1.
- Cierre de elementos del equipo: 1e-9; error de carga de PHREEQC: < 1e-6 %.
- Calcita con CO2 a 1 atm: SIN dato público medido de equilibrio; caso descartado (ver docs).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("phreeqpy")

from procesos import Catalog, Flowsheet, Stream, load_plant, make_species  # noqa: E402
from procesos.equilibrium import EquilibriumReactor, PhreeqcError, database_path  # noqa: E402
from procesos.report import element_balance, worst_closure  # noqa: E402

EXAMPLES = Path(__file__).resolve().parents[1] / "ejemplos"
GYPSUM = "CaSO4·2H2O"


def _catalog() -> Catalog:
    names = [
        ("H2O", "l"),
        ("H2SO4", "aq"),
        ("CaSO4", "aq"),
        (GYPSUM, "s"),
    ]
    return Catalog([make_species(n, phase=p) for n, p in names])


def _reactor() -> EquilibriumReactor:
    return EquilibriumReactor("Equilibrio", ("Entrada",), ("Salida",), {"Gypsum": GYPSUM}, 25.0)


def _solve(feed: Stream):
    catalog = _catalog()
    reactor = _reactor()
    result = reactor.solve([feed], catalog)
    return catalog, reactor, result


def _dissolved_ca_molality(feed: Stream) -> float:
    catalog, _, result = _solve(feed)
    ca = result.flows.get("CaSO4", 0.0) / catalog["CaSO4"].molar_mass  # kmol/h
    return ca / (result.flows["H2O"] / 1000.0)  # kmol/h por t/h de agua = mol/kg


def _acid_feed(molality: float, gypsum_kg: float = 20.0) -> Stream:
    m_acid = make_species("H2SO4", phase="aq").molar_mass
    return Stream({"H2O": 1000.0, "H2SO4": molality * m_acid, GYPSUM: gypsum_kg}, 25.0)


def test_yeso_en_agua_pura():
    m = _dissolved_ca_molality(Stream({"H2O": 1000.0, GYPSUM: 20.0}, 25.0))
    assert m == pytest.approx(0.01528, rel=0.05)


SHEN_2020 = {0.1: 0.01583, 0.2: 0.01713, 0.4: 0.01866, 0.6: 0.01942, 0.8: 0.01973, 1.0: 0.01971}
# Hallazgo: sobre ~0,5 mol/kg de ácido (fuerza iónica > 0,5) el modelo de actividad de
# minteq.v4 (Debye-Hückel extendido) se sale de su rango: el yeso queda -19 % a -27 % y el pH
# del ácido 1 N, +0,102. Fallos esperados y estrictos: si algún día pasan, la suite avisa.
LIMITE = pytest.mark.xfail(strict=True, reason="fuerza iónica sobre el rango de Debye-Hückel")


@pytest.mark.parametrize(
    "acid", [pytest.param(a, marks=LIMITE) if a > 0.5 else a for a in SHEN_2020]
)
def test_yeso_en_acido_sulfurico(acid):
    assert _dissolved_ca_molality(_acid_feed(acid)) == pytest.approx(SHEN_2020[acid], rel=0.15)


HSDB_PH = {0.005: 2.1, 0.05: 1.2, 0.51: 0.3}  # 0,01 N, 0,1 N y 1 N (molal aproximada)


@pytest.mark.parametrize("acid", [pytest.param(a, marks=LIMITE) if a > 0.5 else a for a in HSDB_PH])
def test_ph_del_acido_sulfurico(acid):
    _, _, result = _solve(_acid_feed(acid, gypsum_kg=0.0))
    assert result.ph == pytest.approx(HSDB_PH[acid], abs=0.1)


def test_cierre_de_elementos_y_de_carga():
    feed = _acid_feed(0.3)
    catalog = _catalog()
    sheet = Flowsheet(catalog, [_reactor()], {"Entrada": feed})
    solution = sheet.solve()
    for row in element_balance(sheet, solution):
        assert row.relative_error < 1e-9, row.name
    _, _, result = _solve(feed)
    assert abs(result.charge_error_pct) < 1e-6
    # el agua por balance de H coincide con la masa de agua de PHREEQC (H+ y HSO4- aparte)
    assert result.flows["H2O"] == pytest.approx(result.phreeqc_water_kg_h, rel=1e-3)
    assert result.saturation["Gypsum"] == pytest.approx(0.0, abs=1e-6)


def test_precipita_yeso_si_hay_sobresaturacion():
    # CaSO4 disuelto muy por encima de su solubilidad: el exceso precipita como yeso
    m_caso4 = make_species("CaSO4", phase="aq").molar_mass
    feed = Stream({"H2O": 1000.0, "CaSO4": 0.05 * m_caso4}, 25.0)
    catalog, _, result = _solve(feed)
    assert result.flows[GYPSUM] > 0
    assert result.minerals_mol_h["Gypsum"] == pytest.approx(
        result.flows[GYPSUM] / catalog[GYPSUM].molar_mass * 1000.0
    )


def test_planta_yaml_lixiviacion_con_yeso():
    plant = load_plant(EXAMPLES / "lixiviacion_equilibrio.yaml")
    solution = plant.flowsheet.solve()
    assert worst_closure(plant.flowsheet, solution) < 1e-9
    pls = solution.streams["PLS"]
    assert pls.flow(GYPSUM) > 0  # el calcio del carbonato precipita como yeso


def test_errores():
    catalog = _catalog()
    with pytest.raises(ValueError, match="agua"):
        _reactor().solve([Stream({"H2SO4": 1.0})], catalog)
    wrong = EquilibriumReactor("X", ("a",), ("b",), {"Gypsum": "H2SO4"})
    with pytest.raises(ValueError, match="fórmula"):
        wrong.solve([Stream({"H2O": 1.0})], catalog)
    with pytest.raises(PhreeqcError, match="no está"):
        EquilibriumReactor("X", ("a",), ("b",), {"Unobtainium": GYPSUM}).solve(
            [Stream({"H2O": 1.0})], catalog
        )
    with pytest.raises(FileNotFoundError):
        database_path("no_existe.dat")
    with pytest.raises(ValueError):
        EquilibriumReactor("X", ("a",), ("a",))
    assert _reactor().with_parameter("temperatura", 40.0).temperature == 40.0
    with pytest.raises(KeyError):
        _reactor().with_parameter("otra", 1.0)


def test_linea_de_comandos_informa_el_equilibrio(capsys):
    from procesos.cli import main

    assert main(["resolver", str(EXAMPLES / "lixiviacion_equilibrio.yaml")]) == 0
    out = capsys.readouterr().out
    assert "Equilibrio «Precipitación»: pH" in out and "Gypsum" in out
    m_acid = make_species("H2SO4", phase="aq").molar_mass
    strong = Stream({"H2O": 1000.0, "H2SO4": 0.9 * m_acid}, 25.0)
    _, _, result = _solve(strong)
    assert result.ionic_strength > 0.5  # caso que la CLI marca con aviso
    assert "Debye-Hückel" in result.warnings[0]
