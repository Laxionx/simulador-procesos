"""Esquema animado del banco de flotación: N celdas en serie.

Lo que sale del cálculo: el número de celdas; el ritmo de subida de las burbujas (BUBBLE_RATE_PER_K
× k burbujas por segundo en cada celda); cuántas de ellas llevan CuFeS₂ (proporcional a los t/h
de CuFeS₂ que esa celda manda al concentrado); y el grosor de la espuma de cada celda
(proporcional a los t/h de sólidos que esa celda manda al concentrado). Lo ilustrativo, y así se
rotula: la posición de las burbujas, el arrastre de la ganga (ritmo fijo) y el tamaño de la celda.
"""

from __future__ import annotations

import math

from calculo import FlotationView
from dibujo import (
    BRONZE,
    GANGUE,
    INK,
    RISE_CSS,
    STEEL,
    WATER,
    es,
    rise,
    scheme_note,
    svg,
    text,  # fmt: skip
)
from i18n import t

W, H = 960, 520
X0, X1 = 120.0, 880.0
PULP_Y, TANK_H = 262.0, 150.0
FROTH_MAX_PX = 100.0  # alto de la espuma de la celda que más sólidos manda
BUBBLE_RATE_PER_K = 6.0  # burbujas cargadas por segundo y por celda, por cada 1/min de k
BUBBLES_PER_CELL = 6  # 2 columnas × 3 burbujas; su ciclo dura BUBBLES_PER_CELL / ritmo
GANGUE_RISE_S = 7.0  # el arrastre no tiene cinética: ritmo fijo e ilustrativo
BUBBLE_R = 5.0


def bubble_rate(k: float) -> float:
    """Burbujas cargadas de Cu que llegan a la espuma de cada celda por segundo."""
    return BUBBLE_RATE_PER_K * k


def rise_duration_s(k: float) -> float:
    """Segundos que dura el ciclo de las burbujas de una celda: BUBBLES_PER_CELL / ritmo."""
    return BUBBLES_PER_CELL / bubble_rate(k)


def froth_heights(view: FlotationView) -> list[tuple[float, float]]:
    """(alto del Cu, alto de la ganga) de la espuma de cada celda en px, proporcional a los t/h
    de sólidos que manda al concentrado; la celda con más sólidos mide FROTH_MAX_PX."""
    top = max(view.solids_t_h, default=0.0)
    if top <= 0:
        return [(0.0, 0.0)] * view.params.cells
    scale = FROTH_MAX_PX / top
    return [(c * scale, g * scale) for c, g in zip(view.cu_t_h, view.gangue_t_h, strict=True)]


def loaded_counts(view: FlotationView) -> list[int]:
    """Burbujas con partícula de CuFeS₂ de cada celda: proporcionales a los t/h de CuFeS₂ que
    esa celda manda al concentrado, normalizados a la celda con más (que lleva todas las
    burbujas del dibujo). Redondeo al entero más cercano (mitad hacia arriba); las demás suben
    vacías. En primer orden, lo que flota en una celda es k × el Cu que queda en ella."""
    top = max(view.cu_t_h, default=0.0)
    if top <= 0:
        return [0] * view.params.cells
    return [math.floor(BUBBLES_PER_CELL * c / top + 0.5) for c in view.cu_t_h]


def _bubble(loaded: bool, cell: int = 0) -> str:
    out = (f'<circle r="{BUBBLE_R}" fill="#EAF3F7" fill-opacity=".8" stroke="{WATER}" '
           f'stroke-width="1.2"/>')  # fmt: skip
    if loaded:
        out += (f'<circle class="pc-loaded" data-cell="{cell}" cx="{BUBBLE_R * 0.55:.1f}" '
                f'cy="{-BUBBLE_R * 0.4:.1f}" r="2.4" fill="{BRONZE}"/>')  # fmt: skip
    return out


def _cell(i: int, x: float, w: float, view: FlotationView, heights: tuple[float, float],
          k: float, paused: bool) -> str:  # fmt: skip
    cu_h, g_h = heights
    parts = [
        f'<rect x="{x:.1f}" y="{PULP_Y}" width="{w:.1f}" height="{TANK_H}" fill="#DCE8EE" '
        f'stroke="{STEEL}" stroke-width="2"/>'
    ]
    dist, duration = TANK_H - 20, rise_duration_s(k)
    loaded = loaded_counts(view)[i]
    slots = [(col, b) for b in range(3) for col in range(2)]  # se cargan en este orden
    for n, (col, b) in enumerate(slots):
        phase = (b + 0.5 * col) / 3 % 1.0
        parts.append(
            rise(
                x + w * (0.3, 0.7)[col],
                PULP_Y + TANK_H - 8,
                dist,
                duration,
                phase,
                _bubble(n < loaded, i + 1),
                paused,
            )
        )
    parts.append(rise(x + w * 0.5, PULP_Y + TANK_H - 8, dist, GANGUE_RISE_S, (i * 0.37) % 1.0,
                      f'<circle r="2.2" fill="{GANGUE}"/>', paused))  # fmt: skip
    y = PULP_Y
    for kind, hgt, color in (("gangue", g_h, GANGUE), ("cu", cu_h, BRONZE)):
        if hgt > 0:
            y -= hgt
            parts.append(f'<rect class="pc-froth-{kind}" data-cell="{i + 1}" x="{x + 2:.1f}" '
                         f'y="{y:.2f}" width="{w - 4:.1f}" height="{hgt:.2f}" fill="{color}" '
                         f'fill-opacity=".9"/>')  # fmt: skip
    t_h = view.solids_t_h[i]
    parts.append(text(x + w / 2, PULP_Y - FROTH_MAX_PX - 14, es(t_h, 1), 11 if w > 40 else 9,
                      "middle", color=INK))  # fmt: skip
    parts.append(text(x + w / 2, PULP_Y + TANK_H + 20, str(i + 1), 12, "middle"))
    parts.append(text(x + w / 2, PULP_Y + TANK_H + 38, f"{100 * view.cu_cumulative[i]:.0f} %",
                      11 if w > 40 else 9, "middle", color=STEEL))  # fmt: skip
    return "".join(parts)


def _legend(view: FlotationView) -> str:
    top = max(view.solids_t_h, default=0.0)
    y = H - 36
    items = [
        (BRONZE, t("svg.flot.legend1")),
        (GANGUE, t("svg.flot.legend2")),
    ]
    out = []
    for n, (color, label) in enumerate(items):
        out.append(f'<rect x="{X0}" y="{y - 10 + 16 * n}" width="12" height="12" fill="{color}"/>')
        out.append(text(X0 + 20, y + 16 * n, label, 12))
    out.append(text(X1, y, t("svg.flot.froth", top=es(top)), 12, "end"))
    out.append(text(X1, y + 16, scheme_note(), 12, "end", color=STEEL))
    return "".join(out)


def _static(view: FlotationView, n: int) -> str:
    mid = PULP_Y + TANK_H / 2
    arrows = (
        f'<path d="M 24 {mid} L {X0 - 6} {mid}" stroke="{INK}" stroke-width="4" fill="none"/>'
        f'<path d="M {X0 - 6} {mid - 7} L {X0 + 2} {mid} L {X0 - 6} {mid + 7} Z" fill="{INK}"/>'
        f'<path d="M {X1 + 6} {mid} L {W - 24} {mid}" stroke="{INK}" stroke-width="4" fill="none"/>'
        f'<path d="M {W - 30} {mid - 7} L {W - 22} {mid} L {W - 30} {mid + 7} Z" fill="{INK}"/>'
    )
    launder_y = PULP_Y - FROTH_MAX_PX - 6
    launder = (f'<path d="M {X0} {launder_y} L {X1 + 20} {launder_y}" stroke="{BRONZE}" '
               f'stroke-width="3" fill="none" stroke-dasharray="2 5"/>')  # fmt: skip
    labels = (
        text(24, mid - 14, t("svg.flot.feed"), 12)
        + text(W - 30, mid - 14, t("svg.flot.tails"), 12, "end")
        + text(X1 + 20, launder_y - 18, t("svg.flot.conc"), 12, "end", color=BRONZE)
        + text(X0 - 8, PULP_Y - FROTH_MAX_PX - 14, t("svg.flot.th"), 11, "end", color=STEEL)
        + text(X0 - 8, PULP_Y + TANK_H + 20, t("svg.flot.cell"), 11, "end", color=STEEL)
        + text(X0 - 8, PULP_Y + TANK_H + 38, t("svg.flot.cuacc"), 11, "end", color=STEEL)
    )
    title = text(24, 30, t("svg.flot.title", n=n), 18, cls="t") + text(
        24, 50, t("svg.flot.sub", rec=es(100 * view.recoveries["CuFeS2"]),
                  conc=es(view.concentrate_t_h), grade=es(view.cu_grade_pct)), 13)  # fmt: skip
    return arrows + launder + labels + title


def flotation_svg(view: FlotationView, paused: bool = False) -> str:
    n = view.params.cells
    pitch = (X1 - X0) / n
    w = pitch * 0.86
    heights = froth_heights(view)
    cells = "".join(_cell(i, X0 + i * pitch + (pitch - w) / 2, w, view, heights[i],
                          view.params.k, paused) for i in range(n))  # fmt: skip
    body = _static(view, n) + cells + _legend(view)
    return svg(W, H, body, paused, t("svg.flot.label"), RISE_CSS)
