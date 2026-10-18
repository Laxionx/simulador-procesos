"""Los rótulos y avisos del modelo (`procesos`), en español, vertidos al inglés para la app.

El modelo no cambia: sus cifras y sus textos siguen en español. Aquí se traducen los nombres de
las fases y de los estados del baño, los componentes del voltaje y los avisos y errores conocidos.
Los números se vuelven al formato inglés. La prueba `test_i18n.py` recorre lo que el modelo
produce y comprueba que no queda español.
"""

from __future__ import annotations

import re

EXACT = {
    # estados del baño y fases del convertidor
    "Carga: mata": "Charge: matte",
    "Fin del soplado a escoria": "End of the slag blow",
    "Fin del soplado a cobre": "End of the copper blow",
    "mata": "matte",
    "metal blanco": "white metal",
    "blíster": "blister copper",
    "escoria": "slag",
    "entra": "in",
    "sale": "out",
    # componentes del voltaje de la celda
    "reversible": "reversible",
    "anódico": "anodic",
    "catódico": "cathodic",
    "electrolito": "electrolyte",
    "contactos": "contacts",
}
PHRASES: tuple[tuple[str, str], ...] = (
    ("Soplado a escoria", "Slag blow"),
    ("Soplado a cobre", "Copper blow"),
    ("entra: ", "in: "),
    ("sale: ", "out: "),
    ("mata", "matte"),
    ("fundente", "flux"),
    ("O₂ que reacciona", "reacting O₂"),
    ("metal blanco", "white metal"),
    ("escoria", "slag"),
    ("blíster", "blister copper"),
)
WARNINGS: tuple[tuple[str, str], ...] = (
    (
        r"conductividad: (Cu|H2SO4|temperatura) = (.+) fuera del rango de la correlación "
        r"\((.+)-(.+)\); es una extrapolación",
        "conductivity: {0} = {1} outside the range of the correlation ({2}-{3}); it is an "
        "extrapolation",
    ),
    (
        r"la corriente pide más cobre del que trae el electrolito",
        "the current asks for more copper than the electrolyte carries",
    ),
)
ERRORS: tuple[tuple[str, str], ...] = (
    (
        r"conductividad no física \((.+) mS/cm\): composición fuera de rango",
        "unphysical conductivity ({0} mS/cm): composition out of range",
    ),
    (
        r"densidad de corriente (.+) ≥ densidad límite (.+) A/m²",
        "current density {0} ≥ limiting density {1} A/m²",
    ),
    (r"Los datos deben ser números finitos", "The data must be finite numbers"),
    (
        r"Cobre y ácido suman más que el electrolito: revisa las concentraciones",
        "Copper and acid add up to more than the electrolyte: check the concentrations",
    ),
    (r"Balance imposible con esas metas: (.+)", "Impossible balance with those targets: {0}"),
    (
        r"(.+): imposible con esas metas \((.+) < 0\)",
        "{0}: impossible with those targets ({1} < 0)",
    ),
    (r"La ley de mata debe estar entre 0 y (.+) %", "The matte grade must be between 0 and {0} %"),
    (
        r"La sílice de la escoria debe estar entre 0 y 100 %",
        "The slag silica must be between 0 and 100 %",
    ),
    (
        r"La pérdida térmica del horno no puede ser negativa",
        "The furnace heat loss cannot be negative",
    ),
    (
        r"La mineralogía suma (.+) %, más de 100 %",
        "The mineralogy adds up to {0} %, more than 100 %",
    ),
    (
        r"La mineralogía no admite porcentajes negativos",
        "The mineralogy admits no negative percentages",
    ),
    (r"Minerales sin datos: (.+)", "Minerals without data: {0}"),
    (r"El reparto del zinc no converge", "The zinc distribution does not converge"),
    (
        r"La eficiencia de oxígeno debe estar entre 0 y 1",
        "The oxygen efficiency must be between 0 and 1",
    ),
    (
        r"La fracción de Fe como magnetita debe estar entre 0 y 1",
        "The fraction of Fe as magnetite must be between 0 and 1",
    ),
    (r"El Cu de la escoria debe estar entre 0 y 100 %", "The slag Cu must be between 0 and 100 %"),
    (r"Los análisis no cierran: masa negativa", "The analyses do not close: negative mass"),
    (r"(.+): ley (.+) % imposible para Cu2S \+ FeS", "{0}: grade {1} % impossible for Cu2S + FeS"),
    (r"(.+): el análisis suma más de 100 %", "{0}: the analysis adds up to more than 100 %"),
    (r"(.+): toneladas negativas", "{0}: negative tonnes"),
    (r"(.+): especies sin modelo: (.+)", "{0}: species without a model: {1}"),
    (
        r"El baño no cabe en el dibujo del convertidor",
        "The bath does not fit in the converter drawing",
    ),
)
_DECIMAL = re.compile(r"(?<=\d),(?=\d)")
_HINTS = (
    (
        "el calor no alcanza para fundir sin combustible: falta energía",
        "the heat is not enough to smelt without fuel: energy is missing",
    ),
    (
        "la carga ya trae más sílice que la que pide la escoria",
        "the charge already carries more silica than the slag asks for",
    ),
    (
        "la carga trae más oxígeno que el necesario para esa ley",
        "the charge carries more oxygen than needed for that grade",
    ),
    (" sale negativo", " comes out negative"),
)


def translate(text: str) -> str:
    """Un rótulo del modelo en inglés (lo que no se conoce queda igual)."""
    if text in EXACT:
        return EXACT[text]
    out = text
    for es_, en_ in PHRASES:
        out = out.replace(es_, en_)
    return _DECIMAL.sub(".", out)


def _fill(patterns, message: str) -> str | None:
    for pattern, template in patterns:
        m = re.fullmatch(pattern, message, flags=re.S)
        if m:
            return template.format(*(_DECIMAL.sub(".", g) for g in m.groups()))
    return None


def translate_warning(message: str) -> str:
    """Un aviso del modelo en inglés; si no se conoce, el original."""
    found = _fill(WARNINGS, message)
    return message if found is None else found.replace("temperatura =", "temperature =")


def translate_error(message: str) -> str:
    """Un mensaje de error del modelo en inglés; si no se conoce, el original."""
    found = _fill(ERRORS, message)
    if found is None:
        return message
    for es_, en_ in _HINTS:
        found = found.replace(es_, en_)
    return found
