"""Gráficos de la app con Plotly: recuperación acumulada del banco de flotación (con los datos
medidos de Vinnett et al. 2022) y componentes del voltaje de la celda de electroobtención."""

from __future__ import annotations

import plotly.graph_objects as go
from calculo import MEASURED_CELLS, MEASURED_CU_PCT, EWView, FlotationView
from dibujo import BRONZE, COPPER, INK, PAPER, STEEL, es

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
        name="modelo (primer orden, mezcla perfecta)", line=dict(color=BRONZE, width=3),
        marker=dict(size=7),
    ))  # fmt: skip
    fig.add_trace(go.Scatter(
        x=list(MEASURED_CELLS), y=list(MEASURED_CU_PCT), mode="markers",
        name="medido, Vinnett et al. 2022 (banco A)",
        marker=dict(size=11, symbol="diamond", color=INK, line=dict(color=PAPER, width=1.5)),
    ))  # fmt: skip
    top = max(view.params.cells, max(MEASURED_CELLS))
    return _layout(fig, "Recuperación acumulada de Cu por celda", 400,
                   x=dict(title="Celda", dtick=1, range=[0.5, top + 0.5]),
                   y=dict(title="Cu recuperado acumulado (%)", range=[0, 102]))  # fmt: skip


def voltage_figure(view: EWView) -> go.Figure:
    """Barra apilada con lo que suma el voltaje de la celda, componente por componente."""
    fig = go.Figure()
    for name, volts in view.result.components.items():
        fig.add_trace(go.Bar(
            y=["Celda"], x=[volts], name=f"{name} ({es(volts, 2)} V)", orientation="h",
            marker=dict(color=COMPONENT_COLORS.get(name, COPPER)),
            text=[f"{es(volts, 2)} V"], textposition="inside", insidetextanchor="middle",
            textfont=dict(color="#FFFFFF"),
        ))  # fmt: skip
    fig.update_layout(barmode="stack")
    fig.update_layout(annotations=[dict(
        text=f"Total: {es(view.result.cell_voltage, 2)} V", x=1, y=1.12, xref="paper",
        yref="paper", showarrow=False, xanchor="right", font=dict(family="Georgia, serif", size=15),
    )])  # fmt: skip
    return _layout(fig, "De qué se compone el voltaje de la celda", 260,
                   x=dict(title="Voltaje (V)", range=[0, view.result.cell_voltage * 1.02]),
                   y=dict(showticklabels=False))  # fmt: skip
