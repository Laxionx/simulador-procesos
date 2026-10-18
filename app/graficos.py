"""Gráficos de la app con Plotly: recuperación acumulada del banco de flotación (con los datos
medidos de Vinnett et al. 2022) y componentes del voltaje de la celda de electroobtención."""

from __future__ import annotations

import plotly.graph_objects as go
from calculo import MEASURED_CELLS, MEASURED_CU_PCT, EWView, FlotationView
from calculo_piro import ConverterView
from dibujo import BRONZE, COPPER, INK, PAPER, STEEL, es
from i18n import t, tm

FONT = dict(family="Segoe UI, Helvetica, Arial, sans-serif", color=INK, size=13)
COMPONENT_COLORS = {
    "reversible": "#4F5F69",
    "anódico": "#3B82A6",
    "catódico": "#C0462B",
    "electrolito": "#B7791F",
    "contactos": "#8E979C",
}


def _layout(fig: go.Figure, title: str, height: int, **axes: dict) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(family="Georgia, serif", size=17)),
        paper_bgcolor=PAPER, plot_bgcolor="#FBF9F4", font=FONT, height=height,
        margin=dict(l=60, r=20, t=60, b=50), legend=dict(bgcolor="rgba(0,0,0,0)"),
    )  # fmt: skip
    fig.update_xaxes(gridcolor="#E4DED2", linecolor=STEEL, **axes.get("x", {}))
    fig.update_yaxes(gridcolor="#E4DED2", linecolor=STEEL, **axes.get("y", {}))
    return fig


def recovery_figure(view: FlotationView) -> go.Figure:
    """Recuperación acumulada de Cu tras cada celda (modelo) y los puntos medidos del banco A."""
    cells = list(range(1, view.params.cells + 1))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cells, y=[100 * r for r in view.cu_cumulative], mode="lines+markers",
        name=t("plot.rec.model"), line=dict(color=BRONZE, width=3),
        marker=dict(size=7),
    ))  # fmt: skip
    fig.add_trace(go.Scatter(
        x=list(MEASURED_CELLS), y=list(MEASURED_CU_PCT), mode="markers",
        name=t("plot.rec.measured"),
        marker=dict(size=11, symbol="diamond", color=INK, line=dict(color=PAPER, width=1.5)),
    ))  # fmt: skip
    top = max(view.params.cells, max(MEASURED_CELLS))
    return _layout(fig, t("plot.rec.title"), 400,
                   x=dict(title=t("plot.rec.x"), dtick=1, range=[0.5, top + 0.5]),
                   y=dict(title=t("plot.rec.y"), range=[0, 102]))  # fmt: skip


def voltage_figure(view: EWView) -> go.Figure:
    """Barra apilada con lo que suma el voltaje de la celda, componente por componente."""
    fig = go.Figure()
    for name, volts in view.result.components.items():
        fig.add_trace(go.Bar(
            y=[t("plot.volt.cell")], x=[volts], name=f"{tm(name)} ({es(volts, 2)} V)",
            orientation="h",
            marker=dict(color=COMPONENT_COLORS.get(name, COPPER)),
            text=[f"{es(volts, 2)} V"], textposition="inside", insidetextanchor="middle",
            textfont=dict(color="#FFFFFF"),
        ))  # fmt: skip
    fig.update_layout(barmode="stack")
    fig.update_layout(annotations=[dict(
        text=t("plot.volt.total", v=es(view.result.cell_voltage, 2)), x=1, y=1.12, xref="paper",
        yref="paper", showarrow=False, xanchor="right", font=dict(family="Georgia, serif", size=15),
    )])  # fmt: skip
    return _layout(fig, t("plot.volt.title"), 260,
                   x=dict(title=t("plot.volt.x"), range=[0, view.result.cell_voltage * 1.02]),
                   y=dict(showticklabels=False))  # fmt: skip


def converter_balance_rows(view: ConverterView) -> list[tuple[str, str, float]]:
    """(soplado, concepto, t) de lo que entra y sale de cada soplado, con el O₂ que reacciona:
    entra = sale por masa."""
    carga, fin_escoria, fin_cobre = view.states
    return [
        ("Soplado a escoria", "entra: mata", carga.lower_t),
        ("Soplado a escoria", "entra: fundente", view.flux_t),
        ("Soplado a escoria", "entra: O₂ que reacciona", fin_escoria.o2_t),
        ("Soplado a escoria", "sale: metal blanco", fin_escoria.lower_t),
        ("Soplado a escoria", "sale: escoria", fin_escoria.slag_t),
        ("Soplado a escoria", "sale: SO₂", fin_escoria.so2_t),
        ("Soplado a cobre", "entra: metal blanco", fin_escoria.lower_t),
        ("Soplado a cobre", "entra: O₂ que reacciona", fin_cobre.o2_t),
        ("Soplado a cobre", "sale: blíster", fin_cobre.lower_t),
        ("Soplado a cobre", "sale: escoria", fin_cobre.slag_t),
        ("Soplado a cobre", "sale: SO₂", fin_cobre.so2_t),
    ]


def converter_figure(view: ConverterView) -> go.Figure:
    """Barras apiladas por soplado: lo que entra y lo que sale, en t (cierran por masa)."""
    rows = converter_balance_rows(view)
    colors = ["#8C5A2B", "#8E979C", "#3B82A6", "#B7791F", "#4F5F69", "#B8B0A0", "#C0462B"]
    concepts = list(dict.fromkeys(c for _, c, _ in rows))
    fig = go.Figure()
    for n, concept in enumerate(concepts):
        bars = [(stage, v) for stage, c, v in rows if c == concept]
        side = concept.split(":")[0]
        fig.add_trace(go.Bar(
            x=[f"{tm(stage)} ({tm(side)})" for stage, _ in bars], y=[v for _, v in bars],
            name=tm(concept),
            marker=dict(color=colors[n % len(colors)]),
            text=[es(v, 1) for _, v in bars], textposition="inside",
        ))  # fmt: skip
    fig.update_layout(barmode="stack")
    return _layout(fig, t("plot.conv.title"), 420,
                   x=dict(title=""), y=dict(title=t("plot.conv.y")))  # fmt: skip
