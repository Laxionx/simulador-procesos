"""Conversión Peirce-Smith y horno de ánodos (fase 4b). Tolerancias fijadas ANTES de correr
(brief aprobado el 12-10):

1. Datos: JANAF vs USGS B2131 a ±2 % para Cu líquido y magnetita (el Cu2O ya está en
   test_fusion).
2. Guardas: cierre por elemento, metas cumplidas, sentido físico, un caso a mano y cargas
   imposibles que avisan.
3. Rönnskär, carga 860 (Lennartsson 2013): aire de los soplados a escoria y del soplado a cobre
   ±10 %, escoria de los soplados a escoria (181 t) ±15 % y blíster (322 t) ±10 %. Como el fin
   del primer soplado a escoria no se publica, los dos soplados a escoria van juntos: 2
   comparaciones de aire en vez de 3 (declarado antes de correr).
4. Flin Flon (Kyllo 1995): escoria de los soplados a escoria por balance de Fe ±20 %, 3 cargas.
5. Corte: el modelo FALLA si quedan fuera más de 3 de las 7 comparaciones.
6. Horno de ánodos: NO validado contra planta; solo cierre, casos a mano y sentido físico.
"""

from __future__ import annotations

import runpy
from pathlib import Path
from statistics import mean

import pytest

from procesos.anodos import refine
from procesos.conversion import (
    ConversionError,
    Feed,
    carry_over,
    copper_blow,
    matte,
    oxide_slag,
    skimmed_slag_from_iron,
    slag_blow,
)
from procesos.conversion_datos import (
    FLINFLON,
    FLINFLON_ASSAYS,
    FLINFLON_FLUX,
    ILO_MAGNETITE_FE,
    RONNSKAR_AIR_COPPER_BLOW,
    RONNSKAR_AIR_SLAG_BLOWS,
    RONNSKAR_BLISTER,
    RONNSKAR_CB_SLAG,
    RONNSKAR_CB_TEMP_K,
    RONNSKAR_COLD_COPPER_BLOW_T,
    RONNSKAR_COLD_SLAG_BLOWS_T,
    RONNSKAR_EFF_COPPER,
    RONNSKAR_EFF_SLAG,
    RONNSKAR_FLUX_T,
    RONNSKAR_MATTE,
    RONNSKAR_O2_COPPER_BLOW,
    RONNSKAR_O2_SLAG_BLOWS,
    RONNSKAR_RECYCLED_SLAG_T,
    RONNSKAR_SKIMMED,
    RONNSKAR_SLAG,
    RONNSKAR_WHITE_METAL,
)
from procesos.thermo import MaierKelley
from procesos.thermo_data import DEFAULT_THERMO

T = DEFAULT_THERMO
NM3 = 22.414


# ------------------------------------------------------------------ 1. datos
def test_cobre_liquido_janaf_vs_usgs():
    solid = MaierKelley(298.15, 1357.8, 60.84, -2.875e-2, 3.331e5, -567.1, 1.42e-5)
    usgs = solid.dh(1357.8) + 13.14 + 0.03280 * (1450.0 - 1357.8)  # fusión y Cp del líquido
    assert T.by_key("Cu", "l").enthalpy(1450.0) == pytest.approx(usgs, rel=0.02)


@pytest.mark.parametrize(("temp_k", "usgs_h_over_t"), [(1000.0, 148.81), (1500.0, 165.99)])
def test_magnetita_janaf_vs_usgs(temp_k, usgs_h_over_t):
    record = T.by_key("Fe3O4", "s")
    janaf = record.enthalpy(temp_k) - record.dfh298
    assert janaf == pytest.approx(usgs_h_over_t * temp_k / 1000.0, rel=0.02)


@pytest.mark.parametrize(
    ("key", "temps", "cp"),
    [(("Cu", "l"), (1400, 1500, 1600, 1700, 1800, 1900, 2000), 32.844),
     (("Fe3O4", "s"), (1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800), 200.832)],
    ids=["Cu líquido", "magnetita"],
)  # fmt: skip
def test_tabla_janaf_bien_copiada(key, temps, cp):
    # Guarda de transcripción: la pendiente de la columna H-H298 debe dar la columna Cp de la
    # misma tabla, que en esos tramos es constante.
    record = T.by_key(*key)
    for t in temps:
        assert record.cp(t - 20.0) == pytest.approx(cp, abs=0.02), t  # dentro del tramo


# ------------------------------------------------------------------ Rönnskär
def _ronnskar_slag_blow(magnetite_fe: float = ILO_MAGNETITE_FE, fe3o4_pct: float = 0.0):
    feeds = [matte(f"mata {i}", t, cu, fe3o4_pct) for i, (t, cu) in enumerate(RONNSKAR_MATTE)]
    feeds += [
        Feed("fundente", {"SiO2": RONNSKAR_FLUX_T}),
        oxide_slag(
            "escoria de cobre",
            RONNSKAR_RECYCLED_SLAG_T,
            RONNSKAR_CB_SLAG["Cu"],
            RONNSKAR_CB_SLAG["Fe"],
            RONNSKAR_CB_SLAG["SiO2"],
        ),  # fmt: skip
        Feed("carga fría", {"Cu": RONNSKAR_COLD_SLAG_BLOWS_T}),
    ]
    return slag_blow(
        feeds,
        end_fe_pct=RONNSKAR_WHITE_METAL["Fe"],
        slag_cu_pct=RONNSKAR_SLAG["Cu"],
        magnetite_fe=magnetite_fe,
        efficiency=RONNSKAR_EFF_SLAG,
        pure_o2_nm3=RONNSKAR_O2_SLAG_BLOWS,
    )


def _ronnskar_copper_blow(sb=None):
    sb = sb or _ronnskar_slag_blow()
    feeds = [
        carry_over(sb, "metal", 1.0, 1200.0, "metal blanco"),
        carry_over(sb, "escoria", 1 - RONNSKAR_SKIMMED, 1200.0, "escoria que queda"),
        Feed("carga fría", {"Cu": RONNSKAR_COLD_COPPER_BLOW_T}),
    ]
    return copper_blow(
        feeds,
        blister_s_pct=RONNSKAR_BLISTER["S"],
        slag_cu_pct=RONNSKAR_CB_SLAG["Cu"],
        efficiency=RONNSKAR_EFF_COPPER,
        pure_o2_nm3=RONNSKAR_O2_COPPER_BLOW,
        bath_c=RONNSKAR_CB_TEMP_K - 273.15,
    )


# ------------------------------------------------------------------ 2. guardas
@pytest.mark.parametrize("stage", [_ronnskar_slag_blow, _ronnskar_copper_blow], ids=["SB", "CB"])
def test_cierre_por_elemento(stage):
    inn, out = stage().elements()
    for el in inn:
        assert out[el] == pytest.approx(inn[el], abs=1e-9), el


def test_metas_cumplidas():
    sb = _ronnskar_slag_blow()
    assert sb.percent("metal", "Fe") == pytest.approx(RONNSKAR_WHITE_METAL["Fe"], abs=1e-9)
    assert sb.percent("escoria", "Cu") == pytest.approx(RONNSKAR_SLAG["Cu"], abs=1e-9)
    fe3o4, feo = sb.products["escoria:Fe3O4"], sb.products["escoria:FeO"]
    assert 3 * fe3o4 / (3 * fe3o4 + feo) == pytest.approx(ILO_MAGNETITE_FE, abs=1e-12)
    cb = _ronnskar_copper_blow(sb)
    assert cb.percent("blister", "S") == pytest.approx(RONNSKAR_BLISTER["S"], abs=1e-12)
    assert cb.percent("escoria", "Cu") == pytest.approx(RONNSKAR_CB_SLAG["Cu"], abs=1e-9)


def test_soplado_a_escoria_a_mano():
    # 8 t de FeS + 8 t de Cu2S, sin Cu en escoria ni magnetita, hasta Fe 0: el O2 es 1,5 por
    # FeS (2 FeS + 3 O2 → 2 FeO + 2 SO2) y el aire, O2 / eficiencia / 0,21.
    feeds = [Feed("mata", {"FeS": 8.0, "Cu2S": 8.0})]
    sb = slag_blow(feeds, end_fe_pct=0.0, slag_cu_pct=0.0, magnetite_fe=0.0, efficiency=0.8)
    fes_kmol = 8000.0 / (55.845 + 32.06)
    assert sb.o2_reacted == pytest.approx(1.5 * fes_kmol, rel=1e-9)
    assert sb.air_nm3 == pytest.approx(1.5 * fes_kmol / 0.8 * NM3 / 0.21, rel=1e-9)
    assert sb.products["gas:SO2"] == pytest.approx(fes_kmol, rel=1e-9)


def test_soplado_a_cobre_a_mano():
    # Cu2S puro a cobre sin S: Cu2S + O2 → 2 Cu + SO2.
    feeds = [Feed("metal blanco", {"Cu2S": 159.152}, 1200.0)]
    cb = copper_blow(feeds, blister_s_pct=0.0, slag_cu_pct=0.0, efficiency=1.0)
    assert cb.o2_reacted == pytest.approx(1000.0, rel=1e-6)
    assert cb.mass_t("blister") == pytest.approx(2 * 63.546, rel=1e-6)


def test_carga_fria_que_cabe_es_coherente():
    # Si se agrega justo el cobre frío que el sobrante alcanza a fundir con una pérdida dada,
    # la nueva etapa cierra el calor con esa misma pérdida.
    args = {"blister_s_pct": 0.0, "slag_cu_pct": 0.0, "efficiency": 0.9, "bath_c": 1200.0}
    hot = Feed("metal blanco", {"Cu2S": 100.0}, 1200.0)
    cb = copper_blow([hot], **args)
    h_in, h_out = cb.heat_balance()
    loss = 0.3 * (h_in - h_out)
    extra = cb.cold_copper_capacity_t(loss)
    assert extra > 0
    more = copper_blow([hot, Feed("frío", {"Cu": extra})], **args)
    assert more.air_nm3 == pytest.approx(cb.air_nm3, rel=1e-12)  # el Cu frío no pide O2
    h_in2, h_out2 = more.heat_balance()
    assert h_in2 - h_out2 == pytest.approx(loss, rel=1e-9)


def test_sentido_fisico():
    base = _ronnskar_slag_blow()
    assert _ronnskar_slag_blow(magnetite_fe=0.4).air_nm3 > base.air_nm3  # Fe3O4 pide más O2
    assert _ronnskar_slag_blow(fe3o4_pct=3.0).air_nm3 < base.air_nm3  # la mata trae O
    more_cold = Feed("más frío", {"Cu": 20.0})
    sb2 = slag_blow((*base.feeds, more_cold), end_fe_pct=0.4, slag_cu_pct=6.1,
                    magnetite_fe=ILO_MAGNETITE_FE, efficiency=RONNSKAR_EFF_SLAG,
                    pure_o2_nm3=RONNSKAR_O2_SLAG_BLOWS)  # fmt: skip
    # El Cu metálico no se oxida; como el metal blanco crece, al mismo 0,4 % de Fe queda algo
    # más de FeS sin oxidar y el O2 baja apenas.
    assert 0 < base.o2_reacted - sb2.o2_reacted < 0.005 * base.o2_reacted
    assert sb2.mass_t("metal") > base.mass_t("metal") + 20.0


def test_cargas_imposibles_avisan():
    with pytest.raises(ConversionError, match="ley"):
        matte("mata", 100.0, 85.0)
    with pytest.raises(ConversionError, match="sin modelo"):
        Feed("x", {"PbS": 1.0})
    with pytest.raises(ConversionError, match="negativas"):
        Feed("x", {"FeS": -1.0})
    with pytest.raises(ConversionError, match="eficiencia"):
        slag_blow([matte("m", 100, 60)], end_fe_pct=0.4, slag_cu_pct=5, magnetite_fe=0.2,
                  efficiency=0.0)  # fmt: skip
    with pytest.raises(ConversionError, match="imposible"):  # pide más Fe del que trae la mata
        slag_blow([matte("m", 100, 70)], end_fe_pct=15.0, slag_cu_pct=5, magnetite_fe=0.2,
                  efficiency=0.8)  # fmt: skip


def test_escoria_por_hierro_a_mano():
    # 100 t de mata con 40 % Cu y 30 % Fe; mata final 75 % Cu y 1 % Fe; escoria 5 % Cu, 40 % Fe.
    # Cu: 0,75 M + 0,05 E = 40 ; Fe: 0,01 M + 0,40 E = 30  →  E por Cramer, más 3 t iniciales.
    slag = skimmed_slag_from_iron([(100.0, 40.0, 30.0)], 75.0, 1.0, 5.0, 40.0, initial_slag_t=3.0)
    det = 0.75 * 0.40 - 0.05 * 0.01
    assert slag == pytest.approx((0.75 * 30.0 - 0.01 * 40.0) / det + 3.0, rel=1e-12)


# ------------------------------------------------------------------ 3-5. contra planta
SB_MATA = pytest.mark.xfail(strict=True, reason="mata Cu2S+FeS: sin su análisis de Fe y S")
CU_NO_CIERRA = pytest.mark.xfail(strict=True, reason="la carga publicada no cierra en Cu (−13 %)")


def _flinflon(charge: str) -> float:
    d = FLINFLON[charge]
    a = FLINFLON_ASSAYS
    feeds = [(t, a[k][0], a[k][1]) for t, k in d["mata"]]
    feeds += [(d["fundente_t"], 0.0, FLINFLON_FLUX["Fe"]), (d["chatarra_t"], 100.0, 0.0)]
    if d["escoria_cobre_t"]:
        copper_slag = a["escoria de cobre"]
        feeds.append((d["escoria_cobre_t"], copper_slag[0], copper_slag[1]))
    end = a[d["final"]]
    return skimmed_slag_from_iron(feeds, end[0], end[1], mean(d["escoria_cu"]),
                                  mean(d["escoria_fe"]), d["escoria_inicial_t"])  # fmt: skip


def _comparisons() -> dict[str, tuple[float, float, float]]:
    """nombre: (modelo, planta, tolerancia relativa)."""
    sb = _ronnskar_slag_blow()
    cb = _ronnskar_copper_blow(sb)
    out = {
        "Rönnskär aire soplados a escoria": (sb.air_nm3, RONNSKAR_AIR_SLAG_BLOWS, 0.10),
        "Rönnskär aire soplado a cobre": (cb.air_nm3, RONNSKAR_AIR_COPPER_BLOW, 0.10),
        "Rönnskär escoria": (sb.mass_t("escoria"), RONNSKAR_SLAG["t"], 0.15),
        "Rönnskär blíster": (cb.mass_t("blister"), RONNSKAR_BLISTER["t"], 0.10),
    }
    for charge, d in FLINFLON.items():
        out[f"Flin Flon {charge} escoria"] = (_flinflon(charge), d["escoriado_t"], 0.20)
    return out


FAILS = {"Rönnskär aire soplados a escoria": SB_MATA, "Rönnskär escoria": SB_MATA,
         "Rönnskär blíster": CU_NO_CIERRA}  # fmt: skip
NAMES = list(_comparisons())


@pytest.mark.parametrize(
    "name", [pytest.param(n, marks=FAILS.get(n, ()), id=n) for n in NAMES]
)  # fmt: skip
def test_contra_planta(name):
    model, plant, tol = _comparisons()[name]
    assert model == pytest.approx(plant, rel=tol)


def test_corte():
    outside = [n for n, (m, p, tol) in _comparisons().items() if abs(m - p) > tol * p]
    assert len(outside) <= 3, outside


# ------------------------------------------------------------------ 6. horno de ánodos
def test_anodos_cierra():
    r = refine(368.3, 0.023, 0.05, anode_s_pct=0.003)
    for el, diff in r.elements(0.023, 0.05).items():
        assert diff == pytest.approx(0.0, abs=1e-6), el
    assert r.anode_cu_pct == pytest.approx(100 - 0.12 - 0.003)


def test_anodos_a_mano():
    # 100 t sin S ni O; oxidar a 0,5 % O y reducir a 0 %: el Cu (100 t) no cambia.
    r = refine(100.0, 0.0, 0.0, anode_s_pct=0.0, o_oxidized_pct=0.5, anode_o_pct=0.0)
    o_kg = 100_000.0 / (1 - 0.005) * 0.005
    assert r.o2_oxidation_kmol == pytest.approx(o_kg / 15.999 / 2, rel=1e-9)
    assert r.ch4_min_kg == pytest.approx(o_kg / 15.999 / 4 * 16.043, rel=1e-6)
    assert r.ch4_max_kg == pytest.approx(4 * r.ch4_min_kg, rel=1e-12)
    assert r.anode_t == pytest.approx(100.0, rel=1e-12)


def test_anodos_sentido_y_avisos():
    lean = refine(100.0, 0.02, anode_s_pct=0.003, anode_o_pct=0.2)
    rich = refine(100.0, 0.02, anode_s_pct=0.003, anode_o_pct=0.1)
    assert rich.ch4_min_kg > lean.ch4_min_kg and rich.anode_cu_pct > lean.anode_cu_pct
    assert refine(100.0, 0.02, anode_s_pct=0.003, o2_efficiency=0.5).air_oxidation_nm3 == (
        pytest.approx(2 * refine(100.0, 0.02, anode_s_pct=0.003).air_oxidation_nm3)
    )
    for bad in ({"anode_s_pct": 0.05}, {"anode_s_pct": 0.0, "anode_o_pct": 1.0},
                {"anode_s_pct": 0.0, "o2_efficiency": 0.0}):  # fmt: skip
        with pytest.raises(ValueError):
            refine(100.0, 0.02, **bad)


def test_ejemplo_ilo_corre(capsys):
    runpy.run_path(str(Path(__file__).parents[1] / "ejemplos" / "conversion_ilo.py"))
    assert "ánodo" in capsys.readouterr().out


# ------------------------------------------------------------------ guardas a mano (mutaciones)
def test_aire_descuenta_el_oxigeno_puro():
    feeds = [Feed("mata", {"FeS": 8.0, "Cu2S": 8.0})]
    args = {"end_fe_pct": 0.0, "slag_cu_pct": 0.0, "magnetite_fe": 0.0, "efficiency": 0.8}
    plain = slag_blow(feeds, **args)
    enriched = slag_blow(feeds, pure_o2_nm3=500.0, **args)
    assert plain.air_nm3 - enriched.air_nm3 == pytest.approx(500.0 / 0.21, rel=1e-12)


def test_balance_de_calor_a_mano():
    # Cu2S + O2 → 2 Cu + SO2 a 1.200 °C con 50 % de eficiencia: el O2 que no reacciona y el N2
    # salen calientes; el aire entra a 25 °C.
    cb = copper_blow([Feed("metal blanco", {"Cu2S": 159.152}, 1200.0)], blister_s_pct=0.0,
                     slag_cu_pct=0.0, efficiency=0.5, bath_c=1200.0)  # fmt: skip
    t = 1473.15
    n = 1000.0
    o2_blown, n2 = 2 * n, 2 * n * 0.79 / 0.21
    h = {k: T.by_key(*k).enthalpy(t) for k in [("Cu2S", "l"), ("Cu", "l"), ("SO2", "g"),
                                                 ("O2", "g"), ("N2", "g")]}  # fmt: skip
    h_in = n * h[("Cu2S", "l")] + o2_blown * T.by_key("O2", "g").enthalpy(298.15)
    h_in += n2 * T.by_key("N2", "g").enthalpy(298.15)
    h_out = 2 * n * h[("Cu", "l")] + n * h[("SO2", "g")] + (o2_blown - n) * h[("O2", "g")]
    h_out += n2 * h[("N2", "g")]
    got_in, got_out = cb.heat_balance()
    assert got_in == pytest.approx(h_in, rel=1e-6)
    assert got_out == pytest.approx(h_out, rel=1e-6)


def test_fundente_para_llegar_a_la_silice():
    feeds = [matte("mata", 100.0, 62.0), Feed("arena en la carga", {"SiO2": 1.0})]
    sb = slag_blow(feeds, end_fe_pct=0.4, slag_cu_pct=2.85, magnetite_fe=ILO_MAGNETITE_FE,
                   efficiency=0.62, slag_sio2_pct=25.52)  # fmt: skip
    sio2 = sb.products["escoria:SiO2"] * 60.083 / 1000
    assert 100 * sio2 / sb.mass_t("escoria") == pytest.approx(25.52, abs=1e-9)
    flux = next(f for f in sb.feeds if f.name == "fundente").tonnes["SiO2"]
    assert flux == pytest.approx(sio2 - 1.0, rel=1e-9)
    inn, out = sb.elements()
    for el in inn:
        assert out[el] == pytest.approx(inn[el], abs=1e-9), el


def test_escoria_reciclada_y_mata_reproducen_su_analisis():
    slag = oxide_slag("escoria", 10.0, 28.3, 20.4, 14.1)
    kmol = slag.kmol()
    assert 2 * kmol["Cu2O"] * 63.546 / 100 == pytest.approx(28.3, rel=1e-9)  # kg en 10 t → %
    assert 3 * kmol["Fe3O4"] * 55.845 / 100 == pytest.approx(20.4, rel=1e-9)
    assert slag.tonnes["SiO2"] == pytest.approx(1.41) and sum(slag.tonnes.values()) == 10.0
    m = matte("mata", 100.0, 59.0, fe3o4_pct=3.0)
    assert 2 * m.kmol()["Cu2S"] * 63.546 / 1000 == pytest.approx(59.0, rel=1e-9)
    assert m.tonnes["Fe3O4"] == pytest.approx(3.0)
