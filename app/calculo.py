"""Cálculo de lo que muestra la app, sin Streamlit: llama a los modelos de `procesos` y reparte
sus resultados celda por celda (flotación) o por cátodo (electroobtención). Los esquemas dibujan
exactamente estos números."""

from __future__ import annotations

import math
from dataclasses import dataclass

from procesos import Catalog, Flotation, Stream, make_species
from procesos.ew import FARADAY, Electrowinning, EWResult, conductivity
from procesos.flotacion import cells_recovery

# ------------------------------------------------------------------ flotación
# Alimentación del banco A de Los Pelambres (ejemplos/flotacion_pelambres.yaml), en kg/h.
FEED_KG_H = {"CuFeS2": 14_900.0, "SiO2": 585_100.0, "H2O": 1_114_000.0}
WATER_RECOVERY = 0.10  # supuesto del ejemplo, no medido
MODEL = "primer_orden"
# Recuperación acumulada de Cu medida celda a celda en el banco A (Vinnett et al. 2022, Tabla B1).
MEASURED_CELLS = (1, 3, 5, 7, 9)
MEASURED_CU_PCT = (55.5, 86.7, 91.9, 94.2, 94.7)
CU_IN_CHALCOPYRITE = 63.546 / (63.546 + 55.845 + 2 * 32.06)  # fracción másica de Cu en CuFeS2
FLOTATION_CATALOG = Catalog([make_species("CuFeS2", phase="s"), make_species("SiO2", phase="s"),
                             make_species("H2O", phase="l")])  # fmt: skip


@dataclass(frozen=True)
class FlotationParams:
    cells: int = 9
    tau_min: float = 4.1
    r_inf: float = 0.94
    k: float = 0.35
    gangue_recovery: float = 0.05


@dataclass(frozen=True)
class FlotationView:
    params: FlotationParams
    cu_cumulative: tuple[float, ...]  # recuperación acumulada de Cu tras cada celda (fracción)
    cu_t_h: tuple[float, ...]  # CuFeS2 que manda cada celda al concentrado (t/h)
    gangue_t_h: tuple[float, ...]  # SiO2 que manda cada celda (arrastre fijo)
    water_t_h: tuple[float, ...]
    recoveries: dict[str, float]  # total del modelo por especie
    feed_t_h: dict[str, float]

    @property
    def solids_t_h(self) -> tuple[float, ...]:
        """Sólidos que cada celda manda al concentrado: lo que fija el grosor de su espuma."""
        return tuple(c + g for c, g in zip(self.cu_t_h, self.gangue_t_h, strict=True))

    @property
    def concentrate_t_h(self) -> float:
        return sum(self.solids_t_h)

    @property
    def cu_grade_pct(self) -> float:
        """% de Cu en el concentrado (Cu contenido en la calcopirita ÷ sólidos del concentrado)."""
        total = self.concentrate_t_h
        return 100.0 * CU_IN_CHALCOPYRITE * sum(self.cu_t_h) / total if total > 0 else 0.0


def fixed_split(total_recovery: float, cells: int) -> list[float]:
    """Fracción de lo que queda que cada celda manda al concentrado, para una especie de
    recuperación fija: f = 1 - (1 - R)^(1/N), igual en todas las celdas."""
    f = 1.0 - (1.0 - total_recovery) ** (1.0 / cells)
    return [f] * cells


def per_cell_mass(feed_t_h: float, total_recovery: float, cells: int) -> list[float]:
    """Masa (t/h) que cada celda manda al concentrado con reparto parejo sobre lo que queda."""
    left, out = feed_t_h, []
    for f in fixed_split(total_recovery, cells):
        out.append(left * f)
        left -= left * f
    return out


def run_flotation(p: FlotationParams) -> FlotationView:
    unit = Flotation(
        "Banco", ("Alimentacion",), ("Concentrado", "Relave"), {"CuFeS2": (p.r_inf, p.k)},
        p.cells, MODEL, tau_min=p.tau_min,
        fixed={"SiO2": p.gangue_recovery, "H2O": WATER_RECOVERY},
    )  # fmt: skip
    result = unit.solve([Stream(FEED_KG_H)], FLOTATION_CATALOG)
    cumulative = [cells_recovery(MODEL, p.r_inf, p.k, result.tau_min, i)
                  for i in range(1, p.cells + 1)]  # fmt: skip
    feed = {n: v / 1000.0 for n, v in FEED_KG_H.items()}
    per_cell = [b - a for a, b in zip([0.0, *cumulative], cumulative, strict=False)]
    return FlotationView(
        p, tuple(cumulative), tuple(feed["CuFeS2"] * r for r in per_cell),
        tuple(per_cell_mass(feed["SiO2"], result.recoveries["SiO2"], p.cells)),
        tuple(per_cell_mass(feed["H2O"], result.recoveries["H2O"], p.cells)),
        dict(result.recoveries), feed,
    )  # fmt: skip


# ------------------------------------------------------------------ electroobtención
CU_G_MOL = 63.546
CU_DENSITY_G_CM3 = 8.96  # Cu sólido, CRC Handbook of Chemistry and Physics
FLOW_L_H = 10_000_000.0  # caudal de electrolito tan grande que su composición casi no cambia
EW_CATALOG = Catalog([make_species(n, phase=ph) for n, ph in (
    ("H2O", "l"), ("CuSO4", "aq"), ("H2SO4", "aq"), ("Cu", "s"), ("O2", "g"))])  # fmt: skip


@dataclass(frozen=True)
class EWParams:
    current_density: float = 300.0  # A/m²
    efficiency: float = 0.92
    cu_g_l: float = 40.0
    acid_g_l: float = 170.0
    temp_c: float = 50.0
    cycle_days: float = 7.0
    face_area_m2: float = 1.0  # una cara del cátodo


@dataclass(frozen=True)
class EWView:
    params: EWParams
    result: EWResult
    cathode_kg: float  # masa depositada en un cátodo al final del ciclo
    thickness_mm: float  # espesor por cara
    warnings: tuple[str, ...] = ()

    @property
    def current_a(self) -> float:
        return self.result.current_a


def faraday_mass_kg(j: float, efficiency: float, both_faces_m2: float, seconds: float) -> float:
    """Masa de Cu (kg) por Faraday: eficiencia × j × área × t × M/(2F)."""
    return efficiency * j * both_faces_m2 * seconds * CU_G_MOL / (2.0 * FARADAY) / 1000.0


def thickness_mm(mass_kg: float, both_faces_m2: float) -> float:
    """Espesor por cara (mm): masa ÷ (ρ × área de las dos caras)."""
    volume_cm3 = mass_kg * 1000.0 / CU_DENSITY_G_CM3
    return volume_cm3 / (both_faces_m2 * 1e4) * 10.0


def electrolyte(cu_g_l: float, acid_g_l: float, temp_c: float, density: float = 1.2) -> Stream:
    cuso4 = cu_g_l / CU_G_MOL * EW_CATALOG["CuSO4"].molar_mass
    kg = {"CuSO4": cuso4 * FLOW_L_H / 1000.0, "H2SO4": acid_g_l * FLOW_L_H / 1000.0}
    kg["H2O"] = FLOW_L_H * density - sum(kg.values())
    return Stream(kg, temp_c)


def run_ew(p: EWParams) -> EWView:
    """Un cátodo (dos caras) en una celda de electrolito de composición fija. Lanza ValueError
    si el modelo no puede calcular (composición fuera de rango, agua o cobre agotados)."""
    both = 2.0 * p.face_area_m2
    if not all(math.isfinite(v) for v in (p.cu_g_l, p.acid_g_l, p.temp_c, p.cycle_days)):
        raise ValueError("Los datos deben ser números finitos")
    feed = electrolyte(p.cu_g_l, p.acid_g_l, p.temp_c)
    if min(feed.flows.values()) < 0:
        raise ValueError("Cobre y ácido suman más que el electrolito: revisa las concentraciones")
    unit = Electrowinning("EW", ("Rico",), ("Pobre", "Catodos", "O2"), p.current_density, both,
                          p.efficiency)  # fmt: skip
    result = unit.solve([feed], EW_CATALOG)
    hours = p.cycle_days * 24.0
    mass = result.copper_kg_h * hours
    # El electrolito de composición fija pierde una fracción mínima de Cu al depositar: los avisos
    # de rango se evalúan con los datos exactos del visitante, no con el pobre.
    own = [w for w in result.warnings if not w.startswith("conductividad")]
    own += conductivity(p.cu_g_l, p.acid_g_l, p.temp_c)[1]
    return EWView(p, result, mass, thickness_mm(mass, both), tuple(own))
