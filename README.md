# simulador-procesos

Simulador de procesos metalúrgicos implementado **desde la literatura**: balance de masa y de calor de plantas con reacciones químicas, equilibrio acuoso, reciclos y lazos de control. Es independiente de cualquier software comercial.

**Fases 1 a 3 (esta versión):** balance de masa y de calor en estado estacionario, y equilibrio químico acuoso con PHREEQC.

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

137 pruebas (más 6 fallos esperados: redondeos de la fuente y el límite del modelo de actividad), cobertura del 97 % y ruff limpio:

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

Ver [docs/equilibrio.md](docs/equilibrio.md).

```bash
python -m procesos resolver ejemplos/lixiviacion_equilibrio.yaml
```

## Hoja de ruta

| Fase | Contenido |
|---|---|
| 1 ✅ | Balance de masa con reacciones, reciclos y lazos de control |
| 2 ✅ | Balance de calor: entalpías y temperaturas con datos públicos (NIST-JANAF, USGS, CODATA) |
| 3 ✅ | Equilibrio químico acuoso con PHREEQC (minteq.v4); válido hasta una fuerza iónica de ~0,5 mol/kg |
| 4 | Diagrama interactivo, costos y reportes |

## Límites de esta versión

- Sin `balance_de_calor`, la temperatura se transporta sin balancear: el mezclador la promedia por masa.
- El balance de calor no modela cambios de fase, ni el Cp de los solutos acuosos, ni el calor de dilución del ácido concentrado (ver [docs/balance-de-calor.md](docs/balance-de-calor.md)).
- La presión se transporta pero no se balancea.
- Los separadores usan recuperaciones fijas. Los modelos físicos de flotación, clasificación y molienda viven en el proyecto hermano `simulador-conminucion`.

## Licencia

MIT · Anthony Vera Baldeón
