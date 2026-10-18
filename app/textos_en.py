"""Todos los textos de la app en el idioma «en»: junta los de cada área y no deja que dos áreas
usen la misma clave."""

from __future__ import annotations

from textos_en_datos import T as DATOS
from textos_en_guia import T as GUIA
from textos_en_svg import T as SVG
from textos_en_ui import T as UI

TEXTS: dict[str, str] = {}
for _part in (UI, GUIA, DATOS, SVG):
    _repeated = TEXTS.keys() & _part.keys()
    if _repeated:
        raise ValueError(f"claves repetidas en textos_en: {sorted(_repeated)}")
    TEXTS.update(_part)
