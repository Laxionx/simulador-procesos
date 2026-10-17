"""Auxiliares compartidos por los esquemas animados: paleta «cuaderno de planta», marco SVG,
CSS de movimiento y la entrega como imagen.

Los esquemas se arman solo con números del cálculo y textos fijos: nada que escriba el visitante
entra al dibujo. Se muestran como imagen (<img>, data URL), así que el navegador no ejecuta nada
de ellos. Con «reducir movimiento» en el sistema se ve la versión quieta.
"""

from __future__ import annotations

import base64
from html import escape

INK, PAPER, STEEL, STEEL_LIGHT = "#1F2A30", "#F5F1E8", "#4F5F69", "#A7B3BA"
WATER, BRONZE, GANGUE, COPPER = "#3B82A6", "#B7791F", "#8E979C", "#C0462B"
SANS = "Segoe UI, Helvetica, Arial, sans-serif"
SERIF = "Georgia, 'Times New Roman', serif"
R = ".pc-svg "  # todo el CSS del esquema queda dentro de su raíz
SCHEME_NOTE = "esquema, no a escala: las cantidades sí son del cálculo"


def es(x: float, decimals: int = 1) -> str:
    """Número con coma decimal y espacio de miles."""
    return f"{x:,.{decimals}f}".replace(",", " ").replace(".", ",")


def _css(motion_css: str, paused: bool) -> str:
    base = (
        f"{R}text{{font-family:{SANS};fill:{INK}}} {R}.pc-t{{font-family:{SERIF};font-weight:700}}"
        f"{R}.pc-lbl{{paint-order:stroke;stroke:{PAPER};stroke-width:4px;stroke-linejoin:round}}"
    )
    if paused:
        return base
    return (
        base
        + motion_css
        + f"@media (prefers-reduced-motion: reduce){{{R}*{{animation:none!important}}}}"
    )


def svg(width: int, height: int, body: str, paused: bool, label: str, motion_css: str = "") -> str:
    """Marco SVG. `motion_css` (keyframes y reglas de cada equipo) solo se incluye si se mueve."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" class="pc-svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="{escape(label)}">'
        f"<style>{_css(motion_css, paused)}</style>"
        f'<rect width="{width}" height="{height}" fill="{PAPER}"/>{body}</svg>'
    )


# Una regla de la página elige qué versión se ve: la quieta si el sistema pide reducir movimiento.
MOTION_CSS = (
    "<style>.pc-still{display:none}"
    "@media (prefers-reduced-motion: reduce){.pc-anim{display:none}.pc-still{display:block}}"
    "</style>"
)


def as_images(animated: str, still: str, alt: str) -> str:
    """Las dos versiones del esquema como <img> (data URL). Si la animación está apagada,
    `animated` ya es la versión quieta."""

    def tag(source: str, cls: str) -> str:
        data = base64.b64encode(source.encode("utf-8")).decode("ascii")
        return (
            f'<img class="{cls}" alt="{escape(alt)}" style="width:100%;height:auto" '
            f'src="data:image/svg+xml;base64,{data}">'
        )

    if animated == still:
        return tag(still, "pc-plain")
    return tag(animated, "pc-anim") + tag(still, "pc-still")


def text(x: float, y: float, s: str, size: int = 13, anchor: str = "start", cls: str = "",
         color: str = INK) -> str:  # fmt: skip
    c = f' class="pc-{cls}"' if cls else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" '
        f'style="fill:{color}"{c}>{escape(s)}</text>'
    )


def rise(x: float, y: float, dist: float, duration: float, phase: float, inner: str,
         paused: bool) -> str:  # fmt: skip
    """Grupo que sube `dist` px desde (x, y) y se repite cada `duration` s. `phase` (0 a 1) es en
    qué punto del ciclo va. Quieto, queda congelado en ese punto del ciclo."""
    if paused:
        return f'<g transform="translate({x:.1f} {y - phase * dist:.1f})">{inner}</g>'
    style = (f"--d:{dist:.1f}px;animation-duration:{duration:.4f}s;"
             f"animation-delay:-{phase * duration:.4f}s")  # fmt: skip
    return (f'<g transform="translate({x:.1f} {y:.1f})">'
            f'<g class="pc-rise" style="{style}">{inner}</g></g>')  # fmt: skip


RISE_CSS = (
    "@keyframes pc-rise{from{transform:translateY(0)}to{transform:translateY(calc(-1*var(--d)))}}"
    f"{R}.pc-rise{{animation:pc-rise linear infinite}}"
)


DASH = 36.0  # px que avanza el trazo de un flujo en un ciclo
DASH_CSS = (
    f"@keyframes pc-run{{to{{stroke-dashoffset:-{DASH:g}}}}}"
    f"{R}.pc-dash{{animation:pc-run linear infinite}}"
)


def flow(d: str, width: float, color: str, speed_px_s: float, paused: bool) -> str:
    """Flujo dibujado como trazo grueso (`width`) con rayitas que avanzan a `speed_px_s`."""
    w = max(width, 1.0)
    base = (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w:.2f}" '
            f'stroke-linecap="round"/>')  # fmt: skip
    dur = "" if paused else f' style="animation-duration:{DASH / max(speed_px_s, 1.0):.4f}s"'
    dashes = (
        f'<path class="pc-dash" d="{d}" fill="none" stroke="#FFFFFF" stroke-opacity=".6" '
        f'stroke-width="{max(w / 3, 1.2):.2f}" stroke-dasharray="6 {DASH - 6:g}"{dur}/>'
    )
    return base + dashes
