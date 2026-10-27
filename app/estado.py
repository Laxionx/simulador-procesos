"""Componentes de las pestañas de equipo: el panel «Estado de la operación» (una línea por
chequeo, con el nivel escrito y en color, y su fuente en la ayuda) y «Prueba esto» (experimentos
cuyo texto lleva números calculados en vivo, con un botón que los aplica a los controles).

Nada de lo que escribe el visitante entra aquí: solo textos de diccionarios fijos y números."""

from __future__ import annotations

from dataclasses import dataclass, field

import streamlit as st
from i18n import current, t

NIVELES = ("ok", "aviso", "mal")
COLORES = {"ok": "green", "aviso": "orange", "mal": "red"}


@dataclass(frozen=True)
class Fila:
    """Un chequeo ya traducido: su nivel, la línea con sus números y la fuente o criterio."""

    nivel: str
    texto: str
    ayuda: str = ""

    def __post_init__(self) -> None:
        if self.nivel not in NIVELES:
            raise ValueError(f"Nivel desconocido {self.nivel!r}")


@dataclass(frozen=True)
class Prueba:
    """Un experimento: título y texto ya traducidos, y los valores que el botón fija en los
    controles (clave de la sesión → valor)."""

    clave: str
    titulo: str
    texto: str
    cambios: dict[str, object] = field(default_factory=dict)


def cientifico(x: float) -> str:
    """Notación científica con el separador decimal del idioma."""
    out = f"{x:.1e}"
    return out.replace(".", ",") if current() == "es" else out


def etiqueta(nivel: str) -> str:
    return t("estado.nivel." + nivel)


def linea(f: Fila) -> str:
    """La línea Markdown de un chequeo: el nivel va escrito y en color, no solo en color."""
    return f":{COLORES[f.nivel]}-badge[{etiqueta(f.nivel)}] {f.texto}"


def _mostrar(f: Fila) -> None:
    st.markdown(linea(f), help=f.ayuda or None)


def peor_nivel(filas: list[Fila]) -> str:
    """El peor nivel de una lista de chequeos («ok» si está vacía)."""
    if any(f.nivel == "mal" for f in filas):
        return "mal"
    return "aviso" if any(f.nivel == "aviso" for f in filas) else "ok"


def panel(filas: list[Fila]) -> str:
    """Dibuja el panel. Los chequeos con aviso o problema van uno por línea; los que están en rango
    se agrupan (y si todos lo están, una sola línea). Devuelve el peor nivel."""
    fuera = [f for f in filas if f.nivel != "ok"]
    dentro = [f for f in filas if f.nivel == "ok"]
    for f in fuera:
        _mostrar(f)
    if not fuera:
        st.markdown(f":green-badge[{etiqueta('ok')}] {t('estado.todo_ok')}")
    if dentro:
        with st.expander(t("estado.ver1") if len(dentro) == 1
                         else t("estado.ver", n=len(dentro))):
            for f in dentro:
                _mostrar(f)
    return peor_nivel(filas)


def aplicar(cambios: dict[str, object]) -> None:
    """Fija los controles (se llama como `on_click`, antes de que el script vuelva a correr)."""
    for k, v in cambios.items():
        st.session_state[k] = v


def pruebas(items: list[Prueba], prefijo: str, restablecer=None) -> None:
    """Dibuja los experimentos. `restablecer` (opcional) es el `on_click` del botón que vuelve al
    ejemplo."""
    for p in items:
        with st.container(border=True):
            st.markdown(f"**{p.titulo}.** {p.texto}")
            st.button(t("prueba.aplicar"), key=f"{prefijo}prueba_{p.clave}", on_click=aplicar,
                      args=(p.cambios,))  # fmt: skip
    if restablecer is not None:
        st.button(t("prueba.restablecer"), key=f"{prefijo}prueba_reset", on_click=restablecer)
