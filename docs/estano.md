# Fundición de estaño en dos etapas (fase 4d)

`procesos.estano.smelt_tin` hace el balance de masa de una fundición de estaño como la de Funsur
(Pisco), que trabaja con dos hornos de lanza sumergida:
- **Etapa 1, fusión del concentrado.** El SnO2 y el Fe2O3 se reducen con carbono a estaño crudo,
  con el Fe pedido, y a una escoria rica en SnO y FeO.
- **Etapa 2, reducción de la escoria.** Da una aleación Sn-Fe (hardhead) y la escoria de desecho,
  con el Sn pedido.

El hardhead y los humos de SnO vuelven a la etapa 1. A régimen, el Sn solo sale con el crudo y
con la escoria de desecho. Es un módulo de cálculo, no un equipo del YAML.

`python ejemplos/estano_funsur.py` corre el caso Funsur 2025 (ilustrativo).

## Modelo

El reparto entre metal y escoria sigue la reacción SnO (escoria) + Fe (metal) = Sn (metal) + FeO
(escoria), con su coeficiente de distribución:

    D = (%Sn/%Fe)metal × (%Fe/%Sn)escoria

Kandalam et al. (2023, *Metals* 13, 1742) dan D de 150 a 400 en la fusión (crudo con menos de 2 %
de Fe) y de 20 a 50 en la reducción (hardhead de 10 a 60 % de Fe). Los valores por defecto son
200 (su ejemplo a 1.200 °C) y 35.

**Etapa 1.** Con el Fe del crudo fijado, D da la razón Sn/Fe de la escoria, y los balances de Sn
y Fe dan las masas.

**Etapa 2.** Con el Sn de la escoria de desecho fijado, D se cumple con una sola incógnita, el Fe
que queda en la escoria. Se resuelve por bisección.

**Carbono.** Sale del O que se retira (SnO2 → Sn o SnO; Fe2O3 → FeO o Fe). Cada átomo de C se
lleva 2 − r átomos de O, donde r = CO/(CO + CO2) es un parámetro: 0,5 por defecto, sin validar.

**Caliza.** Se agrega la necesaria para llegar a la razón CaO/SiO2 pedida. En la fusión es 0,3
(ACS Omega 2024, Tabla 1).

**Humos.** Una fracción del Sn de cada etapa se volatiliza como SnO y se recicla. En la segunda
etapa del piloto CSIRO fue de 10 a 25 %.

Sin balance de calor.

## Validación

Tolerancias fijadas antes de correr ([tests/test_estano.py](../tests/test_estano.py)):

| Prueba | Tolerancia | Resultado |
|---|---|---|
| Takeda et al. 1990, 1.573 K: mediana de D con metal < 2 % Fe (47 ensayos) | 150-400 | **166** ✓ (cuartiles 117 y 270) |
| Takeda et al. 1990: mediana de D con metal de 10-60 % Fe (11 ensayos) | 20-50 | **35** ✓ (cuartiles 18 y 53) |
| Funsur 2022-2025: recuperación con el Sn que entra y el refinado, frente a la reportada | ±1 punto | −0,72; −0,72; −0,62 y −0,60 ✓ |
| Cierre por elemento (Sn, Fe, O, C, Ca, Si, Al, Mg, Ti) | 1e-7 t | sí |
| Fe del crudo, Sn del desecho y D cumplidos en cada etapa | 1e-9 | sí |
| Carbono y caliza a mano; humos por etapa; sentido físico | 1e-9 | sí |

**Takeda et al. (1990)**, *Materials Transactions JIM* 31(9), 793 (J-STAGE). Equilibraron
escorias FeOx-CaO-SiO2 con aleaciones Sn-Fe en crisoles de magnesia. Su Tabla 6 tiene 81 ensayos
a 1.573 K, con el análisis de la escoria y del metal. Son mediciones independientes de los rangos
de la revisión.

**Funsur.** Memoria Integrada 2025 de Minsur, Tabla 11 (planta de Pisco):

| | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|
| Concentrado (t, % Sn) | 74.372 (37,11) | 69.994 (37,27) | 81.177 (39,53) | 87.527 (38,73) |
| Escoria de horno rotatorio (t, % Sn) | 1.350 (15,1) | 1.242 (15,5) | 931 (21,3) | 1.091 (19,8) |
| Estaño refinado (t) | 26.706 | 25.374 | 30.926 | 32.981 |
| Recuperación reportada (%) | 96,77 | 97,27 | 96,40 | 97,28 |
| Calculada con Sn que entra y refinado (%) | 96,05 | 96,55 | 95,78 | 96,68 |
| Sn en la escoria de desecho (%) | 0,54 | 0,59 | 0,56 | 0,55 |

## Hallazgos

1. **Los D de la literatura se sostienen frente a equilibrios medidos, pero con mucha
   dispersión.**
   - Las medianas de Takeda caen dentro de los rangos de la revisión.
   - De un ensayo a otro, D va de 69 a 476 en la fusión y de 8 a 163 en la reducción.
   - Las temperaturas no coinciden del todo: la revisión habla de 1.200 °C para la etapa 1 y de
     1.400 °C para la etapa 2; Takeda midió a 1.300 °C.
2. **D sube con la basicidad.** En los ensayos con metal bajo en Fe, D crece con CaO/SiO2
   (Spearman 0,46, p = 0,004). Es lo mismo que la correlación de producción K = 25,7·CaO/SiO2 −
   4,34 (*Materials* 2024) y que los coeficientes de actividad de Rankin (1986). Por eso D es un
   dato de la planta, no una constante.
3. **La recuperación de Funsur se calcula 0,6-0,7 puntos bajo la reportada, los cuatro años.**
   La diferencia es sistemática. La nota de la tabla dice que el refinado incluye el estaño de
   las aleaciones (Sn/Sb, Sn/Bi y el dross alto en Cu), así que la recuperación reportada cuenta
   algo más que el estaño refinado.
4. **La escoria de desecho explica una cuarta parte de la pérdida.**
   - En 2025 entraron 34.115 t de Sn y se refinaron 32.981 t: la diferencia es de 1.134 t.
   - Con la ganga supuesta, el modelo da 49.000-57.000 t de escoria de desecho al 0,55 %, es decir
     270-314 t de Sn. Eso es el 24-28 % de la pérdida.
   - El resto se va por fuera del horno: polvos que no se recuperan, refinación, aleaciones e
     inventario.
   - Para que toda la pérdida fuera escoria al 0,55 %, harían falta 206.000 t de escoria: 2,4 t
     por tonelada de concentrado, imposible.

## Ejemplo (ilustrativo): Funsur 2025

La ganga del concentrado de San Rafael no se publica. Se tomó con las proporciones del
concentrado analizado en *Materials* 2024 (Tabla 1), escaladas a la ley de Funsur: SiO2 18,6;
TiO2 7,5; Fe2O3 5,8; Al2O3 4,0; MgO 3,9 y otros 11,1 %.

| | Sin mineral de hierro | Con 10 % de Fe2O3 agregado |
|---|---|---|
| Estaño crudo (t) | 34.535 | 34.491 |
| Escoria de la etapa 1 (t, % Sn) | 49.788 (1,5) | 61.600 (4,2) |
| Hardhead (t, % Fe) | 450 (23) | 3.406 (45) |
| Escoria de desecho (t) | 49.138 | 57.065 |
| Sn perdido en la escoria (t) | 270 | 314 |
| Recuperación del modelo (%) | 99,21 | 99,08 |
| Carbono / caliza (t) | 4.923 / 8.730 | 5.358 / 8.730 |

La escoria de la etapa 1 sale pobre (1,5 % Sn) porque la ganga supuesta trae poco hierro: con
D = 200, la razón Fe/Sn de la escoria es 4. Las escorias reales de primera etapa tienen de 10 a
25 % de Sn y llevan más hierro. Según la prensa especializada (Discovery Alert, septiembre
de 2026), la alimentación del horno de Funsur incluye mineral de hierro; Minsur no lo publica.

## Balance de calor: gas natural por etapa

`procesos.estano_calor.tin_heat` toma el balance de masa y cierra el calor de cada etapa
quemando gas natural con el aire justo (CH4 + 2 O2 + 7,52 N2 → CO2 + 2 H2O + 7,52 N2).
- **Etapa 1:** entran a 25 °C las cargas, la caliza, el carbono, el hardhead y los humos; salen a
  T1 = 1.200 °C.
- **Etapa 2:** la escoria entra caliente y sale todo a T2 = 1.400 °C. Son las temperaturas de los
  D de Kandalam et al.
- **Pérdidas:** la pérdida de cada horno es un dato, 0 por defecto. Si el calor sobra, no se quema
  gas y se informa el sobrante.

**Datos:**
- **USGS B2131:** Sn (sólido y líquido, de su tabla), SnO2 (casiterita), TiO2 (rutilo), CaO y CO.
  El vapor de agua sobre 800 K también viene de USGS; empalma con el ajuste de JANAF con
  0,03 kJ/mol de diferencia.
- **JANAF:** Fe (tabla Fe-003, con las transiciones α-γ-δ).
- **CODATA:** SnO sólido, solo a 25 °C.
- **SnO líquido:** no está en esas fuentes. Se toma de Takeda et al. (1990, ec. 5),
  ΔG° = −274.500 + 93,3·T J, es decir h(SnO, l) = h(Sn, l) + ½ h(O2) − 274,5 kJ/mol. Está
  medido entre 1.366 y 1.573 K; a 1.673 K es una extrapolación.
- **Humo de SnO:** se trata como SnO líquido, sin el calor de vaporización.

| Prueba | Tolerancia | Resultado |
|---|---|---|
| USGS frente a JANAF a 1.500 K: CaO y CO | ±2 % | −0,5 y −0,1 % ✓ |
| El gas cierra cada etapa con su pérdida; PCI del CH4 a 25 °C | 1e-12; 0,5 kJ/mol | sí |
| Coherencia: CO2 mínimo del modelo bajo el CO2 directo de Pisco 2025 | debajo | 46.960 < 85.087 t ✓ |

Funsur 2025 con la ganga supuesta y sin pérdidas del horno:
- **Gas natural:** 9.144 t/año, de las que 8.463 van a la etapa 1. Son **2,34 GJ por t de
  concentrado**.
- **CO2:** 46.960 t/año. De ellas, 21.875 vienen del carbono reductor y la caliza, y 25.085 del
  gas.
- **Lo que falta para el CO2 reportado:** Pisco emitió 85.087 t directas, el 35,0 % de las
  243.106 t de Minsur. Si el resto (38.100 t) fuera gas quemado a 1.200 °C, serían a lo sumo
  317 TJ/año de pérdidas y otros usos.

Es una cota superior, no una medida. El CO2 de Pisco incluye la refinería, el diésel y todo
lo demás que se quema en la planta, y el carbono reductor real no es carbono puro.

## Mutaciones

Las 14 mutaciones del balance de masa y las 7 del de calor hacen fallar las pruebas. Las que
sobrevivieron a la primera vuelta mostraron pruebas que faltaban, y se agregaron:
- en el balance de masa: otra razón de CO y la fracción de humo de cada etapa;
- en el de calor: el N2 del aire caliente, el CO2 de la calcinación y la pérdida propia de cada
  etapa.

## Límites

- Sin actividades: D es un parámetro de la planta, sube con la basicidad y varía mucho de un
  ensayo a otro. El gas sale de un balance con pérdidas dadas, no medidas.
- Sin Pb, As, Sb, Bi, Cu ni S. La ganga distinta de SiO2, CaO, Al2O3, MgO y TiO2 entra como
  inerte («otros»).
- El humo se recicla como SnO; no se modela su oxidación a SnO2 en la cámara.
- La ganga de San Rafael es un supuesto; el ejemplo no es una validación de Funsur.
