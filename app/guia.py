"""Pestaña «Guía» y fichas de cada equipo: qué hace, qué datos necesita, qué devuelve y de qué
autores salen las ecuaciones (las mismas fuentes de docs/)."""

from __future__ import annotations

import textwrap

import pandas as pd
import streamlit as st
from controles import CONV, EW, FLASH, FLOT, data_table
from dibujo import BRONZE, INK, PAPER, STEEL, as_images, svg, text
from i18n import current, t

REPO = "https://github.com/Laxionx/simulador-procesos"
CONMINUCION = "https://simulador-conminucion-mtxoolyzuvvcxrq8rce3el.streamlit.app/"

# Estado de cada equipo en el mapa: animado aquí, en otra app, próximamente o solo en el repo.
ANIMADO, OTRA, PROXIMO, REPO_ONLY = "animado", "otra app", "próximamente", "en el repo"
RUTA_PIRO = (
    ("Molienda", OTRA),
    ("Flotación", ANIMADO),
    ("Fusión flash", ANIMADO),
    ("Conversión", ANIMADO),
    ("Ánodos", REPO_ONLY),
    ("Electrorrefinación", REPO_ONLY),
)
RUTA_HIDRO = (
    ("Mineral oxidado (chancado)", "materia prima"),
    ("Lixiviación", REPO_ONLY),
    ("Extracción por solventes", REPO_ONLY),
    ("Electroobtención", ANIMADO),
)

DOCS = {
    FLOT: "docs/flotacion.md",
    EW: "docs/ew.md",
    FLASH: "docs/fusion.md",
    CONV: "docs/conversion.md",
}
N_LIMITS = 4  # los «límites del modelo» (claves limits.1 a limits.4)


def markdown_table(df: pd.DataFrame) -> str:
    """Tabla en Markdown: el texto largo se ajusta a la columna en vez de cortarse."""

    def cell(v: object) -> str:
        return str(v).replace("|", "\\|").replace("\n", " ")

    head = "| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns) + "\n"
    return head + "\n".join("| " + " | ".join(cell(v) for v in row) + " |" for row in df.values)


def _box(x: int, y: int, name: str, state: str) -> str:
    fill, stroke, dash, color = PAPER, STEEL, "", INK
    if state == ANIMADO:
        fill, stroke, color = BRONZE, INK, "#FFFFFF"
    elif state == PROXIMO:
        dash = ' stroke-dasharray="6 4"'
    lines = textwrap.wrap(t("route.step." + name), 18)
    size = 12 if max(len(ln) for ln in lines) > 14 else 13
    label = "".join(
        text(
            x + 55, y + (31 if len(lines) == 1 else 24 + 16 * n), line, size, "middle", color=color
        )
        for n, line in enumerate(lines)
    )
    status = text(x + 55, y + 70, t("route.state." + state), 11, "middle", color=STEEL)
    return (
        f'<rect x="{x}" y="{y}" width="110" height="54" rx="6" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="2"{dash}/>{label}{status}'
    )


def _arrow(x1: int, x2: int, y: int) -> str:
    return (
        f'<path d="M {x1} {y} L {x2 - 6} {y}" stroke="{INK}" stroke-width="2" fill="none"/>'
        f'<path d="M {x2 - 8} {y - 5} L {x2} {y} L {x2 - 8} {y + 5} Z" fill="{INK}"/>'
    )


def route_map() -> str:
    """Mapa estático de la ruta del concentrado al cátodo: sin números ni animación."""
    step, x0, y_pyro, y_hydro = 140, 20, 80, 230
    body = text(20, 30, t("route.title"), 17, cls="t")
    body += text(20, y_pyro - 14, t("route.pyro"), 12, color=STEEL)
    body += text(20, y_hydro - 14, t("route.hydro"), 12, color=STEEL)
    for i, (name, state) in enumerate(RUTA_PIRO):
        body += _box(x0 + i * step, y_pyro, name, state)
        body += _arrow(x0 + i * step + 110, x0 + (i + 1) * step, y_pyro + 27)
    body += _box(x0 + len(RUTA_PIRO) * step, y_pyro, "Cátodo de Cu", REPO_ONLY)
    for i, (name, state) in enumerate(RUTA_HIDRO):  # tiene su propio punto de partida
        xi = x0 + i * step
        body += _box(xi, y_hydro, name, state)
        body += _arrow(xi + 110, xi + step, y_hydro + 27)
    body += _box(x0 + len(RUTA_HIDRO) * step, y_hydro, "Cátodo de Cu", REPO_ONLY)
    body += text(20, 335, t("route.note"), 12, color=STEEL)
    return svg(1000, 350, body, True, t("route.label"))


def _app_link(url: str) -> str:
    """El enlace a otra app del autor, en el mismo idioma (`?lang=` solo vale es o en)."""
    return url + "?lang=en" if current() == "en" else url


def limits() -> list[str]:
    return [t(f"limits.{n}") for n in range(1, N_LIMITS + 1)]


def ficha(equipo: str) -> None:
    """Ficha de un equipo, arriba de su pestaña: qué hace, qué entra, qué sale, de quién sale."""
    st.markdown(t("ficha.label.hace", text=t(f"ficha.{equipo}.hace")))
    st.markdown(t("ficha.label.entra", text=t(f"ficha.{equipo}.entra")))
    st.markdown(t("ficha.label.sale", text=t(f"ficha.{equipo}.sale")))
    with st.expander(t("ficha.expander")):
        st.markdown(markdown_table(data_table(equipo).drop(columns=t("col.equipo"))))
    doc = DOCS[equipo]
    st.caption(t("ficha.caption", autores=t(f"ficha.{equipo}.autores"), doc=doc,
                 url=f"{REPO}/blob/main/{doc}"))  # fmt: skip


def guide_tab() -> None:
    st.markdown(t("guide.h.simula"))
    st.markdown(t("guide.simula"))
    st.markdown(t("guide.h.ruta"))
    st.html(as_images(route_map(), route_map(), t("guide.ruta.alt")))
    st.markdown(t("guide.ruta", conminucion=_app_link(CONMINUCION), repo=REPO))
    st.markdown(t("guide.h.leer"))
    st.markdown(t("guide.leer"))
    st.markdown(t("guide.h.datos"))
    st.markdown(t("guide.datos"))
    group_col = t("col.equipo")
    for group, rows in data_table().groupby(group_col, sort=False):
        st.markdown(f"**{group}**")
        st.markdown(markdown_table(rows.drop(columns=group_col)))
    st.markdown(t("guide.h.limites"))
    for item in limits():
        st.markdown(f"- {item}")
