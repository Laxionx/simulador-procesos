# Cadena de concentrado a cátodo

`procesos.cadena.concentrate_to_cathode` lleva una tonelada de concentrado por las cuatro etapas:
- fusión flash ([fusion.md](fusion.md));
- convertidor Peirce-Smith ([conversion.md](conversion.md));
- horno de ánodos;
- electrorrefinación ([er.md](er.md)).

Da el destino del Cu y del S, el ácido potencial y la energía de cada etapa.
`python ejemplos/cadena_atlantic.py` corre la mezcla 1 de Atlantic Copper.

## Cómo se conectan las etapas

| Paso | Qué pasa |
|---|---|
| Fusión → convertidor | La mata entra como Cu2S + FeS a la temperatura de los productos de la fusión. El ZnS de la mata (0,7 % de la mata) no lo modela el convertidor: se informa aparte y no sigue. |
| Convertidor | Usa los parámetros del ejemplo de Ilo de la fase 4b: escoria de Morales 2004, fundente calculado para su sílice, eficiencias de Flin Flon, y fin de etapa y escoria de cobre como en Rönnskär. |
| Horno de ánodos | Toma el blíster con su S, y su O sube y baja como en la fase 4b. |
| Nave de refinación | Disuelve el ánodo entero, porque a régimen la chatarra vuelve al horno. Usa la geometría de Mount Isa y el electrolito de la «Reference Tankhouse 3» sin Ni ni As. El O del ánodo entra como Cu2O y su S va al barro. |

Las escorias del convertidor y la de la fusión **no se recirculan**: su cobre se informa.

## Verificación

Tolerancias fijadas antes de correr ([tests/test_cadena.py](../tests/test_cadena.py)):

| Prueba | Tolerancia | Resultado |
|---|---|---|
| Cierre de Cu y S de punta a punta, 4 mezclas | 1e-9 relativo | 1e-15 ✓ |
| Ácido potencial frente a Ilo 2023-2025 (0,94-1,00 t/t, ±15 %) | 0,80-1,15 t/t | 0,875; 0,887; 0,902 y 0,903 ✓ |
| Lo que sale de cada etapa entra igual en la siguiente | 1e-12 | sí |
| Ácido potencial calculado a mano | 1e-4 | sí |

Datos de Ilo: Form 10-K 2025 de Southern Copper, tabla de la fundición. Es solo coherencia, porque
los concentrados son distintos: Atlantic Copper frente a Toquepala y Cuajone.

| | 2025 | 2024 | 2023 |
|---|---|---|---|
| Concentrado fundido (kt) | 1.040,7 | 1.230,9 | 1.292,9 |
| Recuperación de Cu (%) | 97,4 | 97,1 | 97,1 |
| Ánodos (kt, 99,78 % Cu) | 305,2 | 359,4 | 362,9 |
| Ácido sulfúrico (kt) | 976,5 | 1.185,0 | 1.286,8 |
| Ácido por t de concentrado | 0,94 | 0,96 | 1,00 |

De la recuperación y los ánodos se deduce que el concentrado de Ilo tiene 29 a 30 % de Cu, más
que la mezcla de Atlantic (25,6 %).

## Resultado: mezcla 1 de Atlantic Copper, por tonelada de concentrado

| Destino del Cu | kg | % |
|---|---|---|
| Cátodos | 241,1 | 95,82 |
| Escoria de fusión | 5,2 | 2,06 |
| Escoria del soplado a escoria | 2,3 | 0,92 |
| Escoria del soplado a cobre | 0,7 | 0,28 |
| Barro anódico | 1,2 | 0,46 |
| Electrolito (a las liberadoras) | 1,2 | 0,46 |

- **El 95,8 % llega a los cátodos sin recircular nada.** En la planta, las escorias del
  convertidor vuelven a la limpieza de escorias, y el cobre del barro y del electrolito se
  recupera. Con eso la cifra pasaría de 97 %, cerca de los 97,1-97,4 % de Ilo.
- **Azufre:** 286 de los 289 kg de S salen como SO2: 198 en la fusión, 88 en el convertidor y
  0,05 en el horno de ánodos. Equivalen a 0,875 t de ácido potencial.
- **Energía:**
  - 162 Nm³ de O2 en la fusión;
  - 481 Nm³ de aire en el convertidor;
  - 0,4 a 1,4 kg de gas natural en el horno de ánodos;
  - 46 kWh en la refinación: 192 kWh por t de cátodo, con 0,222 V de celda.

## Límites

- Sin recirculaciones entre etapas: escorias, chatarra y polvos.
- El Zn de la mata no sigue. No se modelan Pb, As, Sb, Bi ni Ni.
- Hereda los límites de cada etapa. Cada una tiene su propia validación, y la cadena no agrega
  otra: solo comprueba que las piezas cierren juntas y que el ácido sea coherente.
