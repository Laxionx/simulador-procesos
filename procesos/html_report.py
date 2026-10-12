"""Fase 4: reporte HTML autocontenido (un solo archivo, sin JavaScript ni recursos externos).

Incluye el diagrama de flujo, la tabla de corrientes, los balances, el equilibrio y el costo
operativo. Todo texto que viene del YAML se escapa.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from html import escape
from pathlib import Path

from .costs import operating_cost
from .diagram import flowsheet_svg
from .flowsheet import Flowsheet, Solution
from .plant_io import Plant
from .report import (
    element_balance,
    energy_balance,
    equilibrium_report,
    ew_report,
    grinding_report,
    worst_closure,
)

CSS = """
:root{--papel:#f5f2ea;--tinta:#16181a;--gris:#6b6a63;--linea:#d6d0c2;--panel:#fffdf8;
--senal:#d9480f;--ok:#2b7a3d;--aviso:#b7791f;--mono:"Cascadia Mono",Consolas,ui-monospace,monospace;
--titulo:Bahnschrift,"DIN Alternate","Roboto Condensed","Arial Narrow",sans-serif}
*{box-sizing:border-box}
body{margin:0;background:var(--papel);color:var(--tinta);font:15px/1.5 var(--titulo)}
main{max-width:1180px;margin:0 auto;padding:40px 32px 64px}
header{border-bottom:3px solid var(--tinta);padding-bottom:18px;display:grid;
grid-template-columns:1fr auto;align-items:end;gap:24px}
header p{margin:0;color:var(--gris);letter-spacing:.08em;text-transform:uppercase;font-size:12px}
h1{font-size:44px;line-height:1.05;margin:6px 0 0;font-weight:700;letter-spacing:-.01em}
h2{font-size:13px;letter-spacing:.14em;text-transform:uppercase;margin:44px 0 12px;
display:flex;gap:12px;align-items:center}
h2::before{content:"";width:22px;height:3px;background:var(--senal)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));margin-top:26px;
border-top:1px solid var(--linea);border-left:1px solid var(--linea)}
.kpi{padding:14px 18px;border-right:1px solid var(--linea);border-bottom:1px solid var(--linea);
background:var(--panel)}
.kpi span{display:block;font-size:11px;letter-spacing:.1em;text-transform:uppercase;
color:var(--gris)}
.kpi b{display:block;font:600 26px/1.2 var(--mono);margin-top:4px;font-variant-numeric:tabular-nums}
.kpi.ok b{color:var(--ok)}.kpi.mal b{color:var(--senal)}
.lamina{background:var(--panel);border:1px solid var(--tinta);padding:18px;overflow-x:auto;
box-shadow:6px 6px 0 var(--linea)}
.diagrama{display:block;max-width:100%;height:auto;font-family:var(--titulo)}
.equipo rect{fill:#fff;stroke:var(--tinta);stroke-width:1.6}
.equipo .nombre{font-size:13px;font-weight:600;text-anchor:middle}
.equipo .tipo{font-size:10px;letter-spacing:.12em;text-transform:uppercase;fill:var(--gris);
text-anchor:middle}
.terminal rect{fill:var(--tinta)}.terminal text{fill:var(--papel);font-size:12px;text-anchor:middle}
.terminal.producto rect{fill:var(--panel);stroke:var(--tinta);stroke-width:1.6}
.terminal.producto text{fill:var(--tinta)}
.flecha path{fill:none;stroke:var(--tinta);stroke-width:1.3}
.flecha text{font-size:11px;fill:var(--gris);text-anchor:middle;paint-order:stroke;
stroke:var(--panel);stroke-width:4px}
.flecha.reciclo path{stroke:var(--senal);stroke-dasharray:6 4}
.flecha.reciclo text{fill:var(--senal)}
marker path{fill:var(--tinta)}
.tabla{overflow-x:auto;border:1px solid var(--linea);background:var(--panel)}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:7px 12px;border-bottom:1px solid var(--linea);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left;position:sticky;left:0;background:var(--panel)}
thead th{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--gris);
border-bottom:2px solid var(--tinta)}
td{font-family:var(--mono);font-variant-numeric:tabular-nums}
td:first-child{font-family:var(--titulo);font-weight:600}
tr.total td{border-top:2px solid var(--tinta);font-weight:700}
tbody tr:hover td{background:#f1ece0}
.cero{color:#bdb7a8}
.chip{display:inline-block;padding:1px 8px;font:600 11px/1.6 var(--titulo);letter-spacing:.06em;
border:1px solid currentColor}
.chip.ok{color:var(--ok)}.chip.mal{color:var(--senal)}
.aviso{border-left:3px solid var(--aviso);padding:8px 14px;background:#fbf3e2;margin:10px 0}
.nota{color:var(--gris);font-size:13px;max-width:78ch}
footer{margin-top:56px;padding-top:14px;border-top:1px solid var(--linea);color:var(--gris);
font-size:12px}
@media print{body{background:#fff}.lamina{box-shadow:none}main{padding:0}}
"""


def _num(value: float, decimals: int = 1) -> str:
    """Formato español: 1.234,5."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", " ").replace(".", ",").replace(" ", ".")


def _cell(value: float, decimals: int = 1) -> str:
    if abs(value) < 0.5 * 10.0**-decimals:
        return '<td class="cero">·</td>'
    return f"<td>{_num(value, decimals)}</td>"


def _table(head: list[str], rows: list[str]) -> str:
    th = "".join(f"<th>{escape(h)}</th>" for h in head)
    return f'<div class="tabla"><table><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'  # noqa: E501


def _streams(flowsheet: Flowsheet, solution: Solution) -> str:
    names = list(flowsheet.feeds) + [o for u in flowsheet.order for o in u.outputs]
    streams = [solution.streams[n] for n in names]
    rows = [
        f"<tr><td>{escape(s)}</td>{''.join(_cell(st.flow(s)) for st in streams)}</tr>"
        for s in flowsheet.catalog.names
    ]
    rows.append(
        f'<tr class="total"><td>Total (kg/h)</td>{"".join(_cell(st.total) for st in streams)}</tr>'
    )  # noqa: E501
    rows.append(
        f"<tr><td>Temperatura (°C)</td>{''.join(_cell(st.temperature, 2) for st in streams)}</tr>"
    )  # noqa: E501
    return _table(["Especie (kg/h)", *names], rows)


def _chip(error: float, limit: float = 1e-6) -> str:
    ok = error < limit
    return f'<span class="chip {"ok" if ok else "mal"}">{"cierra" if ok else "no cierra"}</span>'


def _elements(flowsheet: Flowsheet, solution: Solution) -> str:
    rows = [
        f"<tr><td>{escape(r.name)}</td>{_cell(r.inflow, 3)}{_cell(r.outflow, 3)}"
        f"<td>{r.relative_error:.1e}</td><td>{_chip(r.relative_error)}</td></tr>"
        for r in element_balance(flowsheet, solution)
    ]
    return _table(["Elemento", "Entra (kg/h)", "Sale (kg/h)", "Error relativo", ""], rows)


def _energy(flowsheet: Flowsheet, solution: Solution) -> str:
    rows = [
        f"<tr><td>{escape(r.name)}</td>{_cell(r.inflow)}{_cell(r.duty)}{_cell(r.power)}"
        f"{_cell(r.outflow)}<td>{r.relative_error:.1e}</td></tr>"
        for r in energy_balance(flowsheet, solution)
    ]
    if not rows:
        return ""
    head = [
        "Equipo",
        "Entra (kW)",
        "Calor agregado (kW)",
        "Electricidad (kW)",
        "Sale (kW)",
        "Error relativo",
    ]
    note = (
        '<p class="nota">Entalpías absolutas: incluyen la de formación a 25 °C, por eso son '
        "negativas. Lo que importa es la diferencia: entra + calor + electricidad = sale.</p>"
    )
    return "<h2>Balance de energía</h2>" + _table(head, rows) + note


def _equilibrium(flowsheet: Flowsheet, solution: Solution) -> str:
    parts = []
    for name, eq in equilibrium_report(flowsheet, solution):
        rows = [
            f"<tr><td>{escape(p)}</td>{_cell(eq.minerals_mol_h[p])}<td>{eq.saturation[p]:+.3f}</td></tr>"  # noqa: E501
            for p in eq.minerals_mol_h
        ]
        warnings = "".join(f'<p class="aviso">{escape(w)}</p>' for w in eq.warnings)
        parts.append(
            f"<h2>Equilibrio · {escape(name)}</h2><p>pH <b>{_num(eq.ph, 3)}</b> · fuerza iónica "
            f"<b>{_num(eq.ionic_strength, 3)} mol/kg</b></p>{warnings}"
            + _table(["Mineral", "Cantidad (mol/h)", "Índice de saturación"], rows)
        )
    return "".join(parts)


def _grinding(flowsheet: Flowsheet, solution: Solution) -> str:
    parts = []
    for name, mo in grinding_report(flowsheet, solution):
        circ = (
            ""
            if mo.circulating_load is None
            else f" · carga circulante <b>{_num(100 * mo.circulating_load, 1)} %</b>"
        )
        parts.append(
            f"<h2>Molienda · {escape(name)}</h2><p>{_num(mo.solids_t_h, 1)} t/h de sólidos · "
            f"F80 {_num(mo.f80_um, 0)} µm → P80 <b>{_num(mo.p80_um, 0)} µm</b> · Bond "
            f"{_num(mo.bond_kwh_t, 2)} kWh/t · <b>{_num(mo.power_kw, 0)} kW</b> "
            f"({escape(mo.power_basis)}){circ}</p>"
        )
    return "".join(parts)


def _electrowinning(flowsheet: Flowsheet, solution: Solution) -> str:
    parts = []
    for name, ew in ew_report(flowsheet, solution):
        rows = [
            f"<tr><td>{escape(label)}</td>{_cell(volts, 3)}</tr>"
            for label, volts in ew.components.items()
        ]
        warnings = "".join(f'<p class="aviso">{escape(w)}</p>' for w in ew.warnings)
        parts.append(
            f"<h2>Electroobtención · {escape(name)}</h2><p>{_num(ew.current_a / 1000, 1)} kA · "
            f"cátodos <b>{_num(ew.copper_kg_h, 2)} kg/h</b> · celda <b>{_num(ew.cell_voltage, 3)} V"
            f"</b> · <b>{_num(ew.specific_energy_kwh_t, 0)} kWh/t</b> · electrolito agotado "
            f"{_num(ew.spent_cu_g_l, 2)} g/L de Cu</p>{warnings}"
            + (_table(["Componente del voltaje", "V"], rows) if rows else "")
        )
    return "".join(parts)


def _costs(plant: Plant, flowsheet: Flowsheet, solution: Solution) -> tuple[str, str]:
    """(sección, KPI)."""
    if plant.costs is None:
        return "", ""
    report = operating_cost(flowsheet, solution, plant.costs)
    cur = escape(report.currency)
    rows = [
        f"<tr><td>{escape(line.concept)}</td><td>{_num(line.quantity, 3)} {escape(line.unit)}</td>"
        f"{_cell(line.unit_price, 4)}{_cell(line.cost_per_h, 2)}</tr>"
        for line in report.lines
    ]
    rows.append(
        f'<tr class="total"><td>Total</td><td></td><td></td>{_cell(report.total_per_h, 2)}</tr>'
    )  # noqa: E501
    basis = escape(report.basis_label)
    section = (
        "<h2>Costo operativo</h2>"
        + _table(["Concepto", "Consumo", f"Precio ({cur})", f"{cur}/h"], rows)
        + f'<p class="nota">Por tonelada de {basis} ({_num(report.basis_t_h, 3)} t/h): '
        f"<b>{_num(report.per_tonne, 2)} {cur}/t</b>. Los precios son los del archivo de la "
        "planta. El costo de capital no se estima: no hay correlaciones públicas validadas para "
        "estos equipos.</p>"
    )
    kpi = f'<div class="kpi"><span>Costo operativo · {cur}/t de {basis}</span><b>{_num(report.per_tonne, 2)}</b></div>'  # noqa: E501
    return section, kpi


def html_report(
    plant: Plant,
    flowsheet: Flowsheet,
    solution: Solution,
    controls: Mapping[str, float] | None = None,
) -> str:
    closure = worst_closure(flowsheet, solution)
    cost_section, cost_kpi = _costs(plant, flowsheet, solution)
    state = "ok" if closure < 1e-6 else "mal"
    kpis = (
        f'<div class="kpi {state}"><span>Peor error de cierre</span><b>{closure:.1e}</b></div>'
        f'<div class="kpi"><span>Iteraciones</span><b>{solution.iterations}</b></div>'
        f'<div class="kpi"><span>Equipos · corrientes</span><b>{len(flowsheet.units)} · '
        f"{len(solution.streams)}</b></div>{cost_kpi}"
    )
    control_rows = "".join(
        f"<tr><td>{escape(name)}</td>{_cell(value, 4)}</tr>"
        for name, value in (controls or {}).items()
    )
    control = (
        "<h2>Lazos de control</h2>" + _table(["Controlador", "Valor ajustado"], [control_rows])
        if control_rows
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(plant.name)} · reporte de simulación</title>
<style>{CSS}</style></head>
<body><main>
<header><div><p>Reporte de simulación · simulador-procesos</p><h1>{escape(plant.name)}</h1></div>
<p>{date.today().isoformat()}</p></header>
<section class="kpis">{kpis}</section>
<h2>Diagrama de flujo</h2><div class="lamina">{flowsheet_svg(flowsheet)}</div>
<h2>Corrientes</h2>{_streams(flowsheet, solution)}
<h2>Balance por elemento</h2>{_elements(flowsheet, solution)}
{_energy(flowsheet, solution)}{_equilibrium(flowsheet, solution)}
{_grinding(flowsheet, solution)}{_electrowinning(flowsheet, solution)}{control}{cost_section}
<footer>Simulador implementado desde la literatura. Estado estacionario; los límites de cada
modelo están en la documentación del proyecto.</footer>
</main></body></html>
"""


def write_html(text: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
