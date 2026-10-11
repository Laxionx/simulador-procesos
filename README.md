# simulador-procesos

Simulador de procesos metalúrgicos implementado **desde la literatura**: balance de masa y de calor de plantas con reacciones químicas, equilibrio acuoso, reciclos y lazos de control. Es independiente de cualquier software comercial.

**Fases 1 a 4 (esta versión):** balance de masa y de calor en estado estacionario, equilibrio químico acuoso con PHREEQC, extracción por solventes de cobre, y reporte HTML con diagrama de flujo y costo operativo.

```bash
pip install -e .
python -m procesos resolver ejemplos/lixiviacion_oxidos_cu.yaml --salida salidas
```

```
Planta: Lixiviación de óxidos de cobre
  Controlador «Acidez libre»: 3,200.5820
  Convergió en 1 iteraciones · cortes: ninguno
  Balance por elemento (kg/h): ...
  Peor error de cierre: 1.15e-16
```

## Qué hace

- **Especies** con fórmula química. La masa molar se calcula sola y se admiten hidratos, iones y fases.
- **Equipos:**
  - mezclador;
  - divisor;
  - separador por especie (flotación, espesador, filtro);
  - reactor con estequiometría y conversión de un componente clave. Si otro reactivo se agota, el avance se limita a él y lo informa.
- **Reciclos:** las corrientes de corte se eligen solas y se iteran con Wegstein.
- **Lazos de control:** «ajusta X hasta que Y llegue a la meta». Un lazo se resuelve con Brent y varios en conjunto. Si la meta es inalcanzable, se informa con números.
- **Guardas:**
  - las reacciones que no conservan átomos o carga se rechazan al definir la planta;
  - nunca hay flujos negativos;
  - el reporte muestra el cierre del balance por elemento y por equipo.
- **Planta en YAML** legible, con errores que indican dónde está el problema (ver `ejemplos/`). La tabla de corrientes sale en CSV y Excel.

## Validación

3 casos comparados con resultados calculados aparte: un reciclo con solución exacta, una lixiviación calculada a mano y una concentradora contra la fórmula de dos productos. El detalle está en [docs/casos-validacion.md](docs/casos-validacion.md).

Además, 3 plantas reales publicadas: la producción de Constancia (Hudbay), el ácido de lixiviación de Marimaca y los cátodos del plan minero de Puquios. Las tolerancias se fijaron antes de correr. Detalle y hallazgos en [docs/VALIDACION_PLANTAS_REALES.md](docs/VALIDACION_PLANTAS_REALES.md).

251 pruebas (más 17 fallos esperados: redondeos de la fuente, los límites de los modelos de actividad y el del vapor ideal), cobertura del 98 % y ruff limpio:

```bash
python -m pytest --cov=procesos
```

## Balance de calor (fase 2)

Con `balance_de_calor: true` en el YAML, cada equipo cierra también la energía. Los datos son públicos: NIST-JANAF, USGS y CODATA.
- Los mezcladores y los reactores adiabáticos calculan su temperatura de salida.
- Los reactores con temperatura fija y los calentadores dan el calor necesario.
- Los lazos de control pueden fijar una temperatura de salida.

Los datos de las especies se validaron contra fuentes independientes: JANAF, IAPWS y USGS, con desvíos de 0,6 % o menos. El detalle y los límites están en [docs/balance-de-calor.md](docs/balance-de-calor.md).

```bash
python -m procesos resolver ejemplos/lixiviacion_con_calor.yaml
```

## Equilibrio químico (fase 3)

El equipo `equilibrio` decide por equilibrio cuánto se disuelve o precipita, por ejemplo el yeso en una solución de lixiviación, y da el pH. Usa PHREEQC del USGS (dominio público) mediante phreeqpy, y es opcional: `pip install -e ".[equilibrio]"`.
- Validado contra la solubilidad del yeso en agua (+4,5 %) y en ácido sulfúrico hasta 0,4 mol/kg (±15 %).
- Sobre una fuerza iónica de 0,5 mol/kg, el modelo de actividad se sale de rango, y está documentado.
- Para soluciones concentradas, `base: pitzer_cu.dat` usa el modelo de Pitzer. Es la base pública del USGS más un bloque de cobre a 25 °C tomado de la literatura.
  - El yeso en H2SO4 hasta 3 mol/kg queda entre −1,9 % y −5,4 %, y la calcantita en agua en −2,3 %.
  - **No sirve para cobre con ácido libre:** sobreestima la solubilidad de la calcantita entre 14 y 113 % contra datos medidos, y el simulador avisa.

Ver [docs/equilibrio.md](docs/equilibrio.md).

```bash
python -m procesos resolver ejemplos/lixiviacion_equilibrio.yaml
```

## Extracción por solventes de cobre

Los equipos `extraccion_solventes` y `despojo` calculan, etapa por etapa y en contracorriente, cuánto cobre pasa al orgánico. Usan el equilibrio Cu²⁺ + 2 RH ⇌ CuR₂ + 2 H⁺ del LIX 984N (Devi y Nayak 2014), con eficiencia de Murphree y el ácido que se libera. El orgánico puede circular en circuito cerrado entre la extracción y el despojo.
- **Extracción validada:** reproduce los experimentos de un contacto y de 2 etapas a contracorriente de Devi con un desvío de 2,3 % o menos. Con el orgánico de Isocalc recupera 89,4 % contra 92,8 %.
- **Despojo no validado:** con ácido concentrado el H⁺ ideal despoja de menos, y el circuito completo recupera 70 % en vez de 93 %. Está documentado como fallo esperado.

Ver [docs/sx.md](docs/sx.md).

```bash
python -m procesos resolver ejemplos/sx_2e1s.yaml
```

## Reporte HTML y costo operativo (fase 4)

```bash
python -m procesos resolver ejemplos/lixiviacion_con_calor.yaml --html salidas/lixiviacion.html
```

Genera un solo archivo HTML, sin JavaScript ni recursos externos. Trae el diagrama de flujo con los reciclos marcados, las corrientes, los balances, el equilibrio y el costo operativo por hora y por tonelada. El costo usa los precios que se ponen en la sección `costos:` del YAML. El costo de capital no se estima.

![Reporte HTML](docs/img/reporte_html.png)

Ver [docs/reporte-y-costos.md](docs/reporte-y-costos.md).

## Hoja de ruta

| Fase | Contenido |
|---|---|
| 1 ✅ | Balance de masa con reacciones, reciclos y lazos de control |
| 2 ✅ | Balance de calor: entalpías y temperaturas con datos públicos (NIST-JANAF, USGS, CODATA) |
| 3 ✅ | Equilibrio químico acuoso con PHREEQC: minteq.v4 hasta una fuerza iónica de ~0,5 mol/kg; Pitzer para soluciones concentradas sin cobre ácido |
| 4 ✅ | Reporte HTML con diagrama de flujo y costo operativo; sin costo de capital (no hay correlaciones públicas validadas) |

## Límites de esta versión

- Sin `balance_de_calor`, la temperatura se transporta sin balancear: el mezclador la promedia por masa.
- El balance de calor ya incluye el calor de dilución del H2SO4 (Wu y Young 1980; NBS 1982) y la evaporación del agua (IAPWS-IF97). El vapor se trata como ideal, así que a varios bar el error pasa del 1,8 %, y no se modela la subida del punto de ebullición (ver [docs/balance-de-calor.md](docs/balance-de-calor.md)).
- La presión se transporta pero no se balancea.
- Los separadores usan recuperaciones fijas. Los modelos físicos de flotación, clasificación y molienda viven en el proyecto hermano `simulador-conminucion`.

## Licencia

MIT · Anthony Vera Baldeón
