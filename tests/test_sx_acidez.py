"""SX con la actividad del H⁺ de Pitzer (acidez: pitzer). Tolerancias fijadas ANTES de correr.

Devi y Nayak definieron Kex con el pH medido, es decir con la actividad del H⁺. En este modo
la actividad sale de PHREEQC con pitzer_cu.dat para cada composición acuosa del perfil de etapas.
Kex sigue siendo 5,05. Sin calibrar con ningún pH medido.

Riesgo declarado: pitzer_cu.dat ya falló con cobre en ácido (calcantita, ver docs/equilibrio.md).

Controles:
1. pH de Pitzer del PLS de Mitshabu (7,02 g/L Cu, 3,90 g/L de ácido, 30 g/L de sulfato; el
   sulfato restante como MgSO4) frente al medido, 1,46: ±0,15. No depende de la SX.
2. Devi, Figura 3: ±15 %. Tabla IV: orgánico cargado ±5 %, refino dentro de un factor 2, pH del
   refino 0,9 ± 0,2. El níquel (0,01 M) se omite porque pitzer.dat no lo trae.
3. Devi, Tabla V (despojo): electrolito 25,1 g/L ±3 %; orgánico despojado ≤ 0,05 g/L.
4. Isocalc (Mitshabu): recuperación 92,83 % ± 5 puntos; transferencia neta 0,26 ±20 %; carga del
   orgánico 78,6 % ± 10 puntos.
"""

from __future__ import annotations

import math

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

from procesos import Flowsheet  # noqa: E402
from procesos.sx import SolventExtraction, pitzer_ph  # noqa: E402


def _unit(stages: int = 1, **kw) -> SolventExtraction:
    return SolventExtraction("SX", ("A", "O"), ("R", "C"), stages=stages, acidity="pitzer", **kw)


# Hallazgo: Pitzer da pH 1,81 al PLS, frente a 1,46 medido; el ácido le queda «más débil» y la
# extracción en modo pitzer sale sesgada hacia arriba (96,3 % en el caso Isocalc, dentro de la
# tolerancia pero por exceso). El despojo, en cambio, cuadra. Fallo esperado y estricto.
@pytest.mark.xfail(strict=True, reason="Pitzer: pH del PLS 1,81 frente a 1,46 medido")
def test_ph_de_pitzer_del_pls_de_mitshabu():
    assert pitzer_ph(_pls(), CATALOG) == pytest.approx(1.46, abs=0.15)


@pytest.mark.parametrize("vol_pct", list(FIGURA_3))
def test_devi_un_contacto(vol_pct):
    feed = _aqueous(100, 6.35, acido=0.5 * 10**-3.95 * ACID)
    result = _unit().solve([feed, _organic(100, vol_pct, 0.0, 0.56)], CATALOG)
    assert result.loaded_g_l == pytest.approx(FIGURA_3[vol_pct], rel=0.15)


def test_devi_extraccion_dos_etapas():
    feed = _aqueous(80, 6.35, acido=0.5 * 10**-3.95 * ACID)
    result = _unit(stages=2).solve([feed, _organic(60, 20, 0.0, 0.56)], CATALOG)
    assert result.loaded_g_l == pytest.approx(8.4, rel=0.05)
    assert 0.015 <= result.raffinate_g_l <= 0.060
    assert result.ph[-1] == pytest.approx(0.9, abs=0.2)


def _despojo_devi():
    acido = 0.15 * 1.84 * 0.98 * 1000.0
    strip = _aqueous(20, 0.0, acido=acido, densidad=1.17)
    unit = SolventExtraction("S", ("A", "O"), ("E", "D"), stages=3, density_aq=1.17,
                             acidity="pitzer")  # fmt: skip
    return unit.solve([strip, _organic(60, 20, 8.4, 0.56)], CATALOG)


def test_devi_despojo_electrolito():
    assert _despojo_devi().raffinate_g_l == pytest.approx(25.1, rel=0.03)


def test_devi_despojo_organico_despojado():
    assert _despojo_devi().loaded_g_l <= 0.05


@pytest.fixture(scope="module")
def isocalc():
    spent = _aqueous(1000 / OA_STRIP * OA_EXT, 33.67, acido=199.3, densidad=1.2)
    extraccion = SolventExtraction("E", ("PLS", "OrgD"), ("Refino", "OrgC"), stages=2,
                                   efficiency=(0.92, 0.95), acidity="pitzer")  # fmt: skip
    despojo = SolventExtraction("S", ("Spent", "OrgC"), ("Advance", "OrgD"), stages=1,
                                efficiency=(0.95,), density_aq=1.2, acidity="pitzer")  # fmt: skip
    guess = {"OrgD": _organic(1000 * OA_EXT, VOL, SO, ML)}
    sheet = Flowsheet(CATALOG, [extraccion, despojo], {"PLS": _pls(), "Spent": spent},
                      tears=("OrgD",), initial=guess)  # fmt: skip
    solution = sheet.solve()
    e = extraccion.solve([solution.streams["PLS"], solution.streams["OrgD"]], CATALOG)
    s = despojo.solve([solution.streams["Spent"], solution.streams["OrgC"]], CATALOG)
    return e, s


def test_isocalc_recuperacion(isocalc):
    assert isocalc[0].recovery * 100 == pytest.approx(92.83, abs=5.0)


def test_isocalc_transferencia_neta(isocalc):
    e, s = isocalc
    assert (e.loaded_g_l - s.loaded_g_l) / VOL == pytest.approx(0.26, rel=0.20)


def test_isocalc_carga_del_organico(isocalc):
    assert isocalc[0].loaded_g_l / (ML * VOL) * 100 == pytest.approx(78.6, abs=10.0)


def test_elemento_que_la_base_no_trae():
    feed = _aqueous(100, 5.0, otros={"NiSO4": 1.0})
    with pytest.raises(ValueError, match="Ni"):
        _unit().solve([feed, _organic(100, 20, 0.0, 0.56)], CATALOG)


def test_isocalc_extraccion_calibrada_y_despojo_pitzer():
    """POSTERIOR al resultado: la combinación mejor fundada (extracción calibrada con el pH medido
    del PLS, despojo con la actividad de Pitzer) se eligió después de ver las cifras. Mismas
    tolerancias que el caso Isocalc. No es una validación ciega."""
    spent = _aqueous(1000 / OA_STRIP * OA_EXT, 33.67, acido=199.3, densidad=1.2)
    extraccion = SolventExtraction("E", ("PLS", "OrgD"), ("Refino", "OrgC"), stages=2,
                                   efficiency=(0.92, 0.95), feed_ph=1.46)  # fmt: skip
    despojo = SolventExtraction("S", ("Spent", "OrgC"), ("Advance", "OrgD"), stages=1,
                                efficiency=(0.95,), density_aq=1.2, acidity="pitzer")  # fmt: skip
    guess = {"OrgD": _organic(1000 * OA_EXT, VOL, SO, ML)}
    sheet = Flowsheet(CATALOG, [extraccion, despojo], {"PLS": _pls(), "Spent": spent},
                      tears=("OrgD",), initial=guess)  # fmt: skip
    solution = sheet.solve()
    e = extraccion.solve([solution.streams["PLS"], solution.streams["OrgD"]], CATALOG)
    s = despojo.solve([solution.streams["Spent"], solution.streams["OrgC"]], CATALOG)
    assert e.recovery * 100 == pytest.approx(92.83, abs=5.0)
    assert (e.loaded_g_l - s.loaded_g_l) / VOL == pytest.approx(0.26, rel=0.20)
    assert e.loaded_g_l / (ML * VOL) * 100 == pytest.approx(78.6, abs=10.0)


def test_errores_de_acidez():
    with pytest.raises(ValueError):
        SolventExtraction("SX", ("A", "O"), ("R", "C"), acidity="otra")
    with pytest.raises(ValueError, match="pH"):
        _unit(feed_ph=1.5)


def test_tabla_de_pitzer_coincide_con_el_ph_directo_de_la_alimentacion():
    # verificación: la tabla en el Cu de la alimentación es exactamente su pH según PHREEQC
    feed = _aqueous(1000, 33.67, acido=199.3, densidad=1.2)
    unit = SolventExtraction("S", ("A", "O"), ("E", "D"), density_aq=1.2, acidity="pitzer")
    a = feed.total / 1.2
    x0 = feed.flow("CuSO4") * 1000 / CATALOG["CuSO4"].molar_mass / a
    activity = unit._pitzer_acid(feed, CATALOG, a, 2 * x0)  # x0 cae justo en la grilla
    assert -math.log10(activity(x0)) == pytest.approx(pitzer_ph(feed, CATALOG), abs=1e-9)
