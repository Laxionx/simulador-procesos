# Flotación cinética

El equipo `flotacion` reemplaza la recuperación fija del separador por un modelo cinético de
primer orden por especie, en un banco de celdas de mezcla perfecta en serie. La herramienta
`fit_kinetics` (y `python -m procesos ajustar`) ajusta la cinética a una prueba batch o al perfil
de recuperación de un banco.

## Modelo

Distribución de constantes f(k): `primer_orden` (una sola k; García-Zúñiga 1935), `kelsall` (dos
componentes, ver abajo) o `rectangular`
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

## De laboratorio a piloto: Minerals 16(7):726 (2026)

Para el salto de escala hay un modelo más: `kelsall`, de dos componentes (Kelsall 1961). Cada
especie lleva su cinética como (φ lenta, k rápida, k lenta):

    batch:      (1 - φ)(1 - e^(-kf t)) + φ (1 - e^(-ks t))
    N celdas:   (1 - φ)(1 - (1 + kf τ)^-N) + φ (1 - (1 + ks τ)^-N)

En YAML se escribe `cinetica: {CuFeS2: {phi: 0.269, kf: 0.892, ks: 0.027}}`.

**El caso.** Una mena polimetálica de sulfuros (Universidad Técnica de Košice, CC BY):
- cinética de laboratorio en celdas Denver (Tablas 4-6);
- un circuito piloto de 50 kg/h (Figura 5): rougher y scavenger de 2 celdas, cleaner de 17 L, y
  el concentrado scavenger y las colas cleaner vuelven al rougher;
- la simulación de los autores en HSC SIM (Tabla 8);
- lo medido en el piloto (Tablas 9-11).

`procesos/flotacion_datos.py` arma el circuito y `python ejemplos/flotacion_piloto.py` lo corre.

**Supuestos declarados antes de correr:**
- **Alimentación:** la de la Tabla 1 (0,85 % Cu; 0,14 % Zn; 2,36 % S), pasada a minerales con
  la regla del artículo: Cu → calcopirita, Zn → esfalerita, el S que sobra → pirita, y el resto
  cuarzo.
- **Rougher y scavenger:** 14 min por celda, 28 min por etapa. Cuadra con 50 L para unos 111 L/h
  de pulpa.
- **Cleaner:** el τ que dan sus 17 L con el caudal de sólidos a 200 g/L, la densidad del cleaner
  de laboratorio. El artículo no publica el τ del cleaner. Resulta en 33,6 min.

| Prueba | Tolerancia | Resultado |
|---|---|---|
| Reproducir la simulación HSC: concentrado (Ccp, Sp, Py, Qtz) | ±2 puntos | 27,9 / 2,0 / 31,6 / 38,6 frente a 21,8 / 1,8 / 63,5 / 13,0: **solo Sp ✓** |
| Reproducir la simulación HSC: relave | ±2 puntos | 4 de 4 ✓ |
| Piloto: Cu del concentrado (9,27 %) | ±15 % relativo | 9,65 % (+4 %) ✓ |
| Piloto: concentrado (Ccp, Sp, Py, Qtz: 31,3 / 2,65 / 58,0 / 8,2) | ±5 puntos | Ccp y Sp ✓; **Py 31,6 y Qtz 38,6 ✗** |
| Piloto: relave (1,2 / 0 / 1,45 / 97,3) | ±0,5 puntos | Sp ✓; **Ccp 0,31, Py 0,24 y Qtz 99,4 ✗** |
| Corte del piloto: falla si quedan fuera más de 4 de 9 | | **falla (5 fuera)** |

El rendimiento del concentrado da 7,79 %, frente a 7,92 % en la simulación de los autores.

**Hallazgos:**
1. **La cinética de laboratorio predice el cobre, pero no la ganga.** La ley de Cu (+4 %) y la
   calcopirita del concentrado caen dentro de tolerancia. La pirita y el cuarzo no: el modelo
   arrastra cuarzo al concentrado, 38,6 % frente a los 8,2 % del piloto.
2. **La simulación de los autores no se puede reproducir con lo publicado.** Faltan el τ del
   cleaner y saber con qué alimentación simularon.
   - Diagnóstico, después de correr (no cuenta como validación): con la alimentación de
     laboratorio (Tabla 3: 0,792 % Cu y **3,93 % S**, casi el doble de S que la Tabla 1), el modelo
     da 20,1 / 1,70 / 52,2 / 26,0 frente a sus 21,8 / 1,75 / 63,5 / 13,0.
   - Con un cleaner de 12 min se acerca más: la pirita sube a 57,6.
   - Todo indica que simularon con la alimentación de laboratorio y con un cleaner más corto.
3. **El artículo tiene inconsistencias internas.**
   - La Tabla 8 da 21,78 % de calcopirita en el concentrado simulado, que son 7,5 % de Cu, pero
     el texto dice 9,02 %.
   - El piloto no cierra entre intervalos: con 12,0 % de rendimiento a 10,68 % Cu y relave al
     0,14 %, la alimentación de 120-180 min tendría 1,40 % de Cu, contra 0,85 % de la mena. El
     circuito no estaba en régimen.
4. **Sigue valiendo lo que dice Vallejos (2023):** el salto de laboratorio a planta no se predice
   sin calibrar. El factor de escalamiento fue de 2,5 en una planta chilena y de 0,8 y 15,7 en
   otras dos. `factor_escalamiento` es un dato de la planta.

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
