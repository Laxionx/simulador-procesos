"""Textos en español de la Guía, las fichas de cada equipo y el mapa de la ruta."""

T = {
    "ficha.label.hace": "**Qué hace.** {text}",
    "ficha.label.entra": "**Qué entra.** {text}",
    "ficha.label.sale": "**Qué devuelve.** {text}",
    "ficha.expander": "Qué datos necesita este equipo",
    "ficha.caption": "**De dónde salen las ecuaciones.** {autores} Detalle en [{doc}]({url}).",
    # ------------------------------------------------------------ fichas
    "ficha.Flotación.hace": (
        "Separa el mineral de cobre (calcopirita, CuFeS₂) de la ganga. Las burbujas suben "
        "cargadas de partículas hidrofóbicas y la espuma que rebasa de cada celda es el "
        "concentrado; lo que no flota sigue de celda en celda y sale como relave."
    ),
    "ficha.Flotación.entra": (
        "Pulpa de la alimentación del banco: CuFeS₂, SiO₂ (ganga) y agua. El ejemplo es el "
        "banco rougher A de Los Pelambres: unas 600 t/h de sólidos con 0,86 % de Cu."
    ),
    "ficha.Flotación.sale": (
        "Concentrado y relave. Por especie: recuperación al concentrado y t/h que aporta cada "
        "celda; del concentrado, la ley de Cu y las t/h."
    ),
    "ficha.Flotación.autores": (
        "Cinética de primer orden por especie y celdas de mezcla perfecta en serie "
        "(García-Zúñiga, 1935; Klimpel, 1980). Fórmulas de N celdas y datos medidos del banco: "
        "Vinnett, Pino-Muñoz, Yianatos, Díaz y Henríquez (2022), *Physicochem. Probl. Miner. "
        "Process.* 58(5), 152420. La recuperación fija de SiO₂ (5 %) y del agua (10 %) son "
        "supuestos del ejemplo, no medidas."
    ),
    "ficha.Flotación.doc": "docs/flotacion.md",
    "ficha.Electroobtención.hace": (
        "Deposita cobre metálico sobre cátodos a partir de un electrolito de sulfato de cobre; "
        "en los ánodos se desprende oxígeno. Calcula cuánto cobre se deposita y qué voltaje pide "
        "la celda."
    ),
    "ficha.Electroobtención.entra": (
        "Electrolito (Cu, ácido sulfúrico, temperatura) y la corriente: densidad de corriente "
        "por el área de las dos caras del cátodo."
    ),
    "ficha.Electroobtención.sale": (
        "Cobre depositado (kg por cátodo al cabo del ciclo, y su espesor), corriente, voltaje de "
        "celda por componentes, potencia y energía por tonelada de cobre."
    ),
    "ficha.Electroobtención.autores": (
        "Masa por la ley de Faraday con eficiencia de corriente. Voltaje de celda: Beukes y "
        "Badenhorst (2009), *J. South. Afr. Inst. Min. Metall.* 109 (potencial reversible y "
        "sobrepotenciales); conductividad del electrolito: Kalliomäki et al. (2021), *Miner. "
        "Eng.* 171, 107069; contactos y barras: Schlesinger et al. (2011), *Extractive "
        "Metallurgy of Copper*. Densidad del cobre sólido, 8,96 g/cm³: CRC Handbook of "
        "Chemistry and Physics."
    ),
    "ficha.Electroobtención.doc": "docs/ew.md",
    "ficha.Horno flash.hace": (
        "Funde el concentrado seco en el aire enriquecido con oxígeno que cae por la torre de "
        "reacción: el hierro y el azufre se oxidan, el calor de la reacción funde la carga y en "
        "el asentador se separan la mata (Cu₂S-FeS, abajo) y la escoria (encima). El azufre sale "
        "como SO₂."
    ),
    "ficha.Horno flash.entra": (
        "Una de las cuatro mezclas de concentrado de Atlantic Copper (Huelva), con metas de ley "
        "de mata, SiO₂ de la escoria y pérdida térmica; el modelo calcula el oxígeno, el "
        "enriquecimiento del aire y el fundente."
    ),
    "ficha.Horno flash.sale": (
        "Por tonelada de concentrado: kg de mata, de escoria y de SO₂, Nm³ de O₂ técnico, % de "
        "O₂ del aire y % de fundente. Del dibujo: volumen de cada capa (kg ÷ densidad)."
    ),
    "ficha.Horno flash.autores": (
        "Balance de masa y de calor con el esquema de Bacedoni, Moreno-Ventas y Ríos (2020), "
        "*Metals* 10(9) 1229 (mineralogía, reparto de Cu y Zn, operación industrial); contenido "
        "calórico de matas: González, Patiño y Salinas (2001), *Rev. Soc. Quím. Méx.* 45(1) 13. "
        "Densidades, solo para dibujar: Cu₂S 5,18 y FeS 3,80 g/cm³ (Nagamori, 1968, citado en "
        "Tesfaye Firdu y Taskinen, 2010, Aalto TKK-MT-215, Tabla 9), mezcla ideal para la mata "
        "(±10 %), escoria 3,7 g/cm³ (aprox.)."
    ),
    "ficha.Horno flash.doc": "docs/fusion.md",
    "ficha.Convertidor.hace": (
        "Convierte la mata en cobre soplando aire por las toberas. Primero el soplado a escoria "
        "oxida el hierro (con fundente de sílice forma la escoria) y deja metal blanco (Cu₂S); "
        "luego el soplado a cobre oxida el azufre y deja cobre blíster. Los dos sueltan SO₂."
    ),
    "ficha.Convertidor.entra": (
        "100 t de mata por carga, con su ley, y la eficiencia con que cada soplado aprovecha el "
        "oxígeno. El ejemplo usa parámetros públicos de Ilo (ilustrativo)."
    ),
    "ficha.Convertidor.sale": (
        "Por soplado: aire (Nm³), fundente, escoria, metal blanco o blíster y SO₂ (t). Del "
        "dibujo: el volumen de cada fase (t ÷ densidad) en tres estados del baño."
    ),
    "ficha.Convertidor.autores": (
        "Balance por elemento y de calor de cada soplado, con datos de Lennartsson (2013, tesis, "
        "Luleå), Kyllo (1995, tesis, UBC; eficiencias de Flin Flon) y Morales, Palacios y "
        "Sánchez (2004, Molten Slags VII; escoria de Ilo). Densidades, solo para dibujar: mata y "
        "metal blanco por mezcla ideal Cu₂S-FeS (Nagamori, 1968; ±10 %), blíster = cobre líquido "
        "(Assael et al., 2010, *J. Phys. Chem. Ref. Data* 39, 033105, ec. 1), escoria 3,7 g/cm³ "
        "(aprox.; la del convertidor, con magnetita, es más densa)."
    ),
    "ficha.Convertidor.doc": "docs/conversion.md",
    "limits.1": "Estado estacionario: el banco y la celda no cambian en el tiempo.",
    "limits.2": (
        "La alimentación de la flotación es fija (la del ejemplo de Los Pelambres); se cambian "
        "la cinética y la operación del banco. El horno flash funde las cuatro mezclas "
        "publicadas y el convertidor procesa 100 t de mata por carga."
    ),
    "limits.3": (
        "La celda de electroobtención se calcula para un cátodo con electrolito de composición "
        "fija; el depósito crece de forma pareja (sin nódulos ni dendritas)."
    ),
    "limits.4": (
        "Las animaciones son esquemas: la posición de burbujas, el arrastre de la ganga, las "
        "burbujas de O₂ y el número de placas son ilustrativos. Cada esquema dice qué parte sale "
        "del cálculo."
    ),
    # ------------------------------------------------------------ guía
    "guide.h.simula": "### Qué simula",
    "guide.simula": (
        "Equipos de una planta de cobre, con **animaciones que salen del cálculo**: no son "
        "dibujos sueltos. Cada esquema se arma con las toneladas, las velocidades y los "
        "espesores que calcula el simulador (`procesos`, ecuaciones publicadas), y mueve las "
        "burbujas, la espuma y el depósito según esos números. Cambia un dato en la barra "
        "lateral y el esquema cambia."
    ),
    "guide.h.ruta": "### El recorrido del concentrado al cátodo",
    "guide.ruta.alt": "Mapa del recorrido al cátodo de cobre",
    "guide.ruta": (
        "- **Animados aquí:** Flotación, Horno flash, Convertidor y Electroobtención (pestañas "
        "de arriba).\n"
        "- **Molienda:** tiene su propia app animada, [simulador de conminución]({conminucion}).\n"
        "- **En el simulador, sin animación todavía:** horno de ánodos, electrorrefinación, "
        "lixiviación y extracción por solventes (en el [repositorio]({repo}))."
    ),
    "guide.h.leer": "### Cómo leer un esquema",
    "guide.leer": (
        "Cada esquema dice, debajo, qué parte sale del cálculo y qué parte es ilustrativa. Lo "
        "que sale del cálculo se puede comprobar en los números de al lado. Si tu sistema pide "
        "«reducir movimiento», verás la versión quieta; también hay un interruptor."
    ),
    "guide.h.datos": "### Qué datos necesita",
    "guide.datos": (
        "Cada dato tiene una ayuda (**?**) en la barra lateral. El botón **Cargar ejemplo** pone "
        "todos los valores de la columna «Ejemplo»."
    ),
    "guide.h.limites": "### Lo que no hace",
    # ------------------------------------------------------------ mapa de la ruta
    "route.title": "Del mineral al cátodo de cobre: mapa de los equipos",
    "route.pyro": "Ruta pirometalúrgica (concentrado de sulfuros)",
    "route.hydro": "Ruta hidrometalúrgica (mineral lixiviable)",
    "route.note": "Mapa estático, sin números. Bronce: animado en esta app.",
    "route.label": "Mapa del recorrido del concentrado al cátodo de cobre",
    "route.step.Molienda": "Molienda",
    "route.step.Flotación": "Flotación",
    "route.step.Fusión flash": "Fusión flash",
    "route.step.Conversión": "Conversión",
    "route.step.Ánodos": "Ánodos",
    "route.step.Electrorrefinación": "Electrorrefinación",
    "route.step.Mineral oxidado (chancado)": "Mineral oxidado (chancado)",
    "route.step.Lixiviación": "Lixiviación",
    "route.step.Extracción por solventes": "Extracción por solventes",
    "route.step.Electroobtención": "Electroobtención",
    "route.step.Cátodo de Cu": "Cátodo de Cu",
    "route.state.animado": "animado",
    "route.state.otra app": "otra app",
    "route.state.próximamente": "próximamente",
    "route.state.en el repo": "en el repo",
    "route.state.materia prima": "materia prima",
}
