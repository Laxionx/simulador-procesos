"""App «Planta completa»: humo con AppTest, controles y tabla de datos desde UNA definición, y
valores manipulados que no deben tumbar el servidor."""

import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "app" / "streamlit_app.py")
sys.path.insert(0, str(ROOT / "app"))

import controles  # noqa: E402
from guia import markdown_table  # noqa: E402


def _widgets(at: AppTest) -> list:
    return [*at.sidebar.number_input, *at.sidebar.slider]


def test_las_pestanas_cargan_sin_excepciones():
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception
    assert not at.error
    assert [t.label for t in at.tabs] == ["Guía", "Flotación", "Electroobtención"]
    labels = [m.label for m in at.metric]
    assert "Recuperación de Cu (CuFeS₂)" in labels and "Voltaje de celda" in labels
    values = {m.label: m.value for m in at.metric}
    assert values["Recuperación de Cu (CuFeS₂)"] == "94,0 %"
    assert values["Voltaje de celda"] == "2,18 V"


def test_los_controles_salen_de_la_misma_definicion_que_la_tabla():
    at = AppTest.from_file(APP, default_timeout=120).run()
    widgets = {w.key: w for w in _widgets(at)}
    assert set(widgets) == {controles.PREFIX + d.key for d in controles.DATOS}
    for d in controles.DATOS:  # el widget de la barra lateral es lo que dice la definición
        w = widgets[controles.PREFIX + d.key]
        assert (w.min, w.max, w.value) == (d.lo, d.hi, d.default), d.key
    table = controles.data_table()
    assert len(table) == len(controles.DATOS)
    assert list(table["Dato"]) == [d.label for d in controles.DATOS]
    text = " ".join(m.value for m in at.markdown)  # y la guía muestra la misma tabla
    for d in controles.DATOS:
        assert d.label in text


def test_la_tabla_de_datos_se_desfasa_si_cambia_la_definicion(monkeypatch):
    extra = controles.Dato(controles.FLOT, "nuevo", "Dato nuevo", "", 0, 1, 0.5, 0.1, "x", "y")
    monkeypatch.setattr(controles, "DATOS", (*controles.DATOS, extra))
    assert "Dato nuevo" in list(controles.data_table()["Dato"])  # la tabla lo recoge sola


def test_markdown_table_escapa_barras():
    import pandas as pd

    assert "\\|" in markdown_table(pd.DataFrame({"a": ["x|y"]}))


@pytest.mark.parametrize("extreme", ["min", "max"])
def test_controles_en_los_extremos_no_tumban_la_app(extreme):
    at = AppTest.from_file(APP, default_timeout=120).run()
    for w in _widgets(at):
        w.set_value(w.min if extreme == "min" else w.max)
    at.run()
    assert not at.exception


@pytest.mark.parametrize("value", [10_000_000, -5, float("inf"), float("nan")])
def test_el_servidor_rechaza_valores_fuera_de_rango(value):
    # Un cliente puede mandar valores sin pasar por el navegador: Streamlit (versión fijada en
    # requirements.txt) los devuelve al valor por defecto en el servidor.
    at = AppTest.from_file(APP, default_timeout=120).run()
    cells = at.sidebar.slider[0]  # número de celdas, 1 a 15
    cells.set_value(value).run()
    assert not at.exception
    assert at.sidebar.slider[0].value == 9
    for w in at.sidebar.number_input:
        w.set_value(value)
    at.run()
    assert not at.exception
    assert [w.value for w in at.sidebar.number_input] == [
        d.default for d in controles.DATOS if d.widget == "number"
    ]


def test_un_fallo_del_modelo_se_muestra_sin_traza(monkeypatch):
    import calculo

    def fails(params):
        raise ValueError("conductividad no física: composición fuera de rango")

    monkeypatch.setattr(calculo, "run_ew", fails)
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception
    assert any("composición fuera de rango" in e.value for e in at.error)
