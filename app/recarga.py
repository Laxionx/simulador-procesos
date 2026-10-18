"""Recarga segura de los módulos locales de la app.

Streamlit relee el script principal en cada corrida, pero deja en `sys.modules` los módulos que
ese script importó. Si el servidor sigue despierto cuando se publica una versión nueva, el script
nuevo se encuentra con los módulos VIEJOS de `app/` y falla (por ejemplo, un `ImportError` por un
nombre que el módulo viejo no tiene). `purge_stale` quita de `sys.modules` los módulos locales cuyo
archivo cambió después de cargarse, para que la corrida los importe de nuevo.

- Solo se quitan los que cambiaron y los que dependen de ellos (los que guardan nombres traídos de
  un módulo quitado): un módulo sin cambios ni dependencias conserva su identidad y sus cachés
  (`lru_cache`, estado), así que en las corridas normales no se pierde nada.
- No usa `importlib.reload` en cadena: se borra la entrada y el próximo `import` carga el archivo.
- «Cuándo se cargó» un módulo: el momento en que este módulo lo vio por primera vez, o, si ya
  estaba cargado desde antes (un servidor que arrancó con una versión sin este archivo), la fecha
  de su `.pyc`, que se escribió al importarlo.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType

_LOADED: dict[
    str, float
] = {}  # nombre del módulo -> momento (s) en que se cargó, para todo el proceso


def _local_modules(folders: list[Path]) -> dict[str, Path]:
    """Módulos cargados cuyo archivo está dentro de alguna de las carpetas."""
    found: dict[str, Path] = {}
    for name, module in list(sys.modules.items()):
        if name == __name__ or module is None:
            continue
        file = getattr(module, "__file__", None)
        if not file:
            continue
        path = Path(file).resolve()
        if any(path.is_relative_to(folder) for folder in folders):
            found[name] = path
    return found


def _loaded_at(module: ModuleType) -> float:
    """Cuándo se cargó un módulo que este proceso aún no había visto: la fecha de su `.pyc`."""
    cached = getattr(module, "__cached__", None)
    try:
        return os.stat(cached).st_mtime if cached else time.time()
    except OSError:
        return time.time()


def _depends_on(module: ModuleType, names: set[str]) -> bool:
    """¿Guarda el módulo algún módulo o nombre (clase, función) traído de `names`?"""
    for value in list(vars(module).values()):
        try:
            origin = value.__name__ if isinstance(value, ModuleType) else value.__module__
        except Exception:  # objetos raros: no son una dependencia que se pueda rastrear
            continue
        if origin in names:
            return True
    return False


def purge_stale(folders: Iterable[str | Path]) -> list[str]:
    """Quita de `sys.modules` los módulos de `folders` que cambiaron en disco (y los que dependen
    de ellos). Devuelve los nombres quitados."""
    roots = [Path(f).resolve() for f in folders]
    local = _local_modules(roots)
    stale: set[str] = set()
    for name, path in local.items():
        loaded = _LOADED.setdefault(name, _loaded_at(sys.modules[name]))
        try:
            if path.stat().st_mtime > loaded:
                stale.add(name)
        except OSError:
            continue
    grew = bool(stale)
    while grew:  # los que dependen de uno quitado también se quitan, hasta que no haya más
        grew = False
        for name in local.keys() - stale:
            if _depends_on(sys.modules[name], stale):
                stale.add(name)
                grew = True
    for name in sorted(stale):
        sys.modules.pop(name, None)
        _LOADED.pop(name, None)
        parent, _, child = name.rpartition(".")
        if parent and parent in sys.modules and hasattr(sys.modules[parent], child):
            delattr(sys.modules[parent], child)  # `from paquete import sub` no debe ver el viejo
    return sorted(stale)
