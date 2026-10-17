"""Pestaña «Guía» y fichas de cada equipo: qué hace, qué datos necesita, qué devuelve y de qué
autores salen las ecuaciones (las mismas fuentes de docs/)."""

from __future__ import annotations

import textwrap

import pandas as pd
import streamlit as st
from controles import CONV, EW, FLASH, FLOT, data_table
from dibujo import BRONZE, INK, PAPER, STEEL, as_images, svg, text

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

FICHAS = {
    FLOT: {
        "hace": "Separa el mineral de cobre (calcopirita, CuFeS₂) de la ganga. Las burbujas suben "
        "cargadas de partículas hidrofóbicas y la espuma que rebasa de cada celda es el "
        "concentrado; lo que no flota sigue de celda en celda y sale como relave.",
        "entra": "Pulpa de la alimentación del banco: CuFeS₂, SiO₂ (ganga) y agua. El ejemplo es "
        "el banco rougher A de Los Pelambres: unas 600 t/h de sólidos con 0,86 % de Cu.",
        "sale": "Concentrado y relave. Por especie: recuperación al concentrado y t/h que aporta "
        "cada celda; del concentrado, la ley de Cu y las t/h.",
        "autores": "Cinética de primer orden por especie y celdas de mezcla perfecta en serie "
        "(García-Zúñiga, 1935; Klimpel, 1980). Fórmulas de N celdas y datos medidos del banco: "
        "Vinnett, Pino-Muñoz, Yianatos, Díaz y Henríquez (2022), *Physicochem. Probl. Miner. "
        "Process.* 58(5), 152420. La recuperación fija de SiO₂ (5 %) y del agua (10 %) son "
        "supuestos del ejemplo, no medidas.",
        "doc": "docs/flotacion.md",
    },
    EW: {
        "hace": "Deposita cobre metálico sobre cátodos a partir de un electrolito de sulfato de "
        "cobre; en los ánodos se desprende oxígeno. Calcula cuánto cobre se deposita y qué "
        "voltaje pide la celda.",
        "entra": "Electrolito (Cu, ácido sulfúrico, temperatura) y la corriente: densidad de "
        "corriente por el área de las dos caras del cátodo.",
        "sale": "Cobre depositado (kg por cátodo al cabo del ciclo, y su espesor), corriente, "
        "voltaje de celda por componentes, potencia y energía por tonelada de cobre.",
        "autores": "Masa por la ley de Faraday con eficiencia de corriente. Voltaje de celda: "
        "Beukes y Badenhorst (2009), *J. South. Afr. Inst. Min. Metall.* 109 (potencial "
        "reversible y sobrepotenciales); conductividad del electrolito: Kalliomäki et al. "
        "(2021), *Miner. Eng.* 171, 107069; contactos y barras: Schlesinger et al. (2011), "
        "*Extractive Metallurgy of Copper*. Densidad del cobre sólido, 8,96 g/cm³: CRC Handbook "
        "of Chemistry and Physics.",
        "doc": "docs/ew.md",
    },
}

FICHAS[FLASH] = {
    "hace": "Funde el concentrado seco en el aire enriquecido con oxígeno que cae por la torre de "
    "reacción: el hierro y el azufre se oxidan, el calor de la reacción funde la carga y en el "
    "asentador se separan la mata (Cu₂S-FeS, abajo) y la escoria (encima). El azufre sale como "
    "SO₂.",
    "entra": "Una de las cuatro mezclas de concentrado de Atlantic Copper (Huelva), con metas "
    "de ley de mata, SiO₂ de la escoria y pérdida térmica; el modelo calcula el oxígeno, el "
    "enriquecimiento del aire y el fundente.",
    "sale": "Por tonelada de concentrado: kg de mata, de escoria y de SO₂, Nm³ de O₂ técnico, "
    "% de O₂ del aire y % de fundente. Del dibujo: volumen de cada capa (kg ÷ densidad).",
    "autores": "Balance de masa y de calor con el esquema de Bacedoni, Moreno-Ventas y Ríos "
    "(2020), *Metals* 10(9) 1229 (mineralogía, reparto de Cu y Zn, operación industrial); "
    "contenido calórico de matas: González, Patiño y Salinas (2001), *Rev. Soc. Quím. Méx.* "
    "45(1) 13. Densidades, solo para dibujar: Cu₂S 5,18 y FeS 3,80 g/cm³ (Nagamori, 1968, "
    "citado en Tesfaye Firdu y Taskinen, 2010, Aalto TKK-MT-215, Tabla 9), mezcla ideal para la "
    "mata (±10 %), escoria 3,7 g/cm³ (aprox.).",
    "doc": "docs/fusion.md",
}
FICHAS[CONV] = {
    "hace": "Convierte la mata en cobre soplando aire por las toberas. Primero el soplado a "
    "escoria oxida el hierro (con fundente de sílice forma la escoria) y deja metal blanco "
    "(Cu₂S); luego el soplado a cobre oxida el azufre y deja cobre blíster. Los dos sueltan SO₂.",
    "entra": "100 t de mata por carga, con su ley, y la eficiencia con que cada soplado "
    "aprovecha el oxígeno. El ejemplo usa parámetros públicos de Ilo (ilustrativo).",
    "sale": "Por soplado: aire (Nm³), fundente, escoria, metal blanco o blíster y SO₂ (t). Del "
    "dibujo: el volumen de cada fase (t ÷ densidad) en tres estados del baño.",
    "autores": "Balance por elemento y de calor de cada soplado, con datos de Lennartsson (2013, "
    "tesis, Luleå), Kyllo (1995, tesis, UBC; eficiencias de Flin Flon) y Morales, Palacios y "
    "Sánchez (2004, Molten Slags VII; escoria de Ilo). Densidades, solo para dibujar: mata y "
    "metal blanco por mezcla ideal Cu₂S-FeS (Nagamori, 1968; ±10 %), blíster = cobre líquido "
    "(Assael et al., 2010, *J. Phys. Chem. Ref. Data* 39, 033105, ec. 1), escoria 3,7 g/cm³ "
    "(aprox.; la del convertidor, con magnetita, es más densa).",
    "doc": "docs/conversion.md",
}

LIMITES = (
    "Estado estacionario: el banco y la celda no cambian en el tiempo.",
    "La alimentación de la flotación es fija (la del ejemplo de Los Pelambres); se cambian la "
    "cinética y la operación del banco. El horno flash funde las cuatro mezclas publicadas y el "
    "convertidor procesa 100 t de mata por carga.",
    "La celda de electroobtención se calcula para un cátodo con electrolito de composición "
    "fija; el depósito crece de forma pareja (sin nódulos ni dendritas).",
    "Las animaciones son esquemas: la posición de burbujas, el arrastre de la ganga, las "
    "burbujas de O₂ y el número de placas son ilustrativos. Cada esquema dice qué parte sale "
    "del cálculo.",
)


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
    lines = textwrap.wrap(name, 18)
    size = 12 if max(len(ln) for ln in lines) > 14 else 13
    label = "".join(
        text(
            x + 55, y + (31 if len(lines) == 1 else 24 + 16 * n), line, size, "middle", color=color
        )
        for n, line in enumerate(lines)
    )
    return (
        f'<rect x="{x}" y="{y}" width="110" height="54" rx="6" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="2"{dash}/>{label}{text(x + 55, y + 70, state, 11, "middle", color=STEEL)}'
    )


def _arrow(x1: int, x2: int, y: int) -> str:
    return (
        f'<path d="M {x1} {y} L {x2 - 6} {y}" stroke="{INK}" stroke-width="2" fill="none"/>'
        f'<path d="M {x2 - 8} {y - 5} L {x2} {y} L {x2 - 8} {y + 5} Z" fill="{INK}"/>'
    )


def route_map() -> str:
    """Mapa estático de la ruta del concentrado al cátodo: sin números ni animación."""
    step, x0, y_pyro, y_hydro = 140, 20, 80, 230
    body = text(20, 30, "Del mineral al cátodo de cobre: mapa de los equipos", 17, cls="t")
    body += text(20, y_pyro - 14, "Ruta pirometalúrgica (concentrado de sulfuros)", 12, color=STEEL)
    body += text(20, y_hydro - 14, "Ruta hidrometalúrgica (mineral lixiviable)", 12,
                 color=STEEL)  # fmt: skip
    for i, (name, state) in enumerate(RUTA_PIRO):
        body += _box(x0 + i * step, y_pyro, name, state)
        body += _arrow(x0 + i * step + 110, x0 + (i + 1) * step, y_pyro + 27)
    body += _box(x0 + len(RUTA_PIRO) * step, y_pyro, "Cátodo de Cu", REPO_ONLY)
    for i, (name, state) in enumerate(RUTA_HIDRO):  # tiene su propio punto de partida
        xi = x0 + i * step
        body += _box(xi, y_hydro, name, state)
        body += _arrow(xi + 110, xi + step, y_hydro + 27)
    body += _box(x0 + len(RUTA_HIDRO) * step, y_hydro, "Cátodo de Cu", REPO_ONLY)
    body += text(
        20, 335, "Mapa estático, sin números. Bronce: animado en esta app.", 12, color=STEEL
    )
    return svg(1000, 350, body, True, "Mapa del recorrido del concentrado al cátodo de cobre")


def ficha(equipo: str) -> None:
    """Ficha de un equipo, arriba de su pestaña: qué hace, qué entra, qué sale, de quién sale."""
    f = FICHAS[equipo]
    st.markdown(f"**Qué hace.** {f['hace']}")
    st.markdown(f"**Qué entra.** {f['entra']}")
    st.markdown(f"**Qué devuelve.** {f['sale']}")
    with st.expander("Qué datos necesita este equipo"):
        st.markdown(markdown_table(data_table(equipo).drop(columns="Equipo")))
    st.caption(
        f"**De dónde salen las ecuaciones.** {f['autores']} Detalle en "
        f"[{f['doc']}]({REPO}/blob/main/{f['doc']})."
    )


def guide_tab() -> None:
    st.markdown("### Qué simula")
    st.markdown(
        "Equipos de una planta de cobre, con **animaciones que salen del cálculo**: no son "
        "dibujos sueltos. Cada esquema se arma con las toneladas, las velocidades y los espesores "
        "que calcula el simulador (`procesos`, ecuaciones publicadas), y mueve las burbujas, la "
        "espuma y el depósito según esos números. Cambia un dato en la barra lateral y el "
        "esquema cambia."
    )
    st.markdown("### El recorrido del concentrado al cátodo")
    st.html(as_images(route_map(), route_map(), "Mapa del recorrido al cátodo de cobre"))
    st.markdown(
        "- **Animados aquí:** Flotación, Horno flash, Convertidor y Electroobtención "
        "(pestañas de arriba).\n"
        f"- **Molienda:** tiene su propia app animada, [simulador de conminución]({CONMINUCION}).\n"
        "- **En el simulador, sin animación todavía:** horno de ánodos, electrorrefinación, "
        f"lixiviación y extracción por solventes (en el [repositorio]({REPO}))."
    )
    st.markdown("### Cómo leer un esquema")
    st.markdown(
        "Cada esquema dice, debajo, qué parte sale del cálculo y qué parte es ilustrativa. "
        "Lo que sale del cálculo se puede comprobar en los números de al lado. Si tu sistema "
        "pide «reducir movimiento», verás la versión quieta; también hay un interruptor."
    )
    st.markdown("### Qué datos necesita")
    st.markdown(
        "Cada dato tiene una ayuda (**?**) en la barra lateral. El botón **Cargar ejemplo** pone "
        "todos los valores de la columna «Ejemplo»."
    )
    for group, rows in data_table().groupby("Equipo", sort=False):
        st.markdown(f"**{group}**")
        st.markdown(markdown_table(rows.drop(columns="Equipo")))
    st.markdown("### Lo que no hace")
    for item in LIMITES:
        st.markdown(f"- {item}")
