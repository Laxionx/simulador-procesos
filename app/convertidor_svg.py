"""Esquema animado del convertidor Peirce-Smith: corte transversal (cilindro horizontal visto de
frente) con toberas a un costado y campana de gases arriba.

Lo que sale del cálculo: el área de cada fase en el corte es proporcional a su volumen (t ÷
densidad), a PX2_PER_M3 px² por m³; de ahí salen las alturas de las capas (segmento circular,
como el área de la carga de bolas de la app de conminución). El bucle pasa por tres estados del
cálculo (carga, fin del soplado a escoria, fin del soplado a cobre) con keyframes CSS que llevan
esas alturas; el grosor del aire que entra (Nm³) y del SO₂ que sale (t) de cada soplado también.
Lo ilustrativo, y así se rotula: la transición entre estados, las burbujas de aire en las
toberas y la forma del convertidor.
"""

from __future__ import annotations

import math
import textwrap

from calculo_piro import BathState, ConverterView
from colores import NOTE, darker, temperature_color
from dibujo import (
    DASH_CSS,
    INK,
    RISE_CSS,
    SCHEME_NOTE,
    STEEL,
    STEEL_LIGHT,
    WATER,
    R,
    es,
    flow,  # fmt: skip
    rise,
    svg,
    text,
)

W, H = 960, 640
CX, CY, RAD = 330.0, 300.0, 150.0
INNER = RAD - 8.0  # el baño llena el interior del revestimiento
PX2_PER_M3 = 1000.0  # área dibujada del baño por cada m³ de fase
AIR_PX_PER_NM3 = 0.0002  # grosor de la flecha de aire por Nm³ del soplado
SO2_PX_PER_T = 0.4  # grosor de la flecha de gases por t de SO₂ del soplado
CYCLE_S = 14.0  # el bucle pasa por los tres estados en este tiempo
# Tramos del bucle (% del ciclo) en que se queda quieto cada estado; entre ellos, transición.
HOLDS = ((0.0, 22.0), (33.0, 55.0), (66.0, 88.0))
AIR_BUBBLE_S = 1.6  # ilustrativo
MAX_FILL = 0.9  # fracción máxima del círculo que admite el dibujo


def charge_angle(fraction: float) -> float:
    """Ángulo central θ (rad) del segmento circular cuya área es la fracción `fraction` del
    círculo: θ − sen θ = 2π·fracción (bisección)."""
    if not 0.0 < fraction < 1.0:
        raise ValueError("La fracción del círculo debe estar entre 0 y 1")
    lo, hi = 0.0, 2.0 * math.pi
    for _ in range(80):
        mid = (lo + hi) / 2
        if mid - math.sin(mid) < 2.0 * math.pi * fraction:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def level_y(area_px2: float) -> float:
    """y (px del SVG) de la superficie de un baño cuya sección ocupa `area_px2` px²."""
    if area_px2 <= 0:
        return CY + INNER
    fraction = area_px2 / (math.pi * INNER**2)
    if fraction > MAX_FILL:
        raise ValueError("El baño no cabe en el dibujo del convertidor")
    theta = charge_angle(fraction)
    return CY + INNER - INNER * (1.0 - math.cos(theta / 2.0))


def levels(state: BathState) -> tuple[float, float]:
    """(y de la superficie de la fase de abajo, y de la superficie de la escoria)."""
    lower = PX2_PER_M3 * state.lower_m3
    return level_y(lower), level_y(lower + PX2_PER_M3 * state.slag_m3)


def air_width(air_nm3: float) -> float:
    return air_nm3 * AIR_PX_PER_NM3


def so2_width(so2_t: float) -> float:
    return so2_t * SO2_PX_PER_T


def _keyframes(name: str, values: list[str], prop: str) -> str:
    """Keyframes que valen `values[i]` en cada tramo de HOLDS y vuelven al primero al final."""
    stops = []
    for (a, b), v in zip(HOLDS, values, strict=True):
        stops.append(f"{a:g}%{{{prop}:{v}}}{b:g}%{{{prop}:{v}}}")
    stops.append(f"100%{{{prop}:{values[0]}}}")
    return f"@keyframes {name}{{{''.join(stops)}}}"


def _motion_css(view: ConverterView) -> str:
    low = [levels(s)[0] - (CY - RAD) for s in view.states]
    top = [levels(s)[1] - (CY - RAD) for s in view.states]
    air = ["0", *(f"{air_width(s.air_nm3):.2f}" for s in view.states[1:])]
    gas = ["0", *(f"{so2_width(s.so2_t):.2f}" for s in view.states[1:])]
    css = (
        _keyframes("pc-low", [f"translateY({v:.2f}px)" for v in low], "transform")
        + _keyframes("pc-top", [f"translateY({v:.2f}px)" for v in top], "transform")
        + _keyframes("pc-air", air, "stroke-width")
        + _keyframes("pc-gas", gas, "stroke-width")
    )
    for i, (a, b) in enumerate(HOLDS):  # cada rótulo de estado se ve solo en su tramo
        if i == 0:
            stops = [(0, 1), (b, 1), (b + 3, 0), (97, 0), (100, 1)]
        else:
            stops = [(0, 0), (a - 3, 0), (a, 1), (b, 1), (b + 3, 0), (100, 0)]
        css += (
            f"@keyframes pc-show{i}{{" + "".join(f"{p:g}%{{opacity:{o}}}" for p, o in stops) + "}"
        )
    t = f"{CYCLE_S:g}s linear infinite"
    css += f"{R}.pc-low{{animation:pc-low {t}}}{R}.pc-top{{animation:pc-top {t}}}"
    css += f"{R}.pc-airw{{animation:pc-air {t}}}{R}.pc-gasw{{animation:pc-gas {t}}}"
    for i in range(3):
        css += f"{R}.pc-state{i}{{animation:pc-show{i} {t}}}"
    return css


def _bath(view: ConverterView, paused: bool) -> str:
    hot = temperature_color(view.params.bath_c)
    slag = darker(hot)
    box = f'x="{CX - RAD}" width="{2 * RAD}" height="{2 * RAD + 40}"'
    if paused:  # versión quieta: el fin del soplado a escoria, con las dos fases
        low, top = levels(view.states[1])
        rects = f'<rect {box} y="{top:.2f}" fill="{slag}"/><rect {box} y="{low:.2f}" fill="{hot}"/>'
    else:
        low, top = levels(view.states[0])  # el keyframe empuja la caja desde el borde de arriba
        y0 = CY - RAD
        rects = (
            f'<rect class="pc-top" data-y0="{y0:.2f}" {box} y="{y0:.2f}" fill="{slag}"/>'
            f'<rect class="pc-low" data-y0="{y0:.2f}" {box} y="{y0:.2f}" fill="{hot}"/>'
        )
    return (
        f'<clipPath id="pc-inside"><circle cx="{CX}" cy="{CY}" r="{INNER}"/></clipPath>'
        f'<circle cx="{CX}" cy="{CY}" r="{INNER}" fill="#F5F1E8"/>'
        f'<g clip-path="url(#pc-inside)">{rects}</g>'
    )


def _shell(view: ConverterView, paused: bool) -> str:
    hood_y = CY - RAD
    shell = (
        f'<circle cx="{CX}" cy="{CY}" r="{RAD - 4}" fill="none" stroke="{STEEL}" '
        f'stroke-width="8"/>'
        f'<path d="M {CX - 45} {hood_y + 6} L {CX - 28} {hood_y - 60} L {CX + 28} {hood_y - 60} '
        f'L {CX + 45} {hood_y + 6}" fill="#F5F1E8" stroke="{STEEL}" stroke-width="4"/>'
    )
    # toberas: tubos que entran por el costado izquierdo, hacia el centro
    a = math.radians(200.0)
    tx, ty = CX + RAD * math.cos(a), CY - RAD * math.sin(a)
    tuyere = (
        f'<path d="M {tx - 60:.1f} {ty:.1f} L {tx + 14:.1f} {ty:.1f}" stroke="{STEEL_LIGHT}" '
        f'stroke-width="12"/>'
    )
    bubbles = "".join(
        rise(tx + 22 + 7 * n, ty - 4, 70, AIR_BUBBLE_S, n / 4,
             f'<circle r="3" fill="#EAF3F7" fill-opacity=".85" stroke="{WATER}"/>', paused)
        for n in range(4)
    )  # fmt: skip
    return shell + tuyere + bubbles


def _flows(view: ConverterView, paused: bool) -> str:
    s2 = view.states[1]
    tx = CX + RAD * math.cos(math.radians(200.0)) - 60
    ty = CY - RAD * math.sin(math.radians(200.0))
    air_d = f"M {tx - 90:.1f} {ty:.1f} L {tx:.1f} {ty:.1f}"
    gas_d = f"M {CX} {CY - RAD - 50} L {CX} 40"
    if paused:  # quieto: los grosores del fin del soplado a escoria
        return (flow(air_d, air_width(s2.air_nm3), WATER, 40.0, True)
                + flow(gas_d, so2_width(s2.so2_t), "#B8B0A0", 40.0, True))  # fmt: skip
    out = ""
    for d, cls, color in ((air_d, "pc-airw", WATER), (gas_d, "pc-gasw", "#B8B0A0")):
        out += flow(d, 1.0, color, 40.0, False).replace(
            'stroke-linecap="round"', f'class="{cls}" stroke-linecap="round"', 1
        )
    return out


def _panel(view: ConverterView) -> str:
    out, y = [], 120.0
    for i, s in enumerate(view.states):
        out.append(text(570, y, f"{i + 1} · {s.name}", 13, cls="t"))
        out.append(text(570, y + 18, f"{s.lower_name}: {es(s.lower_t, 1)} t, "
                        f"{es(s.lower_g_cm3, 2)} g/cm³, {es(s.lower_m3, 1)} m³", 12))  # fmt: skip
        slag = (f"escoria: {es(s.slag_t, 1)} t, {es(s.slag_m3, 1)} m³" if s.slag_t > 0
                else "sin escoria todavía")  # fmt: skip
        out.append(text(570, y + 35, slag, 12))
        blow = (f"soplado: {es(s.air_nm3, 0)} Nm³ de aire, {es(s.so2_t, 1)} t de SO₂"
                if s.air_nm3 > 0 else "antes de soplar")  # fmt: skip
        out.append(text(570, y + 52, blow, 12, color=STEEL))
        y += 90
    return "".join(out)


def _state_labels(view: ConverterView, paused: bool) -> str:
    if paused:
        return text(CX, CY + RAD + 36, "Fin del soplado a escoria (estado 2 de 3)", 14,
                    "middle", cls="t")  # fmt: skip
    return "".join(
        f'<g class="pc-state{i}">'
        + text(CX, CY + RAD + 36, f"Estado {i + 1} de 3: {s.name}", 14, "middle", cls="t")
        + "</g>"
        for i, s in enumerate(view.states)
    )


def _legend(view: ConverterView) -> str:
    paragraphs = [
        f"Área del baño ∝ volumen de cada fase (t ÷ densidad): {PX2_PER_M3:g} px² por m³. Mata y "
        "metal blanco por mezcla ideal Cu₂S-FeS (±10 %); blíster = Cu líquido; escoria 3,7 g/cm³ "
        "(aprox.: la del convertidor, con magnetita, es más densa).",
        f"El bucle de {CYCLE_S:g} s pasa por tres estados del cálculo; la transición entre ellos, "
        "las burbujas de las toberas y la forma son ilustrativas. Grosor del aire ∝ Nm³ y del SO₂ "
        f"∝ t de cada soplado. Color: {NOTE} del baño ({es(view.params.bath_c, 0)} °C).",
    ]
    lines = [ln for para in paragraphs for ln in textwrap.wrap(para, 135)] + [SCHEME_NOTE]
    top = H - 17 * len(lines) - 4
    return "".join(
        text(24, top + 17 * n, ln, 12, color=INK if n == len(lines) - 1 else STEEL)
        for n, ln in enumerate(lines)
    )


def converter_svg(view: ConverterView, paused: bool = False) -> str:
    title = text(24, 30, "Convertidor Peirce-Smith, corte transversal", 18, cls="t")
    body = (
        title + _bath(view, paused) + _shell(view, paused) + _flows(view, paused)
        + _state_labels(view, paused) + _panel(view) + _legend(view)
    )  # fmt: skip
    css = RISE_CSS + DASH_CSS + _motion_css(view)
    return svg(W, H, body, paused, "Convertidor Peirce-Smith con baño de mata, metal y escoria",
               css)  # fmt: skip
