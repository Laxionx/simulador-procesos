"""Piezas de interfaz que comparten las pestañas de equipo: indicadores en filas de tres, botones y
tablas de los casos publicados, y el bloque «Prueba esto». Solo texto de diccionarios fijos y
números del cálculo."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from calculo import FlotationView
from calculo_piro import FlashView
from casos import (
    CASOS_FLASH,
    CASOS_FLOT,
    CasoFlash,
    CasoFlot,
    comparacion_flash,
    comparacion_flot,
    rmse_flot,
)
from controles import reset_to_example
from dibujo import es
from estado import aplicar, pruebas
from i18n import num_g, t
from pruebas_planta import SLUG, pruebas_de

POR_FILA = 3  # indicadores por fila: con rótulos cortos caben hasta en una ventana angosta
FILA_FLASH = {"oc": "flash.row.o2", "o2": "flash.row.air", "fundente": "flash.row.flux"}


def indicadores(items: list[tuple[str, str, str | None]]) -> None:
    """Filas de tres indicadores (rótulo corto, valor, ayuda con el nombre completo)."""
    for i in range(0, len(items), POR_FILA):
        for col, (label, value, ayuda) in zip(st.columns(POR_FILA), items[i : i + POR_FILA],
                                              strict=False):  # fmt: skip
            col.metric(label, value, help=ayuda)


def _con_signo(x: float, decimales: int) -> str:
    return ("+" if x >= 0 else "") + es(x, decimales)


# ------------------------------------------------------------------ casos publicados
def botones_casos_flot() -> None:
    st.markdown(t("casos.h"))
    st.caption(t("flot.casos.intro"))
    for col, caso in zip(st.columns(len(CASOS_FLOT)), CASOS_FLOT, strict=True):
        col.button(t("flot.caso." + caso.clave), key=f"flot_caso_{caso.clave}",
                   on_click=aplicar, args=(caso.cambios,), width="stretch")  # fmt: skip


def botones_casos_flash() -> None:
    st.markdown(t("casos.h"))
    st.caption(t("flash.casos.intro"))
    for col, caso in zip(st.columns(len(CASOS_FLASH)), CASOS_FLASH, strict=True):
        col.button(t("flash.caso", n=caso.blend), key=f"flash_caso_{caso.blend}",
                   help=t("flash.caso.help", n=caso.blend), on_click=aplicar,
                   args=(caso.cambios,), width="stretch")  # fmt: skip


def _tabla(columnas: dict[str, list[str]]) -> None:
    """Tabla estática (el texto se ajusta a la columna, no se corta) con la primera columna de
    índice; las cifras entran ya escritas con el formato del idioma."""
    primera = next(iter(columnas))
    st.table(pd.DataFrame(columnas).set_index(primera))


def tabla_caso_flot(view: FlotationView, caso: CasoFlot) -> None:
    """Modelo frente a lo medido celda a celda, con el Δ en puntos y relativo."""
    filas = comparacion_flot(view, caso)
    st.markdown(t("flot.cmp.titulo", banco=caso.clave, tabla=caso.tabla))
    _tabla({
        t("flot.cmp.celda"): [str(n) for n, _, _ in filas],
        t("flot.cmp.modelo"): [es(mod, 1) for _, mod, _ in filas],
        t("flot.cmp.medido"): [es(med, 1) for _, _, med in filas],
        t("flot.cmp.dpuntos"): [_con_signo(mod - med, 1) for _, mod, med in filas],
        t("flot.cmp.dpct"): [_con_signo(100.0 * (mod - med) / med, 1) for _, mod, med in filas],
    })  # fmt: skip
    nota = t("flot.cmp.nota", rmse=es(rmse_flot(filas), 2))
    st.caption(nota + (t("flot.cmp.nota.B") if caso.clave == "B" else ""))


def tabla_caso_flash(view: FlashView, caso: CasoFlash) -> None:
    """Cálculo frente a la planta (Tabla 13): valor, publicado, Δ % y tolerancia del repo."""
    filas = comparacion_flash(view, caso)
    st.markdown(t("flash.cmp.titulo", n=caso.blend))
    _tabla({
        t("flash.cmp.mag"): [t(FILA_FLASH[f.clave]) for f in filas],
        t("flash.cmp.este"): [es(f.modelo, 2 if f.clave == "fundente" else 1) for f in filas],
        t("flash.cmp.planta"): [num_g(f.planta) for f in filas],
        t("flash.cmp.dpct"): [_con_signo(f.delta_pct, 1) for f in filas],
        t("flash.cmp.tol"): [t("flash.tol." + f.clave) for f in filas],
        t("flash.cmp.dentro"): [t("flash.cmp.si" if f.dentro else "flash.cmp.no") for f in filas],
    })  # fmt: skip
    puntos = {f.clave: f.delta_puntos for f in filas}
    st.caption(t("flash.cmp.nota", o2=_con_signo(puntos["o2"], 1),
                 fl=_con_signo(puntos["fundente"], 2)))  # fmt: skip


# ------------------------------------------------------------------ Prueba esto
def bloque_pruebas(equipo: str) -> None:
    st.markdown(t("prueba.h"))
    st.markdown(t("prueba.intro"))
    pruebas(pruebas_de(equipo), SLUG[equipo] + "_", reset_to_example)
