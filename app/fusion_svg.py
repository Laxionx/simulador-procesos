"""Esquema animado del horno flash: torre de reacción, asentador con escoria sobre mata y salida
de gases.

Lo que sale del cálculo: la altura de cada capa del baño (volumen por tonelada de concentrado =
kg/t ÷ densidad, a igual sección; PX_PER_M3_T px por m³/t); el grosor de la flecha de O₂ (Nm³/t)
y de la de gases (kg/t de SO₂), con la rapidez de sus rayitas proporcional al mismo caudal; y el
color de las capas (temperatura de los productos). Lo ilustrativo, y así se rotula: la llama y
las partículas que caen en la torre, y la forma del horno.
"""

from __future__ import annotations

from calculo_piro import FlashView
from colores import darker, temperature_color
from dibujo import (
    BRONZE,
    DASH_CSS,
    INK,
    RISE_CSS,
    STEEL,
    es,
    flow,
    rise,  # fmt: skip
    scheme_note,
    svg,
    text,
)
from i18n import num_g, t

W, H = 960, 580
SETTLER_X0, SETTLER_X1, BATH_BOTTOM, SETTLER_TOP = 130.0, 700.0, 450.0, 300.0
TOWER_X0, TOWER_X1, TOWER_TOP = 130.0, 250.0, 100.0
UPTAKE_X0, UPTAKE_X1 = 620.0, 700.0
PX_PER_M3_T = 500.0  # alto de capa dibujado por cada m³ de fase por t de concentrado
O2_PX_PER_NM3_T = 0.06  # grosor de la flecha de O₂ por cada Nm³/t
SO2_PX_PER_KG_T = 0.025  # grosor de la flecha de gases por cada kg/t de SO₂
O2_SPEED_PER_NM3_T = 0.25  # px/s de las rayitas por cada Nm³/t
SO2_SPEED_PER_KG_T = 0.10  # px/s de las rayitas por cada kg/t
FALL_S = 2.2  # las partículas caen en este tiempo: ilustrativo
PARTICLES = 10


def layer_heights(view: FlashView) -> tuple[float, float]:
    """(alto de la mata, alto de la escoria) en px: volumen por t de concentrado × escala."""
    return view.matte_m3_t * PX_PER_M3_T, view.slag_m3_t * PX_PER_M3_T


def o2_width(nm3_t: float) -> float:
    return nm3_t * O2_PX_PER_NM3_T


def gas_width(so2_kg_t: float) -> float:
    return so2_kg_t * SO2_PX_PER_KG_T


def _bath(view: FlashView) -> str:
    matte_h, slag_h = layer_heights(view)
    hot = temperature_color(view.result.products_k - 273.15)
    width = SETTLER_X1 - SETTLER_X0
    top_of_matte = BATH_BOTTOM - matte_h
    return (
        f'<rect class="pc-matte" x="{SETTLER_X0}" y="{top_of_matte:.2f}" width="{width}" '
        f'height="{matte_h:.2f}" fill="{hot}"/>'
        f'<rect class="pc-slag" x="{SETTLER_X0}" y="{top_of_matte - slag_h:.2f}" width="{width}" '
        f'height="{slag_h:.2f}" fill="{darker(hot)}"/>'
        + text(
            SETTLER_X0 + 10, top_of_matte - slag_h / 2 + 4, t("svg.flash.slag"), 13, color="#FFFFFF"
        )
        + text(
            SETTLER_X0 + 10,
            top_of_matte + matte_h / 2 + 4,
            t("svg.flash.matte"),
            13,
            color="#1F2A30",
        )
    )


def _furnace() -> str:
    wall = f'fill="none" stroke="{STEEL}" stroke-width="4" stroke-linejoin="round"'
    return (
        f'<path d="M {TOWER_X0} {TOWER_TOP} L {TOWER_X0} {BATH_BOTTOM} L {SETTLER_X1} '
        f'{BATH_BOTTOM} L {SETTLER_X1} 110" {wall}/>'
        f'<path d="M {TOWER_X1} {TOWER_TOP} L {TOWER_X1} {SETTLER_TOP} L {UPTAKE_X0} '
        f'{SETTLER_TOP} L {UPTAKE_X0} 110" {wall}/>'
        f'<path d="M {TOWER_X0} {TOWER_TOP} L {TOWER_X1} {TOWER_TOP}" {wall}/>'
    )


def _particles(paused: bool) -> str:
    out = []
    span = SETTLER_TOP - TOWER_TOP - 20
    for n in range(PARTICLES):
        x = TOWER_X0 + 14 + (n * 37) % (TOWER_X1 - TOWER_X0 - 28)
        color = BRONZE if n % 2 else "#8E979C"
        out.append(rise(x, TOWER_TOP + 20, -span, FALL_S, n / PARTICLES,
                        f'<circle r="3" fill="{color}"/>', paused))  # fmt: skip
    return "".join(out)


def _flows(view: FlashView, paused: bool) -> str:
    o2, so2 = view.result.oxygen_nm3_t, view.result.so2_kg
    conc = f"M {TOWER_X0 + 25} 62 L {TOWER_X0 + 25} {TOWER_TOP + 25}"
    air = f"M {TOWER_X1 - 25} 62 L {TOWER_X1 - 25} {TOWER_TOP + 25}"
    ux = (UPTAKE_X0 + UPTAKE_X1) / 2
    gas = f"M {ux} {SETTLER_TOP - 20} L {ux} 60 L 860 60"
    return (
        flow(conc, 8.0, BRONZE, 40.0, paused)
        + flow(air, o2_width(o2), "#3B82A6", O2_SPEED_PER_NM3_T * o2, paused)
        + flow(gas, gas_width(so2), "#B8B0A0", SO2_SPEED_PER_KG_T * so2, paused)
        + text(TOWER_X0 + 25, 54, t("svg.flash.conc"), 12, "middle")
        + text(TOWER_X1 - 12, 54, t("svg.flash.o2", v=es(o2, 1)), 12)
        + text(860, 48, t("svg.flash.gas", v=es(so2, 0)), 12, "end")
    )


def _panel(view: FlashView) -> str:
    r = view.result
    rows = [
        (
            t("svg.flash.p.matte"),
            t("svg.flash.kg_t", v=es(view.matte_kg_t, 0)),
            t("svg.flash.m3_t", v=es(view.matte_m3_t, 3)),
        ),
        (
            t("svg.flash.p.slag"),
            t("svg.flash.kg_t", v=es(view.slag_kg_t, 0)),
            t("svg.flash.m3_t", v=es(view.slag_m3_t, 3)),
        ),
        (
            t("svg.flash.p.enrich"),
            t("svg.flash.o2_pct", v=es(r.enrichment_pct, 1)),
            t("svg.flash.flux", v=es(r.flux_pct, 1)),
        ),
    ]
    out, y = [], 170.0
    for label, big, small in rows:
        out.append(text(730, y, label, 12, color=STEEL))
        out.append(text(730, y + 22, big, 18, cls="t"))
        out.append(text(730, y + 40, small, 12, color=STEEL))
        y += 78
    return "".join(out)


def _legend(view: FlashView) -> str:
    t_c = view.result.products_k - 273.15
    rows = [
        t(
            "svg.flash.legend1",
            px=num_g(PX_PER_M3_T),
            matte=es(view.matte_density, 2),
            slag=es(view.slag_density, 1),
        ),
        t("svg.flash.legend2", note=t("scheme.temp"), temp=es(t_c, 0)),
        scheme_note(),
    ]
    return "".join(text(24, H - 56 + 17 * n, s, 12, color=INK if n == 2 else STEEL)
                   for n, s in enumerate(rows))  # fmt: skip


def flash_svg(view: FlashView, paused: bool = False) -> str:
    title = text(24, 30, t("svg.flash.title"), 18, cls="t")
    body = (
        _furnace() + _bath(view) + _particles(paused) + _flows(view, paused) + _panel(view)
        + _legend(view) + title
    )  # fmt: skip
    return svg(W, H, body, paused, t("svg.flash.label"), RISE_CSS + DASH_CSS)
