"""Textos en español de las pestañas de cada equipo y de sus gráficos."""

T = {
    "page.title": "Simulador de planta de cobre",
    "app.title": "Simulador de planta de cobre",
    "app.caption": (
        "Equipos animados según su cálculo real, desde ecuaciones publicadas. Empieza por la "
        "**Guía**; los datos se cambian en la barra lateral."
    ),
    "err.generic": "Algo falló al calcular. Prueba con otros datos o recarga la página.",
    "toggle.label": "Mover los equipos",
    "toggle.help": (
        "Apaga las animaciones de los esquemas. También se apagan solas si el sistema tiene "
        "activado «reducir movimiento»."
    ),
    "tab.guide": "Guía",
    # ------------------------------------------------------------ flotación
    "flot.err": "No se pudo calcular el banco con estos datos: {exc}",
    "flot.m1": "Recuperación de Cu (CuFeS₂)",
    "flot.m2": "Recuperación de SiO₂ (supuesto)",
    "flot.m3": "Concentrado (t/h de sólidos)",
    "flot.m4": "Ley de Cu del concentrado",
    "flot.alt": "Banco de flotación con celdas en serie",
    "flot.cap1": (
        "Las burbujas cargadas de Cu suben al ritmo de su constante cinética k. La espuma de "
        "cada celda es tan gruesa como los t/h de sólidos que manda al concentrado. La SiO₂ y "
        "el agua no tienen cinética en el modelo: solo se conoce su recuperación total, y se "
        "reparte pareja entre celdas (supuesto del ejemplo)."
    ),
    "flot.cap2": (
        "Los puntos medidos son los del banco A de Los Pelambres (9 celdas, τ de 4,1 min): solo "
        "se comparan con el modelo si los datos son los del ejemplo."
    ),
    "flot.col.cell": "Celda",
    "flot.col.cu": "CuFeS₂ al concentrado (t/h)",
    "flot.col.sio2": "SiO₂ al concentrado (t/h)",
    "flot.col.water": "Agua al concentrado (t/h)",
    "flot.col.cum": "Cu recuperado acumulado (%)",
    "flot.cap3": "La suma de cada columna por celda es lo que el modelo da para el banco entero.",
    # ------------------------------------------------------------ electroobtención
    "ew.err": "No se pudo calcular la celda con estos datos: {exc}",
    "ew.m1": "Corriente (un cátodo)",
    "ew.m2": "Voltaje de celda",
    "ew.m3": "Potencia (un cátodo)",
    "ew.m4": "Energía específica",
    "ew.alt": "Celda de electroobtención con cátodos que engordan",
    "ew.cap": (
        "Cada cátodo termina el ciclo con **{kg} kg** de cobre y **{mm} mm** por cara (Faraday "
        "× eficiencia; espesor = masa ÷ (densidad del Cu × área de las dos caras)). El dibujo "
        "exagera el espesor; los números son los reales."
    ),
    # ------------------------------------------------------------ horno flash
    "flash.err": "No se pudo calcular el horno con estos datos: {exc}",
    "flash.m1": "Mata (kg/t de concentrado)",
    "flash.m2": "Escoria (kg/t)",
    "flash.m3": "O₂ técnico (Nm³/t)",
    "flash.m4": "SO₂ (kg/t)",
    "flash.alt": "Horno flash con torre de reacción y asentador",
    "flash.cap": (
        "Mata: {matte_m3} m³ por t de concentrado; escoria: {slag_m3} m³. El alto de cada capa "
        "es proporcional a ese volumen (kg ÷ densidad). Densidades de dibujo: mata 4,8 g/cm³ "
        "por mezcla ideal (±10 %), escoria 3,7 g/cm³ (aprox.)."
    ),
    "flash.head": "**Modelo frente a la planta** (mezcla {blend}, Bacedoni et al. 2020)",
    "flash.row.o2": "Consumo de O₂ (Nm³/t)",
    "flash.row.air": "O₂ en el aire (% vol.)",
    "flash.row.flux": "Fundente (% de la carga)",
    "flash.col.this": "Este cálculo",
    "flash.col.paper": "Modelo del artículo (Tabla 14)",
    "flash.col.plant": "Planta (Tabla 13)",
    "flash.cap2": (
        "La planta operó esta mezcla con mata de {grade} % Cu, {sio2} % de SiO₂ en la escoria y "
        "{loss} MJ/t de pérdida; los controles no cambian solos al elegir la mezcla. El modelo "
        "del artículo tampoco iguala el consumo de O₂ medido."
    ),
    # ------------------------------------------------------------ convertidor
    "conv.err": "No se pudo calcular el convertidor con estos datos: {exc}",
    "conv.m1": "Aire total (Nm³ por 100 t de mata)",
    "conv.m2": "Fundente (t)",
    "conv.m3": "Blíster (t)",
    "conv.m4": "SO₂ (t)",
    "conv.alt": "Convertidor Peirce-Smith en corte transversal",
    "conv.cap": (
        "Volumen del baño: {charge} m³ de mata al cargar; {slag_end} m³ al fin del soplado a "
        "escoria ({white} de metal blanco y {slag} de escoria); {cu_end} m³ al fin del soplado "
        "a cobre ({blister} de blíster y {slag2} de escoria)."
    ),
    "conv.cap2": "Cada soplado cierra por masa: lo que entra, con el O₂ que reacciona, es lo que sale.",
    # ------------------------------------------------------------ gráficos
    "plot.rec.model": "modelo (primer orden, mezcla perfecta)",
    "plot.rec.measured": "medido, Vinnett et al. 2022 (banco A)",
    "plot.rec.title": "Recuperación acumulada de Cu por celda",
    "plot.rec.x": "Celda",
    "plot.rec.y": "Cu recuperado acumulado (%)",
    "plot.volt.cell": "Celda",
    "plot.volt.total": "Total: {v} V",
    "plot.volt.title": "De qué se compone el voltaje de la celda",
    "plot.volt.x": "Voltaje (V)",
    "plot.conv.title": "Qué entra y qué sale de cada soplado (t)",
    "plot.conv.y": "Toneladas por 100 t de mata",
}
