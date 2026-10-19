"""Recarga segura de los módulos locales de la app.

Streamlit relee el script principal en cada corrida, pero deja en `sys.modules` los módulos que
ese script importó. Si el servidor sigue despierto cuando se publica una versión nueva, el script
nuevo se encuentra con los módulos VIEJOS de `app/` y falla (por ejemplo, un `ImportError` por un
nombre que el módulo viejo no tiene, o un `KeyError` porque `i18n` armó su diccionario con los
textos viejos). `purge_stale` lo evita: si CUALQUIER módulo local cambió en disco después de
cargarse, quita de `sys.modules` TODOS los módulos locales, y la corrida los importa de nuevo.

- Todos y no solo los cambiados: un módulo sin cambios puede guardar objetos armados con los de
  otro (un diccionario, una clase), y eso no se puede rastrear con seguridad. Publicar es raro;
  perder las cachés (`lru_cache`, estado) una vez por publicación no cuesta nada.
- Sin cambios, no se quita nada: cada módulo conserva su identidad y sus cachés.
- No usa `importlib.reload` en cadena: se borra la entrada y el próximo `import` carga el archivo.
- «Cuándo se cargó» un módulo: el momento en que este módulo lo vio por primera vez, o, si ya
  estaba cargado desde antes, la fecha de su `.pyc`, que se escribió al importarlo.
- `LOADED_AT` marca cuándo se cargó ESTE archivo: el punto de entrada lo compara con la fecha del
  archivo para saber si `recarga.py` mismo cambió (ver `streamlit_app.py`).
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType

LOADED_AT = time.time()  # cuándo se cargó este módulo
_LOADED: dict[str, float] = {}  # nombre del módulo -> momento (s) en que se cargó


def local_modules(folders: Iterable[str | Path]) -> dict[str, Path]:
    """Módulos cargados cuyo archivo está dentro de alguna de las carpetas (sin este)."""
    roots = [Path(f).resolve() for f in folders]
    found: dict[str, Path] = {}
    for name, module in list(sys.modules.items()):
        if name == __name__ or module is None:
            continue
        file = getattr(module, "__file__", None)
        if not file:
            continue
        path = Path(file).resolve()
        if any(path.is_relative_to(root) for root in roots):
            found[name] = path
    return found


def _loaded_at(module: ModuleType) -> float:
    """Cuándo se cargó un módulo que este proceso aún no había visto: la fecha de su `.pyc`."""
    cached = getattr(module, "__cached__", None)
    try:
        return os.stat(cached).st_mtime if cached else time.time()
    except OSError:
        return time.time()


def drop(names: Iterable[str]) -> None:
    """Quita los módulos de `sys.modules` y el atributo del paquete padre, para que
    `from paquete import sub` no vea el módulo viejo."""
    for name in sorted(names):
        sys.modules.pop(name, None)
        _LOADED.pop(name, None)
        parent, _, child = name.rpartition(".")
        if parent and parent in sys.modules and hasattr(sys.modules[parent], child):
            delattr(sys.modules[parent], child)


def purge_stale(folders: Iterable[str | Path]) -> list[str]:
    """Si algún módulo de `folders` cambió en disco desde que se cargó, quita TODOS los módulos
    de `folders` y devuelve sus nombres; si ninguno cambió, no quita nada."""
    local = local_modules(folders)
    changed = False
    for name, path in local.items():
        loaded = _LOADED.setdefault(name, _loaded_at(sys.modules[name]))
        try:
            changed = changed or path.stat().st_mtime > loaded
        except OSError:
            continue
    if not changed:
        return []
    drop(local)
    return sorted(local)
