"""Horno flash de Atlantic Copper: oxígeno, enriquecimiento y fundente de cuatro mezclas.

    python ejemplos/fusion_atlantic_copper.py

Datos de Bacedoni, Moreno-Ventas y Ríos (2020), Metals 10(9) 1229, CC BY. Ver docs/fusion.md.
"""

from procesos.fusion import smelt
from procesos.fusion_datos import BLENDS, INDUSTRIAL

print(f"{'':10}{'OC Nm3/t':>18}{'O2 % vol':>16}{'Fundente %':>16}   Mata   Escoria   SO2  (kg/t)")
print(f"{'':10}{'modelo  planta':>18}{'modelo planta':>16}{'modelo planta':>16}")
for blend, mineralogy in BLENDS.items():
    oc, oe, flux, grade, sio2, loss = INDUSTRIAL[blend]
    r = smelt(mineralogy, grade, sio2, loss)
    print(
        f"{blend:10}{r.oxygen_nm3_t:9.1f}{oc:9.1f}{r.enrichment_pct:9.1f}{oe:7.1f}"
        f"{r.flux_pct:9.2f}{flux:7.2f}   {r.matte_kg:4.0f}   {r.slag_kg:5.0f}   {r.so2_kg:4.0f}"
    )
