"""Idioma de la app (español o inglés): qué idioma se usa, `t(clave)` y el formato de números.

El idioma vive en `st.session_state["lang"]` y en el parámetro de la URL `?lang=en`. El parámetro se
valida contra {"es", "en"}: cualquier otro valor es español, y nada de él llega al HTML ni al SVG
(solo se elige entre dos diccionarios fijos). Las funciones de dibujo y de texto leen el idioma de
una variable de contexto que el script fija al empezar cada corrida (`use`); fuera de la app
(pruebas) el idioma es el español.

Números: español = coma decimal y espacio de miles; inglés = punto decimal y coma de miles.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

import streamlit as st
from textos_en import TEXTS as TEXTS_EN
from textos_es import TEXTS as TEXTS_ES

LANGS = ("es", "en")
DEFAULT = "es"
PARAM = "lang"
LABELS = {"es": "Español", "en": "English"}
TEXTS = {"es": TEXTS_ES, "en": TEXTS_EN}

_lang: ContextVar[str] = ContextVar("lang", default=DEFAULT)


def parse_lang(value: object) -> str:
    """El idioma de un valor cualquiera: solo «es» y «en» valen; todo lo demás, español."""
    return value if isinstance(value, str) and value in LANGS else DEFAULT


def current() -> str:
    return _lang.get()


@contextmanager
def use(lang: str) -> Iterator[None]:
    """Fija el idioma mientras dura el bloque (pruebas y corridas del script)."""
    token = _lang.set(parse_lang(lang))
    try:
        yield
    finally:
        _lang.reset(token)


def t(key: str, **values: object) -> str:
    """El texto de `key` en el idioma actual; `values` rellenan los {campos} del texto."""
    text = TEXTS[current()][key]
    return text.format(**values) if values else text


def opt(value: str) -> str:
    """Rótulo de una opción de lista (su valor interno es el del modelo, en español)."""
    key = "opt." + value
    return TEXTS[current()].get(key, value)


def num(x: float, decimals: int = 1) -> str:
    """Número con el formato del idioma: «1 234,5» en español, «1,234.5» en inglés."""
    out = f"{x:,.{decimals}f}"
    if current() == "en":
        return out
    return out.replace(",", " ").replace(".", ",")


def num_g(x: float) -> str:
    """Número con `:g` y el separador decimal del idioma (rangos y valores de los datos)."""
    out = f"{x:g}"
    return out if current() == "en" else out.replace(".", ",")


def int_num(x: float) -> str:
    """Entero con separador de miles del idioma."""
    out = f"{int(x):,}"
    return out if current() == "en" else out.replace(",", " ")


def decimal(x: float) -> str:
    """`:.6g` con el separador decimal del idioma (tablas de validación)."""
    out = f"{x:.6g}"
    return out if current() == "en" else out.replace(".", ",")


def _from_url() -> str:
    return parse_lang(st.query_params.get(PARAM, DEFAULT))


def sidebar_selector() -> str:
    """Selector «Español / English» arriba de la barra lateral. Lee `?lang=` en la primera
    corrida, guarda la elección en la sesión y la escribe de vuelta en la URL."""
    if "lang" not in st.session_state:
        st.session_state["lang"] = _from_url()
    st.sidebar.radio(
        "Idioma / Language",
        LANGS,
        format_func=LABELS.get,
        horizontal=True,
        key="lang",
    )
    lang = parse_lang(st.session_state["lang"])
    if st.query_params.get(PARAM) != lang:
        st.query_params[PARAM] = lang
    return lang


_FIELD = re.compile(r"\{(\w+)[^}]*\}")


def fields(text: str) -> set[str]:
    """Nombres de los {campos} de un texto (para comprobar que los dos idiomas coinciden)."""
    return set(_FIELD.findall(text))


def tm(text: str) -> str:
    """Rótulo que viene del modelo (en español): se traduce si el idioma es el inglés."""
    if current() == "es":
        return text
    from modelo_en import translate

    return translate(text)


def activate() -> str:
    """Al empezar cada corrida del script: elige el idioma (sesión o `?lang=`) y lo deja activo."""
    if "lang" not in st.session_state:
        st.session_state["lang"] = _from_url()
    lang = parse_lang(st.session_state["lang"])
    _lang.set(lang)
    return lang


def tr_error(message: str) -> str:
    """Mensaje de error del modelo (en español) en el idioma de la app."""
    if current() == "es":
        return message
    from modelo_en import translate_error

    return translate_error(message)


def tw(message: str) -> str:
    """Aviso del modelo (en español) en el idioma de la app."""
    if current() == "es":
        return message
    from modelo_en import translate_warning

    return translate_warning(message)
