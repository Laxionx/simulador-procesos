# Conversión Peirce-Smith y horno de ánodos (fase 4b)

Dos módulos de cálculo, no equipos del YAML:

- `procesos.conversion`: balance de masa y de calor del convertidor por etapa de soplado.
  - `slag_blow`: soplado a escoria. Si se le pide una sílice de escoria, calcula también el
    fundente.
  - `copper_blow`: soplado a cobre.
  - `carry_over`: pasa el metal blanco, o la escoria que queda tras escoriar, a la etapa
    siguiente.
  - `Stage.cold_copper_capacity_t`: carga fría que alcanza a fundir el calor que sobra.
- `procesos.anodos.refine`: oxidación y reducción del blíster. **No validado contra planta.**

```python
from procesos.conversion import carry_over, copper_blow, matte, slag_blow

sb = slag_blow(
    [matte("mata", 100.0, 62.0)],
    end_fe_pct=0.4,
    slag_cu_pct=2.85,
    magnetite_fe=0.256,
    slag_sio2_pct=25.5,
    efficiency=0.62,
)
cb = copper_blow(
    [carry_over(sb, "metal", 1.0, 1200.0, "metal blanco")],
    blister_s_pct=0.023,
    slag_cu_pct=28.3,
    efficiency=0.77,
)
sb.air_nm3, cb.air_nm3, cb.mass_t("blister")  # 66.085 Nm³ · 68.136 Nm³ · 61,1 t
```

`python ejemplos/conversion_ilo.py` corre ese caso, mata de Ilo hasta ánodo. Es **ilustrativo**:
Ilo no publica sus flujos por carga.

## Modelo

Cada etapa es un sistema lineal en kmol, con balances de Cu, Fe, S y O. La sílice y la ganga
pasan a la escoria sin reaccionar. Las metas son valores que la planta mide:

| Etapa | Incógnitas | Metas |
|---|---|---|
| Soplado a escoria | metal blanco (Cu2S, FeS, Cu), escoria (FeO, Fe3O4, Cu2S), SO2, O2 (+ fundente) | Fe del metal blanco al final; Cu de la escoria (Cu2S atrapado); fracción del Fe de la escoria como magnetita (+ SiO2 de la escoria) |
| Soplado a cobre | blíster (Cu, Cu2S disuelto), escoria (Fe3O4, Cu2O), SO2, O2 | S del blíster; Cu de la escoria |

Las reglas del modelo:
- El cobre metálico que entra (carga fría) no se oxida en el soplado a escoria.
- En el soplado a cobre, todo el Fe pasa a la escoria como magnetita y el Cu de esa escoria es
  Cu2O.
- El aire sale del O2 que reacciona y de la eficiencia de oxígeno (O2 que reacciona / O2
  soplado): aire = (O2 / eficiencia − O2 puro) / 0,21.
- El calor compara lo que entra (cada carga a su temperatura, aire a 25 °C) con lo que sale a la
  temperatura del baño. El O2 que no reacciona y el N2 salen calientes. La diferencia es la
  pérdida del convertidor, o lo que queda para fundir carga fría.

Datos nuevos: Cu líquido (tabla NIST-JANAF Cu-001) y magnetita (Fe-032), interpoladas sobre la
columna H-H298, con el ΔfH de USGS B2131.

## Validación

Tolerancias fijadas antes de correr ([tests/test_conversion.py](../tests/test_conversion.py)):

| Prueba | Tolerancia | Resultado |
|---|---|---|
| Cu líquido a 1.450 K, JANAF vs USGS | ±2 % | +0,05 % |
| Magnetita a 1.000 y 1.500 K, JANAF vs USGS | ±2 % | −0,8 y −0,4 % |
| Pendiente de H-H298 = columna Cp de JANAF (guarda de copia) | ±0,02 J/(mol·K) | sí |
| Cierre por elemento; metas cumplidas; casos a mano | 1e-9 | sí |
| Rönnskär, aire de los soplados a escoria (148.500 Nm³) | ±10 % | **205.944: +38,7 % ✗** |
| Rönnskär, aire del soplado a cobre (208.200 Nm³) | ±10 % | 195.731: −6,0 % ✓ |
| Rönnskär, escoria de los soplados a escoria (181 t) | ±15 % | **149,6 t: −17,3 % ✗** |
| Rönnskär, blíster (322 t) | ±10 % | **368,3 t: +14,4 % ✗** |
| Flin Flon 586, 588 y 595: escoria por balance de Fe | ±20 % | +9,8; −12,8 y −3,2 % ✓ |
| Corte: falla si quedan fuera más de 3 de 7 | | **pasa (3 fuera), por poco** |

Las fuentes de planta:
- **Rönnskär.** Carga 860 de Boliden Rönnskär, de la tesis de Lennartsson (2013, Luleå). Trae el
  aire por soplado, las toneladas de mata con su Cu, el fundente, la carga fría y lo que sale.
  No da el Fe ni el S de la mata. El fin del primer soplado a escoria no se publica, así que los
  dos soplados a escoria van juntos (declarado antes de correr).
- **Flin Flon.** Cargas 586, 588 y 595 de Hudson Bay, de la tesis de Kyllo (1995, UBC). Trae los
  análisis completos de mata y escoria, pero no el aire soplado: solo las eficiencias que se
  calculan con él.

### El modelo de la tesis da lo mismo

Con la misma carga, el modelo de Lennartsson (FactSage + SimuSage) da:
- escoria: 148 t, y aquí 149,6;
- blíster: 358 t, y aquí 368;
- escoria del soplado a cobre: 13 t, y aquí 13,0.

En la planta fueron 181, 322 y 7 t. Los dos modelos fallan contra la planta en lo mismo, por la
misma razón: los datos publicados no cierran.

## Hallazgos

1. **La carga 860 publicada no cierra en cobre.** Entran 380,6 t de Cu, si la carga fría es
   cobre, y salen 331,5 t en blíster y escorias: faltan 49 t (−12,9 %). Por eso los dos modelos
   dan más blíster que la planta.
2. **La mata supuesta trae demasiado hierro.** Sin el análisis de Fe y S, la mata se tomó como
   Cu2S + FeS:
   - El modelo manda 72,9 t de Fe a la escoria. La escoria medida tiene 56,5 t (181 t × 31,2 %).
   - Ese Fe extra es FeS que hay que oxidar, y de ahí el +39 % de aire.
   - La mata real de Rönnskär trae Pb, Zn y otros: la escoria medida tiene 6,5 % de Pb y
     6,6 % de Zn.
   - Con 3 % de Fe3O4 en la mata, el error baja a +22 %.
   - La magnetita de la escoria mueve poco el resultado: de 0 a 40 % del Fe, el aire va de
     +34 a +41 %.
3. **El soplado a cobre publicado tampoco cierra en calor.** Con el aire medido, el baño a
   ~1.450 K y la carga fría como cobre a 25 °C, el calor sobrante alcanza para fundir 41 de las
   115 t de carga fría, y eso sin ninguna pérdida. Con el aire del balance alcanza para 70 t.
   Puede ser que la carga fría no sea cobre puro, que no entre toda fría o que el pirómetro de
   la campana lea bajo. Los datos no permiten saberlo.
4. **Flin Flon sí cierra.** Sus análisis completos dan la escoria a −13 a +10 %, aun con la
   escoria contada por ollas. La diferencia con Rönnskär está en los datos de entrada, no en el
   modelo.

## Lo que no entró

- **MDPI *Thermo* 5(4), 58 (2025):** su balance del convertidor (Tabla 3) no es comparable.
  449 kg de mata de 63 % dan 155 kg de blíster y 238 kg «perdidos por manejo», así que no cierra
  en cobre.
- **El soplado a escoria por separado:** necesita el fin del primer soplado, que no se publica.

## Horno de ánodos (`anodos.py`)

No hay un balance industrial medido que sea abierto: es estequiometría con guardas.
- **Oxidación:** el S pasa a SO2 y el O sube a `o_oxidized_pct` (0,7 % por defecto; la patente
  EP2111472 da de 0,5 a 1,0 %).
- **Reducción:** el O baja a `anode_o_pct` (0,12 % por defecto, el máximo citado en *Rudy i
  Metale Nieżelazne* 58(12), 2013).
- **Gas natural:** se dan dos cotas.
  - Mínima, si el CH4 se quema entero: CH4 + 4 O → CO2 + 2 H2O.
  - Máxima, si solo llega a CO + 2 H2: CH4 + O → CO + 2 H2.

  Para un blíster con 0,023 % de S salen 1,5 a 5,9 kg de CH4 por t de ánodo y 24 Nm³ de aire.
- **El ánodo** lleva solo Cu, O y S, sin impurezas menores (Pb, Ni, As, etc.).

## Mutaciones

27 de 28 mutaciones hacen fallar las pruebas. La que sobrevive es equivalente: quitar h(Cu,
25 °C) del calor de la carga fría no cambia nada, porque vale cero.

## Límites

- Sin Pb, Zn, As, Sb, Bi ni Ni. La ganga y la escoria reciclada sin Cu ni Fe se tratan como
  Al2O3 inerte.
- El balance es al final de cada etapa, sin dinámica. Las metas (fin de etapa, Cu en escoria,
  magnetita) se miden; no salen de un equilibrio.
- La eficiencia de oxígeno es un dato de la planta y varía mucho: en Flin Flon fue de 55-68 %
  en los soplados a escoria y de 72-82 % en el de cobre (Kyllo, Tabla IV-XII).
- Por debajo de 1.358 K, la ficha «Cu líquido» devuelve cobre sólido.
- Electrorrefinación (4c) y estaño (4d) quedan para las fases siguientes.
