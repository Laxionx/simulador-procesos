"""Base cu_h2so4_fuentes.dat: modelo de Pitzer de Fuentes, Justel, Jimenez y Casas (2023), J. Mol.
Liq. 391, 123377, cargado tal cual. Tolerancias fijadas ANTES de correr (brief aprobado):

1. Reproducción del modelo publicado:
   - log K a 25 °C de las 5 reacciones (Tabla 5): ±0,02.
   - Calcantita en agua vs Bell y Taber (1,419 mol/kg): ±3 %. No del todo ciega: al cargar la base
     se vio un índice de saturación de -0,004 con 1,4 mol/kg.
   - Calcantita con 1,49 mol/kg de H2SO4 (Bell y Taber, dentro de su ajuste: no ciega): ±5 %.
2. Independiente, H2SO4 solo: pH de 0,01 N, 0,1 N y 1 N vs PubChem/HSDB (2,1; 1,2; 0,3): ±0,1.
3. Independiente: pH del PLS de Mitshabu, 1,46 ± 0,15. La base no trae Mg: se calcula el pH del
   cobre y el ácido y se le suma el efecto del Mg que da pitzer_cu.dat (aproximación declarada).
4. Independiente: pH del refino de Devi (Tabla IV, prácticamente H2SO4 0,1 M), 0,9 ± 0,2.
5. SX con esta base (mismas tolerancias que con pitzer_cu.dat): Devi Figura 3 ±15 %; Tabla IV
   orgánico cargado ±5 %, refino en un factor 2, pH 0,9 ± 0,2; Tabla V electrolito ±3 % y orgánico
   despojado ≤ 0,05 g/L; Isocalc con extracción calibrada y despojo con esta base: recuperación
   92,83 % ± 5 puntos, transferencia neta 0,26 ±20 %, carga 78,6 % ± 10 puntos.
"""

from __future__ import annotations

import pytest

pytest.importorskip("phreeqpy")

from test_sx import (  # noqa: E402
    ACID,
    CATALOG,
    FIGURA_3,
    ML,
    OA_EXT,
    OA_STRIP,
    SO,
    VOL,
    _aqueous,
    _organic,
    _pls,
)

from procesos import Catalog, Flowsheet, Stream, make_species  # noqa: E402
from procesos.equilibrium import EquilibriumReactor, _engine, database_path  # noqa: E402
from procesos.sx import SolventExtraction, pitzer_ph  # noqa: E402

FUENTES = "cu_h2so4_fuentes.dat"
CHALCANTHITE = "CuSO4·5H2O"
M_ACID = make_species("H2SO4", phase="aq").molar_mass
M_CUSO4 = make_species("CuSO4", phase="aq").molar_mass


def test_constantes_a_25_grados():
    engine = _engine(database_path(FUENTES))
    engine.run_string(
        "\n".join(
            [
                "SOLUTION 1",
                "  temp 25",
                "USER_PUNCH",
                "  -headings w hso4 h2so4 cuso4 calc",
                '  10 PUNCH LK_SPECIES("OH-"), LK_SPECIES("HSO4-"), LK_SPECIES("H2SO4"), '
                'LK_SPECIES("CuSO4"), LK_PHASE("Chalcanthite")',
                "SELECTED_OUTPUT",
                "  -reset false",
                "END",
            ]
        )
    )
    table = engine.get_selected_output_array()
    row = dict(zip(table[0], table[-1], strict=True))
    expected = {"w": -13.99, "hso4": 1.99, "h2so4": -0.99, "cuso4": 2.39, "calc": -2.60}
    for key, value in expected.items():
        assert row[key] == pytest.approx(value, abs=0.02), key


def _catalog() -> Catalog:
    names = [("H2O", "l"), ("H2SO4", "aq"), ("CuSO4", "aq"), (CHALCANTHITE, "s")]
    return Catalog([make_species(n, phase=p) for n, p in names])


def _chalcanthite(acid_molal: float) -> float:
    """Cu disuelto (mol/kg) con calcantita en exceso, a esa molalidad FINAL de ácido."""
    catalog = _catalog()
    reactor = EquilibriumReactor("Eq", ("A",), ("B",), {"Chalcanthite": CHALCANTHITE}, 25.0,
                                 database_path(FUENTES))  # fmt: skip
    water = 1000.0
    for _ in range(20):
        feed = Stream({"H2O": water, "H2SO4": acid_molal * M_ACID, CHALCANTHITE: 800.0}, 25.0)
        result = reactor.solve([feed], catalog)
        if abs(result.flows["H2O"] - 1000.0) < 1e-9:
            break
        water += 1000.0 - result.flows["H2O"]
    assert result.flows[CHALCANTHITE] > 0
    return result.flows["CuSO4"] / M_CUSO4 / (result.flows["H2O"] / 1000.0)


def test_calcantita_en_agua():
    assert _chalcanthite(0.0) == pytest.approx(18.47 / M_CUSO4 / 0.08153, rel=0.03)


def test_calcantita_en_acido_dentro_de_su_ajuste():
    water_kg = (100.0 - 11.14 - 12.62) / 1000.0  # Bell y Taber: 11,14 % H2SO4 y 12,62 % CuSO4
    acid, cu = 11.14 / M_ACID / water_kg, 12.62 / M_CUSO4 / water_kg
    assert _chalcanthite(acid) == pytest.approx(cu, rel=0.05)


ACID_CATALOG = Catalog([make_species("H2O", phase="l"), make_species("H2SO4", phase="aq"),
                        make_species("CuSO4", phase="aq")])  # fmt: skip


@pytest.mark.parametrize(("molal", "ph"), [(0.005, 2.1), (0.05, 1.2), (0.51, 0.3)])
def test_ph_del_acido_sulfurico(molal, ph):
    stream = Stream({"H2O": 1.0, "H2SO4": molal * M_ACID / 1000.0})
    assert pitzer_ph(stream, ACID_CATALOG, FUENTES) == pytest.approx(ph, abs=0.1)


# Hallazgo: con esta base el PLS da pH 1,74 (1,64 del cobre y el ácido + 0,11 del Mg), y con
# pitzer_cu.dat, 1,81. Dos modelos coherentes coinciden y ninguno llega al 1,46 medido: la
# diferencia no parece del modelo de actividad, sino de la referencia (pH de electrodo a fuerza
# iónica ~1) o de especies que no se modelan (Al, Fe3+). Fallo esperado y estricto.
@pytest.mark.xfail(strict=True, reason="pH medido del PLS: no lo reproduce ningún modelo")
def test_ph_del_pls_de_mitshabu():
    pls = _pls()
    sin_mg = Stream({k: v for k, v in pls.flows.items() if k != "MgSO4"})
    efecto_mg = pitzer_ph(pls, CATALOG) - pitzer_ph(sin_mg, CATALOG)  # con pitzer_cu.dat
    assert pitzer_ph(sin_mg, CATALOG, FUENTES) + efecto_mg == pytest.approx(1.46, abs=0.15)


def test_ph_del_refino_de_devi():
    refino = _aqueous(1000, 0.03, acido=(6.35 - 0.03) / 63.546 * ACID)
    assert pitzer_ph(refino, CATALOG, FUENTES) == pytest.approx(0.9, abs=0.2)


# ------------------------------------------------------------------ SX con esta base


def _unit(stages: int = 1, **kw) -> SolventExtraction:
    return SolventExtraction("SX", ("A", "O"), ("R", "C"), stages=stages, acidity="pitzer",
                             database=FUENTES, **kw)  # fmt: skip


@pytest.mark.parametrize("vol_pct", list(FIGURA_3))
def test_sx_devi_un_contacto(vol_pct):
    feed = _aqueous(100, 6.35, acido=0.5 * 10**-3.95 * ACID)
    result = _unit().solve([feed, _organic(100, vol_pct, 0.0, 0.56)], CATALOG)
    assert result.loaded_g_l == pytest.approx(FIGURA_3[vol_pct], rel=0.15)


def test_sx_devi_dos_etapas():
    feed = _aqueous(80, 6.35, acido=0.5 * 10**-3.95 * ACID)
    result = _unit(stages=2).solve([feed, _organic(60, 20, 0.0, 0.56)], CATALOG)
    assert result.loaded_g_l == pytest.approx(8.4, rel=0.05)
    assert 0.015 <= result.raffinate_g_l <= 0.060
    assert result.ph[-1] == pytest.approx(0.9, abs=0.2)


def test_sx_devi_despojo():
    acido = 0.15 * 1.84 * 0.98 * 1000.0
    strip = _aqueous(20, 0.0, acido=acido, densidad=1.17)
    result = _unit(stages=3, density_aq=1.17).solve([strip, _organic(60, 20, 8.4, 0.56)], CATALOG)
    assert result.raffinate_g_l == pytest.approx(25.1, rel=0.03)
    assert result.loaded_g_l <= 0.05


# Hallazgo: en el despojo de una etapa con 199 g/L de ácido esta base da menos actividad del H+
# que pitzer_cu.dat (pH -0,06 contra -0,37): deja 5,34 g/L en el orgánico (Isocalc 3,12; con
# pitzer_cu.dat, 3,10) y el circuito recupera 67 %. Para el despojo se recomienda pitzer_cu.dat.
@pytest.mark.xfail(strict=True, reason="despojo exigente: Fuentes despoja de menos")
def test_sx_isocalc_extraccion_calibrada_y_despojo_fuentes():
    spent = _aqueous(1000 / OA_STRIP * OA_EXT, 33.67, acido=199.3, densidad=1.2)
    extraccion = SolventExtraction("E", ("PLS", "OrgD"), ("Refino", "OrgC"), stages=2,
                                   efficiency=(0.92, 0.95), feed_ph=1.46)  # fmt: skip
    despojo = SolventExtraction("S", ("Spent", "OrgC"), ("Advance", "OrgD"), stages=1,
                                efficiency=(0.95,), density_aq=1.2, acidity="pitzer",
                                database=FUENTES)  # fmt: skip
    guess = {"OrgD": _organic(1000 * OA_EXT, VOL, SO, ML)}
    sheet = Flowsheet(CATALOG, [extraccion, despojo], {"PLS": _pls(), "Spent": spent},
                      tears=("OrgD",), initial=guess)  # fmt: skip
    solution = sheet.solve()
    e = extraccion.solve([solution.streams["PLS"], solution.streams["OrgD"]], CATALOG)
    s = despojo.solve([solution.streams["Spent"], solution.streams["OrgC"]], CATALOG)
    assert e.recovery * 100 == pytest.approx(92.83, abs=5.0)
    assert (e.loaded_g_l - s.loaded_g_l) / VOL == pytest.approx(0.26, rel=0.20)
    assert e.loaded_g_l / (ML * VOL) * 100 == pytest.approx(78.6, abs=10.0)


def test_la_base_no_trae_magnesio():
    with pytest.raises(ValueError, match="Mg"):
        _unit().solve([_pls(), _organic(1000, 21, 0.0, 0.52)], CATALOG)
