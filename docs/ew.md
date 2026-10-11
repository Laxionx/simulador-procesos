# Electroobtención de cobre

El equipo `electroobtencion` deposita cobre del electrolito rico y calcula el voltaje de celda,
la energía y el calor de la nave. Con él, el circuito LX-SX-EW queda cerrado: el electrolito
agotado vuelve al despojo (ver `ejemplos/sx_ew_circuito.yaml`).

## Modelo

**Masa (ley de Faraday).** Reacción global: CuSO4 + H2O → Cu + H2SO4 + ½ O2. Se deposita
eficiencia × I / (2F). El resto de la corriente se pierde en cortocircuitos y en el ciclo
Fe³⁺/Fe²⁺, sin cambio químico neto: la eficiencia de corriente es un dato, no se predice. La
corriente total es la densidad de corriente por el área catódica (las dos caras de todos los
cátodos de la nave). Si la corriente pide más cobre del que trae el electrolito, deposita todo
y avisa.

**Voltaje de celda.** Se evalúa con el electrolito que sale, porque la celda es de mezcla
completa:

| Componente | Expresión | Fuente |
|---|---|---|
| Potencial reversible | 1,229 − 0,337 = 0,892 V | Beukes y Badenhorst 2009, ec. 72 |
| Sobrepotencial anódico (O₂ sobre plomo) | 0,5 + 0,12·log₁₀(j en A/dm²) | ídem, ec. 74 |
| Sobrepotencial catódico | RT/(αnF)·[ln(j/i₀) + ln(iL/(iL − j))], α = 0,5, i₀ = 0,2 A/m² | ídem, ec. 63-64 |
| Caída en el electrolito | j·L/κ, con L = 45 mm | ídem, Tabla III |
| Conductividad κ | correlación de electrolitos de EW, solo términos de Cu, ácido y T | Kalliomäki et al. 2021, Tabla 4 |
| Contactos y barras | 0,3 V | Schlesinger et al. 2011, citado en JOM 76 (2024) |

Sin densidad límite iL (`densidad_limite`), el sobrepotencial catódico es solo el de activación.
Si se conoce el voltaje de la nave, `voltaje_celda` lo fija y se saltan los componentes.

**Energía.** La potencia eléctrica es V·I y la energía específica, z·F·V/(eficiencia·M). Con
`balance_de_calor: true`, el equipo sale a la temperatura de entrada y el balance muestra el calor
que la nave debe perder (por evaporación y convección): entra + calor + electricidad = sale. Con
`electricidad_por_kwh` en `costos:`, la electricidad entra al costo operativo.

## En el YAML

```yaml
- tipo: electroobtencion
  nombre: Electroobtencion
  entradas: [Electrolito rico]
  salidas: [Electrolito agotado, Catodos, Oxigeno]
  densidad_corriente: 300       # A/m²
  area_catodica: 5640           # m²
  eficiencia_corriente: 0.92    # por defecto 0,92
  # opcionales: voltaje_celda, distancia_anodo_catodo (0,045 m), contactos_v (0,3),
  # densidad_limite (A/m²), densidad (1,2 kg/L, para pasar a g/L)
```

El catálogo necesita `Cu` (fase s) y `O2` (fase g). La densidad de corriente se puede ajustar con
un lazo de control (`parametro: densidad_corriente`).

## Validación

Tolerancias fijadas antes de correr ([tests/test_ew.py](../tests/test_ew.py)).

| Prueba | Tolerancia | Resultado |
|---|---|---|
| Cátodo = Faraday; cierre por elemento y de energía | 1e-9 | exacto |
| Ejemplo resuelto de Beukes y Badenhorst a 200 A/m² | ±0,01 V | anódico 0,536 frente a 0,543 V; catódico 0,233 frente a 0,225 V |
| Celda típica: 40 g/L Cu, 170 g/L ácido, 50 °C, 300 A/m² | 1,9-2,3 V y 1.800-2.200 kWh/t | **2,18 V y 1.998 kWh/t** |
| Gunnison (NI 43-101, 2023): producción declarada / Faraday al 100 % | 0,85-0,95 | 0,858 (etapa 1) y 0,895 (etapas 2 y 3) |
| Conductividad de M3 (Fuentes 2022) a 54,4 y 60 °C, dentro del rango | ±5 % | **+11,8 % y +9,1 %: falla** |
| Conductividad extrapolada: M3 a 48,9 y 71,1 °C; M4 a 48,9-71,1 °C | ±10 % | M3: +15,4 % (falla) y +4,0 %; M4: −4,5 a +6,0 % |
| Circuito SX-EW cerrado: recuperación contra Isocalc (92,83 %) | ±5 puntos | 89,8 % |

La celda típica y Gunnison son pruebas de **coherencia con la industria**, no comparaciones con
una planta medida: no se encontró una nave con voltaje medido y todas sus condiciones publicadas
en abierto. Gunnison no declara su eficiencia de corriente ni su disponibilidad, así que solo se
comprueba que el factor implícito quede en el rango de la industria. Las 13 mutaciones del código
(Faraday, eficiencia, Tafel, conductividad, potencia, calor, estequiometría) hacen fallar las
pruebas.

## Circuito SX-EW cerrado

`ejemplos/sx_ew_circuito.yaml`: la SX de `sx_2e1s.yaml`, un calentador a 50 °C, la nave, una purga
de 1 % del electrolito agotado y una reposición de agua y ácido. El lazo de control ajusta la
densidad de corriente para que el electrolito pobre quede en 33,67 g/L de Cu, como en Isocalc:

| Resultado | Valor |
|---|---|
| Densidad de corriente (5.640 m² de cátodos) | 299 A/m², 1.687 kA |
| Cátodos | 1.839 kg/h; el Cu purgado son 52,7 kg/h |
| Voltaje de celda y energía | 2,148 V y 1.969 kWh/t |
| Orgánico despojado | 3,04 g/L (Isocalc: 3,12) |
| Electricidad de la nave a 0,08 USD/kWh | 3.622 kW · 158 USD/t de cátodo |

Sin purga ni reposición el circuito no tiene un estado estacionario único: el ácido y el agua que
circulan quedarían sin determinar. Con 1 % de purga el lazo del electrolito converge lento (514
iteraciones, ~16 s por resolución; con el lazo de control, ~3 min).

## Hallazgos y límites

- **La correlación de Kalliomäki sobrestima la conductividad de M3** (50 g/L Cu, 171 g/L ácido)
  en 9-12 %, y su efecto de la temperatura es la mitad del medido (0,6 frente a 1,2 %/°C). No se
  ajusta a estos datos: es la correlación publicada. En la celda, un 12 % más de conductividad baja
  la caída óhmica en ~0,03 V, alrededor de 1 % del voltaje.
- El electrolito de las naves suele salir con 34-38 g/L de Cu, bajo el rango de la correlación
  (40-70 g/L): el simulador avisa la extrapolación. Con M4 (34,8 g/L) el error fue de −4,5 a +6 %.
- No se modelan: el ciclo del hierro (la eficiencia es un dato), las burbujas de O₂ en la caída
  óhmica, las impurezas en la conductividad, la calidad del cátodo, la neblina ácida ni la
  dependencia del potencial reversible y del Tafel anódico con la temperatura.
- La caída en contactos y barras varía entre fuentes: 0,2 V en el libro abierto *Aqueous Pathways*
  (BCcampus) y 0,3 V en Schlesinger et al. Por eso es un parámetro (`contactos_v`).

## Fuentes (abiertas)

- Beukes, N.T. y Badenhorst, J. (2009). Copper electrowinning: theoretical and practical design.
  *J. SAIMM* 109(6), 343-356.
- Kalliomäki, T. et al. (2021). Industrial validation of conductivity and viscosity models for
  copper electrolysis processes. *Minerals Engineering* 171, 107069 (CC BY).
- Fuentes, A. (2022). Modelamiento termoquímico y de la especiación iónica del sistema
  CuSO4-H2SO4-H2O en el rango de temperatura 0-100 °C. Tesis de magíster, USM, Tabla 4.24.
- Excelsior Mining (2023). Gunnison Copper Project, Form 43-101F1 Technical Report, sección 17.
- Hannula, P.-M. et al. (2018). *Journal of Cleaner Production* (rangos industriales).
