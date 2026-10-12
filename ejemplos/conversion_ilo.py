"""Conversión y refinación a fuego de 100 t de mata, con parámetros públicos de Ilo. ILUSTRATIVO.

    python ejemplos/conversion_ilo.py

- Mata de 62 % de Cu (Southern Copper, presentación ante la SEC de 2007).
- Escoria de convertidor de Ilo: 2,85 % Cu, 25,5 % SiO2 y 25,6 % del Fe como magnetita
  (Morales et al. 2004, promedio de enero a mayo de 2000, antes de la modernización).
- Eficiencia de O2: promedio de Flin Flon (Kyllo 1995): 62 % en escoria y 77 % en cobre.
- Fin de etapa y escoria del soplado a cobre como en Rönnskär (Lennartsson 2013).
No es una validación: Ilo no publica sus flujos por carga. Ver docs/conversion.md.
"""

from procesos.anodos import refine
from procesos.conversion import carry_over, copper_blow, matte, slag_blow
from procesos.conversion_datos import ILO_MAGNETITE_FE, ILO_SLAG

sb = slag_blow(
    [matte("mata", 100.0, 62.0)],
    end_fe_pct=0.4,
    slag_cu_pct=ILO_SLAG["Cu"],
    magnetite_fe=ILO_MAGNETITE_FE,
    slag_sio2_pct=ILO_SLAG["SiO2"],
    efficiency=0.62,
)
cb = copper_blow(
    [carry_over(sb, "metal", 1.0, 1200.0, "metal blanco")],
    blister_s_pct=0.023,
    slag_cu_pct=28.3,
    efficiency=0.77,
)
anode = refine(cb.mass_t("blister"), 0.023, anode_s_pct=0.003)
flux_t = sum(f.tonnes.get("SiO2", 0.0) for f in sb.feeds if f.name == "fundente")

slag_t, white_t = sb.mass_t("escoria"), sb.mass_t("metal")
cb_slag_t, blister_t = cb.mass_t("escoria"), cb.mass_t("blister")
so2_t = (sb.products["gas:SO2"] + cb.products["gas:SO2"]) * 64.058 / 1000
print("Por 100 t de mata de 62 % Cu")
print(f"  soplado a escoria: aire {sb.air_nm3:9,.0f} Nm³, fundente {flux_t:5.1f} t, "
      f"escoria {slag_t:5.1f} t, metal blanco {white_t:5.1f} t")  # fmt: skip
print(f"  soplado a cobre:   aire {cb.air_nm3:9,.0f} Nm³, escoria {cb_slag_t:5.1f} t, "
      f"blíster {blister_t:5.1f} t")  # fmt: skip
print(f"  SO2 del convertidor: {so2_t:5.1f} t")
print(f"  horno de ánodos:   aire {anode.air_oxidation_nm3:7,.0f} Nm³, CH4 "
      f"{anode.ch4_min_kg:4.0f}-{anode.ch4_max_kg:4.0f} kg, ánodo {anode.anode_t:5.1f} t "
      f"({anode.anode_cu_pct:.2f} % Cu, sin impurezas menores)")  # fmt: skip
