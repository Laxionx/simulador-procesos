"""Fundición de estaño en dos etapas (fase 4d). Tolerancias fijadas ANTES de correr (brief
aprobado el 12-10):

1. Equilibrio medido (Takeda et al. 1990, Tabla 6, 1.573 K): D de cada ensayo. Mediana de las
   filas con metal < 2 % Fe dentro de 150-400 (etapa 1) y de las filas con 10-60 % Fe dentro de
   20-50 (etapa 2), los rangos que usa el modelo (Kandalam et al. 2023).
2. Funsur 2022-2025 (Memoria Integrada 2025 de Minsur, Tabla 11): la recuperación calculada con
   el Sn que entra (concentrado + escoria de horno rotatorio) y el estaño refinado, contra la
   reportada, ±1 punto. Lo que explica la escoria de desecho se informa en docs/estano.md.
3. Guardas: cierre por elemento, metas y D cumplidos en cada etapa, el reciclo converge, el
   carbono y la caliza a mano, sentido físico y cargas imposibles que avisan.
"""

from __future__ import annotations

import runpy
from pathlib import Path
from statistics import median

import pytest

from procesos.elements import molar_mass, parse_formula
from procesos.estano import TinSmeltingError, feed, smelt_tin
from procesos.estano_datos import D_STAGE1, D_STAGE2, FUNSUR, TAKEDA_1573

SN, FE = 118.71, 55.845


def _mm(formula: str) -> float:
    return molar_mass(parse_formula(formula))


# ------------------------------------------------------------------ 1. equilibrio medido
def _d(row) -> float:
    _test, sn_slag, _cao, _sio2, fe_slag, fe_metal, sn_metal = row
    sn_metal = 100.0 - fe_metal if sn_metal is None else sn_metal
    return (sn_metal / fe_metal) * (fe_slag / sn_slag)


def test_takeda_d_etapa_1():
    values = [_d(r) for r in TAKEDA_1573 if r[5] < 2.0]
    assert len(values) > 30
    assert D_STAGE1[0] <= median(values) <= D_STAGE1[1]


def test_takeda_d_etapa_2():
    values = [_d(r) for r in TAKEDA_1573 if 10.0 <= r[5] <= 60.0]
    assert len(values) >= 10
    assert D_STAGE2[0] <= median(values) <= D_STAGE2[1]


def test_takeda_bien_copiado():
    # Guarda de transcripción: 81 ensayos; en las filas con Sn y Fe del metal, la suma que
    # imprime el artículo va de 98,3 a 102,1 % (error analítico de la fuente).
    assert len(TAKEDA_1573) == 81
    for row in TAKEDA_1573:
        if row[6] is not None:
            assert 98.0 <= row[5] + row[6] <= 102.5, row[0]
        assert 0 < row[1] < 70 and 0 < row[4] < 70 and 0 < row[5] < 70, row[0]


# ------------------------------------------------------------------ 2. Funsur
@pytest.mark.parametrize("year", list(FUNSUR))
def test_funsur_recuperacion_coherente(year):
    conc_t, grade, rot_t, rot_sn, refined, recovery, _discard = FUNSUR[year]
    sn_in = conc_t * grade / 100 + rot_t * rot_sn / 100
    assert 100 * refined / sn_in == pytest.approx(recovery, abs=1.0)


# ------------------------------------------------------------------ 3. guardas
def _simple(**kw):
    comp = {"SnO2": 60.0, "Fe2O3": 15.0, "SiO2": 15.0, "CaO": 4.0, "Al2O3": 6.0}
    args = {"crude_fe_pct": 2.0, "discard_sn_pct": 0.8, "d1": 200.0, "d2": 35.0}
    args.update(kw)
    return smelt_tin(feed(1000.0, comp), **args)


@pytest.mark.parametrize("kw", [{}, {"fume1": 0.05, "fume2": 0.2}, {"basicity": 0.4}])
def test_cierre_por_elemento(kw):
    inn, out = _simple(**kw).elements()
    for el in inn:
        assert out[el] == pytest.approx(inn[el], abs=1e-7), el


def test_metas_y_d_cumplidos():
    r = _simple(fume2=0.15)
    assert r.stage1.metal_pct("Fe") == pytest.approx(2.0, abs=1e-9)
    assert r.stage2.slag_pct("Sn") == pytest.approx(0.8, abs=1e-9)
    for stage, d in ((r.stage1, 200.0), (r.stage2, 35.0)):
        metal = stage.metal["Sn"] / stage.metal["Fe"]
        slag = stage.slag_pct("Sn") / stage.slag_pct("Fe")
        assert metal / slag == pytest.approx(d, rel=1e-9)
    assert r.iterations < 100


def test_carbono_y_caliza_a_mano():
    # Sin humos: el C retira el O de SnO2 y Fe2O3 menos el que queda en SnO y FeO de la escoria
    # de desecho (a régimen, el hardhead vuelve como metal). Cada C se lleva 1,5 O (50 % de CO).
    r = _simple(basicity=0.4)
    discard = r.stage2.slag
    o_in = 1000 * (0.60 * 2 * 15.999 / _mm("SnO2") + 0.15 * 3 * 15.999 / _mm("Fe2O3"))
    o_out = discard["SnO"] * 15.999 / _mm("SnO") + discard["FeO"] * 15.999 / _mm("FeO")
    assert r.carbon_t == pytest.approx((o_in - o_out) / 15.999 / 1.5 * 12.011, rel=1e-9)
    assert r.limestone_t == pytest.approx((0.4 * 150 - 40) / _mm("CaO") * _mm("CaCO3"), rel=1e-9)


def test_sentido_fisico():
    base = _simple()
    assert _simple(d1=400.0).stage1.slag_pct("Sn") < base.stage1.slag_pct("Sn")
    assert _simple(discard_sn_pct=1.5).recovery < base.recovery
    assert _simple(crude_fe_pct=4.0).stage1.slag_pct("Sn") < base.stage1.slag_pct("Sn")
    # A régimen, el Sn solo sale con el crudo y la escoria de desecho.
    lost = base.stage2.slag_pct("Sn") / 100 * base.stage2.slag_t
    assert base.recovery == pytest.approx(1 - lost / base.sn_fed_t, rel=1e-9)


def test_cargas_imposibles_avisan():
    with pytest.raises(TinSmeltingError, match="sumar 100"):
        feed(10.0, {"SnO2": 50.0})
    with pytest.raises(TinSmeltingError, match="sin modelo"):
        feed(10.0, {"PbO": 100.0})
    with pytest.raises(TinSmeltingError, match="entre 0 y 100"):
        _simple(crude_fe_pct=0.0)
    with pytest.raises(TinSmeltingError, match="D positivos"):
        _simple(d1=-1.0)
    with pytest.raises(TinSmeltingError, match="Reducción imposible"):
        _simple(discard_sn_pct=60.0)
    with pytest.raises(TinSmeltingError, match="Fusión imposible"):
        smelt_tin(feed(100.0, {"SnO2": 1.0, "Fe2O3": 90.0, "SiO2": 9.0}), crude_fe_pct=1.0,
                  discard_sn_pct=0.5, d1=200.0, d2=35.0)  # fmt: skip


def test_ejemplo_corre(capsys):
    runpy.run_path(str(Path(__file__).parents[1] / "ejemplos" / "estano_funsur.py"))
    assert "Recuperación" in capsys.readouterr().out


def test_carbono_con_otra_razon_de_co():
    # Con 20 % de CO cada C se lleva 1,8 átomos de O (a 50 % las dos fórmulas coinciden).
    half, low = _simple(), _simple(co_fraction=0.2)
    assert low.carbon_t == pytest.approx(half.carbon_t * 1.5 / 1.8, rel=1e-9)


def test_humos_por_etapa():
    r = _simple(fume1=0.05, fume2=0.2)
    sn_slag1 = r.stage1.slag_t * r.stage1.slag_pct("Sn") / 100
    assert r.stage2.fume_sno_t == pytest.approx(0.2 * sn_slag1 / SN * _mm("SnO"), rel=1e-9)
    assert r.stage1.fume_sno_t > 0.04 * r.sn_fed_t / SN * _mm("SnO")
