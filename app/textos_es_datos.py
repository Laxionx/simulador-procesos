"""Textos en español de los datos de entrada (barra lateral y tabla «Qué datos necesita»)."""

T = {
    "sidebar.example": "Cargar ejemplo",
    "group.Flotación": "Flotación",
    "group.Electroobtención": "Electroobtención",
    "group.Horno flash": "Horno flash",
    "group.Convertidor": "Convertidor",
    "dato.help": "{meaning} Rango{unit}: {lo} a {hi}. En planta: {source}",
    "dato.range": "{lo} a {hi}",
    "blend": "Mezcla {n}",
    "unit.days": "días",
    "col.equipo": "Equipo",
    "col.dato": "Dato",
    "col.unit": "Unidad",
    "col.range": "Rango",
    "col.example": "Ejemplo",
    "col.what": "Qué es",
    "col.how": "Cómo se obtiene",
    "dato.cells.label": "Número de celdas",
    "dato.cells.meaning": (
        "Celdas de flotación en serie; el concentrado de cada una se suma al del banco."
    ),
    "dato.cells.source": "plano del banco.",
    "dato.tau.label": "Tiempo de residencia por celda (τ)",
    "dato.tau.meaning": "Tiempo medio que la pulpa pasa dentro de cada celda (mezcla perfecta).",
    "dato.tau.source": "prueba con trazador, o volumen útil de la celda entre el caudal de pulpa.",
    "dato.r_inf.label": "R∞ del Cu (calcopirita)",
    "dato.r_inf.meaning": "Recuperación máxima que alcanzaría el Cu con tiempo infinito.",
    "dato.r_inf.source": "se ajusta a la recuperación medida celda a celda del banco.",
    "dato.k.label": "k del Cu",
    "dato.k.meaning": "Constante cinética de primer orden: qué tan rápido flota el Cu.",
    "dato.k.source": (
        "se ajusta a la recuperación medida celda a celda, o a pruebas batch de laboratorio."
    ),
    "dato.gangue.label": "Recuperación fija de la ganga (SiO₂)",
    "dato.gangue.meaning": (
        "Parte de la ganga que llega al concentrado por arrastre, sin cinética. En el ejemplo es "
        "un supuesto, no una medida."
    ),
    "dato.gangue.source": "ensayes de ganga en concentrado y relave.",
    "dato.j.label": "Densidad de corriente",
    "dato.j.meaning": "Corriente por metro cuadrado de cátodo.",
    "dato.j.source": "corriente de la rectificadora entre el área catódica de la nave.",
    "dato.eff.label": "Eficiencia de corriente",
    "dato.eff.meaning": (
        "Parte de la corriente que deposita cobre; el resto se pierde en cortocircuitos y en el "
        "ciclo Fe³⁺/Fe²⁺."
    ),
    "dato.eff.source": "cobre cosechado entre el que da la ley de Faraday.",
    "dato.cu.label": "Cobre en el electrolito",
    "dato.cu.meaning": "Concentración de Cu²⁺ del electrolito que sale de la celda.",
    "dato.cu.source": "análisis del electrolito (absorción atómica).",
    "dato.acid.label": "Ácido sulfúrico",
    "dato.acid.meaning": "Concentración de H₂SO₄ del electrolito; más ácido, más conductor.",
    "dato.acid.source": "titulación del electrolito.",
    "dato.temp.label": "Temperatura",
    "dato.temp.meaning": "Temperatura del electrolito; más caliente, más conductor.",
    "dato.temp.source": "termocupla en la celda.",
    "dato.days.label": "Días del ciclo de cosecha",
    "dato.days.meaning": (
        "Tiempo que el cátodo queda en la celda antes de cosecharse. Dato operativo, no del "
        "modelo; el valor del ejemplo es un supuesto típico."
    ),
    "dato.days.source": "programa de cosecha de la nave.",
    "dato.area.label": "Área de una cara del cátodo",
    "dato.area.meaning": (
        "Área sumergida de una cara; el cátodo tiene dos. Dato operativo, no del modelo; el "
        "valor del ejemplo es un supuesto típico."
    ),
    "dato.area.source": "plano del cátodo.",
    "dato.blend.label": "Mezcla de concentrados",
    "dato.blend.meaning": (
        "Cuál de las cuatro mezclas de concentrado de Atlantic Copper (Huelva) se funde; cambia "
        "la mineralogía de la carga."
    ),
    "dato.blend.source": "análisis mineralógico de la carga del horno.",
    "dato.f_grade.label": "Ley de la mata",
    "dato.f_grade.meaning": (
        "Meta de cobre en la mata; la operación la fija con el oxígeno que se sopla."
    ),
    "dato.f_grade.source": "ensaye de la mata que sale del horno.",
    "dato.f_sio2.label": "SiO₂ de la escoria",
    "dato.f_sio2.meaning": "Meta de sílice en la escoria; define cuánto fundente se agrega.",
    "dato.f_sio2.source": "ensaye de la escoria.",
    "dato.f_loss.label": "Pérdida térmica del horno",
    "dato.f_loss.meaning": "Calor que el horno pierde por sus paredes, por tonelada de carga.",
    "dato.f_loss.source": "balance de calor de la planta o agua de enfriamiento.",
    "dato.f_temp.label": "Temperatura de los productos",
    "dato.f_temp.meaning": "Temperatura de la mata y la escoria que salen del horno.",
    "dato.f_temp.source": "termocupla o lanza de temperatura en el asentador.",
    "dato.c_grade.label": "Ley de la mata",
    "dato.c_grade.meaning": "Cobre de la mata que se carga al convertidor (100 t por carga).",
    "dato.c_grade.source": "ensaye de la mata del horno.",
    "dato.c_eff_slag.label": "Eficiencia de O₂, soplado a escoria",
    "dato.c_eff_slag.meaning": "Parte del oxígeno soplado que reacciona en el soplado a escoria.",
    "dato.c_eff_slag.source": (
        "oxígeno que reacciona (balance) entre el que se sopla (flujo de aire)."
    ),
    "dato.c_eff_copper.label": "Eficiencia de O₂, soplado a cobre",
    "dato.c_eff_copper.meaning": "Ídem, en el soplado a cobre.",
    "dato.c_eff_copper.source": (
        "oxígeno que reacciona (balance) entre el que se sopla (flujo de aire)."
    ),
    "dato.c_bath.label": "Temperatura del baño",
    "dato.c_bath.meaning": (
        "Temperatura del baño; solo cambia el balance de calor y la densidad del cobre."
    ),
    "dato.c_bath.source": "pirómetro óptico o termocupla de inmersión.",
}
