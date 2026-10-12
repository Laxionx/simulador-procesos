"""Circuito piloto de flotación con la cinética de laboratorio (Minerals 16(7), 726, 2026).

    python ejemplos/flotacion_piloto.py

Rougher y scavenger de 2 celdas (28 min por etapa), cleaner de 17 L; el concentrado scavenger y
las colas cleaner vuelven al rougher. Cinética de Kelsall de dos componentes (Tablas 4-6).
Compara con la simulación de los autores (HSC SIM) y con lo medido en el piloto. Ver
docs/flotacion.md.
"""

from procesos.flotacion_datos import (
    FEED_KG_H,
    HSC_CONCENTRATE,
    HSC_TAILINGS,
    MINERALS,
    PILOT_CONCENTRATE,
    PILOT_CU_PCT,
    PILOT_TAILINGS,
    composition,
    solve_pilot,
)

solution, tau = solve_pilot()
conc, tails = solution.streams["Concentrado final"], solution.streams["Relave final"]
c, t = composition(conc), composition(tails)
print(f"τ del cleaner {tau:.1f} min · rendimiento {100 * conc.total / FEED_KG_H:.2f} % "
      f"(HSC 7,92 %) · Cu del concentrado {c['Ccp'] * 63.546 / 183.511:.2f} % "
      f"(piloto {PILOT_CU_PCT:.2f} %)")  # fmt: skip
print(f"{'':6}{'concentrado: modelo / HSC / piloto':>38}{'relave: modelo / HSC / piloto':>36}")
for m in MINERALS:
    print(f"{m:6}{c[m]:14.2f}{HSC_CONCENTRATE[m]:10.2f}{PILOT_CONCENTRATE[m]:10.2f}"
          f"{t[m]:16.2f}{HSC_TAILINGS[m]:10.2f}{PILOT_TAILINGS[m]:10.2f}")  # fmt: skip
