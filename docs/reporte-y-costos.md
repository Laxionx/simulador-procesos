# Fase 4: reporte HTML, diagrama de flujo y costo operativo (B4)

```bash
python -m procesos resolver ejemplos/lixiviacion_con_calor.yaml --html salidas/lixiviacion.html
```

![Reporte HTML de la lixiviación con balance de calor](img/reporte_html.png)

## El reporte

Es un solo archivo HTML. No usa JavaScript, no carga fuentes ni nada de internet, y se puede abrir sin conexión o imprimir. Incluye:
- el diagrama de flujo;
- los indicadores principales: peor cierre, iteraciones y costo por tonelada;
- la tabla de corrientes;
- el balance por elemento, con su sello de cierre;
- el balance de energía;
- el equilibrio, con sus avisos de validez;
- los lazos de control;
- el costo operativo.

**Diagrama.** Cada equipo va en la columna de su camino más largo desde las alimentaciones. Las corrientes de corte son los reciclos: no cuentan para eso y se dibujan por debajo, en naranja discontinuo. Cada producto se ubica justo después del equipo que lo produce, para que su flecha no cruce otros equipos.

**Seguridad.** Los nombres de la planta, de los equipos, de las corrientes y de las especies vienen del YAML, y todos se escapan. Una prueba carga una planta llamada `<script>…</script>` y comprueba que el reporte la muestra como texto.

## Costo operativo

```yaml
costos:
  moneda: USD
  por_tonelada_de: {corriente: Mineral}       # o {corriente: PLS, elemento: Cu}
  precios_por_t: {"H2SO4(l)": 150, H2O: 0.8}   # lo que entra por las alimentaciones
  calor_por_kwh: 0.03                          # calor agregado (calentadores, evaporadores)
  frio_por_kwh: 0.0                            # calor retirado
  fijo_por_h: 250                              # mano de obra, mantención
```

- **Reactivos.** Su consumo es lo que entra por las alimentaciones, en t/h. Con lazos de control se usa el valor ajustado.
- **Energía.** Se toma el calor de cada calentador, evaporador y reactor isotérmico.
- **Base «por tonelada».** Es el flujo total de una corriente o el de un elemento contenido en ella. Ojo: si la corriente aún trae sólidos, el elemento contenido incluye lo que no reaccionó.
- **Errores que el simulador rechaza:** precios negativos, especies desconocidas, especies con precio que no entran por ninguna alimentación, y una base sin flujo.

Los precios del ejemplo son **ilustrativos, no de mercado**. Cada usuario debe poner los suyos.

**Costo de capital: no se estima.** No hay correlaciones públicas validadas para estos equipos, y el brief pedía usarlas o declarar su ausencia.

## Validación

Las tolerancias se fijaron antes de correr (`tests/test_reporte_html.py`).

| Prueba | Referencia | Resultado |
|---|---|---|
| Costo de una planta con calores dados | A mano: 10 t/h × 0,5 + 500 kW × 0,03 + 200 kW × 0,01 + 30 = 52 USD/h; 1,04 USD/t | 1e-9 ✅ |
| Costo por tonelada de Si contenido | A mano, con las masas atómicas | 1e-4 ✅ |
| Ejemplo de lixiviación | A mano: 3,2009 t/h × 150 + 150,06 t/h × 0,8 + 1.172,7 kW × 0,03 + 250 = 885,36 USD/h | ✅ |
| HTML bien formado, sin recursos externos | Analizador estricto de etiquetas | ✅ |
| Nombres hostiles escapados | `<script>`, `<b>`, `&` | ✅ |
| Diagrama | Un nodo por equipo, una flecha por conexión, los reciclos marcados | ✅ |

La revisión visual se hizo con capturas de Edge sin interfaz. Destapó y se corrigieron:
- un diagrama más ancho que la página;
- etiquetas repetidas en las flechas de alimentación;
- una flecha de producto que pasaba por detrás de otro equipo;
- entalpías negativas sin explicar. El reporte ahora aclara que son absolutas.

## Límites

- El diagrama usa un trazado automático simple. En plantas grandes puede cruzar flechas, aunque se mantiene legible.
- Sin costo de capital ni costos de mantención por equipo.
