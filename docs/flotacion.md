# Flotación cinética

El equipo `flotacion` reemplaza la recuperación fija del separador por un modelo cinético de
primer orden por especie, en un banco de celdas de mezcla perfecta en serie. La herramienta
`fit_kinetics` (y `python -m procesos ajustar`) ajusta la cinética a una prueba batch o al perfil
de recuperación de un banco.

## Modelo

Distribución de constantes f(k): `primer_orden` (una sola k; García-Zúñiga 1935) o `rectangular`
(k uniforme entre 0 y kmax; Klimpel 1980, k media = kmax/2).

| | Batch (t min) | N celdas de mezcla perfecta (τ min cada una) |
|---|---|---|
| Primer orden | R∞·(1 − e^(−kt)) | R∞·(1 − (1 + kτ)^−N) |
| Rectangular | R∞·(1 − (1 − e^(−kmax·t))/(kmax·t)) | N = 1: R∞·(1 − ln(1 + kmax·τ)/(kmax·τ)); N > 1: R∞·(1 − (1 − (1 + kmax·τ)^(1−N))/(kmax·τ·(N − 1))) |

- **τ por celda.** Se da directo (`tiempo_residencia_min`) o sale del volumen de celda:
  τ = V·(1 − aire)/Q, con Q el caudal de pulpa (sólidos a `densidad_solidos`, 2,7 t/m³ por
  defecto, y agua a 1 t/m³) y 15 % de aire por defecto.
- **Factor de escalamiento.** Divide las k: k_planta = k_lab/factor (`factor_escalamiento`).
- **Especies sin cinética** (ganga, agua): se recuperan con la recuperación fija de
  `recuperaciones` o `por_defecto`, como en el separador.

```yaml
- tipo: flotacion
  nombre: Rougher A
  entradas: [Alimentacion rougher]
  salidas: [Concentrado rougher, Relave rougher]
  celdas: 9
  tiempo_residencia_min: 4.1     # o: volumen_celda_m3 y fraccion_aire
  modelo: primer_orden           # o: rectangular (k es kmax)
  cinetica:
    CuFeS2: {r_inf: 0.94, k: 0.35}
  recuperaciones: {SiO2: 0.05, H2O: 0.10}
```

Ajuste desde un CSV (tiempo o número de celda; recuperación en %):

```bash
python -m procesos ajustar prueba_batch.csv --modelo rectangular
python -m procesos ajustar banco.csv --tau 4.1        # perfil de un banco de celdas
```

## Validación

Datos abiertos: Vinnett, Pino-Muñoz, Yianatos, Díaz y Henríquez (2022), *Physicochem. Probl.
Miner. Process.* 58(5), 152420. Son dos bancos rougher industriales de Minera Los Pelambres:
- **Banco A:** 9 celdas Wemco de 130 m³, ~600 t/h, τ medido de 4,1 min por celda.
- **Banco B:** 6 celdas de 250 m³, ~700 t/h, τ de 6,4 min.

El artículo tabula la recuperación de Cu medida celda a celda (Tablas B1 y B2) y los parámetros
que ajustó (Tabla 3). Tolerancias fijadas antes de correr
([tests/test_flotacion.py](../tests/test_flotacion.py)):

| Prueba | Tolerancia | Resultado |
|---|---|---|
| V1: con sus parámetros, reproducir sus recuperaciones modeladas (mezcla perfecta) | ±1,0 punto | desvío máximo de 0,40 (A, primer orden), 0,08 (A, rectangular), 0,20 y 0,21 puntos (B) |
| V2: ajustar sus recuperaciones **medidas** y obtener sus parámetros | R∞ ±1 punto; k ±5 % | R∞ 93,96 frente a 94,0 % y k −1,3 % (A, primer orden); 99,04 frente a 99,1 % y k 0,0 % (A, rectangular); B dentro de +1,1 % |
| Muchas celdas en serie tienden al batch; el rectangular es el promedio del primer orden | 1e-4 y 1e-9 | sí |
| El ajuste recupera parámetros sintéticos; balance de masa | 1e-6 y exacto | sí |

El ajuste reproduce el de los autores con sus propios datos (RMSE de 0,7 a 1,3 puntos contra
lo medido). Las 11 mutaciones del código (fórmulas, k media, escalamiento, aire, densidad,
masa) hacen fallar las pruebas.

## Lo que NO se validó: de laboratorio a planta

El brief pedía predecir con la cinética de laboratorio un resultado continuo o piloto medido. No
se pudo:
- **El candidato,** *Minerals* 16(7):726 (2026), que compara laboratorio con piloto, es de acceso
  abierto pero MDPI bloquea la descarga automática.
- **La literatura abierta muestra que ese salto no es predecible sin calibrar.** En cuatro
  plantas chilenas de cobre (Vallejos 2023, *Physicochem. Probl. Miner. Process.* 59(5),
  177609), el factor de escalamiento entre la prueba batch y el banco rougher fue de 2,5 en una
  planta, pero de 0,8 y 15,7 en las otras dos. Con la misma muestra, cambiar la agitación del
  laboratorio de 1.300 a 1.000 rpm lo bajó a 0,4, y subir el aire de 12 a 18 L/min lo llevó a 6,2.

Por eso `factor_escalamiento` es un dato que se calibra con la planta, no una predicción.

## Ejemplo

`ejemplos/flotacion_pelambres.yaml`: el banco A con su cinética publicada recupera 94,0 % del Cu;
en planta se midió 94,7 % en la última celda. Los 35 % de sólidos y las recuperaciones de la ganga
(5 %) y del agua (10 %) son supuestos, no vienen del artículo.

## Límites

- Sin arrastre mecánico, sin recuperación de espuma separada y sin cinética por tamaño: la k es
  aparente e incluye todo eso.
- Mezcla perfecta en cada celda. El artículo muestra que, con los τ medidos por trazador, los
  parámetros cambian poco frente a la mezcla perfecta (Tabla 3).
- La ley del concentrado depende de cómo se recupera la ganga, que aquí es un dato fijo.
