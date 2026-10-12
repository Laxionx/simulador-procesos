# Molienda: conexión con simulador-conminucion

El equipo `molienda` conecta este simulador con el proyecto hermano
[simulador-conminucion](https://github.com/Laxionx/simulador-conminucion). Así una planta completa
puede ir de la molienda a la flotación o a la lixiviación, con la energía de moler en el costo.
Es un extra opcional:

```bash
pip install -e ".[molienda]"
```

La versión de conminucion queda fijada a un commit en `pyproject.toml`.

## Qué hace

Moler no cambia la composición: la corriente sale igual que entra. El equipo entrega el P80, la
energía específica, la potencia y, si se simula el circuito, la carga circulante. La potencia
entra al costo como electricidad (`electricidad_por_kwh`) y, con balance de calor, al balance de
energía: entra + calor + electricidad = sale, y el calor es la energía del molino que se pierde.

Hay dos modos:

| Modo | Datos | Cálculo | Potencia |
|---|---|---|---|
| Bond | `wi`, `f80`, `p80` | W = 10·Wi·(1/√P80 − 1/√F80), con la función de conminucion | W × t/h |
| Circuito | `circuito`, `caso`, `potencia_kw` opcional | el circuito molino-ciclón de conminucion, con la alimentación de la plantilla escalada a los sólidos de la planta | la del molino de energía |

Los sólidos son las especies de fase `s`; el agua, la especie `H2O` (o la que diga `agua`). En el
modo circuito, `wi` solo se usa para la energía de Bond que se informa.

```yaml
# Modo Bond (diseño): el muestreo 6 de Constancia
- {tipo: molienda, nombre: Molienda, entradas: [Mineral], salidas: [Pulpa molida],
   wi: 16.4, f80: 1068, p80: 188}

# Modo circuito: la plantilla Bougainville con el molino escalado a 100 t/h
- {tipo: molienda, nombre: Molienda, entradas: [Mineral], salidas: [Pulpa molida],
   wi: 14.0, circuito: cerrado_directo, caso: bougainville, potencia_kw: 1087}
```

Desde Python, `Grinding(..., circuit=..., config=CircuitConfig(...))` acepta cualquier
configuración de conminucion (molino, clasificador, granulometría). El YAML solo trae la plantilla
Bougainville, que es la única validada contra MODSIM.

## Validación

Tolerancias fijadas antes de correr ([tests/test_molienda.py](../tests/test_molienda.py)).

| Prueba | Tolerancia | Resultado |
|---|---|---|
| Lo conectado es igual a conminucion por separado: Bond, P80, carga circulante, potencia, agua | 1e-12 | idéntico, también con la alimentación escalada a 100 t/h y con agua |
| Bougainville a través de la conexión contra MODSIM 3.6.24 (las tolerancias de conminucion) | ±5 % | carga circulante 81,87 % frente a 81,92 %; P80 185,6 frente a 185 µm |
| Constancia, 14 muestreos de molienda de bolas: Bond contra la columna «modelo» del reporte | ±5 % | los 14 pasan |
| Composición sin cambio, cierre por elemento y de energía, costo = potencia × precio | exacto | sí |

Las 10 mutaciones del código (escala de la alimentación, unidades de sólidos y agua, potencia,
calor, agua agregada, parámetros) hacen fallar las pruebas.

Esta conexión no agrega validación nueva: muestra que, a través del puente, se conservan las que
conminucion ya tenía. Ver los límites de cada modelo en su
[VALIDACION_PLANTAS_REALES.md](https://github.com/Laxionx/simulador-conminucion/blob/main/docs/VALIDACION_PLANTAS_REALES.md).
En Constancia, por ejemplo, la planta gastó en promedio 12 % más que Bond, y hasta 69 % más con
mineral supérgeno.

## Ejemplo

`ejemplos/concentradora_con_molienda.yaml`: 100 t/h de mineral pasan por el circuito
Bougainville (molino de 1.087 kW, la misma energía específica que el caso original) y luego por
la flotación rougher-cleaner de `concentradora_cu.yaml`.

| Resultado | Valor |
|---|---|
| F80 → P80 | 7.817 → 221 µm |
| Carga circulante | 81,9 % |
| Potencia del molino | 1.087 kW (10,9 kWh/t) |
| Electricidad a 0,08 USD/kWh | 87 USD/h |

## Límites

- El agua que agrega el circuito (cajón y descarga del molino) se informa, pero no se suma a la
  corriente, para no crear masa. Si importa, se agrega como una alimentación de agua.
- Un solo mineral y una densidad de sólidos (como en conminucion): la molienda no distingue la
  calcopirita de la ganga ni calcula liberación.
- La granulometría no viaja a los equipos siguientes: este simulador no tiene clases de tamaño.
  El P80 se informa.
- La plantilla Bougainville escalada a otro tonelaje supone el mismo mineral y la misma energía
  específica si se escala la potencia; no es una planta medida a ese tonelaje.
