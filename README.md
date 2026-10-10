# simulador-procesos

Simulador de procesos metalúrgicos implementado **desde la literatura**: balance de masa de plantas con reacciones químicas, reciclos y lazos de control. Es independiente de cualquier software comercial.

**Fase 1 (esta versión):** balance de masa en estado estacionario.

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

113 pruebas (más 2 fallos esperados por redondeo de la fuente), cobertura del 99 % y ruff limpio:

```bash
python -m pytest --cov=procesos
```

## Hoja de ruta

| Fase | Contenido |
|---|---|
| 1 ✅ | Balance de masa con reacciones, reciclos y lazos de control |
| 2 | Balance de calor: entalpías y temperaturas con datos públicos (NASA, NIST-JANAF) |
| 3 | Equilibrio químico, también acuoso, integrando motores libres |
| 4 | Diagrama interactivo, costos y reportes |

## Límites de esta versión

- La temperatura y la presión se transportan pero no se balancean: el mezclador promedia la temperatura por masa hasta que exista la fase 2.
- Los separadores usan recuperaciones fijas. Los modelos físicos de flotación, clasificación y molienda viven en el proyecto hermano `simulador-conminucion`.

## Licencia

MIT · Anthony Vera Baldeón
