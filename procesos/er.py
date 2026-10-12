"""Electrorrefinación (ER) de cobre: Faraday, reparto del ánodo, voltaje de celda y lo que se
acumula en el electrolito (purga de Ni y celdas liberadoras).

La primera entrada son los ánodos; las demás, el electrolito. Salidas: (electrolito, cátodos,
barro anódico, chatarra anódica).
- Cátodo: Cu²⁺ + 2e → Cu, eficiencia × I / 2F. Ánodo: Cu → Cu²⁺ + 2e y Ni → Ni²⁺ + 2e (la
  fracción de Ni que va al electrolito), con la misma eficiencia: en ER la corriente que se
  pierde es de cortocircuitos, que tocan a los dos electrodos. Así el Ni desplaza Cu del
  electrolito al cátodo sin consumir ácido.
- El ánodo se consume parejo: de lo consumido, el Ni que no se disuelve y las demás especies
  (Ag, Au, Se...) van al barro; lo no consumido sale como chatarra.
- El Cu2O del ánodo se disuelve químicamente: Cu2O + H2SO4 → CuSO4 + Cu + H2O, con el Cu al
  barro. Es el cobre que se acumula en el electrolito y el ácido que se consume; lo retiran las
  celdas liberadoras (electroobtención).

Voltaje = j·L/κ + contactos y placas + sobrepotencial neto. κ: modelo κER.2 de Kalliomäki et al.
(2021, Miner. Eng. 171, 107069, CC BY, Tabla 4), log10 de mS/cm con Cu, H2SO4, Ni, As y T.
Contactos y placas: 60 mV y sobrepotencial neto 0, como la Tabla II del compendio IsaKidd 2020
(refinería típica a 300 A/m²). Sin balance de calor. Ver docs/er.md.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace

from .elements import ATOMIC_WEIGHTS, parse_formula, strip_phase
from .ew import FARADAY
from .species import Catalog
from .stream import Stream, mix
from .units import _check_fraction, _check_ports

CONTACTS_V = 0.060  # 10 mV contacto anódico + 25 placa + 25 contacto catódico (IsaKidd, Tabla II)
# log10(κ, mS/cm), κER.2: términos y coeficientes (Kalliomäki et al. 2021, Tabla 4).
KAPPA_ER2 = {
    "1": 2.446,
    "Cu": -6.089e-4,
    "A": 1.553e-3,
    "Ni": -2.117e-3,
    "As": 1.398e-4,
    "T": 9.518e-4,
    "Cu*A": -7.753e-6,
    "Cu*Ni": -1.235e-5,
    "Cu*As": -8.915e-6,
    "A*As": -4.930e-6,
    "A*T": 1.030e-5,
    "T*As": 1.019e-5,
}
KAPPA_RANGE = {"Cu": (40, 60), "A": (130, 223), "Ni": (0, 30), "As": (0, 63.8), "T": (50, 70)}


def conductivity(cu: float, acid: float, ni: float, arsenic: float,
                 temp_c: float) -> tuple[float, list[str]]:  # fmt: skip
    """Conductividad (S/m) de un electrolito de ER (g/L y °C) y avisos de extrapolación."""
    x = {"1": 1.0, "Cu": cu, "A": acid, "Ni": ni, "As": arsenic, "T": temp_c}
    log_ms_cm = sum(c * math.prod(x[t] for t in term.split("*")) for term, c in KAPPA_ER2.items())
    warnings = [
        f"conductividad: {k} = {x[k]:.2f} fuera del rango del modelo κER.2 ({lo}-{hi})"
        for k, (lo, hi) in KAPPA_RANGE.items()
        if not lo <= x[k] <= hi
    ]
    return 10**log_ms_cm / 10.0, warnings


@dataclass(frozen=True)
class ERResult:
    current_a: float
    copper_kg_h: float  # cátodos
    anode_consumed: float  # fracción del ánodo que entra que se disuelve
    limited: bool
    cell_voltage: float
    components: dict[str, float]
    conductivity_s_m: float
    electrolyte_g_l: dict[str, float]  # Cu, H2SO4, Ni, As del electrolito que sale
    copper_gain_kg_h: float  # Cu que el electrolito gana (Cu2O disuelto)
    nickel_gain_kg_h: float
    acid_consumed_kg_h: float
    electrolyte_m3_h: float
    warnings: tuple[str, ...]

    @property
    def power_kw(self) -> float:
        return self.cell_voltage * self.current_a / 1000.0

    @property
    def specific_energy_kwh_t(self) -> float:
        return self.power_kw / (self.copper_kg_h / 1000.0) if self.copper_kg_h > 0 else math.inf

    def nickel_bleed_m3_h(self, nickel_limit_g_l: float) -> float:
        """Purga (m³/h de electrolito) que saca el Ni que entra con el circuito en el límite."""
        if nickel_limit_g_l <= 0:
            raise ValueError("El límite de Ni debe ser positivo")
        return self.nickel_gain_kg_h / nickel_limit_g_l

    def liberator_current_a(self, efficiency: float, copper_removed_kg_h: float = 0.0) -> float:
        """Corriente de las celdas liberadoras para retirar el Cu que gana el electrolito, menos
        el que ya sale por otra vía (p. ej. con la purga)."""
        _check_fraction(efficiency, "eficiencia de las liberadoras")
        surplus = max(self.copper_gain_kg_h - copper_removed_kg_h, 0.0)
        return surplus / ATOMIC_WEIGHTS["Cu"] * 2 * FARADAY / 3.6 / efficiency


@dataclass(frozen=True)
class Electrorefining:
    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    current_density: float  # A/m²
    cathode_area_m2: float  # las dos caras de todos los cátodos
    current_efficiency: float
    gap_m: float  # distancia ánodo-cátodo
    contacts_v: float = CONTACTS_V
    overpotential_v: float = 0.0
    nickel_to_electrolyte: float = 1.0
    density: float = 1.2  # kg/L del electrolito
    copper: str = "CuSO4"
    acid: str = "H2SO4"
    water: str = "H2O"
    metal: str = "Cu"
    cuprite: str = "Cu2O"
    nickel: str = "Ni"
    nickel_sulfate: str = "NiSO4"
    arsenic: str | None = None  # especie del As disuelto (solo para la conductividad)
    nickel_limit_g_l: float | None = None  # para dimensionar la purga
    liberator_efficiency: float | None = None  # para dimensionar las celdas liberadoras

    def __post_init__(self) -> None:
        _check_ports(self.name, self.inputs, self.outputs, 4)
        if len(self.inputs) < 2:
            raise ValueError(f"{self.name}: entradas = (ánodos, electrolito...)")
        positives = {
            "densidad de corriente": self.current_density,
            "área catódica": self.cathode_area_m2,
            "distancia ánodo-cátodo": self.gap_m,
            "densidad": self.density,
        }
        for label, value in positives.items():
            if not (math.isfinite(float(value)) and value > 0):
                raise ValueError(f"{self.name}: {label} debe ser positiva: {value}")
        if self.contacts_v < 0 or self.overpotential_v < 0:
            raise ValueError(f"{self.name}: voltajes no pueden ser negativos")
        fractions = {
            "current_efficiency": "eficiencia de corriente",
            "nickel_to_electrolyte": "fracción de Ni al electrolito",
        }
        for attr, label in fractions.items():
            object.__setattr__(
                self, attr, _check_fraction(getattr(self, attr), f"{self.name}: {label}")
            )

    @property
    def current_a(self) -> float:
        return self.current_density * self.cathode_area_m2

    def _kmol(self, stream: Stream, species: str, catalog: Catalog) -> float:
        return stream.flow(species) / catalog[species].molar_mass if species in catalog else 0.0

    def _split(self, inputs: Sequence[Stream], catalog: Catalog):
        if catalog.thermo is not None:
            raise ValueError(f"{self.name}: la electrorrefinación no tiene balance de calor")
        anode, electrolyte = inputs[0], mix(inputs[1:])
        n_cu = self._kmol(anode, self.metal, catalog)
        n_ni = self._kmol(anode, self.nickel, catalog)
        n_cu2o = self._kmol(anode, self.cuprite, catalog)
        f = self.nickel_to_electrolyte
        per_anode = n_cu + f * n_ni  # kmol de metal que pasa por los electrodos, por ánodo entero
        wanted = self.current_efficiency * self.current_a / (2 * FARADAY) * 3.6  # kmol/h
        phi = min(1.0, wanted / per_anode) if per_anode > 0 else 0.0
        return anode, electrolyte, n_cu, n_ni, n_cu2o, phi, phi * per_anode

    def compute(self, inputs: Sequence[Stream], catalog: Catalog) -> tuple[Stream, ...]:
        anode, electrolyte, n_cu, n_ni, n_cu2o, phi, deposited = self._split(inputs, catalog)
        f = self.nickel_to_electrolyte
        dissolved_cu2o = phi * n_cu2o
        delta = {  # kmol/h en el electrolito
            self.copper: phi * n_cu - deposited + dissolved_cu2o,
            self.nickel_sulfate: phi * f * n_ni,
            self.acid: -dissolved_cu2o,
            self.water: dissolved_cu2o,
        }
        flows = dict(electrolyte.flows)
        for species, kmol in delta.items():
            if kmol:
                flows[species] = flows.get(species, 0.0) + kmol * catalog[species].molar_mass
        negative = [s for s, v in flows.items() if v < -1e-9]
        if negative:
            raise ValueError(f"{self.name}: el electrolito se queda sin {', '.join(negative)}")
        t, p = electrolyte.temperature, electrolyte.pressure
        cathodes = Stream({self.metal: deposited * catalog[self.metal].molar_mass}, t, p)
        consumed = {s: phi * kg for s, kg in anode.flows.items()}
        slimes = {s: kg for s, kg in consumed.items() if s not in (self.metal, self.cuprite)}
        if self.nickel in slimes:
            slimes[self.nickel] *= 1 - f
        slimes[self.metal] = dissolved_cu2o * catalog[self.metal].molar_mass
        scrap = {s: (1 - phi) * kg for s, kg in anode.flows.items()}
        return (
            Stream({s: max(v, 0.0) for s, v in flows.items()}, t, p),
            cathodes,
            Stream(slimes, t, p),
            Stream(scrap, t, p),
        )

    def _g_l(self, stream: Stream, species: str | None, element: str, catalog: Catalog,
             litres: float) -> float:  # fmt: skip
        if species is None or species not in catalog:
            return 0.0
        n = parse_formula(strip_phase(catalog[species].formula)[0]).get(element, 0.0)
        kmol = stream.flow(species) / catalog[species].molar_mass
        return kmol * n * ATOMIC_WEIGHTS[element] / litres * 1000.0

    def solve(self, inputs: Sequence[Stream], catalog: Catalog) -> ERResult:
        electrolyte, cathodes, _slimes, _scrap = self.compute(inputs, catalog)
        _a, feed, _cu, _ni, n_cu2o, phi, deposited = self._split(inputs, catalog)
        litres = electrolyte.total / self.density
        conc = {
            "Cu": self._g_l(electrolyte, self.copper, "Cu", catalog, litres),
            "H2SO4": electrolyte.flow(self.acid) / litres * 1000.0,
            "Ni": self._g_l(electrolyte, self.nickel_sulfate, "Ni", catalog, litres),
            "As": self._g_l(electrolyte, self.arsenic, "As", catalog, litres),
        }
        kappa, warnings = conductivity(conc["Cu"], conc["H2SO4"], conc["Ni"], conc["As"],
                                       electrolyte.temperature)  # fmt: skip
        wanted = self.current_efficiency * self.current_a / (2 * FARADAY) * 3.6
        limited = deposited < wanted * (1 - 1e-12)
        if limited:
            warnings.insert(0, "la corriente pide más ánodo del que entra: se consume entero")
        j = self.current_density
        components = {
            "electrolito": j * self.gap_m / kappa,
            "contactos y placas": self.contacts_v,
            "sobrepotencial neto": self.overpotential_v,
        }
        cu = ATOMIC_WEIGHTS["Cu"]
        gained_ni = 0.0
        if self.nickel_sulfate in catalog:
            gained = electrolyte.flow(self.nickel_sulfate) - feed.flow(self.nickel_sulfate)
            gained_ni = gained / catalog[self.nickel_sulfate].molar_mass * ATOMIC_WEIGHTS["Ni"]
        return ERResult(
            current_a=self.current_a,
            copper_kg_h=cathodes.flow(self.metal),
            anode_consumed=phi,
            limited=limited,
            cell_voltage=sum(components.values()),
            components=components,
            conductivity_s_m=kappa,
            electrolyte_g_l=conc,
            copper_gain_kg_h=phi * n_cu2o * cu,
            nickel_gain_kg_h=gained_ni,
            acid_consumed_kg_h=phi * n_cu2o * catalog[self.acid].molar_mass,
            electrolyte_m3_h=litres / 1000.0,
            warnings=tuple(warnings),
        )

    def power_kw(self, inputs: Sequence[Stream], catalog: Catalog) -> float:
        return self.solve(inputs, catalog).power_kw

    def with_parameter(self, key: str, value: float) -> Electrorefining:
        """Claves: densidad_corriente, eficiencia_corriente, area_catodica, distancia."""
        fields = {
            "densidad_corriente": "current_density",
            "eficiencia_corriente": "current_efficiency",
            "area_catodica": "cathode_area_m2",
            "distancia": "gap_m",
        }
        if key not in fields:
            raise KeyError(f"{self.name}: parámetro desconocido {key!r}; use uno de {list(fields)}")
        return replace(self, **{fields[key]: value})


def gap_from_geometry(pitch_m: float, anode_thickness_m: float, cathode_thickness_m: float,
                      deposit_m: float = 0.0) -> float:  # fmt: skip
    """Distancia ánodo-cátodo (m): media distancia entre cátodos menos medio ánodo, media placa
    y el cobre depositado en una cara."""
    gap = pitch_m / 2 - anode_thickness_m / 2 - cathode_thickness_m / 2 - deposit_m
    if gap <= 0:
        raise ValueError(f"geometría imposible: distancia ánodo-cátodo {gap * 1000:.1f} mm")
    return gap
