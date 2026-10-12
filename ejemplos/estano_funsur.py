"""Fundición de estaño en dos etapas con los datos de Funsur 2025. ILUSTRATIVO.

    python ejemplos/estano_funsur.py

- Concentrado y escoria de horno rotatorio de la Tabla 11 de la Memoria Integrada 2025 de
  Minsur: 87.527 t al 38,73 % de Sn y 1.091 t al 19,77 %; escoria de desecho al 0,55 % de Sn.
- La ganga del concentrado de San Rafael no se publica: se toma con las proporciones del
  concentrado analizado en Materials 2024 (Tabla 1), escaladas a la ley de Funsur (SUPUESTO).
- D = 200 y 35 (Kandalam et al. 2023), crudo con 2 % Fe, CaO/SiO2 = 0,3 con caliza, 15 % del Sn
  de la segunda etapa a humos (piloto CSIRO) y 50 % de CO en el gas (supuesto).
Ver docs/estano.md.
"""

from procesos.elements import molar_mass, parse_formula
from procesos.estano import feed, smelt_tin
from procesos.estano_datos import CASSITERITE_REF, FUNSUR

conc_t, grade, rot_t, rot_sn, refined_t, recovery, discard = FUNSUR[2025]
sno2 = grade * molar_mass(parse_formula("SnO2")) / 118.71
gangue = {k: v for k, v in CASSITERITE_REF.items() if k != "SnO2"}
scale = (100 - sno2) / sum(gangue.values())
concentrate = feed(conc_t, {"SnO2": sno2} | {k: v * scale for k, v in gangue.items()})
rot_sno = rot_sn * molar_mass(parse_formula("SnO")) / 118.71
rotary = feed(rot_t, {"SnO": rot_sno, "otros": 100 - rot_sno})
sn_in = conc_t * grade / 100 + rot_t * rot_sn / 100

print(f"Funsur 2025: {sn_in:,.0f} t de Sn entran; refinado {refined_t:,.0f} t; "
      f"recuperación reportada {recovery:.2f} %")  # fmt: skip
for label, iron_ore in (("sin mineral de hierro", 0.0), ("con 10 % de Fe2O3", 0.10 * conc_t)):
    feeds = {k: concentrate.get(k, 0.0) + rotary.get(k, 0.0) for k in concentrate | rotary}
    feeds["Fe2O3"] = feeds.get("Fe2O3", 0.0) + iron_ore
    r = smelt_tin(feeds, crude_fe_pct=2.0, discard_sn_pct=discard, d1=200.0, d2=35.0,
                  basicity=0.3, fume2=0.15)  # fmt: skip
    lost = r.stage2.slag_t * r.stage2.slag_pct("Sn") / 100
    print(f"\n{label}:")
    print(f"  crudo {r.stage1.metal_t:,.0f} t · escoria 1 {r.stage1.slag_t:,.0f} t al "
          f"{r.stage1.slag_pct('Sn'):.1f} % Sn · hardhead {r.stage2.metal_t:,.0f} t al "
          f"{r.stage2.metal_pct('Fe'):.0f} % Fe")  # fmt: skip
    print(f"  escoria de desecho {r.stage2.slag_t:,.0f} t · Sn perdido {lost:,.0f} t · "
          f"Recuperación del modelo {100 * r.recovery:.2f} %")  # fmt: skip
    print(f"  carbono {r.carbon_t:,.0f} t · caliza {r.limestone_t:,.0f} t · la escoria explica "
          f"{100 * lost / (sn_in - refined_t):.0f} % de la pérdida de la planta")  # fmt: skip

# Balance de calor (sin pérdidas del horno) y coherencia con las emisiones directas de Pisco.
from procesos.estano_calor import combustion_mj_per_kmol, tin_heat  # noqa: E402
from procesos.estano_datos import PISCO_SCOPE1_2025_T  # noqa: E402

feeds = {k: concentrate.get(k, 0.0) + rotary.get(k, 0.0) for k in concentrate | rotary}
base = smelt_tin(feeds, crude_fe_pct=2.0, discard_sn_pct=discard, d1=200.0, d2=35.0, basicity=0.3,
                 fume2=0.15)  # fmt: skip
heat = tin_heat(base)
deficit_gj = (heat.stage1.deficit_mj + heat.stage2.deficit_mj) / 1000
extra_ch4_kmol = (PISCO_SCOPE1_2025_T - heat.co2_t) / 44.009 * 1000
print("\nCalor (sin mineral de hierro, sin pérdidas del horno):")
print(f"  gas natural {heat.ch4_t:,.0f} t/año ({deficit_gj / conc_t:.2f} GJ por t de concentrado)")
reported = PISCO_SCOPE1_2025_T
extra_tj = extra_ch4_kmol * combustion_mj_per_kmol(1200.0) / 1e6
print(f"  CO2 {heat.co2_t:,.0f} t/año (proceso {heat.co2_process_t:,.0f}, gas "
      f"{heat.co2_fuel_t:,.0f}) frente a {reported:,.0f} t directas de Pisco")  # fmt: skip
print(f"  lo que falta, quemado como gas a 1.200 °C, son a lo sumo {extra_tj:,.0f} TJ/año "
      "de pérdidas y otros usos")  # fmt: skip
