"""Todos los textos de la app en el idioma «es»: junta los de cada área y no deja que dos áreas
usen la misma clave."""

from __future__ import annotations

from textos_es_datos import T as DATOS
from textos_es_guia import T as GUIA
from textos_es_svg import T as SVG
from textos_es_ui import T as UI

TEXTS: dict[str, str] = {}
for _part in (UI, GUIA, DATOS, SVG):
    _repeated = TEXTS.keys() & _part.keys()
    if _repeated:
        raise ValueError(f"claves repetidas en textos_es: {sorted(_repeated)}")
    TEXTS.update(_part)
