# Validación con plantas reales publicadas

Aquí se pregunta si el simulador reproduce los números que publicaron plantas reales, y dónde falla. Solo se usaron fuentes públicas y gratuitas. Las tolerancias se fijaron **antes** de correr cada caso y ningún caso se ajustó para que pase.

- Pruebas, con los datos tal como salen de la fuente (tabla y página): `tests/test_plantas_reales.py`.
- Casos de molienda y clasificación (C1-C4): `simulador-conminucion/docs/VALIDACION_PLANTAS_REALES.md`.

**Qué prueba y qué no prueba esta validación:**
- Prueba el motor de balance, la estequiometría de las reacciones y la contabilidad por elemento contra cifras reales.
- No prueba que el simulador **prediga** recuperaciones: aquí la recuperación es un dato de entrada.

## Resumen

| Caso | Planta | Qué se prueba | Veredicto |
|---|---|---|---|
| P1 | Constancia, Hudbay (Perú) | Mineral × ley × recuperación contra el cobre en concentrado | **Pasa** en 5 de 5 periodos |
| P2 | Marimaca (Chile) | Factor 1,54, ácido de cada especie de la ganga y balance de sulfato | **Pasa**, con 1 hallazgo sobre la fuente |
| P3 | Puquios, Camino (Chile) | Cátodos de cada año del plan minero | **Pasa** en 14 de 16; 2 fallan por redondeo de la fuente |

Para comprobar que las pruebas pueden fallar, se metieron 3 errores a propósito y las pruebas los detectaron:

| Error introducido | Pruebas que fallaron |
|---|---|
| Peso atómico del azufre: 32,06 → 32,5 | 4 |
| Avance de todas las reacciones −2 % | 17 |
| Recuperaciones de los separadores +3 % | 5 |

## P1 · Constancia (Hudbay): cobre en concentrado

**Fuente:** Hudbay Minerals, formulario 6-K ante la SEC (accession 0001062993-20-001139, exhibit 99.3), resultados del 4.º trimestre de 2019, tabla de operaciones de Perú. Los años 2018 y 2019 coinciden con la Tabla 6-1 del NI 43-101 de Constancia (2021).

**Planta simulada:**
- Calcopirita más ganga, en la cantidad que da la ley reportada.
- Flotación con la recuperación reportada.
- El cobre del concentrado se lee del balance por elemento.

**Supuesto:** el portador de cobre es CuFeS2. No cambia el balance de cobre, solo la masa de mineral que lo lleva.

**Tolerancia:** ±2 %.

| Periodo | Simulador (t Cu) | Reportado (t Cu) | Desvío |
|---|---|---|---|
| 4T 2019 | 26.871 | 26.659 | +0,80 % |
| 3T 2019 | 31.181 | 31.091 | +0,29 % |
| 4T 2018 | 31.171 | 30.834 | +1,09 % |
| Año 2019 | 112.975 | 113.825 | −0,75 % |
| Año 2018 | 121.445 | 122.178 | −0,60 % |

Los desvíos caben en el redondeo de la ley, que se reporta con 2 decimales. Por ejemplo, 0,42 % ± 0,005 equivale a ±1,2 %.

## P2 · Marimaca: ácido de la lixiviación

**Fuente:** Marimaca Copper, NI 43-101 PEA de agosto de 2020, [PDF](https://minedocs.com/21/Marimaca-PEA-0842020.pdf):
- factor de 1,54 kg de ácido por kg de cobre disuelto: p. 13-115 (p. 128 del PDF);
- Tabla 13-18 de disolución de impurezas y ácido de la ganga: p. 13-124 (p. 137 del PDF);
- Tabla 13-19 de sulfato y ácido de reposición: p. 13-124.

**Tolerancias:**
- factor 1,54 en disolución y en electroobtención: ±0,01;
- ácido de cada especie: ±0,06 kg/t, porque la tabla redondea a 0,1;
- total: ±0,1 kg/t;
- sulfatos: ±0,05 kg/t.

| Qué | Simulador | Publicado |
|---|---|---|
| Ácido por kg de Cu disuelto (CuO + H2SO4) | 1,5433 | 1,54 |
| Ácido regenerado por kg de cátodo (electroobtención) | 1,5433 | 1,54 |
| Fe → Fe2O3 + 3 H2SO4 (kg/t) | 11,522 | 11,5 |
| Al → Al2O3 + 3 H2SO4 (kg/t) | 6,406 | 6,4 |
| Mg → MgO + H2SO4 (kg/t) | 1,896 | 1,9 |
| Otros (Zn) → ZnO + H2SO4 (kg/t) | 3,402 | 3,4 |
| Carbonato → CaCO3 + H2SO4 (kg/t) | 10,793 | 10,8 |
| **Total de la ganga (kg/t)** | **34,02** | **34,0** |
| Sulfato que precipita como CaSO4 (kg/t) | 10,57 | 10,567 |
| Sulfato del ácido de reposición, 34,222 kg/t de H2SO4 (kg/t) | 33,52 | 33,524 |

**Hallazgo sobre la fuente:** el reporte dice que el factor 1,54 «se repite para la mayoría de las reacciones de disolución del cobre». Eso vale para la tenorita y la crisocola, pero no para la brocantita. Para Cu4(SO4)(OH)6 + 3 H2SO4 → 4 CuSO4 + 6 H2O, el simulador da **1,157 kg/kg**, un 25 % menos. La brocantita está nombrada en una de las columnas que el mismo reporte usa para calcular el ácido de la ganga (C-37, «BROC/ATA»). El reporte calcula el ácido de la ganga como el ácido total menos 1,54 × el cobre disuelto. Si el cobre viene de brocantita, esa resta le carga al cobre 0,39 kg de ácido de más por kg disuelto, y **subestima el ácido de la ganga** en la misma cantidad.

**Coherencia de las columnas, sin veredicto:** el cobre disuelto que implica el ácido es (ácido total − ácido de la ganga) / 1,54. Se compara con la recuperación que muestra la Figura 13-19 a los ~60 días, leída a ojo con ±2 puntos:

| Columna | Implícita por el ácido | Leída del gráfico |
|---|---|---|
| C-29 | 84,5 % | ~84 % |
| C-33 | 75,5 % | ~70 % |
| C-37 | 78,8 % | ~80 % |
| C-42 | 58,3 % | ~62 % |

Detalle menor: la Tabla 13-15 se titula «Geomet III», pero el texto la presenta como Geomet II.

**Corrección al brief:** el brief citaba 40 kg/t de ácido de la ganga. La Tabla 13-18 da **34,0 kg/t**, y se usó esa cifra.

**Errores míos, corregidos:**
- La primera versión de la prueba olvidó multiplicar el avance por el coeficiente del ácido (3 para Fe2O3 y Al2O3).
- También calculó el factor 1,54 con el ácido como reactivo limitante.
- Ambas pruebas ahora exigen ácido en exceso.

## P3 · Puquios (Camino Minerals): cátodos del plan minero

**Fuente:** Puquios Project, NI 43-101 PFS de abril de 2025, [PDF](https://caminocorp.com/wp-content/uploads/2025/04/Camino_Puquios_Project_PFS.pdf):
- plan minero, Tabla 22-3 (p. 317 del PDF);
- año de diseño: 2,1 Mt/a, 0,542 % Cu, 78,98 % y 9.000 t/a de cátodos (p. 39 y p. 228 del PDF).

**Planta simulada:**
1. Óxido de cobre más ganga.
2. Lixiviación en pilas con la recuperación del plan.
3. Electroobtención, que regenera el ácido.
4. Cosecha de cátodos.

**Supuesto:** el portador es CuO.

**Tolerancia:** ±2 % por año y en la vida de la mina.

| Año | Simulador (t) | Plan (t) | Desvío |
|---|---|---|---|
| 1 | 7.680 | 7.714 | −0,44 % |
| 2 | 8.980 | 8.999 | −0,21 % |
| 3 | 9.046 | 9.001 | +0,50 % |
| 4 | 8.974 | 9.000 | −0,29 % |
| 5 | 8.381 | 8.319 | +0,75 % |
| 6 | 9.009 | 8.993 | +0,18 % |
| 7 | 8.996 | 9.000 | −0,05 % |
| 8 | 8.955 | 8.989 | −0,38 % |
| 9 | 5.220 | 5.295 | −1,42 % |
| 10 | 8.826 | 8.781 | +0,51 % |
| 11 | 4.802 | 4.804 | −0,03 % |
| **12** | **3.329** | **3.400** | **−2,08 % ✗** |
| 13 | 3.458 | 3.398 | +1,76 % |
| 14 | 4.970 | 4.901 | +1,41 % |
| **15** | **383** | **391** | **−2,05 % ✗** |
| Vida de la mina | 100.223 | 100.985 | −0,75 % |
| Año de diseño | 8.990 | 9.000 | −0,12 % |

**Los años 12 y 15 fallan el ±2 % declarado, y la causa está en la fuente, no en el simulador.** La tabla publica la ley con 2 decimales:

| Año | Ley publicada | Ley real (contenido / mineral) |
|---|---|---|
| 12 | 0,23 % | 0,2349 % |
| 15 | 0,18 % | 0,1839 % |

A leyes tan bajas, el redondeo pesa más del 2 %. Los dos años quedan marcados como fallo esperado y **estricto**: si algún día pasan, la suite avisa. No se ensanchó la tolerancia.

Además, una prueba comprueba la coherencia interna de la tabla: la ley publicada debe caer dentro del intervalo que permiten el mineral y el cobre contenido redondeados. Se cumple en los 16 renglones.

**Error mío, corregido:** la primera versión de esa prueba comparó contra un solo valor, sin considerar que el mineral (kt) y el contenido (t) también vienen redondeados. El año 3 parecía incoherente (1,01 % contra 1,02 %), pero con los intervalos la ley puede llegar a 1,0154 %, que redondea a 1,02 %.
