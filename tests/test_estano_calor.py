"""Balance de calor de la fundición de estaño (fase 4d). Tolerancias fijadas ANTES de correr
(brief aprobado el 12-10):

1. JANAF contra USGS B2131 a ±2 % donde están las dos fuentes: CaO y CO a 1.500 K.
2. Cierre de calor y guardas: el gas calculado cierra cada etapa con su pérdida; el calor de
   combustión a 25 °C es el poder calorífico inferior del CH4; el vapor empalma a 800 K.
3. Coherencia con Pisco 2025: el CO2 mínimo del modelo (carbono + caliza + gas, sin pérdidas)
   queda por debajo de las 85.087 t de CO2eq directo de la planta. No es una validación: Minsur
   no publica el gas por planta, y ese total incluye la refinería y el diésel.
"""

from __future__ import annotations

import pytest

from procesos.elements import molar_mass, parse_formula
from procesos.estano import feed, smelt_tin
from procesos.estano_calor import (
    SNO_FORMATION_LIQUID,
    combustion_mj_per_kmol,
    enthalpy_mj,
    tin_heat,
)
from procesos.estano_datos import CASSITERITE_REF, FUNSUR, PISCO_SCOPE1_2025_T
from procesos.thermo_data import DEFAULT_THERMO as T


def _funsur_2025():
    conc_t, grade, rot_t, rot_sn, _ref, _rec, discard = FUNSUR[2025]
    sno2 = grade * molar_mass(parse_formula("SnO2")) / 118.71
    gangue = {k: v for k, v in CASSITERITE_REF.items() if k != "SnO2"}
    scale = (100 - sno2) / sum(gangue.values())
    conc = feed(conc_t, {"SnO2": sno2} | {k: v * scale for k, v in gangue.items()})
    rot_sno = rot_sn * molar_mass(parse_formula("SnO")) / 118.71
    rot = feed(rot_t, {"SnO": rot_sno, "otros": 100 - rot_sno})
    feeds = {k: conc.get(k, 0.0) + rot.get(k, 0.0) for k in conc | rot}
    return smelt_tin(feeds, crude_fe_pct=2.0, discard_sn_pct=discard, d1=200.0, d2=35.0,
                     basicity=0.3, fume2=0.15)  # fmt: skip


@pytest.fixture(scope="module")
def funsur():
    return _funsur_2025()


# ------------------------------------------------------------------ 1. datos
JANAF_1500 = [(("CaO", "s"), -635.1, 62.766), (("CO", "g"), -110.5, 38.850)]  # H-H298, kJ/mol


@pytest.mark.parametrize(("key", "dfh", "janaf_1500"), JANAF_1500)
def test_usgs_vs_janaf(key, dfh, janaf_1500):
    assert T.by_key(*key).enthalpy(1500.0) - dfh == pytest.approx(janaf_1500, rel=0.02)


# ------------------------------------------------------------------ 2. cierre y guardas
@pytest.mark.parametrize(("loss1", "loss2"), [(0.0, 0.0), (5e4, 1e4)])
def test_el_gas_cierra_cada_etapa(funsur, loss1, loss2):
    h = tin_heat(funsur, loss1_mj=loss1, loss2_mj=loss2)
    for st, t in ((h.stage1, 1200.0), (h.stage2, 1400.0)):
        assert st.ch4_kmol > 0
        assert st.h_in_mj + st.ch4_kmol * combustion_mj_per_kmol(t) == pytest.approx(
            st.h_out_mj + st.loss_mj, rel=1e-12
        )


def test_combustion_a_25_grados_es_el_pci():
    pci = 393.5 + 2 * 241.826 - 74.8  # CH4 + 2 O2 → CO2 + 2 H2O(g), kJ/mol
    assert combustion_mj_per_kmol(25.0) == pytest.approx(pci, abs=0.5)
    assert combustion_mj_per_kmol(1400.0) < combustion_mj_per_kmol(1200.0) < pci


def test_sno_liquido_de_takeda():
    t = 1400.0
    h = enthalpy_mj({"SnO": 134.709 / 1000.0}, t - 273.15)  # 1 kmol → MJ = kJ/mol
    hand = T.by_key("Sn", "l").enthalpy(t) + 0.5 * T.by_key("O2", "g").enthalpy(t)
    assert h == pytest.approx(hand + SNO_FORMATION_LIQUID, rel=1e-9)


def test_vapor_empalma_a_800_k():
    low, high = T.by_key("H2O", "g").ranges
    assert high.dh(800.0) == pytest.approx(low.dh(800.0), abs=0.05)


def test_sentido_fisico(funsur):
    base = tin_heat(funsur)
    assert tin_heat(funsur, loss1_mj=1e5).ch4_t > base.ch4_t
    assert tin_heat(funsur, t1_c=1300.0).stage1.ch4_t > base.stage1.ch4_t
    assert base.co2_t == pytest.approx(base.co2_process_t + base.co2_fuel_t)
    with pytest.raises(ValueError):
        tin_heat(funsur, loss1_mj=-1.0)


def test_sin_deficit_no_quema_gas(funsur):
    # Una etapa 2 a 1.200 °C con la escoria entrando a 1.400 °C sobra calor: no se quema gas.
    h = tin_heat(funsur, t1_c=1400.0, t2_c=1200.0)
    assert h.stage2.deficit_mj < 0 and h.stage2.ch4_kmol == 0.0


# ------------------------------------------------------------------ 3. coherencia con Pisco
def test_co2_minimo_bajo_lo_reportado(funsur):
    assert tin_heat(funsur).co2_t < PISCO_SCOPE1_2025_T


# ------------------------------------------------------------------ guardas a mano (mutaciones)
def test_combustion_a_mano_con_el_nitrogeno():
    # A 1.200 °C el calor útil es el PCI menos lo que se llevan CO2, 2 H2O y 7,52 N2 calientes.
    def sensible(formula: str, t: float) -> float:
        record = T.by_key(formula, "g")
        return record.enthalpy(t) - record.enthalpy(298.15)

    t = 1473.15
    hot = sensible("CO2", t) + 2 * sensible("H2O", t) + 2 * 79 / 21 * sensible("N2", t)
    assert combustion_mj_per_kmol(1200.0) == pytest.approx(combustion_mj_per_kmol(25.0) - hot,
                                                           rel=1e-12)  # fmt: skip


def test_co2_y_calcinacion_a_mano(funsur):
    h = tin_heat(funsur)
    c_kmol = (funsur.stage1.carbon["C"] + funsur.stage2.carbon["C"]) * 1000 / 12.011
    caco3_kmol = funsur.limestone_t * 1000 / 100.087
    assert h.co2_process_t == pytest.approx((c_kmol + caco3_kmol) * 44.009 / 1000, rel=1e-4)
    # La salida de la etapa 1 incluye el CO2 de la calcinación, caliente.
    co2 = {"CO2": funsur.limestone_t / 100.087 * 44.009}
    s1 = funsur.stage1
    hand = (enthalpy_mj(s1.metal, 1200.0) + enthalpy_mj(s1.slag, 1200.0)
            + enthalpy_mj({k: v for k, v in s1.carbon.items() if k != "C"}, 1200.0)
            + enthalpy_mj(co2, 1200.0) + enthalpy_mj({"SnO": s1.fume_sno_t}, 1200.0))  # fmt: skip
    assert h.stage1.h_out_mj == pytest.approx(hand, rel=1e-6)


def test_cada_etapa_su_perdida(funsur):
    h = tin_heat(funsur, loss1_mj=3e4, loss2_mj=7e3)
    assert h.stage1.loss_mj == 3e4 and h.stage2.loss_mj == 7e3
