"""Horno de ánodos (fase 4b): oxidación y reducción del cobre blíster. NO validado contra planta.

No se encontró un balance industrial medido que sea abierto, así que el módulo es estequiometría
con guardas de cierre y valores de referencia de patentes y literatura:
- Oxidación: el aire quema el S disuelto a SO2 y sube el O del baño (como Cu2O disuelto) hasta
  ``o_oxidized_pct``; por defecto 0,7 %, mitad del rango de 0,5-1,0 % de la patente EP2111472.
- Reducción: el gas natural baja el O hasta ``anode_o_pct``; por defecto 0,12 %, el máximo que
  cita Rudy i Metale Nieżelazne 58(12), 2013. El consumo de CH4 tiene dos cotas:
  mínima, si se quema entero (CH4 + 4 O → CO2 + 2 H2O), y máxima, si solo llega a
  CO + 2 H2 (CH4 + O → CO + 2 H2). La planta real queda entre las dos, según su eficiencia.
"""

from __future__ import annotations

from dataclasses import dataclass

from .elements import ATOMIC_WEIGHTS

NM3_PER_KMOL = 22.414
O2_IN_AIR = 0.21
M_CH4 = ATOMIC_WEIGHTS["C"] + 4 * ATOMIC_WEIGHTS["H"]


@dataclass(frozen=True)
class AnodeResult:
    blister_t: float
    anode_t: float
    anode_o_pct: float
    anode_s_pct: float
    o2_oxidation_kmol: float
    air_oxidation_nm3: float
    so2_kg: float
    ch4_min_kg: float
    ch4_max_kg: float

    @property
    def anode_cu_pct(self) -> float:
        return 100.0 - self.anode_o_pct - self.anode_s_pct

    def elements(self, blister_s_pct: float, blister_o_pct: float) -> dict[str, float]:
        """Diferencia entrada - salida de Cu, S y O (kg), para las guardas de cierre."""
        b = 1000.0 * self.blister_t
        a = 1000.0 * self.anode_t
        s_gas = self.so2_kg * ATOMIC_WEIGHTS["S"] / (ATOMIC_WEIGHTS["S"] + 2 * ATOMIC_WEIGHTS["O"])
        o_gas_so2 = self.so2_kg - s_gas
        o_removed = (self.ch4_min_kg / M_CH4) * 4 * ATOMIC_WEIGHTS["O"]
        o_in = b * blister_o_pct / 100 + 2 * self.o2_oxidation_kmol * ATOMIC_WEIGHTS["O"]
        return {
            "Cu": b * (1 - (blister_s_pct + blister_o_pct) / 100) - a * self.anode_cu_pct / 100,
            "S": b * blister_s_pct / 100 - a * self.anode_s_pct / 100 - s_gas,
            "O": o_in - a * self.anode_o_pct / 100 - o_gas_so2 - o_removed,
        }


def refine(
    blister_t: float,
    blister_s_pct: float,
    blister_o_pct: float = 0.0,
    *,
    anode_s_pct: float,
    o_oxidized_pct: float = 0.7,
    anode_o_pct: float = 0.12,
    o2_efficiency: float = 1.0,
) -> AnodeResult:
    """Oxida y reduce ``blister_t`` t de blíster. ``o2_efficiency`` = 1 da el aire mínimo."""
    if blister_t <= 0:
        raise ValueError("El blíster debe tener masa positiva")
    if not 0 <= anode_s_pct <= blister_s_pct:
        raise ValueError("El S del ánodo debe estar entre 0 y el del blíster")
    if not anode_o_pct <= o_oxidized_pct or not blister_o_pct <= o_oxidized_pct:
        raise ValueError("El O tras la oxidación debe ser el máximo del ciclo")
    if anode_o_pct < 0 or not 0 < o2_efficiency <= 1:
        raise ValueError("O del ánodo negativo o eficiencia fuera de (0, 1]")
    cu_kg = 1000.0 * blister_t * (1 - (blister_s_pct + blister_o_pct) / 100)
    # Cobre, S y O del baño en cada momento: el Cu no cambia; el S y el O sí.
    oxidized_kg = cu_kg / (1 - (anode_s_pct + o_oxidized_pct) / 100)
    anode_kg = cu_kg / (1 - (anode_s_pct + anode_o_pct) / 100)
    s_removed = 1000.0 * blister_t * blister_s_pct / 100 - anode_kg * anode_s_pct / 100
    o_added = oxidized_kg * o_oxidized_pct / 100 - 1000.0 * blister_t * blister_o_pct / 100
    o_removed = oxidized_kg * o_oxidized_pct / 100 - anode_kg * anode_o_pct / 100
    s_kmol = s_removed / ATOMIC_WEIGHTS["S"]
    o2 = s_kmol + o_added / ATOMIC_WEIGHTS["O"] / 2  # S + O2 → SO2; 2 [O] por O2
    o_kmol = o_removed / ATOMIC_WEIGHTS["O"]
    return AnodeResult(
        blister_t=blister_t,
        anode_t=anode_kg / 1000.0,
        anode_o_pct=anode_o_pct,
        anode_s_pct=anode_s_pct,
        o2_oxidation_kmol=o2,
        air_oxidation_nm3=o2 / o2_efficiency / O2_IN_AIR * NM3_PER_KMOL,
        so2_kg=s_kmol * (ATOMIC_WEIGHTS["S"] + 2 * ATOMIC_WEIGHTS["O"]),
        ch4_min_kg=o_kmol / 4 * M_CH4,
        ch4_max_kg=o_kmol * M_CH4,
    )
