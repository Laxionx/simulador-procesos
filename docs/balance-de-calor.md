# Fase 2: balance de calor

Con `balance_de_calor: true` en el YAML, o `Catalog(especies, DEFAULT_THERMO)` en Python, cada equipo cierra la energía además de la masa.

La entalpía molar de cada especie es la de formación a 25 °C más su calor sensible:

    h(T) = ΔfH°(298,15 K) + ∫ Cp dT     [kJ/mol]

Como la entalpía de formación ya está incluida, una misma suma cierra el calor sensible y el de reacción.

| Equipo | Qué hace con la energía |
|---|---|
| Mezclador, divisor, separador | La temperatura de salida es la que conserva la entalpía. |
| Reactor sin `temperatura` | Adiabático: la temperatura de salida sale del balance. |
| Reactor con `temperatura` | Isotérmico: el reporte da el calor que hay que agregar o retirar (kW). |
| Calentador (`tipo: calentador`) | Fija la temperatura de salida y da el calor, o recibe un calor (`calor_kw`, negativo enfría) y da la temperatura. |

Los lazos de control pueden manipular `temperatura` o `calor_kw` y usar `temperatura` como meta. Los reciclos convergen también en temperatura.

Ejemplo: [`ejemplos/lixiviacion_con_calor.yaml`](../ejemplos/lixiviacion_con_calor.yaml).

```
python -m procesos resolver ejemplos/lixiviacion_con_calor.yaml
```

## Datos y fuentes

Todos los datos son públicos y gratuitos. Cada ficha guarda su fuente en `procesos/thermo_data.py`.

| Especies | Fuente | Forma |
|---|---|---|
| H2O líquida, CO2, O2, N2, CuO, Cu, SiO2 (cuarzo α y β), MgO, Al2O3 (corindón) | NIST Chemistry WebBook: ecuaciones de Shomate de Chase (1998), NIST-JANAF | Cp por tramos de temperatura |
| CaCO3 (calcita), CaSO4 (anhidrita) | USGS Bulletin 2131, Robie y Hemingway (1995), dominio público | Cp = A1 + A2 T + A3/T² + A4/√T + A5 T² |
| H2SO4, CuSO4, MgSO4, ZnSO4, Al2(SO4)3 y CO2 acuosos | CODATA Key Values, Cox, Wagman y Medvedev (1989) | ΔfH° como suma de sus iones a dilución infinita |

En el boletín del USGS, el texto extraído del PDF corre los coeficientes una fila. Cada fila se identificó por su entropía y se comprobó reproduciendo la columna de Cp tabulada.

## Validación

Las tolerancias se fijaron antes de correr (`tests/test_balance_calor.py`). Donde se pudo, la comparación es contra **otra** fuente.

| Prueba | Referencia | Tolerancia | Desvío máximo |
|---|---|---|---|
| h − h298 del CO2 y del O2 entre 400 y 1000 K | Tablas NIST-JANAF C-095 y O-029 | ±0,3 % | 0,061 % |
| h(T) − h(25 °C) del agua entre 5 y 95 °C | IAPWS-95, NIST WebBook a 1 atm | ±0,5 % | 0,136 % |
| Cp y h − h298 de calcita y anhidrita | Tablas del USGS | ±0,3 % y ±0,5 % | 0,004 % y 0,015 % |
| Cuarzo y CuO del NIST | Tablas del USGS (otra fuente) | ±1 % | 0,63 % |
| Mezcla de agua a 20 °C y a 80 °C, partes iguales | IAPWS: 50,027 °C | ±0,1 °C | 50,020 °C |
| Reactor isotérmico a 25 °C | Σ avance · ΔrH calculado a mano | 1e-4 relativo | cumple; da −299,2 kW |
| Reactor adiabático | Cierre de energía, y ΔT = calor ÷ capacidad calorífica | 1e-9 y ±2 % | cumple; sube de 25 a 26,71 °C |
| Calentador: temperatura → calor → temperatura | Ida y vuelta, y 1 kg/s de agua de 20 a 60 °C según IAPWS | 1e-9 y ±0,5 % | cumple |
| Lazo que lleva una salida a 60 °C | Meta | 1e-6 °C | cumple |

Para comprobar que las pruebas pueden fallar, se metieron 3 errores a propósito y todos se detectaron:
- quitar el término D de Shomate;
- fijar la masa molar en 18;
- invertir el signo del término A3/T² de la forma del USGS.

**Error mío, corregido:** el primer intento del lazo de control buscaba hasta 1.000 kW. Eso llevaría el agua a más de 227 °C, donde se acaban sus datos. El simulador lo rechazó con un mensaje que da el rango; no devolvió un número falso. La prueba ahora busca hasta 300 kW.

## Calor de dilución del ácido y cambio de fase del agua (B1)

**Ácido concentrado.** El H2SO4 puro es la especie `H2SO4(l)`, con ΔfH = −813,989 kJ/mol de NIST-JANAF H-075 y un ajuste propio de Cp sobre esa tabla. Se disuelve con una reacción explícita, por ejemplo `H2SO4(l) -> H2SO4` en un reactor.

**Calor de dilución.** El H2SO4 acuoso lleva su entalpía molal aparente relativa, ΦL, a la molalidad de cada corriente. Las fuentes son:
- Wu y Young (1980), *J. Res. NBS* 85, 11, Tabla 5, hasta 9 mol/kg;
- más concentrado, las tablas NBS de Wagman et al. (1982), «H2SO4 in n H2O», hasta n = 1.

Al diluir o al consumir ácido, la diferencia de ΦL aparece como calor.

En el ejemplo `lixiviacion_con_calor.yaml`, disolver 3.200 kg/h de ácido al 98 % libera unos 830 kW. Por eso el intercambiador necesita 1.173 kW en vez de 2.001 kW para llevar el PLS a 30 °C.

**Evaporador** (`tipo: evaporador`). A presión fija recibe un calor (kW) y reparte el agua entre líquido y vapor:
- La temperatura de saturación sale de la norma pública IAPWS-IF97 (región 4).
- El vapor de agua es gas ideal: ajuste propio a NIST-JANAF H-064, de 200 a 800 K.
- Si no alcanza a hervir, solo calienta; si sobra calor, sobrecalienta el vapor.
- Una solución ácida no se puede secar: si el calor llevaría el ácido más allá de sus datos, el equipo da error.
- Ejemplo: `ejemplos/evaporacion.yaml`.

### Validación de B1

Las tolerancias se fijaron antes de correr (`tests/test_dilucion_y_fases.py`).

| Prueba | Referencia | Tolerancia | Resultado |
|---|---|---|---|
| ΔfH del H2SO4 en n H2O, para n de 8 a 150.000 (25 valores) | NBS 1982, tablas OCR leídas de las pp. 2-58 y 2-59 | ±0,15 kJ/mol | pasan |
| ΔfH del H2SO4 en 7 H2O (m = 7,9) | NBS 1982 | ±0,15 kJ/mol | **−0,183** ❌: Wu y Young y la NBS se separan cerca de m = 8 |
| L2 derivado de ΦL | Columna L2 de Wu y Young, 16 valores | ±3 % | pasan |
| Calor de disolución del ácido líquido hasta 100 H2O | NBS: −73,65 kJ/mol | ±0,5 % | −73,72 ✅ |
| Ajustes a JANAF (ácido líquido, vapor) | Columna H − H298 | ±0,3 % | pasan |
| Saturación IF97 | Valores de verificación de la propia norma | 1e-8 | pasan |
| Saturación IF97, 5 puntos | IAPWS-95, NIST WebBook | ±0,05 % | pasan |
| Calor latente a 74, 100 y 102 °C | IAPWS-95 | ±1,5 % | +0,3 % a +0,6 % ✅ |
| Calor latente a 150 y 200 °C | IAPWS-95 | ±1,5 % | **+1,8 % y +4,6 %** ❌: el vapor real se aparta del ideal a 4,8 y 15,8 bar |
| Evaporador | Cierre de energía, y evaporar la mitad del agua con el calor calculado a mano | 1e-9 y 1e-6 | pasan |

Los dos casos que fallan quedan como fallos esperados y estrictos.

Para comprobar que las pruebas pueden fallar, se metieron 3 errores a propósito y todos se detectaron:
- conversión de calorías a kJ errada en 4 %;
- un coeficiente de IF97 cambiado;
- ΔfH del vapor corrido 0,8 kJ/mol.

**Error encontrado por el ejemplo, corregido:** el evaporador intentaba evaluar una solución ácida sin agua y fallaba. Ahora la evaporación se limita a lo que dejan los datos de dilución del soluto.

## Límites

- **Vapor ideal:** cerca de 1 atm el calor latente tiene un error de 0,6 % o menos; a varios bar pasa del 1,8 %. Para autoclaves y lixiviación a presión haría falta la región 2 de IAPWS-IF97, el vapor real.
- **No se modela la subida del punto de ebullición por los solutos.** El evaporador vale para soluciones diluidas.
- **Solutos acuosos:** Cp = 0, es decir, a dilución infinita. La NBS da −293 J/mol·K para el H2SO4 acuoso a dilución infinita. En soluciones diluidas pesa menos del 1 %.
- **ΦL a 25 °C:** no se corrige por temperatura. En una mezcla, el ΦL del ácido se evalúa a su propia molalidad, como si estuviera solo.
- Los datos del agua líquida llegan a 227 °C y se usan desde unos −5 °C. Fuera de rango, el simulador da error con el rango admitido.
- **Especies sin datos:** el catálogo las rechaza con un mensaje que las nombra. Por ejemplo, la calcopirita: el NIST y el USGS no publican su Cp en una forma usable aquí.
