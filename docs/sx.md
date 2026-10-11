# Extracción por solventes (SX) de cobre

El equipo calcula cuánto cobre pasa del PLS al orgánico, y del orgánico al electrolito, con un equilibrio químico publicado. El separador con recuperación fija ya no hace falta.

```yaml
- tipo: extraccion_solventes      # o: despojo (es el mismo equipo)
  nombre: Extracción
  entradas: [PLS, Organico descargado]      # (acuosa, orgánica)
  salidas: [Refino, Organico cargado]       # (acuosa, orgánica)
  etapas: 2
  eficiencia: [0.92, 0.95]   # Murphree, por etapa; E1 es la que recibe el PLS
  ph_alimentacion: 1.46      # opcional: pH medido del PLS (ver abajo)
  densidad_acuosa: 1.0       # kg/L
  densidad_organica: 0.81
  kex: 5.05                  # por defecto, el del LIX 984N
```

Ejemplo completo, con el orgánico en circuito cerrado entre la extracción y el despojo: [`ejemplos/sx_2e1s.yaml`](../ejemplos/sx_2e1s.yaml).

## Modelo

**Equilibrio** (Devi y Nayak 2014, *J. SAIMM* 114, 937):

    Cu²⁺ + 2 RH(org) ⇌ CuR₂(org) + 2 H⁺        Kex = D·[H⁺]² / [RH]²

- D = [CuR₂]/[Cu²⁺].
- [RH] es la oxima libre, en mol/L: la total menos 2·[CuR₂].

**Etapas en contracorriente.** La acuosa entra por la etapa 1 y sale por la N; la orgánica, al revés. En cada etapa:

    A·(x[i-1] − x[i]) = O·(y[i] − y[i+1])            balance de cobre
    y[i] = y[i+1] + E[i]·(y*(x[i]) − y[i+1])        eficiencia de Murphree

y* es el cobre orgánico en equilibrio con la acuosa que sale de la etapa.

**H⁺.** Cada Cu extraído libera 2 H⁺, que se reparten con el sulfato según H⁺ + SO₄²⁻ ⇌ HSO₄⁻:
- **ideal** (pKa₂ = 1,99), por defecto;
- **calibrada con el pH medido de la alimentación**, si se da `ph_alimentacion`. Con 30 g/L de sulfato, la asociación ideal da pH 2,48 a un PLS cuyo pH medido es 1,46: la diferencia son las actividades. El pH medido es un dato de entrada, no un resultado.

**En la planta**, el equipo aplica `CuSO4 + 2 RH -> CuR2 + H2SO4` con el avance que da el equilibrio. Por eso cierra por elemento.
- El orgánico se describe con especies de fase `org` y fórmula real: RH = 5-nonilsalicilaldoxima (C₁₆H₂₅NO₂), CuR₂ y un diluyente (C₁₂H₂₆).
- Un orgánico que circula sin alimentación propia necesita `cortes:` y `estimaciones:`. La estimación fija cuánto orgánico circula, y la planta converge en su carga de cobre.

## De dónde sale Kex = 5,05

Devi y Nayak informan Kex = 2,90, pero no declaran en qué unidad está la oxima de su 20 %v/v. Se comprobó que 2,90 es la constante y no su logaritmo: ΔG = −2,69 kJ/mol a 303 K da K = 2,91.

En este simulador, la oxima total sale de la **carga máxima** del reactivo, en g/L de Cu por %v/v: [RH] = 2·carga·%v/v / 63,546.
- Para el LIX 984N de Devi se usó 0,56. Es la cota inferior que exige su propio punto de 2,8 g/L extraídos con 5 %v/v, y por eso ese punto quedó fuera de la validación.
- Con esa convención y [H⁺] = 10^−pH, los 8 puntos de su Tabla III dan Kex entre 2,8 y 8,7. Su media geométrica es **5,05**.

Una mutación que vuelve a 2,90 hace fallar 4 pruebas: la unidad importa.

## Validación

Las tolerancias se fijaron antes de correr (`tests/test_sx.py`).

| Prueba | Referencia | Tolerancia | Resultado |
|---|---|---|---|
| Contracorriente, isoterma lineal, N = 1 a 4 | Ecuación de Kremser | 1e-9 | ✅ |
| Una etapa con eficiencia E | Analítica: x₀/(1 + r·E·m) | 1e-9 | ✅ |
| Cierre por elemento; equilibrio por etapa con E = 1 | — | 1e-9 | ✅ |
| Un contacto, 10 a 25 %v/v | Devi, Figura 3 (tres valores leídos del gráfico) | ±15 % | −0,1 % a −2,3 % ✅ |
| 2 etapas, O:A 3:4: orgánico cargado | Devi, Tabla IV: 8,4 g/L | ±5 % | 8,43 ✅ |
| 2 etapas: refino | Devi, Tabla IV: 0,03 g/L | factor 2 | 0,029 ✅ |
| 2 etapas: pH del refino | Devi, Tabla IV: 0,9 | ±0,2 | 1,00 ✅ |
| Despojo en 3 etapas, O:A 3:1: electrolito | Devi, Tabla V: 25,1 g/L | ±3 % | 24,84 ✅ |
| Despojo: orgánico despojado | Devi, Tabla V: 0,002 g/L | ≤ 0,05 | **0,119** ❌ |
| Circuito 2E-1S: recuperación | Isocalc (Mitshabu 2023): 92,83 % | ±5 puntos | **70,4 %** ❌ |
| Circuito 2E-1S: transferencia neta | Isocalc: 0,26 g/L por %v/v | ±20 % | **0,198** ❌ |
| Circuito 2E-1S: carga del orgánico | Isocalc: 78,6 % de la carga máxima | ±10 puntos | 85,6 % ✅ |
| Extracción sola, con el orgánico despojado de Isocalc | Isocalc: 92,83 % | ±5 puntos | 89,4 % ✅ (*) |

(*) Esta prueba se agregó **después** de ver el fallo del circuito, para aislar su causa. No es una validación ciega.

Sobre las referencias:
- El caso Isocalc es la simulación del fabricante del reactivo, hecha con isotermas de laboratorio de una planta del Congo y la mezcla 50/50 de cetoxima y aldoxima, que es el LIX 984N. Las razones O/A no se publican: salen del balance de sus propios resultados.
- Las eficiencias son las típicas de la patente US 7635457: 92 % en E1 y 95 % en E2. Para S1 se supuso 95 %.

Para comprobar que las pruebas pueden fallar, se metieron 7 errores a propósito y todos se detectaron:
- 1 H⁺ por Cu en vez de 2;
- oxima libre mal calculada;
- H⁺ sin elevar al cuadrado;
- sin eficiencia de Murphree;
- sin calibrar con el pH medido;
- Kex de Devi en su unidad (2,90);
- ácido que no se libera en la salida.

## Hallazgos y límites

- **La extracción se valida; el despojo no.** Con ácido concentrado (199 a 270 g/L), el modelo trata el H⁺ como ideal, y su actividad real es mucho mayor. Por eso despoja de menos:
  - en Devi deja 0,119 g/L en el orgánico, contra 0,002 medido;
  - en el caso Isocalc deja 5,0 g/L, contra 3,1.

  Como el orgánico vuelve más cargado, el circuito completo recupera 70 % en vez de 93 %. Son 3 fallos esperados y **estrictos**. No se ajustó nada para tapar la diferencia. El siguiente paso sería la actividad del H⁺ en ácido concentrado, con Pitzer, pero `pitzer_cu.dat` ya mostró que el cobre con ácido no se transfiere bien (ver `docs/equilibrio.md`).
- **Calibrar con el pH medido es decisivo.** Sin calibrar, el modelo ideal daría 99,5 % de recuperación en la extracción del caso Isocalc; calibrado, 89,4 %.
- No modela:
  - hierro ni manganeso, ni su coextracción;
  - arrastres de una fase en la otra;
  - la cinética ni la dinámica de los mezcladores;
  - la temperatura: Kex es de 30 °C;
  - la electroobtención.
- La densidad de cada fase es constante y la da el usuario.
