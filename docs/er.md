# Electrorrefinación de cobre (fase 4c)

El equipo `electrorrefinacion` hace el balance de una nave de refinación. Recibe los ánodos (su
primera entrada) y el electrolito, y da:
- los cátodos, el barro anódico y la chatarra anódica;
- el voltaje de celda y la energía;
- lo que se acumula en el electrolito: el Cu y el Ni que gana y el ácido que pierde.

Con eso dimensiona la purga de Ni y las celdas liberadoras. Las liberadoras usan el equipo de
electroobtención que ya existía.

```yaml
- tipo: electrorrefinacion
  nombre: Nave de refinacion
  entradas: [Anodos, Electrolito a celdas]       # la primera son los ánodos
  salidas: [Electrolito de celdas, Catodos, Barro anodico, Chatarra anodica]
  densidad_corriente: 305
  area_catodica: 77932.8          # m², las dos caras de todos los cátodos
  eficiencia_corriente: 0.975
  distancia_anodo_catodo: 0.0322  # m
  arsenico: H3AsO4                # especie del As disuelto (solo para la conductividad)
  limite_ni_g_l: 18.9             # opcional: dimensiona la purga
  eficiencia_liberadoras: 0.85    # opcional: dimensiona las liberadoras
```

Ejemplo completo: `python -m procesos resolver ejemplos/refineria_atlantic_mount_isa.yaml`. Usa
ánodos con el análisis del ánodo comercial AC1 de Atlantic Copper y la geometría publicada de
Mount Isa, más liberadoras y purga de Ni. Es **ilustrativo**.

## Modelo

**Electrodos.**
- El cátodo deposita eficiencia × I / 2F de cobre.
- El ánodo se disuelve con la misma eficiencia: Cu → Cu²⁺ + 2e, y Ni → Ni²⁺ + 2e para la fracción
  de Ni que va al electrolito.
- En refinación, la corriente que se pierde es de cortocircuitos, que tocan a los dos electrodos.
  El compendio IsaKidd atribuye a menos cortocircuitos la mejora de Mount Isa de 85,9 a 97,5 %.
- Así, el Ni desplaza Cu del electrolito al cátodo sin consumir ácido.

**Ánodo.**
- Se consume parejo.
- De lo consumido, el Ni que no se disuelve y las demás especies (Ag, Au, Se, Pb...) van al barro.
- Lo que no se consume sale como chatarra. Si la corriente pide más ánodo del que entra, se
  consume entero y avisa.

**Cu2O.** Se disuelve químicamente: Cu2O + H2SO4 → CuSO4 + Cu + H2O, con el Cu al barro. Es el
cobre que se acumula en el electrolito y el ácido que se consume.

**Voltaje** = j·L/κ + contactos y placas + sobrepotencial neto.
- κ es el modelo **κER.2** de Kalliomäki et al. (2021, *Miner. Eng.* 171, 107069, CC BY,
  Tabla 4): log10 de mS/cm, con Cu, H2SO4, Ni, As, T y sus interacciones.
  - Se eligió antes de correr: es el mejor de los modelos que no piden las impurezas menores
    supuestas. En las naves del artículo tuvo pendiente de 0,87-0,89, contra 0,85 de κER.1.
- Contactos y placas: 60 mV, y sobrepotencial neto 0. Así lo trae la Tabla II del compendio
  IsaKidd 2020 para una refinería típica.
- Sin balance de calor.

**Purga y liberadoras.**
- Purga (m³/h) = Ni que gana el electrolito / límite de Ni.
- Corriente de las liberadoras = Cu que gana el electrolito × 2F / (M × eficiencia), menos el que
  ya sale por otra vía.

## Validación

Tolerancias fijadas antes de correr ([tests/test_er.py](../tests/test_er.py)):

| Prueba | Tolerancia | Resultado |
|---|---|---|
| κER.2 vs Fuentes, M3 a 54,4 y 60 °C (en rango) | ±5 % | **+9,8 y +7,2 % ✗** |
| κER.2 vs Fuentes, M3 a 48,9 y 71,1 °C | ±10 % | **+13,4 % ✗** y +2,7 % ✓ |
| κER.2 vs Fuentes, M4 (Cu 34,8 g/L, fuera de rango), 4 temperaturas | ±10 % | −5,0 a +3,8 % ✓ |
| Corte: falla si quedan fuera más de 4 de 8 | | **pasa (3 fuera)** |
| Mount Isa: eficiencia × disponibilidad implícita por Faraday | 0,85-0,98 | 0,911 ✓ (coherencia) |
| Caída en el electrolito vs Tabla II del compendio, por cosecha | ±30 % | **−32, −33 y −34 % ✗** (coherencia) |
| Voltaje total por cosecha dentro de 280-385 mV | | **209, 241 y 273 mV ✗** (coherencia) |
| Cierre por elemento, Faraday, Ni que desplaza Cu, Cu2O disuelto, reparto del ánodo | 1e-9 | sí |
| La purga calculada deja el Ni en el límite, en un circuito con reciclo | 1e-6 | sí |
| Las liberadoras retiran justo el Cu ganado: el electrolito vuelve igual | 1e-12 | sí |

Las mediciones de Fuentes (USM 2022, Tabla 4.24) son independientes del ajuste del modelo. Son
dos electrolitos de laboratorio sin Ni ni As:
- M3: 50 g/L Cu y 171 g/L de ácido.
- M4: 34,8 g/L Cu y 188 g/L de ácido.

## Hallazgos

1. **El modelo de refinación repite lo que el de electroobtención hizo con la misma muestra.**
   - Con M3 sobrestima entre 7 y 13 %, más cuanto más fría la muestra: su efecto de la
     temperatura es la mitad del medido.
   - Con M4 acierta a ±5 %, aun fuera de su rango de Cu.
   - Dos modelos ajustados por separado fallan igual en la misma muestra, así que el problema
     puede estar en M3 tanto como en los modelos.
2. **Mount Isa es coherente con Faraday.**
   - Con 1.320 celdas, 36 cátodos de 0,82 m² por cara y 305 A/m², la corriente da 240.700 t/año
     de Cu al 97,5 % de eficiencia, si no para nunca.
   - La capacidad de 225.000 t/año implica 93,5 % de disponibilidad: 6,5 % de tiempo parado.
   - Por Faraday, cada ánodo de 320 kg pierde 250 kg en su ciclo de 18 días: 22 % de chatarra.
3. **j·L/κ da un tercio menos de caída que la Tabla II del compendio.**
   - La distancia ánodo-cátodo sale de la geometría de Mount Isa:
     - paso de 100 mm;
     - ánodo de 320 kg sobre una cara de 0,82 m², adelgazando por Faraday;
     - placa de 3,25 mm y medio depósito.
     Da 26,5, 32,2 y 37,9 mm por cosecha.
   - Con el electrolito de la «Reference Tankhouse 3» (κ = 53,4 S/m), la caída es de 149, 181 y
     213 mV, contra 220, 270 y 320 en la Tabla II.
   - Para cuadrar haría falta κ = 36 S/m, o una resistencia extra: el barro adherido al ánodo,
     la capa límite o un sobrepotencial que la tabla no muestra.
   - La tabla es de una «refinería típica», sin su electrolito. Con lo publicado no se puede
     separar la causa.

## Ejemplo (ilustrativo)

| | |
|---|---|
| Corriente | 23,8 MA (1.320 celdas, 305 A/m²) |
| Cátodos | 27.474 kg/h, a 0,244 V y 211 kWh/t |
| Electrolito | gana 171,5 kg/h de Cu (Cu2O del ánodo) y 26,0 kg/h de Ni; pierde 265 kg/h de ácido |
| Purga para mantener 18,9 g/L de Ni | 1,37 m³/h |
| Liberadoras | 144 kA (el lazo de control), contra 170 kA si tuvieran que retirar todo el Cu ganado |

Las liberadoras necesitan menos que esos 170 kA porque la purga también saca Cu, y porque la meta
del lazo es la concentración del electrolito de retorno.

Supuestos del ejemplo:
- 20 L/min de electrolito por celda.
- Todo el O del ánodo como Cu2O.
- Todo el Ni al electrolito.
- Electrolito de la «Reference Tankhouse 3» (Kalliomäki 2021, Tabla 3).
- 85 % de eficiencia en las liberadoras.

## Mutaciones

Las 20 mutaciones del equipo hacen fallar las pruebas. Las 4 que sobrevivieron a la primera vuelta
mostraron pruebas que faltaban, y se agregaron:
- la caída óhmica calculada a mano;
- las concentraciones del electrolito;
- el Ni que va al barro;
- el Cu que ya sale por la purga.

## Límites

- El reparto de impurezas (As, Sb, Bi, Ag, Se...) **no está validado contra planta**: no hay un
  balance industrial abierto. Todo lo que no es Cu ni Ni va al barro. El As disuelto solo entra
  en la conductividad.
- Sin balance de calor, sin pasivación del ánodo, sin aditivos y sin distribución de corriente.
- El sobrepotencial neto es un parámetro (0 por defecto). No hay una fuente abierta de la cinética
  de refinación: con la constante cinética que se usa en electroobtención, la celda pasaría de
  0,6 V.
