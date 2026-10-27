"""Textos en español de los indicadores nuevos, el panel «Estado de la operación», los casos
publicados y «Prueba esto» de las pestañas de equipo. Cada chequeo lleva su criterio y su fuente en
la clave `*.crit.*` (es la ayuda de su línea en el panel)."""

T = {
    "estado.nivel.ok": "En rango",
    "estado.nivel.aviso": "Aviso",
    "estado.nivel.mal": "Problema",
    "estado.todo_ok": "Operación dentro de rango.",
    "estado.ver": "Ver los {n} chequeos en rango",
    "estado.h": "#### Estado de la operación",
    "prueba.h": "#### Prueba esto",
    "prueba.intro": (
        "Experimentos desde el **ejemplo de la barra lateral**; los números los calcula el modelo "
        "en vivo. El botón pone el cambio en los datos de la barra lateral."
    ),
    "prueba.aplicar": "Aplicar este cambio a los controles",
    "prueba.restablecer": "Volver al ejemplo",
    "casos.h": "#### Casos publicados",
    # ------------------------------------------------------------ indicadores
    "flot.l1": "Recuperación de Cu",
    "flot.l2": "Recuperación de SiO₂",
    "flot.l3": "Concentrado (t/h)",
    "flot.l4": "Ley de Cu (conc.)",
    "flot.l5": "Cu al relave (t/h)",
    "flot.m5": "CuFeS₂ que se va al relave (t/h): alimentación × (1 − recuperación).",
    "flot.l6": "Enriquecimiento",
    "flot.m6": "Ley de Cu del concentrado ÷ ley de Cu de la alimentación (veces).",
    "flash.l1": "Mata (kg/t)",
    "flash.l5": "O₂ del aire (% vol.)",
    "flash.m5": "O₂ del aire de proceso (enriquecimiento), en % del volumen.",
    "flash.l6": "Fundente (% carga)",
    "flash.m6": "Fundente (SiO₂ agregada) en % de la carga seca.",
    "conv.l1": "Aire total (Nm³)",
    "conv.l5": "Metal blanco (t)",
    "conv.m5": "Metal blanco (Cu₂S) al fin del soplado a escoria, por 100 t de mata.",
    "conv.l6": "Escoria total (t)",
    "conv.m6": "Escoria de los dos soplados, por 100 t de mata.",
    "ew.l4": "Energía (kWh/t)",
    "ew.l5": "Cobre por cátodo (kg)",
    "ew.m5": "Masa de cobre depositada en un cátodo al final del ciclo de cosecha.",
    "ew.l6": "Espesor por cara (mm)",
    "ew.m6": "Espesor del depósito de cobre en cada cara del cátodo al final del ciclo.",
    # ------------------------------------------------------------ flotación: panel y caso
    "flot.chk.cierre": (
        "Balance de masa por especie: la suma celda a celda es el total del modelo (error "
        "relativo {err}; tolerancia {tol})."
    ),
    "flot.crit.cierre": (
        "Problema si la suma por celda de CuFeS₂, SiO₂ y agua no es la alimentación × la "
        "recuperación del banco. Es la definición del balance (docs/flotacion.md, «Modelo»)."
    ),
    "flot.chk.rinf": "La recuperación de Cu ({rec} %) no pasa de R∞ ({rinf} %).",
    "flot.crit.rinf": (
        "Problema si la recuperación supera a R∞. En primer orden, R = R∞·(1 − (1 + kτ)^−N) "
        "(docs/flotacion.md, «Modelo»), que nunca pasa de R∞."
    ),
    "flot.casos.intro": (
        "Pone en la barra lateral los datos de un banco rougher de Los Pelambres (Vinnett et al. "
        "2022, Tabla 3: celdas, τ, R∞ y k; la ganga vuelve a 5 %). Mientras no los cambies, "
        "más abajo se compara el modelo con la recuperación medida celda a celda."
    ),
    "flot.caso.A": "Banco A (9 celdas, τ 4,1 min)",
    "flot.caso.B": "Banco B (6 celdas, τ 6,4 min)",
    "flot.cmp.titulo": "**Banco {banco} frente a lo medido** (Vinnett et al. 2022, Tabla {tabla})",
    "flot.cmp.celda": "Celda",
    "flot.cmp.modelo": "Modelo (% de Cu)",
    "flot.cmp.medido": "Medido (% de Cu)",
    "flot.cmp.dpuntos": "Δ (puntos)",
    "flot.cmp.dpct": "Δ relativo (%)",
    "flot.cmp.nota": "Error cuadrático medio del modelo contra lo medido: {rmse} puntos.",
    "flot.cmp.nota.B": (
        " La alimentación del dibujo (t/h) sigue siendo la del banco A: del banco B solo se "
        "compara la recuperación, que no depende del caudal."
    ),
    "plot.rec.measured_b": "medido, Vinnett et al. 2022 (banco B)",
    # ------------------------------------------------------------ horno flash: panel y caso
    "flash.chk.elementos": (
        "Balance por elemento (Cu, Fe, Zn, S, O, Si): lo que entra es lo que sale (error máximo "
        "{err} kmol/t; tolerancia {tol})."
    ),
    "flash.crit.elementos": (
        "Problema si algún elemento no cierra. Es la definición del balance (docs/fusion.md, "
        "«Validación»: cierre por elemento, 1e-9 kmol)."
    ),
    "flash.chk.calor": (
        "Balance de calor: entra = sale + pérdida del horno (error {err} MJ/t; tolerancia {tol})."
    ),
    "flash.crit.calor": (
        "Problema si el calor no cierra. Es la definición del balance (docs/fusion.md, "
        "«Validación»: cierre de calor, 1e-6 MJ/t)."
    ),
    "flash.chk.metas": (
        "La mata y la escoria salen con la ley y la SiO₂ pedidas (error máximo {err} puntos; "
        "tolerancia {tol})."
    ),
    "flash.crit.metas": (
        "Problema si la ley de mata o la SiO₂ de la escoria calculadas no son las metas "
        "(docs/fusion.md, «Validación»: metas cumplidas, 1e-9)."
    ),
    "flash.chk.cobertura.ok": (
        "Ley de la mata, SiO₂ de la escoria y pérdida térmica dentro de lo que cubre la "
        "operación publicada (mata {grade_lo} a {grade_hi} %, SiO₂ {sio2_lo} a {sio2_hi} %, "
        "pérdida {loss_lo} a {loss_hi} MJ/t)."
    ),
    "flash.chk.cobertura.fuera": (
        "Fuera de lo que cubre la operación publicada: {lista} (mata {grade_lo} a {grade_hi} %, "
        "SiO₂ {sio2_lo} a {sio2_hi} %, pérdida {loss_lo} a {loss_hi} MJ/t). El modelo sigue "
        "calculando, pero sin una planta publicada que lo respalde."
    ),
    "flash.crit.cobertura": (
        "Aviso si la ley de mata, la SiO₂ de la escoria o la pérdida térmica salen del rango de "
        "las cuatro mezclas de Atlantic Copper (Bacedoni et al. 2020, Tabla 13; "
        "procesos/fusion_datos.py, INDUSTRIAL). Los coeficientes de reparto son los de FactSage "
        "para una mata de 62 % y una escoria de 29 % de SiO₂ (docs/fusion.md, «Límites»)."
    ),
    "flash.var.grade": "ley de la mata",
    "flash.var.sio2": "SiO₂ de la escoria",
    "flash.var.loss": "pérdida térmica",
    "flash.chk.temp": (
        "Temperatura de los productos: {temp} °C; los coeficientes de reparto del modelo son de "
        "{ref} °C."
    ),
    "flash.crit.temp": (
        "Aviso si no son 1.300 °C: los coeficientes de distribución son los de FactSage a 1.300 "
        "°C y todos los productos salen a la misma temperatura (docs/fusion.md, «Modelo» y "
        "«Límites»)."
    ),
    "flash.casos.intro": (
        "Pone en la barra lateral la mezcla y su operación medida en Atlantic Copper (Bacedoni et "
        "al. 2020, Tabla 13): ley de mata, SiO₂ de la escoria y pérdida térmica. Mientras no los "
        "cambies, más abajo se compara el cálculo con la planta."
    ),
    "flash.caso": "Mezcla {n}",
    "flash.caso.help": "Mezcla {n}: pone en la barra lateral su operación en la planta (Tabla 13).",
    "flash.cmp.titulo": "**Mezcla {n} frente a la planta** (Tabla 13)",
    "flash.cmp.mag": "Magnitud",
    "flash.cmp.este": "Este cálculo",
    "flash.cmp.planta": "Planta (Tabla 13)",
    "flash.cmp.dpct": "Δ relativo (%)",
    "flash.cmp.tol": "Tolerancia del repo",
    "flash.cmp.dentro": "¿Dentro?",
    "flash.cmp.si": "dentro",
    "flash.cmp.no": "fuera",
    "flash.tol.oc": "±10 % relativo",
    "flash.tol.o2": "±5 puntos",
    "flash.tol.fundente": "±2 puntos",
    "flash.cmp.nota": (
        "Δ relativo (%) es la diferencia respecto de la planta. En puntos: O₂ del aire {o2} y fundente "
        "{fl}."
    ),
    # ------------------------------------------------------------ convertidor: panel
    "conv.chk.elementos": (
        "Balance por elemento (Cu, Fe, S, O) de los dos soplados: error máximo {err} kmol; "
        "tolerancia {tol}."
    ),
    "conv.crit.elementos": (
        "Problema si algún elemento no cierra. Es la definición del balance (docs/conversion.md, "
        "«Validación»: cierre por elemento, 1e-9)."
    ),
    "conv.chk.masa": (
        "Balance de masa de cada soplado: lo que entra, con el O₂ que reacciona, es lo que sale "
        "(error relativo máximo {err}; tolerancia {tol})."
    ),
    "conv.crit.masa": (
        "Problema si la masa de un soplado no cierra: mata + fundente + O₂ = metal blanco + "
        "escoria + SO₂ en el soplado a escoria, y lo análogo en el soplado a cobre. Son las "
        "cifras del gráfico de balance."
    ),
    "conv.chk.eficiencia.ok": (
        "Eficiencias de O₂ dentro de lo medido en Flin Flon: soplado a escoria {lo_e} a {hi_e} "
        "%, soplado a cobre {lo_c} a {hi_c} %."
    ),
    "conv.chk.eficiencia.fuera": (
        "Eficiencia de O₂ fuera de lo medido en Flin Flon ({lista}). Medido: soplado a escoria "
        "{lo_e} a {hi_e} %, soplado a cobre {lo_c} a {hi_c} %. La eficiencia es un dato de la "
        "planta: el modelo no la predice."
    ),
    "conv.crit.eficiencia": (
        "Aviso si una eficiencia sale del rango medido en Flin Flon: 55 a 68 % en los soplados a "
        "escoria y 72 a 82 % en el de cobre (Kyllo 1995, Tablas IV-XII; docs/conversion.md, "
        "«Límites»)."
    ),
    "conv.var.escoria": "soplado a escoria",
    "conv.var.cobre": "soplado a cobre",
    # ------------------------------------------------------------ electroobtención: panel
    "ew.chk.sin_avisos": (
        "El modelo no emitió avisos: el electrolito está dentro del rango de la correlación de "
        "conductividad."
    ),
    "ew.crit.avisos": (
        "Aviso si el modelo extrapola la correlación de conductividad (Kalliomäki et al. 2021; "
        "docs/ew.md, «Hallazgos y límites»). Cada aviso dice el rango exacto."
    ),
    "ew.chk.faraday": (
        "Cobre por cátodo: {kg} kg, la ley de Faraday (error relativo {err}; tolerancia {tol})."
    ),
    "ew.crit.faraday": (
        "Problema si la masa del cátodo se aparta de la ley de Faraday: eficiencia × j × área × "
        "t × M/(2F) (docs/ew.md, «Validación»: cátodo = Faraday, 1e-9). Falla, por ejemplo, si "
        "la corriente pide más cobre del que trae el electrolito."
    ),
    "ew.chk.voltaje": (
        "Voltaje de celda {v} V; rango de una celda típica de electroobtención de cobre: {lo} a "
        "{hi} V."
    ),
    "ew.crit.voltaje": (
        "Aviso si el voltaje sale de 1,9 a 2,3 V, el rango de una celda típica (Beukes y "
        "Badenhorst 2009; docs/ew.md, «Validación»). Es una referencia de la industria, no un "
        "límite del modelo: se verificó con 40 g/L de Cu, 170 g/L de ácido, 50 °C y 300 A/m²."
    ),
    # ------------------------------------------------------------ Prueba esto
    "exp.flot.celdas.titulo": "Menos celdas en serie",
    "exp.flot.celdas.texto": (
        "Con {cells1} celdas en vez de {cells0}, el Cu tiene menos tiempo para flotar: la "
        "recuperación baja de {rec0} a {rec1} %, el relave se lleva {relave1} t/h de CuFeS₂ en "
        "vez de {relave0} y el concentrado sale con {ley1} % de Cu en vez de {ley0} %: pierde "
        "Cu, pero la ganga que arrastra es la misma."
    ),
    "exp.flot.saturado.titulo": "Más tiempo en cada celda",
    "exp.flot.saturado.texto": (
        "Con τ de {tau1} min en vez de {tau0} min por celda, la recuperación pasa de {rec0} a "
        "{rec1} %: solo {recd} puntos más, porque el banco del ejemplo ya está casi en su "
        "máximo (R∞). Compáralo con acortar el banco, donde sí se pierde recuperación."
    ),
    "exp.flot.ganga.titulo": "Más arrastre de ganga",
    "exp.flot.ganga.texto": (
        "Con {gangue1} % de la ganga al concentrado en vez de {gangue0} %, la recuperación de Cu "
        "no cambia ({rec0} %), pero el concentrado sube de {conc0} a {conc1} t/h y su ley baja "
        "de {ley0} a {ley1} % de Cu: es dilución, no pérdida de cobre."
    ),
    "exp.flash.mata.titulo": "Subir la ley de la mata",
    "exp.flash.mata.texto": (
        "Con mata de {f_grade1} % de Cu en vez de {f_grade0} %, hay que oxidar más hierro y "
        "azufre: el O₂ técnico sube de {oc0} a {oc1} Nm³/t, el aire se enriquece menos ({enr0} "
        "a {enr1} % de O₂), la mata baja de {mata0} a {mata1} kg/t y el SO₂ sube de {so20} a "
        "{so21} kg/t. El panel sigue en rango: {f_grade1} % está dentro de la operación "
        "publicada."
    ),
    "exp.flash.perdida.titulo": "Subir la pérdida térmica",
    "exp.flash.perdida.texto": (
        "Con {f_loss1} MJ/t de pérdida en vez de {f_loss0}, el horno necesita más calor: el O₂ "
        "técnico no cambia ({oc0} Nm³/t) ni el fundente ({fund0} %), pero el aire se enriquece "
        "más, de {enr0} a {enr1} % de O₂. El panel da **aviso**: {f_loss1} MJ/t está fuera de "
        "lo que cubre la operación publicada."
    ),
    "exp.flash.silice.titulo": "Subir la SiO₂ de la escoria",
    "exp.flash.silice.texto": (
        "Con {f_sio21} % de SiO₂ en la escoria en vez de {f_sio20} %, se agrega más fundente: "
        "sube de {fund0} a {fund1} % de la carga y la escoria de {esc0} a {esc1} kg/t. {f_sio21} "
        "% es el tope de lo publicado: el panel sigue en rango, pero un poco más arriba ya "
        "avisaría."
    ),
    "exp.conv.mata.titulo": "Subir la ley de la mata",
    "exp.conv.mata.texto": (
        "Con mata de {c_grade1} % de Cu en vez de {c_grade0} %, hay menos hierro y azufre que "
        "oxidar: el aire total baja de {aire0} a {aire1} Nm³, el fundente de {fund0} a {fund1} t "
        "y el SO₂ de {so20} a {so21} t, y el blíster sube de {blis0} a {blis1} t."
    ),
    "exp.conv.eficiencia.titulo": "Aprovechar peor el oxígeno",
    "exp.conv.eficiencia.texto": (
        "Con {c_eff_slag1} % de eficiencia de O₂ en el soplado a escoria en vez de {c_eff_slag0} "
        "%, hace falta más aire: el aire total sube de {aire0} a {aire1} Nm³, pero el blíster "
        "({blis0} t), el fundente ({fund0} t) y el SO₂ ({so20} t) no cambian: la eficiencia solo "
        "cambia el aire. El panel da **aviso**: {c_eff_slag1} % está bajo lo medido en Flin "
        "Flon."
    ),
    "exp.conv.bano.titulo": "Calentar el baño",
    "exp.conv.bano.texto": (
        "Con el baño a {c_bath1} °C en vez de {c_bath0} °C, el aire ({aire0} Nm³) y el blíster "
        "({blis0} t) no cambian: la temperatura solo entra al balance de calor y a la densidad "
        "del cobre. El cobre caliente es menos denso y su volumen sube de {m30} a {m31} m³."
    ),
    "exp.ew.corriente.titulo": "Subir la densidad de corriente",
    "exp.ew.corriente.texto": (
        "Con {j1} A/m² en vez de {j0}, el cátodo termina el ciclo con {kg1} kg en vez de {kg0} "
        "(+{kgp} %) y {mm1} mm por cara en vez de {mm0}; pero la celda pide más voltaje, de {v0} "
        "a {v1} V, y cada tonelada de cobre cuesta más energía: de {kwh0} a {kwh1} kWh/t."
    ),
    "exp.ew.eficiencia.titulo": "Bajar la eficiencia de corriente",
    "exp.ew.eficiencia.texto": (
        "Con {eff1} % de eficiencia en vez de {eff0} %, el cátodo deposita {kg1} kg en vez de "
        "{kg0}. El voltaje de celda no cambia ({v0} V), pero la energía por tonelada sube de "
        "{kwh0} a {kwh1} kWh/t: la misma electricidad deposita menos cobre."
    ),
    "exp.ew.temp.titulo": "Enfriar el electrolito",
    "exp.ew.temp.texto": (
        "Con {temp1} °C en vez de {temp0} °C, el electrolito conduce menos y el voltaje sube de "
        "{v0} a {v1} V; el cobre depositado no cambia ({kg0} kg). El panel da **aviso**: "
        "{temp1} °C está fuera del rango de la correlación de conductividad, y el modelo lo "
        "dice."
    ),
}
