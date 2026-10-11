"""Uso: ``python -m procesos resolver ejemplos/lixiviacion_oxidos_cu.yaml --salida salidas``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .control import ControlError, solve_with_controllers
from .costs import operating_cost
from .flowsheet import ConvergenceError
from .html_report import html_report, write_html
from .plant_io import PlantFileError, load_plant
from .report import (
    element_balance,
    energy_balance,
    equilibrium_report,
    stream_table,
    sx_report,
    worst_closure,
    write_csv,
    write_xlsx,
)


def _solve(path: Path, output: Path | None, html: Path | None = None) -> int:
    plant = load_plant(path)
    flowsheet = plant.flowsheet
    print(f"Planta: {plant.name}")
    controls: dict[str, float] = {}
    if plant.controllers:
        controlled = solve_with_controllers(flowsheet, plant.controllers)
        flowsheet, solution = controlled.flowsheet, controlled.solution
        controls = dict(controlled.values)
        for name, value in controlled.values.items():
            print(f"  Controlador «{name}»: {value:,.4f}")
        print(f"  Evaluaciones de la planta: {controlled.evaluations}")
    else:
        solution = flowsheet.solve()
    cuts = ", ".join(solution.tears) or "ninguno"
    print(f"  Convergió en {solution.iterations} iteraciones · cortes: {cuts}")
    print("  Balance por elemento (kg/h):")
    for row in element_balance(flowsheet, solution):
        print(f"    {row.name:>3}: entra {row.inflow:14,.4f} · sale {row.outflow:14,.4f}")
    energy = energy_balance(flowsheet, solution)
    if energy:
        print("  Balance de energía (kW):")
        for row in energy:
            print(
                f"    {row.name:>20}: entra {row.inflow:14,.1f} · calor {row.duty:12,.1f}"
                f" · sale {row.outflow:14,.1f}"
            )
        for name in flowsheet.products:
            print(f"    {name} sale a {solution.streams[name].temperature:.2f} °C")
    for name, eq in equilibrium_report(flowsheet, solution):
        minerals = ", ".join(
            f"{p} {eq.minerals_mol_h[p]:,.1f} mol/h (IS {eq.saturation[p]:+.3f})"
            for p in eq.minerals_mol_h
        )
        print(
            f"  Equilibrio «{name}»: pH {eq.ph:.3f} · fuerza iónica {eq.ionic_strength:.3f} mol/kg"
        )
        if minerals:
            print(f"    Minerales: {minerals}")
        for warning in eq.warnings:
            print(f"    Aviso: {warning}")
    for name, sx in sx_report(flowsheet, solution):
        print(
            f"  SX «{name}»: Cu acuoso {sx.feed_aqueous_mol_l * 63.546:.3f} → "
            f"{sx.raffinate_g_l:.3f} g/L · orgánico sale con {sx.loaded_g_l:.3f} g/L · "
            f"pH {sx.ph[-1]:.2f} · transfiere {sx.transferred_mol_h * 63.546e-3:,.2f} kg/h de Cu"
        )
    closure = worst_closure(flowsheet, solution)
    print(f"  Peor error de cierre: {closure:.2e}")
    if plant.costs is not None:
        cost = operating_cost(flowsheet, solution, plant.costs)
        print(
            f"  Costo operativo: {cost.total_per_h:,.2f} {cost.currency}/h · "
            f"{cost.per_tonne:,.4f} {cost.currency}/t de {cost.basis_label}"
        )
    if html is not None:
        report = html_report(plant, flowsheet, solution, controls)
        print(f"  Reporte: {write_html(report, html)}")
    if output is not None:
        rows = stream_table(flowsheet, solution)
        stem = path.stem
        print(f"  Tabla: {write_csv(rows, output / f'{stem}.csv')}")
        print(f"  Tabla: {write_xlsx(rows, output / f'{stem}.xlsx')}")
    return 0 if closure < 1e-6 else 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="procesos", description="Simulador de procesos metalúrgicos"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    solve = commands.add_parser("resolver", help="Resuelve una planta descrita en YAML")
    solve.add_argument("planta", type=Path)
    solve.add_argument(
        "--salida", type=Path, default=None, help="Carpeta para la tabla CSV y Excel"
    )
    solve.add_argument("--html", type=Path, default=None, help="Archivo del reporte HTML")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # tildes legibles en consolas de Windows
    try:
        return _solve(args.planta, args.salida, args.html)
    except (PlantFileError, ControlError, ConvergenceError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
