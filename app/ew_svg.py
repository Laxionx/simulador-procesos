"""Esquema animado de una celda de electroobtención, en corte lateral: ánodos y cátodos
alternados, y el depósito de cobre que engorda en los cátodos durante un ciclo de cosecha.

Lo que sale del cálculo: el espesor final del depósito (masa de Faraday × eficiencia ÷ (ρ ×
área de las dos caras)), dibujado con un factor DECLARADO (DEPOSIT_PX_PER_MM), y los kg por cátodo,
la corriente, el voltaje, la potencia y los kWh/t que se rotulan. Lo ilustrativo, y así se rotula:
el ciclo comprimido a CYCLE_S segundos, las burbujas de O₂ y el número de placas.
"""

from __future__ import annotations

from calculo import EWView
from dibujo import (
    BRONZE,
    COPPER,
    INK,
    RISE_CSS,
    STEEL,
    STEEL_LIGHT,
    R,
    es,
    rise,
    scheme_note,
    svg,  # fmt: skip
    text,
)
from i18n import num_g, t

W, H = 940, 560
TANK_X, TANK_TOP, TANK_BOTTOM = 50.0, 150.0, 430.0
LIQUID_Y = 178.0
PITCH = 52.0  # px entre placas (ánodo, cátodo, ánodo...)
PLATES = 11  # 6 ánodos y 5 cátodos, solo para dibujar
PLATE_TOP, PLATE_BOTTOM = 112.0, 410.0
DEPOSIT_PX_PER_MM = 2.6  # factor DECLARADO: 1 mm real de depósito se dibuja con 2,6 px
BLANK_PX, ANODE_PX = 3.0, 7.0
CYCLE_S = 8.0  # el ciclo de cosecha, comprimido a este tiempo
O2_RISE_S = 2.4  # ilustrativo
DEPOSIT_COLOR = "#C97B4A"

MOTION_CSS = (
    RISE_CSS
    + "@keyframes pc-grow{0%{transform:scaleX(0)}88%{transform:scaleX(1)}100%{transform:scaleX(1)}}"
    + f"{R}.pc-grow{{transform-box:fill-box;animation:pc-grow linear infinite}}"
    + f"{R}.pc-grow-l{{transform-origin:right center}}{R}.pc-grow-r{{transform-origin:left center}}"
)


def deposit_px(thickness_mm: float) -> float:
    """Ancho dibujado (px) del depósito de una cara: espesor real × DEPOSIT_PX_PER_MM."""
    return thickness_mm * DEPOSIT_PX_PER_MM


def _deposit(cx: float, width: float, paused: bool) -> str:
    y, h = LIQUID_Y + 6, PLATE_BOTTOM - LIQUID_Y - 12
    out = []
    for side, x in (("l", cx - BLANK_PX / 2 - width), ("r", cx + BLANK_PX / 2)):
        cls = (
            ""
            if paused
            else f' class="pc-grow pc-grow-{side}" style="animation-duration:{CYCLE_S:g}s"'
        )
        out.append(
            f'<rect{cls} data-deposit-px="{width:.3f}" x="{x:.2f}" y="{y}" width="{width:.3f}" '
            f'height="{h}" fill="{DEPOSIT_COLOR}" stroke="{COPPER}" stroke-width=".6"/>'
        )
    return "".join(out)


def _plates(view: EWView, paused: bool) -> str:
    width = deposit_px(view.thickness_mm)
    out = []
    for i in range(PLATES):
        cx = TANK_X + PITCH / 2 + i * PITCH
        if i % 2 == 0:  # ánodo
            out.append(
                f'<rect x="{cx - ANODE_PX / 2:.1f}" y="{PLATE_TOP}" width="{ANODE_PX}" '
                f'height="{PLATE_BOTTOM - PLATE_TOP}" fill="#5A6670"/>'
            )
            for side in (-1, 1):
                for ph in (0.0, 0.5):
                    bubble = '<circle r="3" fill="#EAF3F7" fill-opacity=".85" stroke="#3B82A6"/>'
                    start = PLATE_BOTTOM - 30
                    phase = (ph + 0.2 * (i % 3)) % 1
                    x = cx + side * (ANODE_PX / 2 + 5)
                    out.append(rise(x, start, start - LIQUID_Y, O2_RISE_S, phase, bubble, paused))
        else:  # cátodo
            out.append(
                f'<rect x="{cx - BLANK_PX / 2}" y="{PLATE_TOP}" width="{BLANK_PX}" '
                f'height="{PLATE_BOTTOM - PLATE_TOP}" fill="{STEEL_LIGHT}"/>'
            )
            out.append(_deposit(cx, width, paused))
    return "".join(out)


def _panel(view: EWView) -> str:
    r = view.result
    x = TANK_X + PLATES * PITCH + 38
    rows = [
        (t("svg.ew.p.cathode"), f"{es(view.cathode_kg, 1)} kg", True),
        (t("svg.ew.p.thickness"), f"{es(view.thickness_mm, 2)} mm", True),
        (t("ew.m1"), f"{es(r.current_a, 0)} A", False),
        (t("ew.m2"), f"{es(r.cell_voltage, 2)} V", False),
        (t("ew.m3"), f"{es(r.power_kw, 2)} kW", False),
        (t("ew.m4"), f"{es(r.specific_energy_kwh_t, 0)} kWh/t", False),
    ]
    out, y = [], 175.0
    for label, value, big in rows:
        out.append(text(x, y, label, 12, color=STEEL))
        out.append(text(x, y + 22, value, 20 if big else 17, cls="t", color=COPPER if big else INK))
        y += 52
    return "".join(out)


def _legend(view: EWView) -> str:
    p = view.params
    y = H - 56
    rows = [
        t(
            "svg.ew.legend1",
            days=_days(p.cycle_days),
            cycle=num_g(CYCLE_S),
            px=es(DEPOSIT_PX_PER_MM),
        ),
        t("svg.ew.legend2"),
        scheme_note(),
    ]
    return "".join(text(TANK_X, y + 16 * n, s, 12, color=STEEL if n else INK)
                   for n, s in enumerate(rows))  # fmt: skip


def _days(d: float) -> str:
    if float(d).is_integer() and d != 1:
        return t("svg.ew.days", n=es(d, 0))
    return t("svg.ew.day", n=es(d, 1))


def ew_svg(view: EWView, paused: bool = False) -> str:
    width = TANK_X + PLATES * PITCH
    tank = (
        f'<rect x="{TANK_X}" y="{LIQUID_Y}" width="{width - TANK_X}" '
        f'height="{TANK_BOTTOM - LIQUID_Y}" fill="#CFE3EA"/>'
        f'<path d="M {TANK_X} {TANK_TOP} L {TANK_X} {TANK_BOTTOM} L {width} {TANK_BOTTOM} '
        f'L {width} {TANK_TOP}" fill="none" stroke="{STEEL}" stroke-width="3"/>'
        f'<rect x="{TANK_X - 4}" y="{PLATE_TOP - 6}" width="{width - TANK_X + 8}" height="6" '
        f'fill="{BRONZE}"/>'  # barra de contacto
    )
    pr = view.params
    title = text(24, 30, t("svg.ew.title"), 18, cls="t") + text(
        24, 50, t("svg.ew.sub", cu=es(pr.cu_g_l, 0), acid=es(pr.acid_g_l, 0),
                  temp=es(pr.temp_c, 0), j=es(pr.current_density, 0),
                  eff=es(100 * pr.efficiency, 0)), 13)  # fmt: skip
    labels = text(
        TANK_X + PITCH / 2, PLATE_TOP - 14, t("svg.ew.anode"), 11, "middle", color=STEEL
    ) + text(TANK_X + 1.5 * PITCH, PLATE_TOP - 14, t("svg.ew.cathode"), 11, "middle", color=STEEL)
    body = title + tank + _plates(view, paused) + labels + _panel(view) + _legend(view)
    return svg(W, H, body, paused, t("svg.ew.label"), MOTION_CSS)
