"""Textos en español de los esquemas animados (los rótulos que van DENTRO de cada SVG)."""

T = {
    "scheme.note": "esquema, no a escala: las cantidades sí son del cálculo",
    "scheme.temp": "color ilustrativo de la temperatura",
    # ------------------------------------------------------------ flotación
    "svg.flot.title": "Banco de flotación: {n} celdas en serie",
    "svg.flot.sub": "Recuperación de Cu: {rec} %  ·  concentrado: {conc} t/h  ·  ley: {grade} % Cu",
    "svg.flot.label": "Banco de flotación en serie con burbujas y espuma",
    "svg.flot.legend1": "CuFeS₂: ritmo de las burbujas ∝ k; las que llevan Cu, ∝ t/h de la celda",
    "svg.flot.legend2": "SiO₂: arrastre fijo, supuesto del ejemplo; reparto parejo entre celdas",
    "svg.flot.ilus": (
        "Posición y velocidad absoluta de las burbujas, tamaño de las celdas y ritmo de la "
        "ganga: ilustrativos, solo cambia el dibujo."
    ),
    "svg.flot.froth": "Alto de la espuma ∝ t/h de sólidos (la mayor: {top} t/h)",
    "svg.flot.feed": "Alimentación",
    "svg.flot.tails": "Relave",
    "svg.flot.conc": "Concentrado →",
    "svg.flot.th": "t/h",
    "svg.flot.cell": "celda",
    "svg.flot.cuacc": "Cu acum.",
    # ------------------------------------------------------------ horno flash
    "svg.flash.title": "Horno flash de cobre",
    "svg.flash.label": "Horno flash con torre de reacción y asentador",
    "svg.flash.slag": "escoria",
    "svg.flash.matte": "mata",
    "svg.flash.conc": "concentrado",
    "svg.flash.o2": "O₂ técnico {v} Nm³/t",
    "svg.flash.gas": "gases: SO₂ {v} kg/t",
    "svg.flash.p.matte": "Mata",
    "svg.flash.p.slag": "Escoria",
    "svg.flash.p.enrich": "Enriquecimiento",
    "svg.flash.kg_t": "{v} kg/t",
    "svg.flash.m3_t": "{v} m³/t",
    "svg.flash.o2_pct": "{v} % O₂",
    "svg.flash.flux": "fundente {v} %",
    "svg.flash.legend1": (
        "Alto de capa ∝ volumen por t de concentrado (kg/t ÷ densidad): {px} px por m³/t, "
        "misma sección. Densidad de la mata {matte} g/cm³ (±10 %), escoria {slag} g/cm³ "
        "(aprox.)."
    ),
    "svg.flash.legend2": (
        "Grosor de las flechas de O₂ y de gases, y rapidez de sus rayitas, ∝ caudal calculado. "
        "Color de las capas: {note} de los productos ({temp} °C)."
    ),
    "svg.flash.ilus": (
        "Partículas de la torre (ritmo fijo), flecha del concentrado (grosor y rapidez fijos) y "
        "forma del horno: ilustrativas, solo cambia el dibujo."
    ),
    # ------------------------------------------------------------ convertidor
    "svg.conv.title": "Convertidor Peirce-Smith, corte transversal",
    "svg.conv.label": "Convertidor Peirce-Smith con baño de mata, metal y escoria",
    "svg.conv.state": "{i} · {name}",
    "svg.conv.lower": "{name}: {t} t, {rho} g/cm³, {m3} m³",
    "svg.conv.slag": "escoria: {t} t, {m3} m³",
    "svg.conv.noslag": "sin escoria todavía",
    "svg.conv.blow": "soplado: {air} Nm³ de aire, {so2} t de SO₂",
    "svg.conv.noblow": "antes de soplar",
    "svg.conv.paused": "Fin del soplado a escoria (estado 2 de 3)",
    "svg.conv.stateof": "Estado {i} de 3: {name}",
    "svg.conv.legend1": (
        "Área del baño ∝ volumen de cada fase (t ÷ densidad): {px} px² por m³. Mata y metal "
        "blanco por mezcla ideal Cu₂S-FeS (±10 %); blíster = Cu líquido; escoria 3,7 g/cm³ "
        "(aprox.: la del convertidor, con magnetita, es más densa)."
    ),
    "svg.conv.legend2": (
        "El bucle de {cycle} s pasa por tres estados del cálculo. La transición entre "
        "estados, las burbujas de las toberas y la forma son ilustrativas: solo cambia el dibujo. "
        "Grosor del aire ∝ Nm³ y del SO₂ ∝ t de cada soplado. Color: {note} del baño ({temp} °C)."
    ),
    # ------------------------------------------------------------ electroobtención
    "svg.ew.title": "Celda de electroobtención en corte",
    "svg.ew.label": "Celda de electroobtención con cátodos que engordan",
    "svg.ew.sub": "Cu {cu} g/L · H₂SO₄ {acid} g/L · {temp} °C · {j} A/m² · eficiencia {eff} %",
    "svg.ew.anode": "ánodo",
    "svg.ew.cathode": "cátodo",
    "svg.ew.p.cathode": "Cátodo al final del ciclo",
    "svg.ew.p.thickness": "Espesor por cara",
    "svg.ew.days": "{n} días",
    "svg.ew.day": "{n} día(s)",
    "svg.ew.legend1": (
        "Ciclo de cosecha de {days} comprimido en {cycle} s; depósito dibujado con {px} px por "
        "mm real (exagerado: solo cambia el dibujo). Celeste: electrolito."
    ),
    "svg.ew.legend2": (
        "Burbujas de O₂ en los ánodos y número de placas (6 ánodos y 5 cátodos): ilustrativas, "
        "solo cambia el dibujo."
    ),
}
