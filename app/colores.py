"""Color ilustrativo de la temperatura de un baño fundido. Rampa propia, monótona en
luminosidad, de rojo oscuro (500 °C) a blanco amarillento (1700 °C); fuera de ese rango se
satura. Es una rampa ilustrativa (no se pudo verificar la tabla de cuerpo negro de Mitchell
Charity, vendian.org, 2001), y así se rotula en los esquemas."""

from __future__ import annotations

STOPS = (
    (500.0, (70, 20, 15)),
    (800.0, (150, 30, 20)),
    (1000.0, (210, 70, 20)),
    (1200.0, (245, 140, 40)),
    (1300.0, (250, 175, 70)),
    (1500.0, (255, 225, 150)),
    (1700.0, (255, 245, 220)),
)


def temperature_rgb(temp_c: float) -> tuple[int, int, int]:
    t = min(max(temp_c, STOPS[0][0]), STOPS[-1][0])
    for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:], strict=False):
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            return tuple(round(a + (b - a) * f) for a, b in zip(c0, c1, strict=True))
    return STOPS[-1][1]


def temperature_color(temp_c: float) -> str:
    return "#{:02X}{:02X}{:02X}".format(*temperature_rgb(temp_c))


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def darker(color: str, amount: float = 0.45) -> str:
    """El mismo color mezclado con gris oscuro: para la escoria, más fría que la mata."""
    rgb = [int(color[i : i + 2], 16) for i in (1, 3, 5)]
    mixed = [round(c * (1 - amount) + 60 * amount) for c in rgb]
    return "#{:02X}{:02X}{:02X}".format(*mixed)
