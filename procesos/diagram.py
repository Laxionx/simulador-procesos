"""Fase 4: diagrama de flujo en SVG, sin dependencias ni recursos externos.

Cada equipo va en la columna de su camino más largo desde las alimentaciones; las corrientes de
corte (los reciclos) no cuentan para eso y se dibujan por debajo, con trazo discontinuo. Todo el
texto que viene del YAML se escapa.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from .flowsheet import Flowsheet

BOX_W, BOX_H = 150.0, 54.0
PILL_W, PILL_H = 118.0, 30.0
COL_GAP, ROW_GAP = 210.0, 104.0
MARGIN = 36.0
KIND = {
    "Mixer": "mezclador",
    "Splitter": "divisor",
    "Separator": "separador",
    "Reactor": "reactor",
    "Heater": "calentador",
    "Evaporator": "evaporador",
    "EquilibriumReactor": "equilibrio",
}


@dataclass(frozen=True)
class _Node:
    key: str
    label: str
    kind: str  # "alimentacion", "producto" o el tipo de equipo
    x: float
    y: float
    w: float
    h: float


def _columns(flowsheet: Flowsheet) -> dict[str, int]:
    producer = {o: u.name for u in flowsheet.units for o in u.outputs}
    tears = set(flowsheet.tears)
    column = {f"in:{name}": 0 for name in flowsheet.feeds}
    for unit in flowsheet.order:
        deps = [column[producer[s]] if s in producer else 0 for s in unit.inputs if s not in tears]
        column[unit.name] = 1 + max(deps, default=0)
    # cada producto va justo después de su equipo, para que su flecha no cruce otros equipos
    column |= {f"out:{name}": column[producer[name]] + 1 for name in flowsheet.products}
    return column


def _nodes(flowsheet: Flowsheet) -> dict[str, _Node]:
    column = _columns(flowsheet)
    kinds = {u.name: KIND.get(type(u).__name__, type(u).__name__.lower()) for u in flowsheet.units}
    rows: dict[int, list[str]] = {}
    for key in column:  # orden de inserción: alimentaciones, equipos en orden, productos
        rows.setdefault(column[key], []).append(key)
    height = max(len(keys) for keys in rows.values())
    nodes = {}
    for col, keys in rows.items():
        offset = (height - len(keys)) * ROW_GAP / 2.0
        for row, key in enumerate(keys):
            terminal = key.startswith(("in:", "out:"))
            w, h = (PILL_W, PILL_H) if terminal else (BOX_W, BOX_H)
            cx = MARGIN + BOX_W / 2.0 + col * COL_GAP
            cy = MARGIN + BOX_H / 2.0 + offset + row * ROW_GAP
            kind = (
                ("alimentacion" if key.startswith("in:") else "producto")
                if terminal
                else (kinds[key])
            )
            label = key.split(":", 1)[1] if terminal else key
            nodes[key] = _Node(key, label, kind, cx - w / 2.0, cy - h / 2.0, w, h)
    return nodes


def _ports(count: int, node: _Node, index: int) -> float:
    return node.y + node.h * (index + 1) / (count + 1)


def flowsheet_svg(flowsheet: Flowsheet) -> str:
    nodes = _nodes(flowsheet)
    producer = {o: u for u in flowsheet.units for o in u.outputs}
    tears = set(flowsheet.tears)
    width = max(n.x + n.w for n in nodes.values()) + MARGIN
    bottom = max(n.y + n.h for n in nodes.values())
    loops = 0
    edges = []
    for unit in flowsheet.units:
        target = nodes[unit.name]
        for i, stream in enumerate(unit.inputs):
            if stream in producer:
                src = producer[stream]
                source = nodes[src.name]
                sy = _ports(len(src.outputs), source, src.outputs.index(stream))
            else:
                source, sy = nodes[f"in:{stream}"], nodes[f"in:{stream}"].y + PILL_H / 2.0
            ty = _ports(len(unit.inputs), target, i)
            label = stream if stream in producer else ""  # la alimentación ya lleva su nombre
            if stream in tears:
                loops += 1
                edges.append(_loop(source, sy, target, ty, bottom + 28.0 * loops, stream))
            else:
                edges.append(_edge(source.x + source.w, sy, target.x, ty, label))
    for name in flowsheet.products:
        unit = producer[name]
        source, sink = nodes[unit.name], nodes[f"out:{name}"]
        sy = _ports(len(unit.outputs), source, unit.outputs.index(name))
        edges.append(_edge(source.x + source.w, sy, sink.x, sink.y + PILL_H / 2.0, ""))
    height = bottom + 28.0 * loops + MARGIN + 12.0
    body = "\n".join(edges + [_node(n) for n in nodes.values()])
    return (
        f'<svg class="diagrama" viewBox="0 0 {width:.0f} '  # en línea: HTML5 pone el xmlns
        f'{height:.0f}" width="{width:.0f}" height="{height:.0f}" role="img" '
        f'aria-label="Diagrama de flujo">\n'
        '<defs><marker id="punta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z"/></marker>'
        "</defs>\n"
        f"{body}\n</svg>"
    )


def _edge(x1: float, y1: float, x2: float, y2: float, name: str) -> str:
    mx = (x1 + x2) / 2.0
    path = f"M{x1:.1f},{y1:.1f} C{mx:.1f},{y1:.1f} {mx:.1f},{y2:.1f} {x2:.1f},{y2:.1f}"
    text = f'<text x="{mx:.1f}" y="{(y1 + y2) / 2.0 - 6:.1f}">{escape(name)}</text>' if name else ""
    return f'<g class="flecha"><path d="{path}" marker-end="url(#punta)"/>{text}</g>'


def _loop(source: _Node, sy: float, target: _Node, ty: float, low: float, name: str) -> str:
    x1, x2 = source.x + source.w, target.x
    path = f"M{x1:.1f},{sy:.1f} H{x1 + 22:.1f} V{low:.1f} H{x2 - 22:.1f} V{ty:.1f} H{x2:.1f}"
    return (
        f'<g class="flecha reciclo"><path d="{path}" marker-end="url(#punta)"/>'
        f'<text x="{(x1 + x2) / 2.0:.1f}" y="{low - 6:.1f}">{escape(name)} (reciclo)</text></g>'
    )


def _node(node: _Node) -> str:
    label = escape(node.label)
    if node.kind in ("alimentacion", "producto"):
        return (
            f'<g class="terminal {node.kind}"><rect x="{node.x:.1f}" y="{node.y:.1f}" '
            f'width="{node.w:.1f}" height="{node.h:.1f}" rx="{node.h / 2:.1f}"/>'
            f'<text x="{node.x + node.w / 2:.1f}" y="{node.y + node.h / 2 + 4:.1f}">{label}</text>'
            "</g>"
        )
    return (
        f'<g class="equipo"><rect x="{node.x:.1f}" y="{node.y:.1f}" width="{node.w:.1f}" '
        f'height="{node.h:.1f}"/><text class="nombre" x="{node.x + node.w / 2:.1f}" '
        f'y="{node.y + 24:.1f}">{label}</text><text class="tipo" x="{node.x + node.w / 2:.1f}" '
        f'y="{node.y + 42:.1f}">{escape(node.kind)}</text></g>'
    )
