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

## Límites de esta fase

- **No hay cambios de fase:** el agua no se evapora ni hierve. Los datos del agua líquida llegan a 227 °C y se usan hasta 30 K por debajo de su primer tramo (desde unos −5 °C). Fuera de rango, el simulador da error con el rango admitido.
- **Solutos acuosos:** Cp = 0, es decir, a dilución infinita. En soluciones diluidas pesa menos del 1 %, porque la capacidad calorífica la pone el agua. No vale para soluciones concentradas.
- **Calor de dilución del ácido:** no se modela. El H2SO4 se trata como acuoso desde que entra; el ácido concentrado y su calor de dilución quedan para más adelante.
- **Especies sin datos:** el catálogo las rechaza con un mensaje que las nombra. Por ejemplo, la calcopirita: el NIST y el USGS no publican su Cp en una forma usable aquí.
