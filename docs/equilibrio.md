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
                                      # pitzer_cu.dat para soluciones concentradas
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

  Esos casos quedan como fallos esperados y **estrictos**. Con esta base, la CLI avisa cuando un equilibrio pasa de 0,5 mol/kg. Para soluciones concentradas está `pitzer_cu.dat`; ver la sección siguiente.
- **Primer intento, corregido:** se leían los totales disueltos directamente de PHREEQC, y el azufre cerraba a 1,5·10⁻⁸ por la tolerancia interna de PHREEQC, no a 10⁻⁹. Ahora lo disuelto sale de conservar la masa y PHREEQC queda como control.
- **Calcita descartada.** El dato clásico (Plummer y Busenberg, 1982) está tras un muro de pago, y el informe abierto del USGS (OFR 99-247) trata de crecimiento de cristales a 34 °C. No se inventa una referencia.
- **Alcance de la traducción:**
  - cada metal disuelto necesita una única especie acuosa de la planta que lo lleve;
  - no hay fase gaseosa en equilibrio: el CO2 gaseoso pasa sin reaccionar;
  - el equipo es isotérmico y no se combina con el balance de calor, salvo que todas las especies tengan datos termodinámicos.
- **El ejemplo** (`lixiviacion_equilibrio.yaml`) es la lixiviación del caso 2. El calcio del carbonato queda disuelto muy por encima de la solubilidad del yeso, y el equilibrio precipita 1.083 kg/h de yeso. El PLS sale a pH 1,52, con fuerza iónica 0,28 mol/kg, dentro del rango del modelo.

## Soluciones concentradas: Pitzer (B2)

Con `base: pitzer_cu.dat`, PHREEQC usa el modelo de Pitzer en vez de Debye-Hückel.

La base tiene dos partes:
- `pitzer.dat` del USGS, de la etiqueta v3.7.3, sin cambios;
- un bloque de cobre a 25 °C, agregado antes del primer `END` y marcado con un comentario.

El bloque de cobre trae:
- los parámetros de Pitzer Cu-SO4, Cu-HSO4, θ Cu-H y los ψ de Cu-H-SO4-HSO4;
- la calcantita, CuSO4·5H2O.

Todos esos valores vienen de Justel et al. (2020), *ACS Omega* 5, 29150, Tablas 3 a 6. Los de Cu-SO4 son los clásicos de Pitzer y Mayorga (1974). El log K de la calcantita, −2,6366, sale de la Tabla 6: m = 1,39 mol/kg, γ± = 0,0368, a_w = 0,9753.

### Validación

Las tolerancias se fijaron antes de correr (`tests/test_pitzer_cu.py`).

| Prueba | Referencia | Tolerancia | Resultado |
|---|---|---|---|
| γ±, a_w y SI de la calcantita con CuSO4 1,39 mol/kg | Justel et al. (2020), Tabla 6 | ±2 %, ±0,002 y 0,01 | pasan |
| Calcantita en agua a 25 °C | Bell y Taber (1908), en Seidell (1919), p. 276: 1,419 mol/kg | ±5 % | 1,387: **−2,3 %** ✅ |
| Yeso en agua | Nordstrom: 0,01528 mol/kg | ±5 % | −1,5 % ✅ |
| Yeso en H2SO4 de 0,1 a 3 mol/kg (10 puntos) | Shen et al. (2020) | ±10 % | −1,9 % a −5,4 % ✅ |
| Calcantita en H2SO4 de 1,5 a 9,8 mol/kg (5 puntos) | Bell y Taber (1908) | ±10 % | **+14, +80, +113, +92 y +18 %** ❌ |
| Cierre de elementos con cobre, ácido, yeso y calcantita | Balance por elemento | 1e-9 | pasa |

Sobre las referencias:
- La tabla de Bell y Taber es una medición. El libro de Seidell es de 1919 y de dominio público. Los dígitos se leyeron del escaneo de Internet Archive, no solo del texto extraído.
- La tolerancia del yeso **no es ciega**: con `pitzer.dat` sin cobre ya se había visto entre −0,1 % y −5,4 %.

Para comprobar que las pruebas pueden fallar, se metieron 4 errores a propósito y todos se detectaron:
- β1 de Cu-SO4 cambiado de 2,527 a 1,527;
- log K de la calcantita corrido 0,1;
- β0 H-HSO4 del USGS corrido 0,1;
- el aviso de ácido libre desactivado.

### Hallazgo: el cobre en ácido no se reproduce

Con ácido sulfúrico, la base sobreestima la solubilidad de la calcantita. Los 5 puntos quedan como fallos esperados y **estrictos**. Se diagnosticó así, sin ajustar nada a los datos de validación:

| Variante | Desvío con 1,5 · 3,8 · 6,3 · 7,8 · 9,8 mol/kg de H2SO4 |
|---|---|
| Base tal cual | +14, +80, +113, +92, +18 % |
| Sin los términos Cu-HSO4 | se disuelve toda la calcantita |
| Sin θ ni ψ del cobre | +4, +42, +11, −37, −85 % |
| Cu-HSO4 igual al Mg-HSO4 del USGS | +12, +91, +246, +382, +525 % |
| Con el modelo del H2SO4 de Justel completo (Christov y Moller) | +25, +96, +126, +99, +18 % |

El resultado depende casi por completo de los términos Cu-HSO4 y de los ternarios. Sus autores los ajustaron dentro de otro modelo del H2SO4, y no se transfieren a este. Usar el modelo del ácido de Justel completo tampoco lo arregla.

Por eso **no se recomienda `pitzer_cu.dat` para cobre con ácido libre**, como en electrolitos de EW o en la cristalización de sulfato de cobre.

Sin ácido, o con calcio, magnesio, sodio, potasio o hierro(II) en ácido, sí sirve dentro de lo validado.

El reactor devuelve un aviso, y la CLI lo imprime, en estos casos:
- con cobre disuelto y más de 0,01 mol/kg de ácido libre;
- con cobre a una temperatura distinta de 25 °C, porque los parámetros del cobre no dependen de la temperatura.

Con `minteq.v4.dat` sigue el aviso de fuerza iónica sobre 0,5 mol/kg. Con Pitzer ese aviso no aplica y no se da.

**Otras bases que se probaron antes de elegir** (exploración, no validación):
- `sit.dat` (ThermoChimie): mejora el yeso hasta ~0,6 mol/kg y se pasa por encima. Además, su licencia no está verificada, así que no se incluye.
- `pitzer.dat` del repositorio actual: no carga en el IPhreeqc 3.7.3 de phreeqpy.
