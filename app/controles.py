"""Cada dato de entrada se define una sola vez: arma la barra lateral y la tabla «Qué datos
necesita» de la guía, así las dos no se pueden desfasar."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st
from calculo import EWParams, FlotationParams

FLOT, EW = "Flotación", "Electroobtención"
PREFIX = "dato_"


@dataclass(frozen=True)
class Dato:
    equipo: str
    key: str
    label: str
    unit: str
    lo: float
    hi: float
    default: float
    step: float
    meaning: str
    source: str
    widget: str = "number"  # number | slider

    @property
    def help(self) -> str:
        unit = f" ({self.unit})" if self.unit else ""
        return (
            f"{self.meaning} Rango{unit}: {_num(self.lo)} a {_num(self.hi)}. "
            f"En planta: {self.source}"
        )


def _num(x: float) -> str:
    """Número en español: «1 000», «2,7»."""
    if float(x).is_integer():
        return f"{int(x):,}".replace(",", " ")
    return f"{x:g}".replace(".", ",")


DATOS: tuple[Dato, ...] = (
    Dato(FLOT, "cells", "Número de celdas", "", 1, 15, 9, 1,
         "Celdas de flotación en serie; el concentrado de cada una se suma al del banco.",
         "plano del banco.", widget="slider"),
    Dato(FLOT, "tau", "Tiempo de residencia por celda (τ)", "min", 0.5, 15, 4.1, 0.1,
         "Tiempo medio que la pulpa pasa dentro de cada celda (mezcla perfecta).",
         "prueba con trazador, o volumen útil de la celda entre el caudal de pulpa."),
    Dato(FLOT, "r_inf", "R∞ del Cu (calcopirita)", "%", 50, 100, 94, 1,
         "Recuperación máxima que alcanzaría el Cu con tiempo infinito.",
         "se ajusta a la recuperación medida celda a celda del banco."),
    Dato(FLOT, "k", "k del Cu", "1/min", 0.05, 2.0, 0.35, 0.05,
         "Constante cinética de primer orden: qué tan rápido flota el Cu.",
         "se ajusta a la recuperación medida celda a celda, o a pruebas batch de laboratorio."),
    Dato(FLOT, "gangue", "Recuperación fija de la ganga (SiO₂)", "%", 0, 30, 5, 1,
         "Parte de la ganga que llega al concentrado por arrastre, sin cinética. En el ejemplo es "
         "un supuesto, no una medida.",
         "ensayes de ganga en concentrado y relave."),
    Dato(EW, "j", "Densidad de corriente", "A/m²", 150, 400, 300, 10,
         "Corriente por metro cuadrado de cátodo.",
         "corriente de la rectificadora entre el área catódica de la nave."),
    Dato(EW, "eff", "Eficiencia de corriente", "%", 80, 99, 92, 1,
         "Parte de la corriente que deposita cobre; el resto se pierde en cortocircuitos y en el "
         "ciclo Fe³⁺/Fe²⁺.",
         "cobre cosechado entre el que da la ley de Faraday."),
    Dato(EW, "cu", "Cobre en el electrolito", "g/L", 20, 70, 40, 1,
         "Concentración de Cu²⁺ del electrolito que sale de la celda.",
         "análisis del electrolito (absorción atómica)."),
    Dato(EW, "acid", "Ácido sulfúrico", "g/L", 100, 220, 170, 5,
         "Concentración de H₂SO₄ del electrolito; más ácido, más conductor.",
         "titulación del electrolito."),
    Dato(EW, "temp", "Temperatura", "°C", 35, 65, 50, 1,
         "Temperatura del electrolito; más caliente, más conductor.",
         "termocupla en la celda."),
    Dato(EW, "days", "Días del ciclo de cosecha", "días", 1, 10, 7, 1,
         "Tiempo que el cátodo queda en la celda antes de cosecharse. Dato operativo, no del "
         "modelo; el valor del ejemplo es un supuesto típico.",
         "programa de cosecha de la nave."),
    Dato(EW, "area", "Área de una cara del cátodo", "m²", 0.5, 1.5, 1.0, 0.05,
         "Área sumergida de una cara; el cátodo tiene dos. Dato operativo, no del modelo; el "
         "valor del ejemplo es un supuesto típico.",
         "plano del cátodo."),
)  # fmt: skip
BY_KEY = {d.key: d for d in DATOS}


def _ask(d: Dato, container) -> float:
    key, label = PREFIX + d.key, f"{d.label} ({d.unit})" if d.unit else d.label
    integer = float(d.default).is_integer() and float(d.step).is_integer()
    if integer and d.widget == "slider":
        return container.slider(label, int(d.lo), int(d.hi), int(d.default), int(d.step),
                                help=d.help, key=key)  # fmt: skip
    lo, hi, v, step = (float(x) for x in (d.lo, d.hi, d.default, d.step))  # un solo tipo
    if d.widget == "slider":
        return container.slider(label, lo, hi, v, step, help=d.help, key=key)
    return container.number_input(label, lo, hi, v, step, help=d.help, key=key)


def reset_to_example() -> None:
    """Vuelve todos los datos al ejemplo."""
    for k in [k for k in st.session_state if str(k).startswith(PREFIX)]:
        del st.session_state[k]


def sidebar_config() -> tuple[FlotationParams, EWParams]:
    """Lee la barra lateral y arma los parámetros de cada equipo."""
    sb = st.sidebar
    sb.button("Cargar ejemplo", on_click=reset_to_example, width="stretch")
    v: dict[str, float] = {}
    with sb.expander(FLOT, expanded=True):
        for d in DATOS:
            if d.equipo == FLOT:
                v[d.key] = _ask(d, st)
    with sb.expander(EW, expanded=True):
        for d in DATOS:
            if d.equipo == EW:
                v[d.key] = _ask(d, st)
    flot = FlotationParams(int(v["cells"]), v["tau"], v["r_inf"] / 100.0, v["k"],
                           v["gangue"] / 100.0)  # fmt: skip
    ew = EWParams(v["j"], v["eff"] / 100.0, v["cu"], v["acid"], v["temp"], v["days"], v["area"])
    return flot, ew


def data_table(equipo: str | None = None) -> pd.DataFrame:
    """La tabla «Qué datos necesita», hecha de las mismas definiciones que la barra lateral."""
    rows = [
        {
            "Equipo": d.equipo,
            "Dato": d.label,
            "Unidad": d.unit,
            "Rango": f"{_num(d.lo)} a {_num(d.hi)}",
            "Ejemplo": _num(d.default),
            "Qué es": d.meaning,
            "Cómo se obtiene": d.source[0].upper() + d.source[1:],
        }
        for d in DATOS
        if equipo in (None, d.equipo)
    ]
    return pd.DataFrame(rows)
