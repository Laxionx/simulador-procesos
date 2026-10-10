"""Fase 3: equilibrio químico acuoso con PHREEQC (USGS, dominio público), vía phreeqpy.

El reactor de equilibrio:
1. traduce su entrada a una SOLUTION de PHREEQC: totales por elemento de las especies acuosas,
   el agua y el pH ajustado por balance de carga;
2. agrega como EQUILIBRIUM_PHASES los minerales permitidos, con lo que ya trae la corriente;
3. deja que PHREEQC resuelva especiación, actividades y disolución o precipitación;
4. vuelve a las especies de la planta: cada metal disuelto a su única especie acuosa, el sulfato
   que sobra a H2SO4(aq) y el agua por el balance de hidrógeno. El oxígeno queda como control.

Bases incluidas:
- minteq.v4.dat (EPA MINTEQA2 v4, distribuida con PHREEQC), la de defecto: Debye-Hückel extendido /
  Davies, válido en soluciones diluidas (fuerza iónica hasta ~0,5 mol/kg);
- pitzer_cu.dat: pitzer.dat de PHREEQC 3.7.3 más un bloque de cobre a 25 °C (Justel et al., 2020),
  para soluciones concentradas.
Cada resultado trae los avisos de validez que correspondan a su base. Ver docs/equilibrio.md.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from functools import cache
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .species import Catalog, Species, make_species
from .stream import Stream, element_flows, mix

DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_DATABASE = DATA_DIR / "minteq.v4.dat"
PITZER_CU = DATA_DIR / "pitzer_cu.dat"
IONIC_STRENGTH_LIMIT = 0.5  # mol/kg: hasta aquí vale Debye-Hückel extendido / Davies
FREE_ACID_LIMIT = 0.01  # mol/kg: con cobre y más ácido libre, pitzer_cu.dat no está validada
WATER = "H2O"
MASTER = {"S": "S(6)", "C": "C(4)"}  # azufre como sulfato, carbono como carbonato
NOT_TOTALS = {"H", "O"}


class PhreeqcError(RuntimeError):
    """PHREEQC no está disponible o rechazó el cálculo."""


@dataclass(frozen=True)
class EquilibriumResult:
    ph: float
    ionic_strength: float  # mol/kg
    charge_error_pct: float  # error de balance de carga que informa PHREEQC
    phreeqc_water_kg_h: float
    minerals_mol_h: Mapping[str, float]
    saturation: Mapping[str, float]
    flows: Mapping[str, float]  # salida en especies de la planta (kg/h)
    warnings: tuple[str, ...] = ()  # fuera del rango validado del modelo de actividad


@cache
def _engine(database: str) -> Any:
    try:
        from phreeqpy.iphreeqc.phreeqc_dll import IPhreeqc
    except ImportError as error:  # pragma: no cover - depende del entorno
        raise PhreeqcError(
            "Falta phreeqpy; instálelo con: pip install procesos[equilibrio]"
        ) from error
    engine = IPhreeqc()
    engine.load_database(database)
    return engine


@cache
def uses_pitzer(database: str) -> bool:
    """La base activa el modelo de Pitzer de PHREEQC (tiene un bloque PITZER)."""
    lines = Path(database).read_text(encoding="utf-8", errors="replace").splitlines()
    return any(line.strip() == "PITZER" for line in lines)


@cache
def phase_composition(database: str, phase: str) -> dict[str, float]:
    """Composición elemental de un mineral, leída de su reacción en la base de PHREEQC."""
    lines = Path(database).read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines):
        if line.strip() == phase and not line.startswith((" ", "\t")):
            for nxt in lines[i + 1 :]:
                if "=" in nxt:
                    formula = nxt.split("=")[0].strip().replace(":", "·")
                    return dict(make_species(formula).composition)
    raise PhreeqcError(f"El mineral {phase!r} no está en {Path(database).name}")


def _master(element: str) -> str:
    return MASTER.get(element, element)


@dataclass(frozen=True)
class EquilibriumReactor:
    """Reactor de equilibrio químico acuoso (PHREEQC).

    `minerals`: fase de PHREEQC -> especie de la planta (p. ej. {"Gypsum": "CaSO4·2H2O"}).
    Los sólidos y gases que no figuran ahí pasan sin reaccionar. Si `temperature` es None se
    usa la de la entrada; la salida sale a esa temperatura (no hay balance de calor aquí).
    """

    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    minerals: Mapping[str, str] = field(default_factory=dict)
    temperature: float | None = None
    database: str = str(DEFAULT_DATABASE)

    def __post_init__(self) -> None:
        if not self.name or not self.inputs or len(self.outputs) != 1:
            raise ValueError(f"{self.name}: necesita nombre, entradas y una sola salida")
        if set(self.inputs) & set(self.outputs):
            raise ValueError(f"{self.name}: la salida no puede ser una entrada")
        object.__setattr__(self, "minerals", MappingProxyType(dict(self.minerals)))

    # ---------------------------------------------------------------- traducción
    def _check_minerals(self, catalog: Catalog) -> None:
        for phase, name in self.minerals.items():
            plant = dict(catalog[name].composition)
            if phase_composition(self.database, phase) != plant:
                raise ValueError(
                    f"{self.name}: {name} no tiene la fórmula de {phase} en la base de PHREEQC"
                )

    def _input(
        self, feed: Stream, catalog: Catalog, temp: float
    ) -> tuple[str, list[str], dict[str, float], dict[str, float]]:
        water = feed.flow(WATER)
        if water <= 0:
            raise ValueError(f"{self.name}: el equilibrio acuoso necesita agua líquida (H2O)")
        totals: dict[str, float] = {}
        for name, flow in feed.flows.items():
            sp = catalog[name]
            if sp.phase != "aq":
                continue
            mol = flow / sp.molar_mass * 1000.0
            for element, count in sp.composition.items():
                if element not in NOT_TOTALS:
                    totals[element] = totals.get(element, 0.0) + mol * count
        lines = ["SOLUTION 1", f"  temp {temp}", "  pH 7 charge", "  units mol/kgw"]
        lines.append(f"  -water {water}")
        lines += [f"  {_master(e)} {m / water:.15g}" for e, m in totals.items() if m > 0]
        lines.append("EQUILIBRIUM_PHASES 1")
        present: dict[str, float] = {}
        for phase, name in self.minerals.items():
            present[phase] = feed.flow(name) / catalog[name].molar_mass * 1000.0
            lines.append(f"  {phase} 0 {present[phase]:.15g}")
        elements = sorted(
            set(totals)
            | {e for n in self.minerals.values() for e in catalog[n].composition} - NOT_TOTALS
        )
        masters = [_master(e) for e in elements]
        phases = " ".join(self.minerals)
        lines += [
            "SELECTED_OUTPUT",
            "  -reset false",
            "  -pH true",
            "  -ionic_strength true",
            "  -percent_error true",
            "  -water true",
            f"  -totals {' '.join(masters)}",
        ]
        if self.minerals:
            lines += [f"  -equilibrium_phases {phases}", f"  -saturation_indices {phases}"]
        lines.append("END")
        return "\n".join(lines), elements, totals, present

    def solve(self, inputs: Sequence[Stream], catalog: Catalog) -> EquilibriumResult:
        feed = mix(inputs)
        self._check_minerals(catalog)
        temp = feed.temperature if self.temperature is None else self.temperature
        text, elements, totals, present = self._input(feed, catalog, temp)
        engine = _engine(self.database)
        try:
            engine.run_string(text)
        except Exception as error:  # noqa: BLE001 - phreeqpy lanza Exception genérica
            raise PhreeqcError(f"{self.name}: PHREEQC falló: {error}") from error
        table = engine.get_selected_output_array()
        row = dict(zip(table[0], table[-1], strict=True))
        water_kg = float(row["mass_H2O"])
        phreeqc_moles = {e: float(row[f"{_master(e)}(mol/kgw)"]) * water_kg for e in elements}
        minerals = {p: float(row[p]) for p in self.minerals}
        # Lo disuelto sale de conservar la masa con lo que PHREEQC decidió para los minerales;
        # sus totales (resueltos con su propia tolerancia) quedan como control de consistencia.
        moles = {e: totals.get(e, 0.0) for e in elements}
        for phase, name in self.minerals.items():
            change = minerals[phase] - present[phase]
            for e, count in catalog[name].composition.items():
                if e in moles:
                    moles[e] -= change * count
        for e, value in moles.items():
            scale = max(abs(value), abs(phreeqc_moles[e]), 1e-12)
            if abs(value - phreeqc_moles[e]) > 1e-6 * scale:
                raise PhreeqcError(
                    f"{self.name}: PHREEQC no conserva {e} "
                    f"({phreeqc_moles[e]:.6g} frente a {value:.6g} mol/h)"
                )
        saturation = {p: float(row[f"si_{p}"]) for p in self.minerals}
        flows = self._back_to_plant(feed, catalog, moles, minerals)
        warnings = self._warnings(catalog, flows, float(row["mu"]), temp)
        return EquilibriumResult(
            float(row["pH"]),
            float(row["mu"]),
            float(row["pct_err"]),
            water_kg,
            MappingProxyType(minerals),
            MappingProxyType(saturation),
            MappingProxyType(flows),
            warnings,
        )

    def _warnings(
        self, catalog: Catalog, flows: Mapping[str, float], ionic_strength: float, temp: float
    ) -> tuple[str, ...]:
        """Avisos de validez según la base (ver docs/equilibrio.md)."""
        if not uses_pitzer(self.database):
            if ionic_strength > IONIC_STRENGTH_LIMIT:
                return (
                    "fuerza iónica sobre 0,5 mol/kg, fuera del rango de Debye-Hückel "
                    "(para soluciones concentradas: base pitzer_cu.dat)",
                )
            return ()
        if Path(self.database).resolve() != PITZER_CU.resolve():
            return ()
        aqueous = [catalog[n] for n in flows if catalog[n].phase == "aq"]
        if not any("Cu" in sp.composition and flows[sp.name] > 0 for sp in aqueous):
            return ()
        notes = []
        if abs(temp - 25.0) > 0.5:
            notes.append("los parámetros de Pitzer del cobre son solo de 25 °C")
        acid = _find(aqueous, {"H": 2, "S": 1, "O": 4})
        water_t_h = flows[WATER] / 1000.0
        if acid is not None and flows[acid.name] / acid.molar_mass / water_t_h > FREE_ACID_LIMIT:
            notes.append(
                "cobre con ácido libre: no validado; con 1,5 a 9,8 mol/kg de H2SO4 la base "
                "sobreestima la solubilidad de la calcantita entre 14 y 113 %"
            )
        return tuple(notes)

    def _back_to_plant(
        self,
        feed: Stream,
        catalog: Catalog,
        moles: Mapping[str, float],
        minerals: Mapping[str, float],
    ) -> dict[str, float]:
        flows = {
            n: f
            for n, f in feed.flows.items()
            if catalog[n].phase != "aq" and n != WATER and n not in self.minerals.values()
        }
        for phase, name in self.minerals.items():
            flows[name] = flows.get(name, 0.0) + minerals[phase] * catalog[name].molar_mass / 1e3
        aqueous = [catalog[n] for n in catalog.names if catalog[n].phase == "aq"]
        acid = _find(aqueous, {"H": 2, "S": 1, "O": 4})
        carbonic = _find(aqueous, {"C": 1, "O": 2})
        # lo que queda en solución = total de PHREEQC (los minerales ya se descontaron allí)
        left = dict(moles)
        for element in sorted(left):
            if element in ("S", "C"):
                continue
            carriers = [s for s in aqueous if element in s.composition and s is not acid]
            if len(carriers) != 1:
                raise ValueError(
                    f"{self.name}: el elemento {element} disuelto necesita UNA especie acuosa "
                    f"que lo lleve; hay {[s.name for s in carriers]}"
                )
            sp = carriers[0]
            mol_sp = left[element] / sp.composition[element]
            for e, c in sp.composition.items():
                if e in left:
                    left[e] -= mol_sp * c
            flows[sp.name] = flows.get(sp.name, 0.0) + mol_sp * sp.molar_mass / 1e3
        for element, carrier in (("S", acid), ("C", carbonic)):
            amount = left.get(element, 0.0)
            if amount < -1e-9 * max(1.0, abs(moles.get(element, 1.0))):
                raise ValueError(f"{self.name}: faltaría {element} para las especies disueltas")
            if amount > 0:
                if carrier is None:
                    raise ValueError(
                        f"{self.name}: sobra {element} disuelto y la planta no tiene "
                        f"{'H2SO4(aq)' if element == 'S' else 'CO2(aq)'} para llevarlo"
                    )
                flows[carrier.name] = flows.get(carrier.name, 0.0) + amount * (
                    carrier.molar_mass / 1e3
                )
        h_in = element_flows(feed, catalog).get("H", 0.0)
        h_rest = element_flows(Stream(flows), catalog).get("H", 0.0)
        water = catalog[WATER]
        h_per_kg_water = element_flows(Stream({WATER: 1.0}), catalog)["H"]
        flows[WATER] = max(h_in - h_rest, 0.0) / h_per_kg_water
        if water.phase != "l":  # pragma: no cover - el catálogo define el agua
            raise ValueError("El agua del catálogo debe ser líquida")
        return flows

    # ---------------------------------------------------------------- interfaz de equipo
    def compute(self, inputs: Sequence[Stream], catalog: Catalog) -> tuple[Stream, ...]:
        feed = mix(inputs)
        temp = feed.temperature if self.temperature is None else self.temperature
        result = self.solve(inputs, catalog)
        return (Stream(dict(result.flows), temp, feed.pressure),)

    def with_parameter(self, key: str, value: float) -> EquilibriumReactor:
        """``'temperatura'``."""
        if key == "temperatura":
            return replace(self, temperature=value)
        raise KeyError(f"{self.name}: parámetro desconocido {key!r}; use 'temperatura'")


def _find(species: list[Species], composition: Mapping[str, float]) -> Species | None:
    for sp in species:
        if dict(sp.composition) == dict(composition):
            return sp
    return None


def database_path(name: str | None) -> str:
    """Ruta de una base: la incluida (por nombre) o una ruta explícita."""
    if not name:
        return str(DEFAULT_DATABASE)
    candidate = DATA_DIR / name
    if re.fullmatch(r"[\w.\-]+\.dat", name) and candidate.exists():
        return str(candidate)
    if Path(name).exists():
        return str(Path(name).resolve())
    raise FileNotFoundError(f"No encuentro la base de PHREEQC {name!r}")
