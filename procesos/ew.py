"""Electroobtención (EW) de cobre: masa por Faraday y voltaje de celda por componentes.

Reacción global (por cada Cu depositado): CuSO4 + H2O -> Cu + H2SO4 + ½ O2. Lo depositado es
eficiencia × I / (2F); el resto de la corriente se pierde en cortocircuitos y en el ciclo
Fe³⁺/Fe²⁺, sin cambio químico neto. La celda es de mezcla completa: el voltaje se evalúa con el
electrolito que sale (el pobre).

Voltaje de celda = E_rev + η_a + |η_c| + j·L/κ + V_contactos:
- E_rev = 1,229 - 0,337 = 0,892 V (Beukes y Badenhorst 2009, J. SAIMM 109, ec. 72).
- η_a = 0,5 + 0,12·log10(j en A/dm²), Tafel del O₂ sobre plomo (Beukes y Badenhorst, ec. 74).
- η_c = RT/(αnF)·[ln(j/i0) + ln(iL/(iL - j))], α = 0,5 e i0 = 0,2 A/m² (Beukes y Badenhorst,
  ec. 63-64); sin densidad límite iL, solo el término de activación.
- κ: correlación de Kalliomäki et al. (2021, Miner. Eng. 171, 107069, CC BY, Tabla 4) para
  electrolitos de EW, con solo los términos de Cu, H2SO4 y temperatura (sin impurezas).
- V_contactos ≈ 0,3 V (Schlesinger et al. 2011, citado en JOM 76, 2024).
Ver docs/ew.md.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace

from .species import Catalog
from .stream import Stream, moles
from .thermo import stream_enthalpy
from .units import _check_fraction, _check_ports, _mixed, inlet_enthalpy

FARADAY = 96485.33212  # C/mol
GAS_R = 8.314462618  # J/(mol·K)
E_REV = 1.229 - 0.337  # V
TAFEL_ANODE = (0.5, 0.12)  # η_a = a + b·log10(j en A/dm²)
ALPHA_CATHODE = 0.5
I0_CATHODE = 0.2  # A/m²
GAP_M = 0.045  # distancia ánodo-cátodo (Beukes y Badenhorst, Tabla III)
CONTACTS_V = 0.3
ACID_SPLIT = 142.0  # g/L: Kalliomäki usa un modelo bajo y otro sobre esta acidez
# κ (mS/cm) = c0 + cCu·Cu + cA·A + cT·T + cCuA·Cu·A + cAT·A·T, con g/L y °C.
KAPPA_LOW = (19.442, 1.328, 3.386, -0.288, -0.028, 0.020)  # κEW.1: 50-142 g/L de ácido
KAPPA_HIGH = (217.759, 0.175, 1.805, -1.293, -0.017, 0.029)  # κEW.2: 120-223 g/L
KAPPA_RANGE = {"low": ((40, 90), (50, 142)), "high": ((40, 70), (120, 223))}  # Cu, ácido
KAPPA_T_RANGE = (50.0, 70.0)


def conductivity(cu_g_l: float, acid_g_l: float, temp_c: float) -> tuple[float, list[str]]:
    """Conductividad (S/m) del electrolito y avisos si se sale del rango de la correlación."""
    model = "low" if acid_g_l < ACID_SPLIT else "high"
    c0, c_cu, c_a, c_t, c_cua, c_at = KAPPA_LOW if model == "low" else KAPPA_HIGH
    ms_cm = (
        c0
        + c_cu * cu_g_l
        + c_a * acid_g_l
        + c_t * temp_c
        + c_cua * cu_g_l * acid_g_l
        + c_at * acid_g_l * temp_c
    )
    warnings = []
    (cu_lo, cu_hi), (a_lo, a_hi) = KAPPA_RANGE[model]
    for label, value, lo, hi in (
        ("Cu", cu_g_l, cu_lo, cu_hi),
        ("H2SO4", acid_g_l, a_lo, a_hi),
        ("temperatura", temp_c, *KAPPA_T_RANGE),
    ):
        if not lo <= value <= hi:
            warnings.append(
                f"conductividad: {label} = {value:.2f} fuera del rango de la correlación "
                f"({lo}-{hi}); es una extrapolación"
            )
    if ms_cm <= 0:
        raise ValueError(f"conductividad no física ({ms_cm:.1f} mS/cm): composición fuera de rango")
    return ms_cm / 10.0, warnings


def anode_overpotential(j: float) -> float:
    a, b = TAFEL_ANODE
    return a + b * math.log10(j / 100.0)


def cathode_overpotential(j: float, temp_c: float, limiting: float | None = None) -> float:
    """Valor absoluto (V). Con densidad límite, suma el término de concentración."""
    factor = GAS_R * (temp_c + 273.15) / (ALPHA_CATHODE * 2 * FARADAY)
    eta = factor * math.log(j / I0_CATHODE)
    if limiting is not None:
        if j >= limiting:
            raise ValueError(f"densidad de corriente {j:.0f} ≥ densidad límite {limiting:.0f} A/m²")
        eta += factor * math.log(limiting / (limiting - j))
    return eta


@dataclass(frozen=True)
class EWResult:
    current_a: float  # corriente total que pasa por los cátodos (suma de las celdas)
    copper_kg_h: float
    limited: bool  # se agotó el cobre o el agua antes de lo que pide la corriente
    cell_voltage: float
    components: dict[str, float]  # V; vacío si el voltaje lo dio el usuario
    conductivity_s_m: float | None
    spent_cu_g_l: float
    spent_acid_g_l: float
    warnings: tuple[str, ...]

    @property
    def power_kw(self) -> float:
        return self.cell_voltage * self.current_a / 1000.0

    @property
    def specific_energy_kwh_t(self) -> float:
        return self.power_kw / (self.copper_kg_h / 1000.0) if self.copper_kg_h > 0 else math.inf


@dataclass(frozen=True)
class Electrowinning:
    """Salidas: (electrolito pobre, cátodos, oxígeno). La corriente total es j × área catódica
    (las dos caras de todos los cátodos de la nave)."""

    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    current_density: float  # A/m²
    cathode_area_m2: float
    current_efficiency: float = 0.92
    cell_voltage: float | None = None  # V; si falta, se calcula por componentes
    gap_m: float = GAP_M
    contacts_v: float = CONTACTS_V
    limiting_current: float | None = None  # A/m²
    density: float = 1.2  # kg/L del electrolito, para pasar a g/L
    copper: str = "CuSO4"
    acid: str = "H2SO4"
    water: str = "H2O"
    metal: str = "Cu"
    oxygen: str = "O2"

    def __post_init__(self) -> None:
        _check_ports(self.name, self.inputs, self.outputs, 3)
        positives = {
            "densidad de corriente": self.current_density,
            "área catódica": self.cathode_area_m2,
            "distancia ánodo-cátodo": self.gap_m,
            "densidad": self.density,
        }
        for label, value in positives.items():
            if not (math.isfinite(float(value)) and value > 0):
                raise ValueError(f"{self.name}: {label} debe ser positiva: {value}")
        if self.contacts_v < 0 or (self.cell_voltage is not None and self.cell_voltage <= 0):
            raise ValueError(f"{self.name}: voltajes no pueden ser negativos")
        object.__setattr__(
            self,
            "current_efficiency",
            _check_fraction(self.current_efficiency, f"{self.name}: eficiencia de corriente"),
        )

    @property
    def current_a(self) -> float:
        return self.current_density * self.cathode_area_m2

    def _products(self, inputs: Sequence[Stream], catalog: Catalog) -> tuple[Stream, ...]:
        feed = _mixed(inputs, catalog)
        amounts = moles(feed, catalog)
        wanted = self.current_efficiency * self.current_a / (2 * FARADAY) * 3.6  # kmol/h
        extent = min(wanted, amounts.get(self.copper, 0.0), amounts.get(self.water, 0.0))
        flows = dict(feed.flows)
        for species, coefficient in ((self.copper, -1), (self.water, -1), (self.acid, 1)):
            new = flows.get(species, 0.0) + coefficient * extent * catalog[species].molar_mass
            flows[species] = max(new, 0.0)
        t, p = feed.temperature, feed.pressure
        cathodes = Stream({self.metal: extent * catalog[self.metal].molar_mass}, t, p)
        gas = Stream({self.oxygen: 0.5 * extent * catalog[self.oxygen].molar_mass}, t, p)
        return Stream(flows, t, p), cathodes, gas

    def compute(self, inputs: Sequence[Stream], catalog: Catalog) -> tuple[Stream, ...]:
        return self._products(inputs, catalog)

    def solve(self, inputs: Sequence[Stream], catalog: Catalog) -> EWResult:
        spent, cathodes, _ = self._products(inputs, catalog)
        litres = spent.total / self.density
        cu = spent.flow(self.copper) * catalog[self.metal].molar_mass
        cu_g_l = cu / catalog[self.copper].molar_mass / litres * 1000.0
        acid_g_l = spent.flow(self.acid) / litres * 1000.0
        copper = cathodes.flow(self.metal)
        wanted = self.current_efficiency * self.current_a / (2 * FARADAY) * 3.6
        limited = copper < wanted * catalog[self.metal].molar_mass * (1 - 1e-12)
        warnings: list[str] = []
        if limited:
            warnings.append("la corriente pide más cobre del que trae el electrolito")
        if self.cell_voltage is not None:
            return EWResult(self.current_a, copper, limited, self.cell_voltage, {}, None,
                            cu_g_l, acid_g_l, tuple(warnings))  # fmt: skip
        j, t = self.current_density, spent.temperature
        kappa, kappa_warnings = conductivity(cu_g_l, acid_g_l, t)
        components = {
            "reversible": E_REV,
            "anódico": anode_overpotential(j),
            "catódico": cathode_overpotential(j, t, self.limiting_current),
            "electrolito": j * self.gap_m / kappa,
            "contactos": self.contacts_v,
        }
        return EWResult(self.current_a, copper, limited, sum(components.values()), components,
                        kappa, cu_g_l, acid_g_l, tuple(warnings + kappa_warnings))  # fmt: skip

    def power_kw(self, inputs: Sequence[Stream], catalog: Catalog) -> float:
        return self.solve(inputs, catalog).power_kw

    def heat_duty(self, inputs: Sequence[Stream], catalog: Catalog) -> float:
        """Calor intercambiado (kW) para salir a la temperatura de entrada; negativo = la nave
        debe perder ese calor (lo hace por evaporación y convección)."""
        outputs = self._products(inputs, catalog)
        h_out = sum(stream_enthalpy(s.flows, s.temperature, catalog) for s in outputs)
        return h_out - inlet_enthalpy(inputs, catalog) - self.power_kw(inputs, catalog)

    def with_parameter(self, key: str, value: float) -> Electrowinning:
        """Claves: densidad_corriente, eficiencia_corriente, voltaje_celda, area_catodica."""
        fields = {
            "densidad_corriente": "current_density",
            "eficiencia_corriente": "current_efficiency",
            "voltaje_celda": "cell_voltage",
            "area_catodica": "cathode_area_m2",
        }
        if key not in fields:
            raise KeyError(f"{self.name}: parámetro desconocido {key!r}; use uno de {list(fields)}")
        return replace(self, **{fields[key]: value})


def specific_energy_kwh_t(cell_voltage: float, efficiency: float, molar_mass: float) -> float:
    """kWh por tonelada de cobre: z·F·V / (eficiencia·M·3600), con M en g/mol."""
    return 2 * FARADAY * cell_voltage / (efficiency * molar_mass * 3600.0) * 1000.0
