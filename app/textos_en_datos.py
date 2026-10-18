"""English texts of the input data (sidebar and the «What data it needs» table)."""

T = {
    "sidebar.example": "Load example",
    "group.Flotación": "Flotation",
    "group.Electroobtención": "Electrowinning",
    "group.Horno flash": "Flash furnace",
    "group.Convertidor": "Converter",
    "dato.help": "{meaning} Range{unit}: {lo} to {hi}. In the plant: {source}",
    "dato.range": "{lo} to {hi}",
    "blend": "Blend {n}",
    "unit.days": "days",
    "col.equipo": "Equipment",
    "col.dato": "Input",
    "col.unit": "Unit",
    "col.range": "Range",
    "col.example": "Example",
    "col.what": "What it is",
    "col.how": "How it is obtained",
    "dato.cells.label": "Number of cells",
    "dato.cells.meaning": (
        "Flotation cells in series; the concentrate of each one is added to that of the bank."
    ),
    "dato.cells.source": "bank drawing.",
    "dato.tau.label": "Residence time per cell (τ)",
    "dato.tau.meaning": "Mean time the pulp spends inside each cell (perfect mixing).",
    "dato.tau.source": "tracer test, or useful cell volume divided by the pulp flow rate.",
    "dato.r_inf.label": "R∞ of Cu (chalcopyrite)",
    "dato.r_inf.meaning": "Maximum recovery that the Cu would reach with infinite time.",
    "dato.r_inf.source": "fitted to the cell-by-cell recovery measured on the bank.",
    "dato.k.label": "k of Cu",
    "dato.k.meaning": "First-order kinetic constant: how fast the Cu floats.",
    "dato.k.source": "fitted to the cell-by-cell measured recovery, or to laboratory batch tests.",
    "dato.gangue.label": "Fixed recovery of the gangue (SiO₂)",
    "dato.gangue.meaning": (
        "Part of the gangue that reaches the concentrate by entrainment, without kinetics. In "
        "the example it is an assumption, not a measurement."
    ),
    "dato.gangue.source": "gangue assays in concentrate and tailings.",
    "dato.j.label": "Current density",
    "dato.j.meaning": "Current per square meter of cathode.",
    "dato.j.source": "rectifier current divided by the cathode area of the tankhouse.",
    "dato.eff.label": "Current efficiency",
    "dato.eff.meaning": (
        "Part of the current that deposits copper; the rest is lost in short circuits and in "
        "the Fe³⁺/Fe²⁺ cycle."
    ),
    "dato.eff.source": "copper harvested divided by what Faraday's law gives.",
    "dato.cu.label": "Copper in the electrolyte",
    "dato.cu.meaning": "Cu²⁺ concentration of the electrolyte leaving the cell.",
    "dato.cu.source": "electrolyte analysis (atomic absorption).",
    "dato.acid.label": "Sulfuric acid",
    "dato.acid.meaning": "H₂SO₄ concentration of the electrolyte; more acid, more conductive.",
    "dato.acid.source": "electrolyte titration.",
    "dato.temp.label": "Temperature",
    "dato.temp.meaning": "Electrolyte temperature; hotter, more conductive.",
    "dato.temp.source": "thermocouple in the cell.",
    "dato.days.label": "Days of the harvest cycle",
    "dato.days.meaning": (
        "Time the cathode stays in the cell before being harvested. Operating datum, not a "
        "model one; the example value is a typical assumption."
    ),
    "dato.days.source": "harvest schedule of the tankhouse.",
    "dato.area.label": "Area of one face of the cathode",
    "dato.area.meaning": (
        "Submerged area of one face; the cathode has two. Operating datum, not a model one; the "
        "example value is a typical assumption."
    ),
    "dato.area.source": "cathode drawing.",
    "dato.blend.label": "Concentrate blend",
    "dato.blend.meaning": (
        "Which of the four Atlantic Copper (Huelva) concentrate blends is smelted; it changes "
        "the mineralogy of the charge."
    ),
    "dato.blend.source": "mineralogical analysis of the furnace charge.",
    "dato.f_grade.label": "Matte grade",
    "dato.f_grade.meaning": (
        "Copper target in the matte; the operation sets it with the oxygen that is blown."
    ),
    "dato.f_grade.source": "assay of the matte leaving the furnace.",
    "dato.f_sio2.label": "SiO₂ of the slag",
    "dato.f_sio2.meaning": "Silica target in the slag; it defines how much flux is added.",
    "dato.f_sio2.source": "slag assay.",
    "dato.f_loss.label": "Furnace heat loss",
    "dato.f_loss.meaning": "Heat the furnace loses through its walls, per tonne of charge.",
    "dato.f_loss.source": "plant heat balance or cooling water.",
    "dato.f_temp.label": "Product temperature",
    "dato.f_temp.meaning": "Temperature of the matte and the slag leaving the furnace.",
    "dato.f_temp.source": "thermocouple or temperature lance in the settler.",
    "dato.c_grade.label": "Matte grade",
    "dato.c_grade.meaning": "Copper of the matte charged to the converter (100 t per charge).",
    "dato.c_grade.source": "assay of the furnace matte.",
    "dato.c_eff_slag.label": "O₂ efficiency, slag blow",
    "dato.c_eff_slag.meaning": "Part of the blown oxygen that reacts in the slag blow.",
    "dato.c_eff_slag.source": "oxygen that reacts (balance) divided by what is blown (air flow).",
    "dato.c_eff_copper.label": "O₂ efficiency, copper blow",
    "dato.c_eff_copper.meaning": "Same, in the copper blow.",
    "dato.c_eff_copper.source": "oxygen that reacts (balance) divided by what is blown (air flow).",
    "dato.c_bath.label": "Bath temperature",
    "dato.c_bath.meaning": (
        "Bath temperature; it only changes the heat balance and the density of the copper."
    ),
    "dato.c_bath.source": "optical pyrometer or immersion thermocouple.",
}
