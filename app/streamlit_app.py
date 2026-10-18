"""Punto de entrada de la app. Hace dos cosas antes de correr `principal.py` (la app de siempre):

1. Recarga segura: quita de `sys.modules` los módulos locales que cambiaron en disco, porque
   Streamlit Cloud relee este script en cada corrida pero conserva los módulos viejos de `app/`
   (ver `recarga.py`).
2. Errores sin traza: lo que falle (también un `ImportError`) va al log del servidor y el
   visitante ve solo un mensaje genérico, sin tipo, mensaje ni rutas.

`principal.py` se ejecuta con `runpy` en cada corrida, igual que Streamlit ejecuta un script:
sus `import` se repiten y toman los módulos al día.
"""

from __future__ import annotations

import logging
import runpy
import sys
from pathlib import Path

import streamlit as st

# Streamlit Community Cloud instala solo requirements.txt: el paquete se importa desde la raíz,
# y los módulos de la app, desde esta carpeta.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

from recarga import purge_stale  # noqa: E402

# Texto fijo para cuando ni siquiera se pudieron cargar las traducciones.
GENERIC = (
    "Algo falló al cargar la app. Recarga la página. / "
    "Something went wrong loading the app. Reload the page."
)


def _show_error() -> None:
    """El mensaje genérico, en el idioma de la visita si las traducciones cargan."""
    try:
        from i18n import activate, t

        activate()
        message = t("err.generic")
    except Exception:
        message = GENERIC
    st.error(message)


def _start() -> None:
    try:
        purge_stale([ROOT / "app", ROOT / "procesos"])
        runpy.run_path(str(ROOT / "app" / "principal.py"), run_name="principal")
    except Exception:
        logging.getLogger("app").exception("fallo en la app")  # el detalle, solo en el log
        try:
            st.set_page_config(layout="wide")  # si el fallo fue antes de configurarla
        except Exception:
            pass
        _show_error()


_start()
