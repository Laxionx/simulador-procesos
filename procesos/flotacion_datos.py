"""Caso publicado de flotación de laboratorio a piloto (Minerals 16(7), 726, 2026, CC BY).

Mena polimetálica de sulfuros, celdas Denver: cinética de laboratorio de dos componentes (Kelsall,
Tablas 4-6), circuito piloto de 50 kg/h (Figura 5: rougher y scavenger de 2 celdas con 28 min por
etapa, cleaner de 17 L; el concentrado scavenger y las colas cleaner vuelven al rougher), la
simulación de los autores en HSC SIM (Tabla 8) y lo medido en el piloto (Tablas 9-11).
Minerales simplificados como en el artículo: calcopirita (Ccp), esfalerita (Sp), pirita (Py) y
cuarzo (Qtz, toda la ganga).
"""

from __future__ import annotations

from .elements import molar_mass, parse_formula
from .flotacion import KELSALL, Flotation
from .flowsheet import Flowsheet, Solution
from .species import Catalog, make_species
from .stream import Stream
from .units import Mixer

SOURCE = "Minerals 16(7), 726 (2026), CC BY"
MINERALS = {"Ccp": "CuFeS2", "Sp": "ZnS", "Py": "FeS2", "Qtz": "SiO2"}
FEED_KG_H = 50.0
FEED_CHEMISTRY = {"Cu": 0.85, "Zn": 0.14, "Fe": 11.8, "S": 2.36}  # Tabla 1, % en masa
STAGE_TAU_MIN = 28.0  # rougher y scavenger, 2 celdas cada uno
CLEANER_VOLUME_L = 17.0
CLEANER_SOLIDS_G_L = 200.0  # densidad de pulpa del cleaner de laboratorio (supuesto para el piloto)

# Kelsall de dos componentes: (φ lenta, kf, ks) en 1/min. Tablas 4, 5 y 6.
KINETICS = {
    "rougher": {"Ccp": (0.269, 0.892, 0.027), "Sp": (0.37, 0.92, 0.013),
                "Py": (0.451, 0.898, 0.016), "Qtz": (0.959, 0.255, 0.001)},
    "scavenger": {"Ccp": (0.918, 2.18, 0.012), "Sp": (0.963, 1.44, 0.005),
                  "Py": (0.337, 0.928, 0.027), "Qtz": (0.983, 0.191, 0.001)},
    "cleaner": {"Ccp": (0.005, 0.227, 0.0), "Sp": (0.046, 0.225, 0.0),
                "Py": (1.0, 0.221, 0.207), "Qtz": (0.910, 0.376, 0.020)},
}  # fmt: skip

# Tabla 8 (simulación HSC SIM): % en masa de cada mineral; rendimiento del concentrado 7,92 %.
HSC_CONCENTRATE = {"Ccp": 21.78, "Sp": 1.75, "Py": 63.52, "Qtz": 12.95}
HSC_TAILINGS = {"Ccp": 0.64, "Sp": 0.11, "Py": 0.83, "Qtz": 98.42}
HSC_YIELD_PCT = 7.92
# Piloto, promedio de 60-120 y 120-180 min (Tablas 9, 10 y 11).
PILOT_CU_PCT = (7.87 + 10.68) / 2
PILOT_CONCENTRATE = {"Ccp": 31.3, "Sp": 2.65, "Py": 58.0, "Qtz": 8.2}
PILOT_TAILINGS = {"Ccp": 1.2, "Sp": 0.0, "Py": 1.45, "Qtz": 97.3}


def _mm(formula: str) -> float:
    return molar_mass(parse_formula(formula))


def _fraction(formula: str, element: str) -> float:
    return parse_formula(formula)[element] * molar_mass({element: 1}) / _mm(formula)


def feed_mineralogy() -> dict[str, float]:
    """% en masa con la regla del artículo: Cu → Ccp, Zn → Sp, el S que sobra → Py, resto Qtz."""
    ccp = FEED_CHEMISTRY["Cu"] / _fraction("CuFeS2", "Cu")
    sp = FEED_CHEMISTRY["Zn"] / _fraction("ZnS", "Zn")
    s_left = FEED_CHEMISTRY["S"] - ccp * _fraction("CuFeS2", "S") - sp * _fraction("ZnS", "S")
    py = s_left / _fraction("FeS2", "S")
    return {"Ccp": ccp, "Sp": sp, "Py": py, "Qtz": 100.0 - ccp - sp - py}


CATALOG = Catalog([make_species(f, phase="s") for f in MINERALS.values()])


def _cells(name: str, stage: str, inputs: tuple[str, ...], outputs: tuple[str, ...], cells: int,
           tau: float) -> Flotation:  # fmt: skip
    kinetics = {MINERALS[m]: p for m, p in KINETICS[stage].items()}
    return Flotation(name, inputs, outputs, kinetics, cells, KELSALL, tau_min=tau)


def pilot_circuit(cleaner_tau_min: float) -> Flowsheet:
    feed = {MINERALS[m]: FEED_KG_H * pct / 100 for m, pct in feed_mineralogy().items()}
    stage_tau = STAGE_TAU_MIN / 2
    units = [
        Mixer("Acondicionador rougher", ("Alimentacion", "Concentrado scavenger", "Colas cleaner"),
              ("Alimentacion rougher",)),
        _cells("Rougher", "rougher", ("Alimentacion rougher",),
               ("Concentrado rougher", "Colas rougher"), 2, stage_tau),
        _cells("Scavenger", "scavenger", ("Colas rougher",),
               ("Concentrado scavenger", "Relave final"), 2, stage_tau),
        _cells("Cleaner", "cleaner", ("Concentrado rougher",),
               ("Concentrado final", "Colas cleaner"), 1, cleaner_tau_min),
    ]  # fmt: skip
    return Flowsheet(CATALOG, units, {"Alimentacion": Stream(feed, 25.0)})


def solve_pilot(tol: float = 1e-10, max_iter: int = 200) -> tuple[Solution, float]:
    """Resuelve el circuito con el τ del cleaner que da su volumen a 200 g/L de sólidos: el τ
    depende del caudal que entra al cleaner, que depende de los reciclos (punto fijo)."""
    tau = 30.0
    for _ in range(max_iter):
        solution = pilot_circuit(tau).solve()
        solids = solution.streams["Concentrado rougher"].total  # kg/h
        new = CLEANER_VOLUME_L * CLEANER_SOLIDS_G_L / 1000.0 / solids * 60.0
        if abs(new - tau) < tol * tau:
            return solution, new
        tau = new
    raise RuntimeError("el τ del cleaner no converge")


def composition(stream: Stream) -> dict[str, float]:
    """% en masa de cada mineral (con los nombres del artículo)."""
    return {m: 100.0 * stream.flow(f) / stream.total for m, f in MINERALS.items()}
