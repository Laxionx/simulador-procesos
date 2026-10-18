"""Español e inglés: mismas claves, mismas cifras, sin restos de un idioma en el otro, y el
parámetro `?lang=` validado."""

import ast
import json
import re
import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "app" / "streamlit_app.py")
sys.path.insert(0, str(ROOT / "app"))

import calculo  # noqa: E402
import calculo_piro as cp  # noqa: E402
import controles  # noqa: E402
import convertidor_svg  # noqa: E402
import ew_svg  # noqa: E402
import flotacion_svg  # noqa: E402
import fusion_svg  # noqa: E402
import graficos  # noqa: E402
import guia  # noqa: E402
import i18n  # noqa: E402
import modelo_en  # noqa: E402
from i18n import TEXTS  # noqa: E402

ES, EN = TEXTS["es"], TEXTS["en"]
# restos de español que no deben aparecer en un texto en inglés (los apellidos de las citas con
# tilde se dejan: se citan tal cual)
SPANISH = re.compile(
    r"[áéíóúñ¿¡]|\b(de|del|la|las|los|el|con|para|por|una|sin|que|se|más|muy)\b", re.IGNORECASE
)
CITED = (
    "García-Zúñiga", "Ríos", "Luleå", "Kalliomäki", "Díaz", "Henríquez", "Pino-Muñoz",
    "Sánchez", "González", "Patiño", "Quím", "Méx", "Bacedoni", "Los Pelambres",
)  # fmt: skip


def spanish_left(text: str) -> bool:
    clean = re.sub(r"\{[^}]*\}|`[^`]*`", "", text)
    for name in CITED:
        clean = clean.replace(name, "")
    return bool(SPANISH.search(clean))


def run(lang: str | None = None, **values) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=300)
    if lang is not None:
        at.query_params["lang"] = lang
    at.run()
    for key, value in values.items():
        for w in [*at.sidebar.number_input, *at.sidebar.slider, *at.sidebar.selectbox]:
            if w.key == "dato_" + key:
                if key == "blend":
                    with i18n.use(lang or "es"):
                        value = i18n.t("blend", n=value)  # la lista muestra «Mezcla n»
                w.set_value(value)
    if values:
        at.run()
    return at


# ------------------------------------------------------------------ las claves
def test_los_dos_idiomas_tienen_las_mismas_claves():
    assert set(ES) == set(EN), sorted(set(ES) ^ set(EN))


def test_cada_texto_tiene_los_mismos_campos_en_los_dos_idiomas():
    for key in ES:
        assert i18n.fields(ES[key]) == i18n.fields(EN[key]), key


def test_ningun_texto_esta_vacio_y_solo_los_cognados_son_iguales_en_los_dos_idiomas():
    assert not {k for k in ES if not ES[k].strip() or not EN[k].strip()}
    same = {k for k in ES if ES[k] == EN[k]}
    # rutas de archivo, fórmulas y unidades (SO₂, t/h), y textos que solo llevan campos
    assert same == {
        "conv.m4", "flash.m4", "plot.volt.total", "svg.conv.lower", "svg.conv.state",
        "svg.flash.gas", "svg.flash.kg_t", "svg.flash.m3_t", "svg.flash.o2_pct", "svg.flot.th",
        "ficha.Convertidor.doc", "ficha.Electroobtención.doc", "ficha.Flotación.doc",
        "ficha.Horno flash.doc",
    }  # fmt: skip


def _literals_and_prefixes() -> tuple[set[str], set[str]]:
    literals, prefixes = set(), set()
    for path in (ROOT / "app").glob("*.py"):
        if path.name.startswith("textos_"):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                literals.add(node.value)
            if isinstance(node, ast.JoinedStr) and node.values:
                first = node.values[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    prefixes.add(first.value)
            if (
                isinstance(node, ast.BinOp)
                and isinstance(node.op, ast.Add)
                and isinstance(node.left, ast.Constant)
                and isinstance(node.left.value, str)
            ):
                prefixes.add(node.left.value)
    return literals, {p for p in prefixes if "." in p and len(p) >= 3}


def test_no_hay_claves_sin_usar():
    literals, prefixes = _literals_and_prefixes()
    unused = [k for k in ES if k not in literals and not any(k.startswith(p) for p in prefixes)]
    assert not unused, unused


def test_las_familias_dinamicas_estan_completas():
    for d in controles.DATOS:
        for field in ("label", "meaning", "source"):
            assert f"dato.{d.key}.{field}" in ES, (d.key, field)
        assert "group." + d.equipo in ES
    for equipo in (controles.FLOT, controles.EW, controles.FLASH, controles.CONV):
        for part in ("hace", "entra", "sale", "autores", "doc"):
            assert f"ficha.{equipo}.{part}" in ES, (equipo, part)
        assert guia.DOCS[equipo] == ES[f"ficha.{equipo}.doc"]
    assert all(f"limits.{n}" in ES for n in range(1, guia.N_LIMITS + 1))
    assert f"limits.{guia.N_LIMITS + 1}" not in ES
    for name in [n for n, _ in guia.RUTA_PIRO + guia.RUTA_HIDRO] + ["Cátodo de Cu"]:
        assert f"route.step.{name}" in ES and f"route.step.{name}" in EN
    for state in (guia.ANIMADO, guia.OTRA, guia.PROXIMO, guia.REPO_ONLY, "materia prima"):
        assert f"route.state.{state}" in ES and f"route.state.{state}" in EN


def test_los_textos_en_ingles_no_llevan_palabras_en_espanol():
    bad = {k: v[:80] for k, v in EN.items() if not k.endswith(".doc") and spanish_left(v)}
    assert not bad, bad


# ------------------------------------------------------------------ el idioma y la URL
@pytest.mark.parametrize("value", ["fr", "EN", "es ", "", "en;alert(1)", "<script>", "../en"])
def test_un_parametro_lang_invalido_es_espanol_sin_error(value):
    at = run(value)
    assert not at.exception
    assert at.tabs[0].label == "Guía"
    assert at.sidebar.radio[0].value == "es"
    assert at.query_params["lang"] in (["es"], "es")


def test_parse_lang_solo_acepta_es_y_en():
    assert [i18n.parse_lang(v) for v in ("es", "en")] == ["es", "en"]
    assert {i18n.parse_lang(v) for v in ("fr", None, 3, ["en"], "EN", " en")} == {"es"}


def test_lang_en_en_la_url_abre_en_ingles_y_el_selector_cambia_el_idioma():
    en = run("en")
    assert [t.label for t in en.tabs] == [
        "Guide", "Flotation", "Flash furnace", "Converter", "Electrowinning"
    ]  # fmt: skip
    assert en.sidebar.radio[0].value == "en"
    en.sidebar.radio[0].set_value("es").run()
    assert en.tabs[0].label == "Guía"
    assert en.query_params["lang"] in (["es"], "es")
    es_ = run()
    es_.sidebar.radio[0].set_value("en").run()
    assert es_.tabs[0].label == "Guide" and not es_.exception


def test_el_valor_de_lang_nunca_llega_al_html_ni_al_svg():
    at = run("en<script>alert(1)</script>")
    blob = json.dumps([m.value for m in at.markdown] + [c.value for c in at.caption])
    assert "alert(1)" not in blob and "<script" not in blob.lower()


def test_los_datos_y_la_mezcla_se_conservan_al_cambiar_de_idioma():
    at = run("es", tau=6.0, blend=3)
    at.sidebar.radio[0].set_value("en").run()
    tau = next(w for w in at.sidebar.number_input if w.key == "dato_tau")
    blend = next(w for w in at.sidebar.selectbox if w.key == "dato_blend")
    assert tau.value == 6.0 and blend.value == "Blend 3"
    at.sidebar.radio[0].set_value("es").run()
    blend = next(w for w in at.sidebar.selectbox if w.key == "dato_blend")
    assert blend.value == "Mezcla 3" and not at.exception


# ------------------------------------------------------------------ humo de todas las pestañas
@pytest.mark.parametrize("lang", ["es", "en"])
def test_humo_de_todas_las_pestanas(lang):
    at = run(lang)
    assert not at.exception and not at.error
    assert len(at.tabs) == 5 and len(at.metric) == 16
    assert len(at.sidebar.expander) == 4


@pytest.mark.parametrize("lang", ["es", "en"])
def test_humo_con_extremos_y_avisos_de_la_celda(lang):
    at = run(lang, cu=21.0, acid=219.0, temp=64.0, j=399.0, blend=4)
    assert not at.exception
    assert at.warning, "la celda en el borde de la correlación avisa de la extrapolación"


# ------------------------------------------------------------------ mismas cifras
_NUMBER = {
    "es": re.compile(r"-?\d+(?: \d{3})*(?:[.,]\d+)?(?:e-?\d+)?"),
    "en": re.compile(r"-?\d+(?:,\d{3})*(?:\.\d+)?(?:e-?\d+)?"),
}


def _numbers(text: str, lang: str) -> list[float]:
    """Los números de un texto, leídos con el formato de su idioma."""
    out = []
    for item in _NUMBER[lang].findall(text.replace("\xa0", " ")):
        item = item.replace(",", "") if lang == "en" else item.replace(" ", "").replace(",", ".")
        out.append(float(item))
    return out


def _figures(at: AppTest, lang: str) -> list:
    parts = [m.value for m in at.metric] + [m.delta for m in at.metric]
    out = [_numbers(p or "", lang) for p in parts]
    for df in at.dataframe:
        for row in df.value.values.tolist():
            out.append([x for x in row if isinstance(x, int | float)])
    for md in at.markdown:
        if md.value.startswith("| "):
            for line in md.value.splitlines()[2:]:
                out.append([_numbers(c, lang) for c in line.strip("| ").split(" | ")])
    return out


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"cells": 5, "tau": 8.0, "k": 0.8},
        {"j": 250.0, "eff": 85.0, "days": 3, "blend": 2},
        {"f_grade": 66.0, "f_sio2": 27.0, "c_grade": 70.0, "c_bath": 1250.0, "blend": 4},
    ],
)
def test_las_cifras_son_identicas_en_los_dos_idiomas(values):
    es_, en = run("es", **values), run("en", **values)
    assert not es_.exception and not en.exception
    a, b = _figures(es_, "es"), _figures(en, "en")
    assert len(a) == len(b) > 20 and a == b
    assert len(es_.metric) == len(en.metric) == 16


# ------------------------------------------------------------------ los gráficos y los esquemas
def _fig_text(fig) -> str:
    return json.dumps(fig.to_plotly_json(), ensure_ascii=False)


def _views():
    flot = calculo.run_flotation(calculo.FlotationParams())
    ew = calculo.run_ew(calculo.EWParams())
    flash = cp.run_flash(cp.FlashParams())
    conv = cp.run_converter(cp.ConverterParams())
    return flot, ew, flash, conv


def test_los_graficos_en_ingles_no_llevan_espanol_y_en_espanol_siguen_igual():
    flot, ew, _, conv = _views()
    for lang in ("es", "en"):
        with i18n.use(lang):
            figs = [
                graficos.recovery_figure(flot), graficos.voltage_figure(ew),
                graficos.converter_figure(conv),
            ]  # fmt: skip
            blob = " ".join(_fig_text(f) for f in figs)
        texts = re.findall(r'"(?:text|title|name|label)": "([^"]+)"', blob)
        texts += re.findall(r'"title": \{"text": "([^"]+)"', blob)
        if lang == "en":
            assert not [x for x in texts if spanish_left(x)], texts[:6]
            assert "Slag blow" in blob and "in: matte" in blob and "anodic" in blob
        else:
            assert "Soplado a escoria" in blob and "entra: mata" in blob and "anódico" in blob


def test_los_esquemas_en_ingles_no_llevan_espanol():
    flot, ew, flash, conv = _views()
    for lang in ("es", "en"):
        with i18n.use(lang):
            svgs = [
                flotacion_svg.flotation_svg(flot), fusion_svg.flash_svg(flash),
                convertidor_svg.converter_svg(conv), convertidor_svg.converter_svg(conv, True),
                ew_svg.ew_svg(ew), guia.route_map(),
            ]  # fmt: skip
            blob = " ".join(svgs)
        texts = re.findall(r">([^<]+)</text>", blob) + re.findall(r'aria-label="([^"]+)"', blob)
        if lang == "en":
            assert not [x for x in texts if spanish_left(x)], [x for x in texts if spanish_left(x)]
            for expected in ("Flotation bank", "slag", "Charge: matte", "cathode", "Grinding"):
                assert any(expected in x for x in texts), expected
        else:
            for expected in ("Banco de flotación", "escoria", "Carga: mata", "cátodo", "Molienda"):
                assert any(expected in x for x in texts), expected


def test_los_numeros_de_los_esquemas_cambian_de_formato_pero_no_de_valor():
    _, ew, flash, _ = _views()
    with i18n.use("es"):
        es_svg = ew_svg.ew_svg(ew) + fusion_svg.flash_svg(flash)
    with i18n.use("en"):
        en_svg = ew_svg.ew_svg(ew) + fusion_svg.flash_svg(flash)
    thick = f"{ew.thickness_mm:.2f}"
    assert thick.replace(".", ",") + " mm" in es_svg and thick + " mm" in en_svg
    volume = f"{flash.matte_m3_t:.3f}"
    assert volume.replace(".", ",") + " m³/t" in es_svg and volume + " m³/t" in en_svg


def test_formato_de_numeros_por_idioma():
    with i18n.use("es"):
        assert i18n.num(1234.5, 1) == "1 234,5" and i18n.num(0.5, 2) == "0,50"
        assert i18n.int_num(20000) == "20 000" and i18n.num_g(2.5) == "2,5"
    with i18n.use("en"):
        assert i18n.num(1234.5, 1) == "1,234.5" and i18n.num(0.5, 2) == "0.50"
        assert i18n.int_num(20000) == "20,000" and i18n.num_g(2.5) == "2.5"


# ------------------------------------------------------------------ lo que sale del modelo
def _model_labels() -> set[str]:
    _, ew, _, conv = _views()
    out = {s.name for s in conv.states} | {s.lower_name for s in conv.states}
    out |= {stage for stage, _, _ in graficos.converter_balance_rows(conv)}
    out |= {concept for _, concept, _ in graficos.converter_balance_rows(conv)}
    out |= set(ew.result.components)
    out |= {concept.split(":")[0] for _, concept, _ in graficos.converter_balance_rows(conv)}
    return out


def test_ningun_rotulo_del_modelo_queda_en_espanol_en_ingles():
    with i18n.use("en"):
        left = {x: i18n.tm(x) for x in _model_labels() if spanish_left(i18n.tm(x))}
    assert not left, left
    with i18n.use("es"):
        assert all(i18n.tm(x) == x for x in _model_labels())


def test_los_avisos_y_errores_del_modelo_se_traducen():
    msg = (
        "conductividad: Cu = 12,00 fuera del rango de la correlación (20-70); es una extrapolación"
    )
    with i18n.use("en"):
        out = i18n.tw(msg)
        assert out == (
            "conductivity: Cu = 12.00 outside the range of the correlation (20-70); it is an "
            "extrapolation"
        )
        assert i18n.tw("la corriente pide más cobre del que trae el electrolito").startswith(
            "the current asks"
        )
        assert i18n.tw("un aviso que no se conoce") == "un aviso que no se conoce"
        assert "Impossible balance" in i18n.tr_error("Balance imposible con esas metas: x")
        assert "limiting density" in i18n.tr_error(
            "densidad de corriente 600 ≥ densidad límite 500 A/m²"
        )
        assert i18n.tr_error("algo desconocido") == "algo desconocido"
    with i18n.use("es"):
        assert i18n.tw(msg) == msg and i18n.tr_error("Balance imposible") == "Balance imposible"
    assert all(re.compile(p) for p, _ in modelo_en.ERRORS + modelo_en.WARNINGS)


def test_los_avisos_reales_de_la_celda_no_quedan_en_espanol():
    ew = calculo.run_ew(calculo.EWParams(cu_g_l=21.0, acid_g_l=219.0, temp_c=64.0))
    extreme = calculo.run_ew(calculo.EWParams(cu_g_l=20.0, acid_g_l=100.0, temp_c=35.0))
    seen = list(ew.warnings) + list(extreme.warnings)
    with i18n.use("en"):
        translated = [i18n.tw(w) for w in seen]
    assert all(not spanish_left(w) for w in translated), translated


@pytest.mark.parametrize("lang", ["es", "en"])
def test_un_error_del_modelo_se_muestra_sin_traza_en_los_dos_idiomas(monkeypatch, lang):
    def fails(params):
        raise ValueError(
            "Balance imposible con esas metas: el calor no alcanza para fundir sin combustible: "
            "falta energía"
        )

    monkeypatch.setattr(cp, "run_flash", fails)
    at = run(lang)
    assert not at.exception
    messages = " ".join(e.value for e in at.error)
    if lang == "en":
        assert "Impossible balance with those targets" in messages
        assert "energy is missing" in messages and not spanish_left(messages)
    else:
        assert "Balance imposible con esas metas" in messages


# ------------------------------------------------------------------ README y GIF
def test_los_readme_se_enlazan_entre_si_y_los_gif_existen_y_pesan_menos_de_3_mb():
    es_, en = (ROOT / "README.md").read_text("utf-8"), (ROOT / "README.en.md").read_text("utf-8")
    assert es_.splitlines()[0] == "[English version](README.en.md)"
    assert en.splitlines()[0] == "[Versión en español](README.md)"
    assert "?lang=en" in en
    for readme, name in ((es_, "convertidor.es.gif"), (en, "converter.en.gif")):
        assert f"docs/img/{name}" in readme
        gif = ROOT / "docs" / "img" / name
        assert gif.read_bytes()[:6] in (b"GIF89a", b"GIF87a")
        assert 0 < gif.stat().st_size < 3_000_000


def test_el_ingles_usa_comillas_inglesas_y_no_las_espanolas():
    bad = [k for k, v in EN.items() if "«" in v or "»" in v]
    assert not bad, bad
    assert not [x for x in _model_labels() if "«" in modelo_en.translate(x)]
