# Fase 3: equilibrio químico acuoso

El equipo `equilibrio` (`EquilibriumReactor`) decide por equilibrio químico cuánto se disuelve o precipita, en vez de recibirlo como dato. Usa **PHREEQC** del USGS, que es de dominio público, a través de [phreeqpy](https://pypi.org/project/phreeqpy/) (licencia BSD-3).

```bash
pip install -e ".[equilibrio]"
python -m procesos resolver ejemplos/lixiviacion_equilibrio.yaml
```

```yaml
- tipo: equilibrio
  nombre: Precipitación
  entradas: [Descarga]
  salidas: [PLS]
  minerales: {Gypsum: "CaSO4·2H2O"}   # fase de PHREEQC -> especie de la planta
  temperatura: 25                     # opcional; si no, la de la entrada
  base: minteq.v4.dat                 # opcional; es la incluida por defecto
```

## Cómo traduce entre la planta y PHREEQC

1. **Entrada.** Las especies acuosas de la planta, como CuSO4(aq) o H2SO4(aq), se suman como totales por elemento. El azufre entra como sulfato y el carbono como carbonato. PHREEQC fija el pH por balance de carga. Los minerales permitidos entran con la cantidad que ya trae la corriente.
2. **Equilibrio.** PHREEQC resuelve la especiación, las actividades y cuánto de cada mineral se disuelve o precipita.
3. **Vuelta a la planta.** Lo disuelto sale de **conservar la masa** con lo que PHREEQC decidió para los minerales; los totales del propio PHREEQC se usan como control y deben coincidir a 10⁻⁶. Cada metal disuelto vuelve a la única especie acuosa de la planta que lo contiene. El sulfato que sobra vuelve como H2SO4(aq) y el carbonato como CO2(aq). El agua se cierra con el balance de hidrógeno, así que el oxígeno queda como control independiente. Los sólidos y gases que no están en `minerales` pasan sin reaccionar.

La base incluida es `minteq.v4.dat` (EPA MINTEQA2 v4, distribuida con PHREEQC). Trae los complejos del cobre y minerales como yeso, tenorita, brocantita y antlerita. Se eligió **antes** de ver ningún resultado. La `phreeqc.dat` más reciente del repositorio no carga en el IPhreeqc 3.7.3 que trae phreeqpy.

## Validación

Las tolerancias se fijaron en el brief, antes de correr (`tests/test_equilibrio.py`).

| Prueba | Referencia | Tolerancia | Resultado |
|---|---|---|---|
| Yeso en agua a 25 °C | Nordstrom: 0,01528 mol/kg (citado en una nota de C. Hall, U. de Edimburgo) | ±5 % | 0,01597: **+4,5 %** ✅ |
| Yeso en H2SO4 de 0,1 a 0,4 mol/kg | Shen et al. (2020), *J. Chem. Eng. Data* 65, 2310, tabla suplementaria | ±15 % | −1,0 %, −6,2 % y −13,5 % ✅ |
| Yeso en H2SO4 de 0,6 a 1,0 mol/kg | La misma | ±15 % | −19 %, −24 % y −27 % ❌ |
| pH de H2SO4 0,01 N y 0,1 N | PubChem / HSDB: 2,1 y 1,2 | ±0,1 | 2,129 y 1,292 ✅ |
| pH de H2SO4 1 N | PubChem / HSDB: 0,3 | ±0,1 | 0,402 ❌, por 0,002 |
| Cierre de elementos del equipo, y de la planta de ejemplo | Balance por elemento | 1e-9 | 4·10⁻¹⁶ ✅ |
| Error de carga que informa PHREEQC | — | < 10⁻⁶ % | ✅ |
| Calcita con CO2 a 1 atm | — | ±10 % | **Descartado:** no hay un dato público medido de equilibrio (ver abajo) |

Sobre las referencias:
- La de Shen et al. es su modelo de Pitzer, ajustado a 7 conjuntos de datos experimentales evaluados, con un error medio del 1,8 % a 25 °C. Es un modelo evaluado, no una medición directa.
- Los valores de HSDB vienen con un solo decimal.

Para comprobar que las pruebas pueden fallar, se metieron 3 errores a propósito y todos se detectaron:
- fijar el pH en 7, sin balance de carga;
- ignorar lo que precipita;
- convertir mal el agua.

## Hallazgos y límites

- **El modelo de actividad se rompe sobre una fuerza iónica de unos 0,5 mol/kg**, como se anticipó en el brief. `minteq.v4` usa Debye-Hückel extendido y Davies:
  - con ácido sobre 0,5 mol/kg, subestima la solubilidad del yeso entre 19 y 27 %;
  - el pH del ácido 1 N sale 0,1 alto.

  Esos casos quedan como fallos esperados y **estrictos**. La CLI avisa cuando un equilibrio pasa de 0,5 mol/kg. Para soluciones de lixiviación concentradas haría falta Pitzer, y la base pública `pitzer.dat` no trae cobre.
- **Primer intento, corregido:** se leían los totales disueltos directamente de PHREEQC, y el azufre cerraba a 1,5·10⁻⁸ por la tolerancia interna de PHREEQC, no a 10⁻⁹. Ahora lo disuelto sale de conservar la masa y PHREEQC queda como control.
- **Calcita descartada.** El dato clásico (Plummer y Busenberg, 1982) está tras un muro de pago, y el informe abierto del USGS (OFR 99-247) trata de crecimiento de cristales a 34 °C. No se inventa una referencia.
- **Alcance de la traducción:**
  - cada metal disuelto necesita una única especie acuosa de la planta que lo lleve;
  - no hay fase gaseosa en equilibrio: el CO2 gaseoso pasa sin reaccionar;
  - el equipo es isotérmico y no se combina con el balance de calor, salvo que todas las especies tengan datos termodinámicos.
- **El ejemplo** (`lixiviacion_equilibrio.yaml`) es la lixiviación del caso 2. El calcio del carbonato queda disuelto muy por encima de la solubilidad del yeso, y el equilibrio precipita 1.083 kg/h de yeso. El PLS sale a pH 1,52, con fuerza iónica 0,28 mol/kg, dentro del rango del modelo.
