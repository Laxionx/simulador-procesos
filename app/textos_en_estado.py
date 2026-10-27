"""English texts of the new indicators, the "Operating state" panel, the published cases and
"Try this" of the equipment tabs. Each check carries its criterion and source in its `*.crit.*`
key (it is the help of its line in the panel)."""

T = {
    "estado.nivel.ok": "In range",
    "estado.nivel.aviso": "Warning",
    "estado.nivel.mal": "Problem",
    "estado.todo_ok": "Operation within range.",
    "estado.ver": "Show the {n} checks in range",
    "estado.ver1": "Show the check in range",
    "estado.h": "#### Operating state",
    "prueba.h": "#### Try this",
    "prueba.intro": (
        "Experiments from the **sidebar example**; the model computes the numbers live. The "
        "button puts the change into the sidebar inputs."
    ),
    "prueba.aplicar": "Apply this change to the controls",
    "prueba.restablecer": "Back to the example",
    "casos.h": "#### Published cases",
    # ------------------------------------------------------------ indicators
    "flot.l1": "Cu recovery",
    "flot.l2": "SiO₂ recovery",
    "flot.l3": "Concentrate (t/h)",
    "flot.l4": "Cu grade (conc.)",
    "flot.l5": "Cu to tailings (t/h)",
    "flot.m5": "CuFeS₂ that goes to the tailings (t/h): feed × (1 − recovery).",
    "flot.l6": "Enrichment",
    "flot.m6": "Cu grade of the concentrate ÷ Cu grade of the feed (times).",
    "flash.l1": "Matte (kg/t)",
    "flash.l5": "Air O₂ (% vol.)",
    "flash.m5": "O₂ of the process air (enrichment), in % of the volume.",
    "flash.l6": "Flux (% of charge)",
    "flash.m6": "Flux (added SiO₂) in % of the dry charge.",
    "conv.l1": "Total air (Nm³)",
    "conv.l5": "White metal (t)",
    "conv.m5": "White metal (Cu₂S) at the end of the slag blow, per 100 t of matte.",
    "conv.l6": "Total slag (t)",
    "conv.m6": "Slag from both blows, per 100 t of matte.",
    "ew.l4": "Energy (kWh/t)",
    "ew.l5": "Copper per cathode (kg)",
    "ew.m5": "Mass of copper plated on one cathode at the end of the harvest cycle.",
    "ew.l6": "Thickness per face (mm)",
    "ew.m6": "Thickness of the copper deposit on each face of the cathode at the end of the cycle.",
    # ------------------------------------------------------------ flotation: panel and case
    "flot.chk.cierre": (
        "Mass balance per species: the sum over the cells is the model total (relative error "
        "{err}; tolerance {tol})."
    ),
    "flot.crit.cierre": (
        "Problem if the per-cell sum of CuFeS₂, SiO₂ and water is not the feed × the bank "
        "recovery. It is the definition of the balance (docs/flotacion.md, model section)."
    ),
    "flot.chk.rinf": "The Cu recovery ({rec} %) does not exceed R∞ ({rinf} %).",
    "flot.crit.rinf": (
        "Problem if the recovery exceeds R∞. In first order, R = R∞·(1 − (1 + kτ)^−N) "
        "(docs/flotacion.md, model section), which never exceeds R∞."
    ),
    "flot.casos.intro": (
        "Puts the data of a Los Pelambres rougher bank into the sidebar (Vinnett et al. 2022, "
        "Table 3: cells, τ, R∞ and k; the gangue goes back to 5 %). While you keep them, the "
        "model is compared below with the recovery measured cell by cell."
    ),
    "flot.caso.A": "Bank A (9 cells, τ 4.1 min)",
    "flot.caso.B": "Bank B (6 cells, τ 6.4 min)",
    "flot.cmp.titulo": "**Bank {banco} against the measurements** (Vinnett et al. 2022, Table {tabla})",
    "flot.cmp.celda": "Cell",
    "flot.cmp.modelo": "Model (% of Cu)",
    "flot.cmp.medido": "Measured (% of Cu)",
    "flot.cmp.dpuntos": "Δ (points)",
    "flot.cmp.dpct": "Relative Δ (%)",
    "flot.cmp.nota": "Root-mean-square error of the model against the measurements: {rmse} points.",
    "flot.cmp.nota.B": (
        " The feed in the drawing (t/h) is still that of bank A: for bank B only the recovery is "
        "compared, which does not depend on the flow."
    ),
    "plot.rec.measured_b": "measured, Vinnett et al. 2022 (bank B)",
    # ------------------------------------------------------------ flash furnace: panel and case
    "flash.chk.elementos": (
        "Element balance (Cu, Fe, Zn, S, O, Si): what goes in comes out (maximum error {err} "
        "kmol/t; tolerance {tol})."
    ),
    "flash.crit.elementos": (
        "Problem if any element does not close. It is the definition of the balance "
        "(docs/fusion.md, validation section: element closure, 1e-9 kmol)."
    ),
    "flash.chk.calor": (
        "Heat balance: in = out + furnace loss (error {err} MJ/t; tolerance {tol})."
    ),
    "flash.crit.calor": (
        "Problem if the heat does not close. It is the definition of the balance (docs/fusion.md, "
        "validation section: heat closure, 1e-6 MJ/t)."
    ),
    "flash.chk.metas": (
        "The matte and the slag come out with the requested grade and SiO₂ (maximum error {err} "
        "points; tolerance {tol})."
    ),
    "flash.crit.metas": (
        "Problem if the calculated matte grade or slag SiO₂ are not the targets (docs/fusion.md, "
        "validation section: targets met, 1e-9)."
    ),
    "flash.chk.cobertura.ok": (
        "Matte grade, slag SiO₂ and heat loss within what the published operation covers (matte "
        "{grade_lo} to {grade_hi} %, SiO₂ {sio2_lo} to {sio2_hi} %, loss {loss_lo} to {loss_hi} "
        "MJ/t)."
    ),
    "flash.chk.cobertura.fuera": (
        "Outside what the published operation covers: {lista} (matte {grade_lo} to {grade_hi} %, "
        "SiO₂ {sio2_lo} to {sio2_hi} %, loss {loss_lo} to {loss_hi} MJ/t). The model still "
        "calculates, but no published plant backs it up."
    ),
    "flash.crit.cobertura": (
        "Warning if the matte grade, the slag SiO₂ or the heat loss leave the range of the four "
        "Atlantic Copper blends (Bacedoni et al. 2020, Table 13; procesos/fusion_datos.py, "
        "INDUSTRIAL). The partition coefficients are the FactSage ones for a 62 % matte and a "
        "29 % SiO₂ slag (docs/fusion.md, limits section)."
    ),
    "flash.var.grade": "matte grade",
    "flash.var.sio2": "slag SiO₂",
    "flash.var.loss": "heat loss",
    "flash.chk.temp": (
        "Product temperature: {temp} °C; the partition coefficients of the model are for {ref} °C."
    ),
    "flash.crit.temp": (
        "Warning if it is not 1,300 °C: the distribution coefficients are the FactSage ones at "
        "1,300 °C and all products leave at the same temperature (docs/fusion.md, model and "
        "limits sections)."
    ),
    "flash.casos.intro": (
        "Puts the blend and its measured operation at Atlantic Copper into the sidebar "
        "(Bacedoni et al. 2020, Table 13): matte grade, slag SiO₂ and heat loss. While you keep "
        "them, the calculation is compared below with the plant."
    ),
    "flash.caso": "Blend {n}",
    "flash.caso.help": "Blend {n}: puts its plant operation (Table 13) into the sidebar.",
    "flash.cmp.titulo": "**Blend {n} against the plant** (Table 13)",
    "flash.cmp.mag": "Quantity",
    "flash.cmp.este": "This calculation",
    "flash.cmp.planta": "Plant (Table 13)",
    "flash.cmp.dpct": "Relative Δ (%)",
    "flash.cmp.tol": "Repo tolerance",
    "flash.cmp.dentro": "Within?",
    "flash.cmp.si": "within",
    "flash.cmp.no": "outside",
    "flash.tol.oc": "±10 % relative",
    "flash.tol.o2": "±5 points",
    "flash.tol.fundente": "±2 points",
    "flash.cmp.nota": (
        "Relative Δ (%) is the difference relative to the plant. In points: air O₂ {o2} and "
        "flux {fl}."
    ),
    # ------------------------------------------------------------ converter: panel
    "conv.chk.elementos": (
        "Element balance (Cu, Fe, S, O) of both blows: maximum error {err} kmol; tolerance {tol}."
    ),
    "conv.crit.elementos": (
        "Problem if any element does not close. It is the definition of the balance "
        "(docs/conversion.md, validation section: element closure, 1e-9)."
    ),
    "conv.chk.masa": (
        "Mass balance of each blow: what goes in, with the reacting O₂, is what comes out "
        "(maximum relative error {err}; tolerance {tol})."
    ),
    "conv.crit.masa": (
        "Problem if the mass of a blow does not close: matte + flux + O₂ = white metal + slag + "
        "SO₂ in the slag blow, and the same in the copper blow. These are the figures of the "
        "balance chart."
    ),
    "conv.chk.eficiencia.ok": (
        "O₂ efficiencies within what was measured at Flin Flon: slag blow {lo_e} to {hi_e} %, "
        "copper blow {lo_c} to {hi_c} %."
    ),
    "conv.chk.eficiencia.fuera": (
        "O₂ efficiency outside what was measured at Flin Flon ({lista}). Measured: slag blow "
        "{lo_e} to {hi_e} %, copper blow {lo_c} to {hi_c} %. The efficiency is a plant input: "
        "the model does not predict it."
    ),
    "conv.crit.eficiencia": (
        "Warning if an efficiency leaves the range measured at Flin Flon: 55 to 68 % in the "
        "slag blows and 72 to 82 % in the copper blow (Kyllo 1995, Tables IV-XII; "
        "docs/conversion.md, limits section)."
    ),
    "conv.var.escoria": "slag blow",
    "conv.var.cobre": "copper blow",
    # ------------------------------------------------------------ electrowinning: panel
    "ew.chk.sin_avisos": (
        "The model issued no warnings: the electrolyte is within the range of the conductivity "
        "correlation."
    ),
    "ew.crit.avisos": (
        "Warning if the model extrapolates the conductivity correlation (Kalliomäki et al. "
        "2021; docs/ew.md, findings and limits section). Each warning states the exact range."
    ),
    "ew.chk.faraday": (
        "Copper per cathode: {kg} kg, Faraday's law (relative error {err}; tolerance {tol})."
    ),
    "ew.crit.faraday": (
        "Problem if the cathode mass departs from Faraday's law: efficiency × j × area × t × "
        "M/(2F) (docs/ew.md, validation section: cathode = Faraday, 1e-9). It fails, for example, "
        "if the current asks for more copper than the electrolyte carries."
    ),
    "ew.chk.voltaje": (
        "Cell voltage {v} V; range of a typical copper electrowinning cell: {lo} to {hi} V."
    ),
    "ew.crit.voltaje": (
        "Warning if the voltage leaves 1.9 to 2.3 V, the range of a typical cell (Beukes and "
        "Badenhorst 2009; docs/ew.md, validation section). It is an industry reference, not a limit "
        "of the model: it was checked with 40 g/L of Cu, 170 g/L of acid, 50 °C and 300 A/m²."
    ),
    # ------------------------------------------------------------ Try this
    "exp.flot.celdas.titulo": "Fewer cells in series",
    "exp.flot.celdas.texto": (
        "With {cells1} cells instead of {cells0}, the Cu has less time to float: the recovery "
        "drops from {rec0} to {rec1} %, the tailings take {relave1} t/h of CuFeS₂ instead of "
        "{relave0} and the concentrate comes out with {ley1} % Cu instead of {ley0} %: it loses "
        "Cu, but the gangue it carries is the same."
    ),
    "exp.flot.saturado.titulo": "More time in each cell",
    "exp.flot.saturado.texto": (
        "With τ of {tau1} min instead of {tau0} min per cell, the recovery goes from {rec0} to "
        "{rec1} %: only {recd} points more, because the example bank is already close to its "
        "maximum (R∞). Compare it with shortening the bank, where recovery is lost."
    ),
    "exp.flot.ganga.titulo": "More gangue entrainment",
    "exp.flot.ganga.texto": (
        "With {gangue1} % of the gangue reaching the concentrate instead of {gangue0} %, the Cu "
        "recovery does not change ({rec0} %), but the concentrate rises from {conc0} to {conc1} "
        "t/h and its grade drops from {ley0} to {ley1} % Cu: it is dilution, not copper loss."
    ),
    "exp.flash.mata.titulo": "Raise the matte grade",
    "exp.flash.mata.texto": (
        "With a {f_grade1} % Cu matte instead of {f_grade0} %, more iron and sulfur must be "
        "oxidized: the technical O₂ rises from {oc0} to {oc1} Nm³/t, the air is enriched less "
        "({enr0} to {enr1} % O₂), the matte drops from {mata0} to {mata1} kg/t and the SO₂ "
        "rises from {so20} to {so21} kg/t. The panel stays in range: {f_grade1} % is within the "
        "published operation."
    ),
    "exp.flash.perdida.titulo": "Raise the heat loss",
    "exp.flash.perdida.texto": (
        "With {f_loss1} MJ/t of loss instead of {f_loss0}, the furnace needs more heat: the "
        "technical O₂ does not change ({oc0} Nm³/t) and neither does the flux ({fund0} %), but "
        "the air is enriched more, from {enr0} to {enr1} % O₂. The panel gives a **warning**: "
        "{f_loss1} MJ/t is outside what the published operation covers."
    ),
    "exp.flash.silice.titulo": "Raise the slag SiO₂",
    "exp.flash.silice.texto": (
        "With {f_sio21} % SiO₂ in the slag instead of {f_sio20} %, more flux is added: it rises "
        "from {fund0} to {fund1} % of the charge and the slag from {esc0} to {esc1} kg/t. "
        "{f_sio21} % is the top of what is published: the panel stays in range, but a little "
        "higher it would warn."
    ),
    "exp.conv.mata.titulo": "Raise the matte grade",
    "exp.conv.mata.texto": (
        "With a {c_grade1} % Cu matte instead of {c_grade0} %, there is less iron and sulfur to "
        "oxidize: the total air drops from {aire0} to {aire1} Nm³, the flux from {fund0} to "
        "{fund1} t and the SO₂ from {so20} to {so21} t, and the blister copper rises from "
        "{blis0} to {blis1} t."
    ),
    "exp.conv.eficiencia.titulo": "Use the oxygen worse",
    "exp.conv.eficiencia.texto": (
        "With {c_eff_slag1} % O₂ efficiency in the slag blow instead of {c_eff_slag0} %, more "
        "air is needed: the total air rises from {aire0} to {aire1} Nm³, but the blister copper "
        "({blis0} t), the flux ({fund0} t) and the SO₂ ({so20} t) do not change: the efficiency "
        "only changes the air. The panel gives a **warning**: {c_eff_slag1} % is below what was "
        "measured at Flin Flon."
    ),
    "exp.conv.bano.titulo": "Heat the bath",
    "exp.conv.bano.texto": (
        "With the bath at {c_bath1} °C instead of {c_bath0} °C, the air ({aire0} Nm³) and the "
        "blister copper ({blis0} t) do not change: the temperature only enters the heat balance "
        "and the copper density. Hot copper is less dense and its volume rises from {m30} to "
        "{m31} m³."
    ),
    "exp.ew.corriente.titulo": "Raise the current density",
    "exp.ew.corriente.texto": (
        "With {j1} A/m² instead of {j0}, the cathode ends the cycle with {kg1} kg instead of "
        "{kg0} (+{kgp} %) and {mm1} mm per face instead of {mm0}; but the cell asks for more "
        "voltage, from {v0} to {v1} V, and each tonne of copper costs more energy: from {kwh0} "
        "to {kwh1} kWh/t."
    ),
    "exp.ew.eficiencia.titulo": "Lower the current efficiency",
    "exp.ew.eficiencia.texto": (
        "With {eff1} % efficiency instead of {eff0} %, the cathode plates {kg1} kg instead of "
        "{kg0}. The cell voltage does not change ({v0} V), but the energy per tonne rises from "
        "{kwh0} to {kwh1} kWh/t: the same electricity plates less copper."
    ),
    "exp.ew.temp.titulo": "Cool the electrolyte",
    "exp.ew.temp.texto": (
        "With {temp1} °C instead of {temp0} °C, the electrolyte conducts less and the voltage "
        "rises from {v0} to {v1} V; the plated copper does not change ({kg0} kg). The panel "
        "gives a **warning**: {temp1} °C is outside the range of the conductivity correlation, "
        "and the model says so."
    ),
}
