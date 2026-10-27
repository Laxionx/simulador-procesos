"""Pestañas de equipo de «Planta completa»: el panel «Estado de la operación» (sus chequeos pueden
fallar), «Prueba esto» (cada experimento hace lo que dice su texto, y su botón lo pone en la barra
lateral), los casos publicados (los datos de entrada coinciden con la fuente y el Δ % es el que
documenta `docs/fusion.md`) y los rótulos de lo ilustrativo en los esquemas."""

import dataclasses
import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "app" / "streamlit_app.py")
sys.path.insert(0, str(ROOT / "app"))

import calculo  # noqa: E402
import calculo_piro as cp  # noqa: E402
import casos  # noqa: E402
import controles  # noqa: E402
import convertidor_svg  # noqa: E402
import estado_planta as ep  # noqa: E402
import ew_svg  # noqa: E402
import flotacion_svg  # noqa: E402
import fusion_svg  # noqa: E402
import i18n  # noqa: E402
import pruebas_planta as pp  # noqa: E402
from controles import CONV, EW, FLASH, FLOT  # noqa: E402
from dibujo import es  # noqa: E402
from test_flotacion import BANCOS, TABLA_3  # noqa: E402

from procesos.fusion_datos import INDUSTRIAL  # noqa: E402

EQUIPOS = (FLOT, FLASH, CONV, EW)
ENTORNO = {  # (rango de cada magnitud del ejemplo que el texto de «Prueba esto» da por supuesto)
    FLOT: {"cells": 9, "tau": 4.1, "gangue": 5.0},
    FLASH: {"f_grade": 63.7, "f_sio2": 29.0, "f_loss": 205.5},
    CONV: {"c_grade": 62.0, "c_eff_slag": 62.0, "c_bath": 1200.0},
    EW: {"j": 300.0, "eff": 92.0, "temp": 50.0},
}


def run(lang: str = "es") -> AppTest:
    at = AppTest.from_file(APP, default_timeout=300)
    at.query_params["lang"] = lang
    return at.run()


def lines(at: AppTest) -> list[str]:
    return [m.value for m in at.markdown]


def badges(at: AppTest, color: str) -> list[str]:
    return [m for m in lines(at) if m.startswith(f":{color}-badge[")]


def widget(at: AppTest, key: str):
    return next(w for w in [*at.sidebar.number_input, *at.sidebar.slider,
                            *at.sidebar.selectbox] if w.key == key)  # fmt: skip


# ------------------------------------------------------------------ el ejemplo y el panel
@pytest.mark.parametrize("equipo", EQUIPOS)
def test_el_ejemplo_de_cada_equipo_esta_en_rango(equipo):
    with i18n.use("es"):
        medicion = pp.medir(equipo)
    assert medicion.nivel == "ok", [(f.nivel, f.texto) for f in medicion.filas if f.nivel != "ok"]


def test_los_datos_de_ejemplo_que_suponen_los_experimentos_son_los_de_la_barra_lateral():
    ejemplo = controles.valores_ejemplo()
    for equipo, valores in ENTORNO.items():
        for clave, valor in valores.items():
            assert ejemplo[clave] == valor, (equipo, clave)


def test_los_chequeos_de_definicion_fallan_si_el_balance_no_cierra():
    """Cada chequeo de cierre tiene que poder fallar: se rompe el resultado a propósito."""
    with i18n.use("es"):
        flot = calculo.run_flotation(calculo.FlotationParams())
        roto = dataclasses.replace(flot, cu_t_h=tuple(1.01 * x for x in flot.cu_t_h))
        assert ep.filas_flotacion(roto)[0].nivel == "mal"
        pasa_r_inf = dataclasses.replace(flot, recoveries={**flot.recoveries, "CuFeS2": 0.99})
        assert ep.filas_flotacion(pasa_r_inf)[1].nivel == "mal"

        flash = cp.run_flash(cp.FlashParams())
        sin_calor = dataclasses.replace(
            flash, result=dataclasses.replace(flash.result, heat_loss_mj_t=300.0)
        )
        assert ep.filas_flash(sin_calor)[1].nivel == "mal"  # el calor ya no cierra
        otra_meta = dataclasses.replace(flash, params=dataclasses.replace(
            flash.params, matte_grade=65.0))  # fmt: skip
        assert ep.filas_flash(otra_meta)[2].nivel == "mal"  # la mata no sale con esa ley

        conv = cp.run_converter(cp.ConverterParams())
        estados = list(conv.states)
        estados[1] = dataclasses.replace(estados[1], lower_t=estados[1].lower_t + 1.0)
        filas = ep.filas_convertidor(dataclasses.replace(conv, states=tuple(estados)))
        assert filas[1].nivel == "mal"  # la masa de un soplado no cierra

        ew = calculo.run_ew(calculo.EWParams())
        filas = ep.filas_ew(dataclasses.replace(ew, cathode_kg=1.02 * ew.cathode_kg))
        assert [f.nivel for f in filas if "Faraday" in f.texto] == ["mal"]


def test_los_avisos_del_modelo_de_electroobtencion_pasan_al_panel_tal_cual():
    view = calculo.run_ew(calculo.EWParams(temp_c=35.0))
    assert view.warnings
    with i18n.use("es"):
        avisos = [f for f in ep.filas_ew(view) if f.nivel == "aviso"]
    assert [f.texto for f in avisos] == list(view.warnings)
    with i18n.use("en"):
        en = [f.texto for f in ep.filas_ew(view) if f.nivel == "aviso"]
    assert en and "extrapolation" in en[0]


@pytest.mark.parametrize(
    ("params", "nivel"),
    [
        (cp.FlashParams(matte_grade=66.6), "ok"),  # el tope de lo publicado cuenta como dentro
        (cp.FlashParams(matte_grade=66.7), "aviso"),
        (cp.FlashParams(slag_sio2=27.4), "aviso"),
        (cp.FlashParams(heat_loss_mj_t=219.0), "aviso"),
        (cp.FlashParams(products_c=1250.0), "aviso"),  # los coeficientes son de 1.300 °C
    ],
)
def test_la_cobertura_del_horno_sale_de_la_tabla_13(params, nivel):
    with i18n.use("es"):
        filas = ep.filas_flash(cp.run_flash(params))
    assert max((f.nivel for f in filas), key=("ok", "aviso", "mal").index) == nivel


def test_las_eficiencias_del_convertidor_se_comparan_con_flin_flon():
    with i18n.use("es"):
        for eff, esperado in ((0.62, "ok"), (0.55, "ok"), (0.68, "ok"), (0.54, "aviso"),
                              (0.69, "aviso")):  # fmt: skip
            view = cp.run_converter(cp.ConverterParams(eff_slag=eff))
            assert ep.filas_convertidor(view)[2].nivel == esperado, eff
        for eff, esperado in ((0.72, "ok"), (0.82, "ok"), (0.71, "aviso"), (0.83, "aviso")):
            view = cp.run_converter(cp.ConverterParams(eff_copper=eff))
            assert ep.filas_convertidor(view)[2].nivel == esperado, eff


# ------------------------------------------------------------------ Prueba esto
def _ids(e: pp.Experimento) -> str:
    return f"{pp.SLUG[e.equipo]}_{e.clave}"


@pytest.mark.parametrize("exp", pp.EXPERIMENTOS, ids=_ids)
def test_cada_experimento_hace_lo_que_dice_su_texto(exp):
    with i18n.use("es"):
        base, nuevo = pp.medir(exp.equipo), pp.medir(exp.equipo, exp.cambios)
    for magnitud, signo in exp.direcciones.items():
        antes, despues = base.magnitudes[magnitud], nuevo.magnitudes[magnitud]
        if signo == 0:
            # «no cambia»: a 1e-6 (el voltaje usa el electrolito que sale, que varía ~1e-8)
            assert despues == pytest.approx(antes, rel=1e-6), (exp.clave, magnitud)
        else:
            assert (despues - antes) * signo > 0, (exp.clave, magnitud)
    assert nuevo.nivel == exp.nivel, [(f.nivel, f.texto) for f in nuevo.filas]


def test_los_experimentos_declaran_cambios_con_los_valores_del_ejemplo_distintos():
    ejemplo = controles.valores_ejemplo()
    assert 2 <= len([e for e in pp.EXPERIMENTOS if e.equipo == FLOT]) <= 4
    for equipo in EQUIPOS:
        assert 2 <= len([e for e in pp.EXPERIMENTOS if e.equipo == equipo]) <= 4, equipo
    for e in pp.EXPERIMENTOS:
        assert e.cambios and all(ejemplo[c] != v for c, v in e.cambios.items()), e.clave


def test_los_numeros_de_los_experimentos_que_el_texto_da_por_cuantitativos():
    pares = {(e.equipo, e.clave): (a, b) for e, a, b in
             [x for eq in EQUIPOS for x in pp.pares(eq)]}  # fmt: skip
    a, b = pares[(FLOT, "saturado")]  # «solo X puntos más»: casi no cambia
    assert 0 < b.magnitudes["rec"] - a.magnitudes["rec"] < 0.1
    a, b = pares[
        (FLOT, "celdas")
    ]  # la ganga es la misma: el concentrado pierde lo que pierde el Cu
    cu_perdido = b.magnitudes["relave"] - a.magnitudes["relave"]
    assert a.magnitudes["conc"] - b.magnitudes["conc"] == pytest.approx(cu_perdido, rel=1e-6)
    a, b = pares[(FLOT, "ganga")]  # dilución: el Cu del concentrado no cambia
    cu_a = a.magnitudes["ley"] * a.magnitudes["conc"]
    assert b.magnitudes["ley"] * b.magnitudes["conc"] == pytest.approx(cu_a, rel=1e-9)
    a, b = pares[(EW, "corriente")]  # Faraday: el cátodo crece como la corriente
    assert b.magnitudes["kg"] / a.magnitudes["kg"] == pytest.approx(400.0 / 300.0, rel=1e-9)
    a, b = pares[(EW, "eficiencia")]  # kWh/t ∝ 1/eficiencia, con el mismo voltaje
    assert b.magnitudes["kwh"] / a.magnitudes["kwh"] == pytest.approx(92.0 / 85.0, rel=1e-6)
    a, b = pares[(FLASH, "silice")]  # 30 % es el tope publicado: sigue en rango
    assert b.nivel == "ok" and b.magnitudes["fund"] > a.magnitudes["fund"]
    a, b = pares[(CONV, "eficiencia")]  # la eficiencia solo cambia el aire
    assert b.magnitudes["blis"] == pytest.approx(a.magnitudes["blis"], rel=1e-12)


@pytest.mark.parametrize("lang", ["es", "en"])
def test_el_texto_de_cada_experimento_se_arma_en_los_dos_idiomas(lang):
    with i18n.use(lang):
        for equipo in EQUIPOS:
            for prueba in pp.pruebas_de(equipo):
                assert prueba.titulo and "{" not in prueba.texto and "}" not in prueba.texto
                assert all(k.startswith("dato_") for k in prueba.cambios)


def test_las_cifras_del_texto_vienen_del_modelo_en_vivo():
    with i18n.use("es"):
        (prueba,) = [p for p in pp.pruebas_de(EW) if p.clave == "corriente"]
        base, nuevo = pp.medir(EW), pp.medir(EW, {"j": 400.0})
    assert es(base.magnitudes["kg"], 1) in prueba.texto
    assert es(nuevo.magnitudes["kg"], 1) in prueba.texto
    assert es(nuevo.magnitudes["kwh"], 0) in prueba.texto


# ------------------------------------------------------------------ casos publicados
def test_los_casos_de_flotacion_son_los_de_la_tabla_3_y_las_tablas_b1_b2():
    for caso in casos.CASOS_FLOT:
        tau, cells, medida, _, _ = BANCOS[caso.clave]
        r_inf, k = TABLA_3[caso.clave]["primer_orden"]
        assert (caso.tau_min, caso.r_inf_pct, caso.k) == (tau, r_inf, k)
        assert list(caso.celdas_medidas) == cells and list(caso.medidas_pct) == medida
        assert caso.celdas == max(cells)  # el banco entero


def test_el_caso_a_de_flotacion_es_el_ejemplo_y_el_b_no():
    ejemplo = controles.armar_params(controles.valores_ejemplo())[0]
    assert casos.caso_flot_activo(ejemplo).clave == "A"
    otro = dataclasses.replace(ejemplo, k=0.36)
    assert casos.caso_flot_activo(otro) is None


@pytest.mark.parametrize("caso", casos.CASOS_FLOT, ids=lambda c: c.clave)
def test_el_modelo_queda_cerca_de_lo_medido_en_cada_banco(caso):
    params = controles.armar_params({**controles.valores_ejemplo(),
                                     **{k.removeprefix("dato_"): v for k, v in caso.cambios.items()}
                                     })[0]  # fmt: skip
    assert casos.caso_flot_activo(params) is caso
    filas = casos.comparacion_flot(calculo.run_flotation(params), caso)
    assert casos.rmse_flot(filas) < 1.4  # puntos: A 0,68 y B 1,32 (docs/flotacion.md, V2)
    assert max(abs(mod - med) for _, mod, med in filas) < 2.5


def test_los_casos_del_horno_son_la_tabla_13_y_su_comparacion_la_de_docs_fusion():
    assert [c.blend for c in casos.CASOS_FLASH] == [1, 2, 3, 4]
    esperado = {  # docs/fusion.md, «Contra la operación de Atlantic Copper»: OC, O₂ %, fundente
        1: (False, True, True), 2: (False, True, False),
        3: (True, False, False), 4: (True, True, True),
    }  # fmt: skip
    for caso, nombre in zip(casos.CASOS_FLASH, INDUSTRIAL, strict=True):
        oc, o2, fund, ley, sio2, perdida = INDUSTRIAL[nombre]
        assert (caso.oc_nm3_t, caso.o2_pct, caso.fundente_pct) == (oc, o2, fund)
        assert (caso.ley_mata, caso.sio2_escoria, caso.perdida_mj_t) == (ley, sio2, perdida)
        params = cp.FlashParams(caso.blend, ley, sio2, perdida)
        assert casos.caso_flash_activo(params) is caso
        filas = casos.comparacion_flash(cp.run_flash(params), caso)
        assert tuple(f.dentro for f in filas) == esperado[caso.blend], caso.blend
    total = sum(
        f.dentro
        for c in casos.CASOS_FLASH
        for f in casos.comparacion_flash(
            cp.run_flash(cp.FlashParams(c.blend, c.ley_mata, c.sio2_escoria, c.perdida_mj_t)), c
        )
    )
    assert total == 7  # «7 de 12 dentro»


def test_el_delta_del_horno_es_el_relativo_a_la_planta():
    caso = casos.CASOS_FLASH[0]
    view = cp.run_flash(cp.FlashParams(1, caso.ley_mata, caso.sio2_escoria, caso.perdida_mj_t))
    oc = casos.comparacion_flash(view, caso)[0]
    assert oc.delta_pct == pytest.approx(100 * (161.77 - 186.0) / 186.0, abs=0.01)  # −13,0 %
    assert oc.delta_puntos == pytest.approx(161.77 - 186.0, abs=0.01)


# ------------------------------------------------------------------ rótulos de lo ilustrativo
@pytest.mark.parametrize(("lang", "frase"), [("es", "solo cambia el dibujo"),
                                             ("en", "drawing only")])  # fmt: skip
def test_cada_esquema_rotula_lo_ilustrativo(lang, frase):
    views = (
        calculo.run_flotation(calculo.FlotationParams()),
        cp.run_flash(cp.FlashParams()),
        cp.run_converter(cp.ConverterParams()),
        calculo.run_ew(calculo.EWParams()),
    )
    with i18n.use(lang):
        svgs = (flotacion_svg.flotation_svg(views[0]), fusion_svg.flash_svg(views[1]),
                convertidor_svg.converter_svg(views[2]), ew_svg.ew_svg(views[3]))  # fmt: skip
        quietos = (
            flotacion_svg.flotation_svg(views[0], True),
            fusion_svg.flash_svg(views[1], True),
            convertidor_svg.converter_svg(views[2], True),
            ew_svg.ew_svg(views[3], True),
        )
    for movil, quieto in zip(svgs, quietos, strict=True):
        assert frase in movil and frase in quieto


# ------------------------------------------------------------------ la app
@pytest.mark.app
@pytest.mark.parametrize("lang", ["es", "en"])
def test_los_indicadores_tienen_rotulos_cortos_en_filas_de_tres(lang):
    at = run(lang)
    assert not at.exception and not at.error
    assert len(at.metric) == 24
    assert all(len(m.label) <= 24 for m in at.metric), [m.label for m in at.metric]
    assert [len(tab.metric) for tab in at.tabs] == [0, 6, 6, 6, 6]  # dos filas de tres por pestaña


@pytest.mark.app
def test_el_ejemplo_abre_con_todos_los_paneles_en_rango():
    at = run()
    assert not badges(at, "orange") and not badges(at, "red")
    assert sum(m == ":green-badge[En rango] Operación dentro de rango." for m in lines(at)) == 4


@pytest.mark.app
@pytest.mark.parametrize("exp", pp.EXPERIMENTOS, ids=_ids)
def test_el_boton_de_cada_experimento_pone_el_cambio_y_el_panel_lo_refleja(exp):
    at = run()
    next(b for b in at.button if b.key == f"{pp.SLUG[exp.equipo]}_prueba_{exp.clave}").click().run()
    assert not at.exception and not at.error
    for clave, valor in exp.cambios.items():
        assert widget(at, "dato_" + clave).value == valor, clave
    assert not badges(at, "red")
    assert (len(badges(at, "orange")) >= 1) == (exp.nivel == "aviso")
    next(b for b in at.button if b.key == f"{pp.SLUG[exp.equipo]}_prueba_reset").click().run()
    for clave in exp.cambios:
        assert widget(at, "dato_" + clave).value == controles.valores_ejemplo()[clave]
    assert not badges(at, "orange")


@pytest.mark.app
@pytest.mark.parametrize("exp", [e for e in pp.EXPERIMENTOS if e.nivel == "aviso"], ids=_ids)
def test_el_experimento_con_aviso_tambien_funciona_en_ingles(exp):
    at = run("en")
    next(b for b in at.button if b.key == f"{pp.SLUG[exp.equipo]}_prueba_{exp.clave}").click().run()
    assert not at.exception and not at.error
    assert len(badges(at, "orange")) >= 1 and badges(at, "orange")[0].startswith(":orange-badge[W")


@pytest.mark.app
def test_los_indicadores_muestran_los_numeros_del_modelo_tras_aplicar_un_experimento():
    at = run()
    next(b for b in at.button if b.key == "ew_prueba_corriente").click().run()
    valores = {m.label: m.value for m in at.metric}
    with i18n.use("es"):
        nuevo = pp.medir(EW, {"j": 400.0})
    assert valores["Voltaje de celda"] == f"{es(nuevo.magnitudes['v'], 2)} V"
    assert valores["Cobre por cátodo (kg)"] == f"{es(nuevo.magnitudes['kg'], 1)} kg"
    next(b for b in at.button if b.key == "flot_prueba_celdas").click().run()
    valores = {m.label: m.value for m in at.metric}
    with i18n.use("es"):
        nuevo = pp.medir(FLOT, {"cells": 4})
    assert valores["Recuperación de Cu"] == f"{es(nuevo.magnitudes['rec'], 1)} %"


@pytest.mark.app
@pytest.mark.parametrize("lang", ["es", "en"])
def test_los_botones_de_casos_ponen_los_datos_y_muestran_lo_publicado(lang):
    at = run(lang)
    assert len(at.table) == 2  # el ejemplo es el banco A y la mezcla 1: ya se comparan
    next(b for b in at.button if b.key == "flot_caso_B").click().run()
    assert not at.exception and not at.error
    assert (widget(at, "dato_cells").value, widget(at, "dato_tau").value) == (6, 6.4)
    assert (widget(at, "dato_r_inf").value, widget(at, "dato_k").value) == (93.3, 0.27)
    assert len(at.table) == 2
    with i18n.use(lang):
        medido = [es(x, 1) for x in casos.CASOS_FLOT[1].medidas_pct]
        assert list(at.table[0].value.iloc[:, 1]) == medido  # Tabla B2 del banco B
        assert list(at.table[0].value.index) == ["1", "2", "3", "4", "5", "6"]
    next(b for b in at.button if b.key == "flash_caso_3").click().run()
    assert not at.exception and not at.error
    with i18n.use(lang):
        assert widget(at, "dato_blend").value == i18n.t("blend", n=3)
        tabla = at.table[1].value
        assert list(tabla.iloc[:, 1]) == [i18n.num_g(x) for x in (193.0, 53.4, 10.6)]  # Tabla 13
        assert list(tabla.iloc[:, 2]) == [es(x, 1) for x in (-7.2, -28.0, -27.4)]  # Δ %
    assert widget(at, "dato_f_grade").value == 66.6 and widget(at, "dato_f_loss").value == 205.5
    assert not badges(at, "red")
    next(b for b in at.button if b.key == "flot_prueba_reset").click().run()
    assert widget(at, "dato_cells").value == 9 and widget(at, "dato_f_grade").value == 63.7


@pytest.mark.app
def test_si_se_cambia_un_dato_del_caso_la_comparacion_desaparece():
    at = run()
    next(b for b in at.button if b.key == "flash_caso_2").click().run()
    assert len(at.table) == 2
    widget(at, "dato_f_grade").set_value(63.0).run()
    assert len(at.table) == 1  # queda la del banco A
