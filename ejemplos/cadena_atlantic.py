"""Una tonelada de la mezcla 1 de Atlantic Copper, de concentrado a cátodo (4a → 4c).

    python ejemplos/cadena_atlantic.py

Fusión con la ley de mata y la sílice medidas (Bacedoni et al. 2020); convertidor con los
parámetros del ejemplo de Ilo (4b); nave con la geometría de Mount Isa (4c). Ver docs/cadena.md.
"""

from procesos.cadena import concentrate_to_cathode
from procesos.fusion_datos import BLENDS, INDUSTRIAL

_oc, _oe, _flux, grade, sio2, loss = INDUSTRIAL["Mezcla 1"]
r = concentrate_to_cathode(BLENDS["Mezcla 1"], matte_grade=grade, slag_sio2=sio2,
                           heat_loss_mj_t=loss)  # fmt: skip

print(f"Por t de concentrado: {1000 * r.concentrate_cu_t:.1f} kg de Cu y "
      f"{1000 * r.concentrate_s_t:.1f} kg de S")  # fmt: skip
print("Destino del cobre (kg):")
for name, t in r.copper_t().items():
    print(f"  {name:30}{1000 * t:8.2f}  ({100 * t / r.concentrate_cu_t:5.2f} %)")
print("Destino del azufre (kg):")
for name, t in r.sulfur_t().items():
    print(f"  {name:30}{1000 * t:8.2f}")
print(f"Ácido potencial: {r.potential_acid_t:.3f} t por t de concentrado")
print(f"Oxígeno de fusión {r.smelting.oxygen_nm3_t:.0f} Nm³ · aire del convertidor "
      f"{r.slag_blow.air_nm3 + r.copper_blow.air_nm3:.0f} Nm³ · gas natural del horno de ánodos "
      f"{r.anode.ch4_min_kg:.2f}-{r.anode.ch4_max_kg:.2f} kg · refinación "
      f"{r.refining.power_kw:.1f} kWh (celda {r.refining.cell_voltage:.3f} V)")  # fmt: skip
