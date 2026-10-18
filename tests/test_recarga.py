"""Recarga segura de módulos (`app/recarga.py`) y errores sin traza en la app."""

import importlib
import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import recarga  # noqa: E402


@pytest.fixture
def paquete(tmp_path, monkeypatch):
    """Tres módulos: `uno`, `dos` (sin relación) y `tres` (trae un nombre de `uno`)."""
    (tmp_path / "rc_uno.py").write_text("VIEJO = 1\n\ndef f():\n    return 'viejo'\n")
    (tmp_path / "rc_dos.py").write_text("DOS = 2\n")
    (tmp_path / "rc_tres.py").write_text("from rc_uno import f\n\nTRES = f()\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    yield tmp_path
    for name in ("rc_uno", "rc_dos", "rc_tres"):
        sys.modules.pop(name, None)
        recarga._LOADED.pop(name, None)


def _edit(path: Path, text: str) -> None:
    path.write_text(text)
    future = time.time() + 5
    os.utime(path, (future, future))  # el archivo queda con fecha posterior a la carga


def test_un_modulo_cambiado_se_ve_nuevo_tras_la_purga(paquete):
    uno = importlib.import_module("rc_uno")
    assert not hasattr(uno, "NUEVO")
    assert recarga.purge_stale([paquete]) == []  # nada cambió: no se quita nada
    _edit(paquete / "rc_uno.py", "VIEJO = 1\nNUEVO = 2\n\ndef f():\n    return 'nuevo'\n")
    assert "rc_uno" in recarga.purge_stale([paquete])
    nuevo = importlib.import_module("rc_uno")
    assert nuevo is not uno and nuevo.NUEVO == 2  # el nombre nuevo se ve


def test_un_modulo_sin_cambios_conserva_su_identidad(paquete):
    dos = importlib.import_module("rc_dos")
    importlib.import_module("rc_uno")
    recarga.purge_stale([paquete])
    _edit(paquete / "rc_uno.py", "VIEJO = 1\nNUEVO = 2\n")
    assert recarga.purge_stale([paquete]) == ["rc_uno"]
    assert importlib.import_module("rc_dos") is dos and sys.modules["rc_dos"] is dos


def test_sin_cambios_ninguna_corrida_quita_nada(paquete):
    mods = [importlib.import_module(n) for n in ("rc_uno", "rc_dos", "rc_tres")]
    for _ in range(3):
        assert recarga.purge_stale([paquete]) == []
    assert [sys.modules[n] for n in ("rc_uno", "rc_dos", "rc_tres")] == mods


def test_un_modulo_que_importa_nombres_del_cambiado_tambien_se_recarga(paquete):
    tres = importlib.import_module("rc_tres")
    assert tres.TRES == "viejo"
    recarga.purge_stale([paquete])
    _edit(paquete / "rc_uno.py", "def f():\n    return 'nuevo'\n")
    assert recarga.purge_stale([paquete]) == ["rc_tres", "rc_uno"]
    assert importlib.import_module("rc_tres").TRES == "nuevo"


def test_el_reimport_de_un_submodulo_no_ve_el_atributo_viejo_del_paquete(tmp_path, monkeypatch):
    pkg = tmp_path / "rc_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "sub.py").write_text("V = 1\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    try:
        from rc_pkg import sub

        recarga.purge_stale([tmp_path])
        _edit(pkg / "sub.py", "V = 2\n")
        assert "rc_pkg.sub" in recarga.purge_stale([tmp_path])
        from rc_pkg import sub as nuevo  # noqa: F811

        assert nuevo is not sub and nuevo.V == 2
    finally:
        for name in ("rc_pkg", "rc_pkg.sub"):
            sys.modules.pop(name, None)
            recarga._LOADED.pop(name, None)


def test_los_modulos_de_fuera_de_las_carpetas_no_se_tocan(paquete, tmp_path_factory):
    otra = tmp_path_factory.mktemp("otra")
    importlib.import_module("rc_dos")
    recarga.purge_stale([otra])  # no mira `paquete`
    _edit(paquete / "rc_dos.py", "DOS = 3\n")
    assert recarga.purge_stale([otra]) == []
    assert sys.modules["rc_dos"].DOS == 2


# ------------------------------------------------------------------ errores sin traza
pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(ROOT / "app" / "streamlit_app.py")
SECRETS = ("Traceback", "RuntimeError", "ImportError", "secreto", "/ruta", "principal")


def _page_text(at: AppTest) -> str:
    parts = [e.value for e in (*at.markdown, *at.caption, *at.error, *at.warning, *at.info)]
    parts += [e.value for e in at.title] + [str(e.value) for e in at.exception]
    return " ".join(parts)


def _run(lang: str | None = None) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=300)
    if lang:
        at.query_params["lang"] = lang
    return at.run()


@pytest.mark.parametrize(
    "lang,message",
    [
        ("es", "Algo falló al calcular. Prueba con otros datos o recarga la página."),
        ("en", "Something went wrong. Try other inputs or reload the page."),
    ],
)
def test_un_fallo_inesperado_muestra_solo_el_mensaje_generico(monkeypatch, lang, message):
    import calculo

    def boom(*args, **kwargs):
        raise RuntimeError("secreto /ruta/interna")

    monkeypatch.setattr(calculo, "run_flotation", boom)
    at = _run(lang)
    assert not at.exception
    assert [e.value for e in at.error] == [message]
    text = _page_text(at)
    assert not [word for word in SECRETS if word in text]


@pytest.mark.parametrize("lang", ["es", "en"])
def test_un_importerror_al_arrancar_muestra_el_mensaje_generico(monkeypatch, lang):
    monkeypatch.setitem(sys.modules, "graficos", None)  # `import graficos` falla
    at = _run(lang)
    assert not at.exception
    assert len(at.error) == 1
    expected = "Something went wrong" if lang == "en" else "Algo falló al calcular"
    assert expected in at.error[0].value
    assert not [word for word in SECRETS if word in _page_text(at)]


def test_si_ni_las_traducciones_cargan_el_mensaje_es_bilingue(monkeypatch):
    monkeypatch.setitem(sys.modules, "i18n", None)
    at = _run()
    assert not at.exception and len(at.error) == 1
    assert "Algo falló" in at.error[0].value and "Something went wrong" in at.error[0].value
    assert not [word for word in SECRETS if word in _page_text(at)]


def test_los_errores_controlados_de_la_app_se_siguen_mostrando(monkeypatch):
    """Un fallo inesperado no oculta los avisos propios: la página normal no trae el genérico."""
    at = _run("en")
    assert not at.exception and not at.error
