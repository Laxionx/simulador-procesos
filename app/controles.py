"""Cada dato de entrada se define una sola vez: arma la barra lateral y la tabla «Qué datos
necesita» de la guía, así las dos no se pueden desfasar. Sus textos están en `textos_es_datos.py`
y `textos_en_datos.py`, con las claves `dato.<clave>.label|meaning|source`."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st
from calculo import EWParams, FlotationParams
from calculo_piro import ConverterParams, FlashParams
from i18n import current, int_num, num_g, t, use

FLOT, EW = "Flotación", "Electroobtención"
FLASH, CONV = "Horno flash", "Convertidor"
PREFIX = "dato_"


def _tx(text: str) -> str:
    """El texto de una clave de `textos_*`; si no es una clave, el propio texto."""
    try:
        return t(text)
    except KeyError:
        return text


@dataclass(frozen=True)
class Dato:
    equipo: str
    key: str
    label_k: str
    unit_k: str
    lo: float
    hi: float
    default: float
    step: float
    meaning_k: str
    source_k: str
    widget: str = "number"  # number | slider | select (enteros de lo a hi)

    @property
    def label(self) -> str:
        return _tx(self.label_k)

    @property
    def unit(self) -> str:
        return _tx(self.unit_k)

    @property
    def meaning(self) -> str:
        return _tx(self.meaning_k)

    @property
    def source(self) -> str:
        return _tx(self.source_k)

    @property
    def help(self) -> str:
        unit = f" ({self.unit})" if self.unit else ""
        return t("dato.help", meaning=self.meaning, unit=unit, lo=_num(self.lo), hi=_num(self.hi),
                 source=self.source)  # fmt: skip


def _num(x: float) -> str:
    """Número en el formato del idioma: «1 000», «2,7» (es) o «1,000», «2.7» (en)."""
    return int_num(x) if float(x).is_integer() else num_g(x)


DATOS: tuple[Dato, ...] = (
    Dato(FLOT, "cells", "dato.cells.label", "", 1, 15, 9, 1,
         "dato.cells.meaning", "dato.cells.source", widget="slider"),
    Dato(FLOT, "tau", "dato.tau.label", "min", 0.5, 15, 4.1, 0.1,
         "dato.tau.meaning", "dato.tau.source"),
    Dato(FLOT, "r_inf", "dato.r_inf.label", "%", 50, 100, 94, 1,
         "dato.r_inf.meaning", "dato.r_inf.source"),
    Dato(FLOT, "k", "dato.k.label", "1/min", 0.05, 2.0, 0.35, 0.05,
         "dato.k.meaning", "dato.k.source"),
    Dato(FLOT, "gangue", "dato.gangue.label", "%", 0, 30, 5, 1,
         "dato.gangue.meaning", "dato.gangue.source"),
    Dato(EW, "j", "dato.j.label", "A/m²", 150, 400, 300, 10,
         "dato.j.meaning", "dato.j.source"),
    Dato(EW, "eff", "dato.eff.label", "%", 80, 99, 92, 1,
         "dato.eff.meaning", "dato.eff.source"),
    Dato(EW, "cu", "dato.cu.label", "g/L", 20, 70, 40, 1,
         "dato.cu.meaning", "dato.cu.source"),
    Dato(EW, "acid", "dato.acid.label", "g/L", 100, 220, 170, 5,
         "dato.acid.meaning", "dato.acid.source"),
    Dato(EW, "temp", "dato.temp.label", "°C", 35, 65, 50, 1,
         "dato.temp.meaning", "dato.temp.source"),
    Dato(EW, "days", "dato.days.label", "unit.days", 1, 10, 7, 1,
         "dato.days.meaning", "dato.days.source"),
    Dato(EW, "area", "dato.area.label", "m²", 0.5, 1.5, 1.0, 0.05,
         "dato.area.meaning", "dato.area.source"),
    Dato(FLASH, "blend", "dato.blend.label", "", 1, 4, 1, 1,
         "dato.blend.meaning", "dato.blend.source", widget="select"),
    Dato(FLASH, "f_grade", "dato.f_grade.label", "% Cu", 60, 70, 63.7, 0.5,
         "dato.f_grade.meaning", "dato.f_grade.source"),
    Dato(FLASH, "f_sio2", "dato.f_sio2.label", "%", 25, 32, 29, 0.5,
         "dato.f_sio2.meaning", "dato.f_sio2.source"),
    Dato(FLASH, "f_loss", "dato.f_loss.label", "MJ/t", 150, 260, 205.5, 5,
         "dato.f_loss.meaning", "dato.f_loss.source"),
    Dato(FLASH, "f_temp", "dato.f_temp.label", "°C", 1250, 1325, 1300, 5,
         "dato.f_temp.meaning", "dato.f_temp.source"),
    Dato(CONV, "c_grade", "dato.c_grade.label", "% Cu", 50, 72, 62, 0.5,
         "dato.c_grade.meaning", "dato.c_grade.source"),
    Dato(CONV, "c_eff_slag", "dato.c_eff_slag.label", "%", 40, 95, 62, 1,
         "dato.c_eff_slag.meaning", "dato.c_eff_slag.source"),
    Dato(CONV, "c_eff_copper", "dato.c_eff_copper.label", "%", 50, 95, 77, 1,
         "dato.c_eff_copper.meaning", "dato.c_eff_copper.source"),
    Dato(CONV, "c_bath", "dato.c_bath.label", "°C", 1150, 1300, 1200, 10,
         "dato.c_bath.meaning", "dato.c_bath.source"),
)  # fmt: skip
BY_KEY = {d.key: d for d in DATOS}


def _ask(d: Dato, container) -> float:
    key, label = PREFIX + d.key, f"{d.label} ({d.unit})" if d.unit else d.label
    if d.widget == "select":
        options = list(range(int(d.lo), int(d.hi) + 1))
        labels = [t("blend", n=v) for v in options]  # el valor (1 a 4) se rotula aquí
        chosen = container.selectbox(label, labels, int(d.default) - int(d.lo), key=key,
                                     help=d.help)  # fmt: skip
        return options[labels.index(chosen)]
    integer = float(d.default).is_integer() and float(d.step).is_integer()
    if integer and d.widget == "slider":
        return container.slider(label, int(d.lo), int(d.hi), int(d.default), int(d.step),
                                help=d.help, key=key)  # fmt: skip
    lo, hi, v, step = (float(x) for x in (d.lo, d.hi, d.default, d.step))  # un solo tipo
    if d.widget == "slider":
        return container.slider(label, lo, hi, v, step, help=d.help, key=key)
    return container.number_input(label, lo, hi, v, step, help=d.help, key=key)


def _relabel_selects(previous: str) -> None:
    """Al cambiar de idioma, la lista de mezclas conserva su elección: se pasa del rótulo del
    idioma anterior al del idioma actual (el valor guardado en la sesión es el rótulo)."""
    for d in DATOS:
        key = PREFIX + d.key
        if d.widget != "select" or key not in st.session_state:
            continue
        for n in range(int(d.lo), int(d.hi) + 1):
            with use(previous):
                old = t("blend", n=n)
            if old == st.session_state[key]:
                st.session_state[key] = t("blend", n=n)
                break


def reset_to_example() -> None:
    """Vuelve todos los datos al ejemplo."""
    for k in [k for k in st.session_state if str(k).startswith(PREFIX)]:
        del st.session_state[k]


def sidebar_config() -> tuple[FlotationParams, EWParams, FlashParams, ConverterParams]:
    """Lee la barra lateral y arma los parámetros de cada equipo."""
    sb = st.sidebar
    seen = st.session_state.get("_lang_seen")
    if seen and seen != current():
        _relabel_selects(seen)
    st.session_state["_lang_seen"] = current()
    sb.button(t("sidebar.example"), on_click=reset_to_example, width="stretch")
    v: dict[str, float] = {}
    for group in (FLOT, EW, FLASH, CONV):
        with sb.expander(t("group." + group), expanded=group == FLOT):
            for d in DATOS:
                if d.equipo == group:
                    v[d.key] = _ask(d, st)
    flot = FlotationParams(int(v["cells"]), v["tau"], v["r_inf"] / 100.0, v["k"],
                           v["gangue"] / 100.0)  # fmt: skip
    ew = EWParams(v["j"], v["eff"] / 100.0, v["cu"], v["acid"], v["temp"], v["days"], v["area"])
    flash = FlashParams(int(v["blend"]), v["f_grade"], v["f_sio2"], v["f_loss"], v["f_temp"])
    conv = ConverterParams(v["c_grade"], v["c_eff_slag"] / 100.0, v["c_eff_copper"] / 100.0,
                           v["c_bath"])  # fmt: skip
    return flot, ew, flash, conv


def data_table(equipo: str | None = None) -> pd.DataFrame:
    """La tabla «Qué datos necesita», hecha de las mismas definiciones que la barra lateral."""
    rows = [
        {
            t("col.equipo"): t("group." + d.equipo),
            t("col.dato"): d.label,
            t("col.unit"): d.unit,
            t("col.range"): t("dato.range", lo=_num(d.lo), hi=_num(d.hi)),
            t("col.example"): _num(d.default),
            t("col.what"): d.meaning,
            t("col.how"): d.source[0].upper() + d.source[1:],
        }
        for d in DATOS
        if equipo in (None, d.equipo)
    ]
    return pd.DataFrame(rows)
