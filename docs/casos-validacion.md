# Casos de validación de la fase 1

Cada caso se compara con un resultado calculado **aparte** del simulador. Las pruebas están en `tests/test_validation_cases.py` y fallan si el simulador se desvía. Se comprobó que fallan de verdad: cambiar el peso atómico del azufre de 32,06 a 32,065 rompe el caso 2, y subir una recuperación un 0,1 % rompe el caso 3.

## Caso 1 — reciclo con solución exacta (`ejemplos/reciclo_simple.yaml`)

Un cajón mezcla la alimentación F con el reciclo R. Un separador manda la fracción *s* de cada especie al producto, y del fondo un divisor recircula la fracción *r* = 0,7. En estado estacionario, para cada especie:

  M = F / (1 − r · (1 − s))

| Especie | F (kg/h) | s | Mezcla M | Producto s·M | Purga 0,3·(1 − s)·M |
|---|---|---|---|---|---|
| SiO2 | 100 | 0,6 | 138,8889 | 83,3333 | 16,6667 |
| H2O | 50 | 0,2 | 113,6364 | 22,7273 | 27,2727 |

**Criterio:** coincidencia de 1e-9 relativa en las 4 corrientes. El simulador elige solo la corriente de corte (`Reciclo`) y Wegstein converge en 3 iteraciones.

## Caso 2 — lixiviación de óxidos de cobre (`ejemplos/lixiviacion_oxidos_cu.yaml`)

**Alimentación:**
- Mineral: 1.500 kg/h de CuO, 800 kg/h de CaCO3 y 97.700 kg/h de SiO2.
- Agua: 150.000 kg/h.
- Ácido sulfúrico puro: la cantidad la ajusta el controlador.

**Reacciones:**
- CuO + H2SO4 → CuSO4 + H2O, conversión 90 %.
- CaCO3 + H2SO4 → CaSO4 + H2O + CO2, conversión 100 %. Es la ganga que consume ácido.

**Meta del controlador:** 5 g de H2SO4 libre por kg de agua en la descarga.

**Cálculo a mano**, con la tabla de pesos atómicos propia de la prueba:

| Cantidad | Valor |
|---|---|
| Masas molares (kg/kmol) | CuO 79,545 · H2SO4 98,072 · CaCO3 100,086 |
| CuO que reacciona | 0,9 · 1.500 / 79,545 = 16,9715 kmol/h |
| CaCO3 que reacciona | 800 / 100,086 = 7,9931 kmol/h |
| Ácido consumido | por el cobre 1.664,43 + por la ganga 783,90 = 2.448,33 kg/h |
| Agua en la descarga | 150.000 + (16,9715 + 7,9931) · 18,015 = 150.449,74 kg/h |
| Ácido libre buscado | 5 / 1.000 · 150.449,74 = 752,25 kg/h |
| **Ácido a alimentar** | 2.448,33 + 752,25 = **3.200,58 kg/h** |
| Productos | CuSO4 2.708,69 · CaSO4 1.088,14 · CO2 351,77 kg/h |

**Resultado del simulador:** 3.200,5820 kg/h de ácido. Se cumple 1e-6 en el ácido y 1e-9 en los productos, y los elementos cierran con un error de 10⁻¹⁶.

**Criterio de muerte del brief:** el lazo debe converger de forma confiable. Se probó con 20 metas entre 0,5 y 40 g/kg y todas convergen (`test_criterio_de_muerte_…`). Una meta inalcanzable dentro de los límites da un error con los desvíos medidos, no un resultado falso.

## Caso 3 — concentradora rougher-cleaner con reciclo (`ejemplos/concentradora_cu.yaml`)

El relave cleaner vuelve al cajón del rougher. Con recuperaciones fijas por etapa, la recuperación global de cada especie es:

  R = Rr · Rc / (1 − Rr · (1 − Rc))

| Especie | Rougher Rr | Cleaner Rc | Recuperación global |
|---|---|---|---|
| CuFeS2 | 0,92 | 0,95 | 91,6143 % |
| SiO2 | 0,08 | 0,15 | 1,2876 % |
| H2O | 0,15 | 0,40 | 6,5934 % |

Además, las leyes de cobre sobre sólidos secos de la alimentación (f), del concentrado (c) y del relave (t) deben cumplir la **fórmula de dos productos** (Wills y Finch, *Wills' Mineral Processing Technology*, 8.ª ed., cap. 3):

- rendimiento de sólidos C/F = (f − t) / (c − t);
- recuperación de cobre = c · (f − t) / (f · (c − t)).

**Criterio:** ambas igualdades con 1e-9 relativa, más el cierre de los elementos.

## Fuentes

- Pesos atómicos: IUPAC, *Standard atomic weights of the elements 2021* (Pure Appl. Chem. 94, 2022), valores abreviados.
- Wegstein, J. H. (1958). *Accelerating convergence of iterative processes*. Commun. ACM 1(6).
- Wills, B. A. y Finch, J. A. (2016). *Wills' Mineral Processing Technology*, 8.ª ed. Butterworth-Heinemann.
- Brent, R. P. (1973). *Algorithms for Minimization without Derivatives*. Prentice-Hall.
