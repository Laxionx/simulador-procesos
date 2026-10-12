# Fusión flash de cobre (fase 4a)

`procesos.fusion.smelt` hace el balance de masa y de calor de un horno de fusión flash por
tonelada de carga seca. Recibe la mineralogía de la mezcla, la ley de mata y la sílice de la
escoria que se quieren y la pérdida térmica del horno. Devuelve:
- el coeficiente de oxígeno (OC, Nm³ de O2 por t);
- el enriquecimiento del aire de proceso (% vol de O2), con el que el horno funde sin combustible;
- el fundente (SiO2, % de la carga);
- las masas de mata, escoria y SO2.

```python
from procesos.fusion import smelt
from procesos.fusion_datos import BLENDS

r = smelt(BLENDS["Mezcla 1"], matte_grade=63.7, slag_sio2=29.0, heat_loss_mj_t=205.5)
r.oxygen_nm3_t, r.enrichment_pct, r.flux_pct   # 161,8 Nm³/t · 50,7 % · 6,79 %
```

`python ejemplos/fusion_atlantic_copper.py` corre las cuatro mezclas de la validación.

Es un **módulo de cálculo**, no un equipo del YAML. Sus especies son minerales y fases fundidas a
1.300 °C, y la ley de mata y la sílice de la escoria son metas que fijan el reparto. Encaja mal
con el reactor de conversión fija de las plantas hidrometalúrgicas.

## Modelo

Trece incógnitas, en kmol por t de carga:
- **Mata:** Cu2S, FeS y ZnS.
- **Escoria:** FeO, SiO2, ZnO, ZnS, Cu2O y Cu2S.
- **Gas:** SO2.
- **Entradas:** el O2 y el N2 del aire de proceso y el SiO2 del fundente.

Trece ecuaciones:

| Ecuación | Cantidad |
|---|---|
| Balance de Cu, Fe, Zn, S, O y Si | 6 |
| Ley de mata (masa de Cu / masa de mata) | 1 |
| SiO2 de la escoria (la ganga inerte también es escoria) | 1 |
| Cu en escoria = ley / D(Cu mata/escoria), con D = 63,45 | 1 |
| Cu2S mata / Cu2S escoria = 1.900,28 (molar); el resto del Cu de la escoria es Cu2O | 1 |
| ZnO / ZnS de la escoria = 24,18 (molar) | 1 |
| % Zn escoria / % Zn mata = 1,95 | 1 |
| Calor: H(carga, 25 °C) + H(fundente, 25 °C) + H(aire, 227 °C) = H(productos, 1.300 °C) + pérdida | 1 |

Los coeficientes de distribución y las relaciones molares son los que Bacedoni et al. (2020)
calcularon con FactSage para una mata de 62 % y una escoria con 29 % de SiO2 a 1.300 °C (sus
Tablas 1 y 2). Todas las ecuaciones son lineales salvo el reparto del zinc. Ese reparto se
resuelve por sustitución sucesiva sobre la razón escoria/mata y converge en pocas vueltas.

**Supuestos declarados antes de calcular:**
- Entalpías absolutas: ΔfH de USGS B2131 más calor sensible (ver abajo).
- FeO y SiO2 de la escoria son líquidos subenfriados: el sólido más su calor de fusión de JANAF.
- El zinc no se volatiliza.
- No hay O2 libre ni SO3 en los gases.
- No hay magnetita en la escoria.
- Los minerales con Pb, As, Sn y Sb (< 0,5 %) y la masa que la mineralogía no lista entran como
  ganga inerte (Al2O3), que sale en la escoria: entre los dos, 4,1 a 5,3 % de la carga.
- La delafosita (CuFeO2) se representa como ½ Cu2O + ½ Fe2O3, y la dolerofanita (Cu2O·SO4) como
  CuO + CuSO4. USGS no las tabula.
- El fundente es SiO2 puro.

## Datos termodinámicos (`procesos/thermo_piro.py`)

| Especie | ΔfH (kJ/mol) | Calor sensible |
|---|---|---|
| Cu2S (mata y escoria) | −83,9 | US Bureau of Mines RI 8305 (Ferrante et al. 1978), α, β, γ y líquido |
| FeS | −101,0 | NIST-JANAF: troilita y líquido |
| FeO | −272,0 | NIST-JANAF + fusión de 24,06 kJ/mol |
| SiO2 | −910,86 | NIST-JANAF + fusión de 10,17 kJ/mol |
| Cu2O | −170,6 | NIST-JANAF |
| ZnS, ZnO | −204,1; −350,46 | USGS B2131 (ecuación de Cp) |
| SO2 | −296,84 | NIST-JANAF |
| Minerales de la carga | USGS B2131 | entran a 25 °C: solo ΔfH |

Todas las entalpías de formación salen de un solo juego, USGS B2131. Así, el calor de reacción
no mezcla fuentes. En los tramos de JANAF, el parámetro H de Shomate se reemplaza por el ΔfH del
sólido de JANAF, para que el calor de fusión quede dentro del calor sensible.

## Validación

Tolerancias fijadas antes de correr ([tests/test_fusion.py](../tests/test_fusion.py)):

| Prueba | Tolerancia | Resultado |
|---|---|---|
| Calor sensible JANAF vs USGS, Cu2O 298→1.400 K | ±2 % | −0,12 % |
| Calor sensible JANAF vs USGS, FeO 298→1.573 K | ±2 % | **+7,3 %: falla** (ver hallazgos) |
| Saltos del Cu2S de RI 8305 (0,865; 0,280; 3,070 kcal/mol) | ±0,005 | sí |
| Matas Cu2S-FeS medidas a 1.473 K (González et al. 2001), mezcla ideal | ±3 % | −0,8 a −1,6 % en las 5 |
| Cierre por elemento y de calor | 1e-9 kmol; 1e-6 MJ/t | sí |
| Ley, SiO2, repartos de Cu y Zn cumplidos | 1e-9 | sí |
| Atlantic Copper: OC, enriquecimiento y fundente de 4 mezclas | ±10 %, ±5 y ±2 puntos | 7 de 12 dentro |
| Corte: falla si quedan fuera más de 6 de 12 | | **pasa (5 fuera), por poco** |

Matas medidas: la escoria y la mata salen del horno a 1.300 °C, así que su contenido calórico
pesa en el balance. El modelo queda 1-2 % bajo lo medido en todo el rango de composición:

| Cu2S (% masa) | 0 | 25 | 50 | 75 | 100 |
|---|---|---|---|---|---|
| Medido (J/g) | 1.253 | 1.134 | 1.008 | 879 | 756 |
| Modelo (J/g) | 1.243 | 1.119 | 994 | 869 | 744 |

### Contra la operación de Atlantic Copper (Huelva)

Datos abiertos: Bacedoni, Moreno-Ventas y Ríos (2020), *Metals* 10(9), 1229, CC BY. El artículo
publica:
- la mineralogía de cuatro mezclas (Tabla 9);
- la operación medida (Tabla 13): OC, enriquecimiento, fundente, ley de mata, SiO2 de la escoria
  y pérdida térmica;
- los resultados de su propio modelo, que usa HSC y FactSage (Tabla 14).

Aquí la ley y la SiO2 medidas son las metas, y se comparan el OC, el enriquecimiento y el
fundente.

| Mezcla | OC modelo | OC planta | O2 % modelo | O2 % planta | Fundente modelo | Fundente planta |
|---|---|---|---|---|---|---|
| 1 | 161,8 (−13 %) ✗ | 186 | 50,7 ✓ | 50,1 | 6,79 ✓ | 8,26 |
| 2 | 160,9 (−14 %) ✗ | 188 | 48,2 ✓ | 51,0 | 2,99 ✗ | 5,24 |
| 3 | 179,1 (−7 %) ✓ | 193 | 38,5 ✗ | 53,4 | 7,70 ✗ | 10,6 |
| 4 | 168,8 (−9 %) ✓ | 186 | 48,9 ✓ | 53,8 | 9,20 ✓ | 10,0 |

El modelo del artículo tampoco llega: su OC queda entre −13 y −18 % y su fundente entre −27 y
−46 %.

## Hallazgos

1. **La termodinámica coincide con la del artículo.** Con sus mismas entradas (ley 63,9 %, SiO2
   30 %), la mezcla 1 da OC 162,3 Nm³/t frente a sus 161,8. Es una diferencia de 0,3 % entre
   datos públicos (USGS + JANAF) y FactSage.
2. **El OC queda bajo en los dos modelos.** Ninguno tiene magnetita en la escoria, O2 libre en
   los gases, SO3 ni polvo. El oxígeno que la planta gasta en todo eso no aparece.
3. **El fundente queda bajo, como explica el artículo.** Parte del cuarzo sale arrastrado con los
   gases sin reaccionar, y el fundente real no es SiO2 puro.
4. **La pérdida térmica no es un dato independiente.** Los autores fijaron 33.900 MJ/h para que
   su modelo diera el enriquecimiento medido de la mezcla 1. Aquí se usa tal cual, sin
   reajustarla. Por eso, el acierto en el O2 % de la mezcla 1 no prueba mucho.
5. **El enriquecimiento de la mezcla 3 no es alcanzable.** Con la pérdida máxima que la planta
   reporta (37.000 MJ/h), el modelo llega a 39,5 %, lejos del 53,4 % medido.
6. **La mineralogía publicada no cuadra con el ensaye.** La de las mezclas 3 y 4 trae 1,05 y
   0,85 puntos más de azufre que su análisis químico (Tabla 8), y la 4 trae 1,7 puntos más de
   hierro:
   - Ese azufre extra es combustible, del orden de 90 MJ/t: casi la mitad de la pérdida del horno.
   - Con más calor, el modelo pide más N2 como refrigerante y enriquece de menos.
   - Con las mismas entradas que el artículo, el O2 % del modelo queda 1,3 puntos sobre el suyo
     en la mezcla 1, y 3,4, 9,3 y 9,0 puntos bajo él en las mezclas 2, 3 y 4.
   - La diferencia crece con el exceso de azufre de la mineralogía (−0,09; 0,60; 1,05 y 0,85
     puntos). Esto **sugiere**, sin probarlo, que los autores trabajaron con datos reconciliados
     con el ensaye.
7. **JANAF y USGS discrepan en el FeO.** JANAF da 7,3 % más calor sensible que el FeO
   «ficticio» de USGS: a 900 K, Cp de 58 frente a 54 J/(mol·K). Con el de USGS, el O2 % baja 1,2
   a 2,0 puntos y el OC no cambia.

## Mutaciones

23 de 26 mutaciones hacen fallar las pruebas. Las 3 que sobreviven:
- **El ΔfH del FeS +1 kJ/mol:** mueve el O2 % 0,03 a 0,08 puntos.
- **Los tramos sólidos β y γ del FeS:** no se usan, porque mata y escoria a 1.300 °C solo leen el
  tramo líquido.
- **El proxy de la delafosita:** un error grande (Fe2O3 ×2) mueve el O2 % 1,1 a 2,2 puntos, por
  debajo de la tolerancia de 5. La mineralogía trae 0,76 % de delafosita.

## Límites

- Sin magnetita, plomo, arsénico, antimonio ni estaño. Sin polvo, sin O2 ni SO3 en los gases.
- Todos los productos salen a la misma temperatura, y la carga entra seca a 25 °C.
- Los coeficientes de distribución son fijos: los de FactSage para una mata de 62 % y una escoria
  de 29 % de SiO2. Para leyes muy distintas habría que recalcularlos.
- Por debajo de 1.190 °C, la ficha «FeS líquido» devuelve el FeS sólido.
- La conversión (fase 4b), el horno de ánodos y la electrorrefinación quedan para las fases
  siguientes.
