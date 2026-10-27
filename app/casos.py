"""Equipos predefinidos: casos publicados cuyos datos de entrada coinciden EXACTO con los controles
de la pestaña. Un botón los pone en la barra lateral; mientras los controles sigan siendo los del
caso, la pestaña muestra junto al resultado el valor publicado y la diferencia (Δ %).

- Flotación: los bancos rougher A y B de Los Pelambres (Vinnett et al. 2022; `docs/flotacion.md`).
  Los controles son celdas, τ, R∞ y k de la Tabla 3; lo publicado es la recuperación medida celda a
  celda (Tablas B1 y B2). La alimentación (t/h) del banco B no es un control: el dibujo conserva la
  del banco A, y de B solo se compara la recuperación (que no depende del caudal).
- Horno flash: las cuatro mezclas de Atlantic Copper (Bacedoni et al. 2020, Tabla 13): mezcla, ley
  de mata, SiO₂ de la escoria y pérdida térmica son controles; lo publicado es el consumo de O₂, el
  O₂ del aire y el fundente (`docs/fusion.md`).
- Convertidor y electroobtención: sin casos. Rönnskär y Flin Flon traen sus propias cargas y
  análisis (la app fija mata de 100 t y la escoria de Ilo), y los ejemplos de electroobtención
  (Beukes y Badenhorst a 200 A/m², Gunnison) usan datos que no son controles de la pestaña.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from calculo import (
    MEASURED_B_CELLS,
    MEASURED_B_CU_PCT,
    MEASURED_CELLS,
    MEASURED_CU_PCT,
    FlotationParams,
    FlotationView,
)
from calculo_piro import BLEND_NAMES, FlashParams, FlashView
from controles import PREFIX
from i18n import t

from procesos.fusion_datos import INDUSTRIAL, T_PRODUCTS_C

TOL_IGUAL = 1e-9  # dos controles son «el mismo valor» si difieren menos que esto
# Tolerancias fijadas antes de correr en docs/fusion.md (Validación): OC ±10 %, O₂ ±5 puntos,
# fundente ±2 puntos.
TOL_OC_REL_PCT, TOL_O2_PUNTOS, TOL_FUNDENTE_PUNTOS = 10.0, 5.0, 2.0


def _igual(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=0.0, abs_tol=TOL_IGUAL)


# ------------------------------------------------------------------ flotación
@dataclass(frozen=True)
class CasoFlot:
    """Un banco de Los Pelambres: sus datos de la Tabla 3 y la recuperación medida celda a celda."""

    clave: str
    celdas: int
    tau_min: float
    r_inf_pct: float
    k: float
    celdas_medidas: tuple[int, ...]
    medidas_pct: tuple[float, ...]
    tabla: str  # tabla del artículo con la recuperación medida

    @property
    def cambios(self) -> dict[str, object]:
        """Lo que el botón fija en la barra lateral (la ganga vuelve a su supuesto, 5 %)."""
        return {PREFIX + "cells": self.celdas, PREFIX + "tau": self.tau_min,
                PREFIX + "r_inf": self.r_inf_pct, PREFIX + "k": self.k,
                PREFIX + "gangue": 5.0}  # fmt: skip

    def es_este(self, p: FlotationParams) -> bool:
        return (p.cells == self.celdas and _igual(p.tau_min, self.tau_min)
                and _igual(100.0 * p.r_inf, self.r_inf_pct) and _igual(p.k, self.k))  # fmt: skip


CASOS_FLOT = (
    CasoFlot("A", 9, 4.1, 94.0, 0.35, MEASURED_CELLS, MEASURED_CU_PCT, "B1"),
    CasoFlot("B", 6, 6.4, 93.3, 0.27, MEASURED_B_CELLS, MEASURED_B_CU_PCT, "B2"),
)


def caso_flot_activo(p: FlotationParams) -> CasoFlot | None:
    return next((c for c in CASOS_FLOT if c.es_este(p)), None)


def comparacion_flot(view: FlotationView, caso: CasoFlot) -> list[tuple[int, float, float]]:
    """(celda, modelo %, medido %) de las celdas con dato medido."""
    return [(n, 100.0 * view.cu_cumulative[n - 1], m)
            for n, m in zip(caso.celdas_medidas, caso.medidas_pct, strict=True)]  # fmt: skip


def rmse_flot(filas: list[tuple[int, float, float]]) -> float:
    """Raíz del error cuadrático medio (puntos) del modelo contra lo medido."""
    return math.sqrt(sum((mod - med) ** 2 for _, mod, med in filas) / len(filas))


# ------------------------------------------------------------------ horno flash
@dataclass(frozen=True)
class CasoFlash:
    """Una mezcla de Atlantic Copper con su operación medida (Tabla 13)."""

    blend: int
    oc_nm3_t: float
    o2_pct: float
    fundente_pct: float
    ley_mata: float
    sio2_escoria: float
    perdida_mj_t: float

    @property
    def cambios(self) -> dict[str, object]:
        return {PREFIX + "blend": t("blend", n=self.blend), PREFIX + "f_grade": self.ley_mata,
                PREFIX + "f_sio2": self.sio2_escoria, PREFIX + "f_loss": self.perdida_mj_t,
                PREFIX + "f_temp": T_PRODUCTS_C}  # fmt: skip

    def es_este(self, p: FlashParams) -> bool:
        return (p.blend == self.blend and _igual(p.matte_grade, self.ley_mata)
                and _igual(p.slag_sio2, self.sio2_escoria)
                and _igual(p.heat_loss_mj_t, self.perdida_mj_t)
                and _igual(p.products_c, T_PRODUCTS_C))  # fmt: skip


CASOS_FLASH = tuple(
    CasoFlash(n, *INDUSTRIAL[nombre]) for n, nombre in enumerate(BLEND_NAMES, start=1)
)


def caso_flash_activo(p: FlashParams) -> CasoFlash | None:
    return next((c for c in CASOS_FLASH if c.es_este(p)), None)


@dataclass(frozen=True)
class FilaFlash:
    """Una magnitud del horno frente a la planta: su clave de texto, el valor del modelo y el de la
    planta, la diferencia relativa (%) y en puntos, y si cabe en la tolerancia del repo."""

    clave: str
    modelo: float
    planta: float
    delta_pct: float
    delta_puntos: float
    tolerancia: float
    dentro: bool


def comparacion_flash(view: FlashView, caso: CasoFlash) -> list[FilaFlash]:
    r = view.result
    datos = (
        ("oc", r.oxygen_nm3_t, caso.oc_nm3_t, TOL_OC_REL_PCT, True),
        ("o2", r.enrichment_pct, caso.o2_pct, TOL_O2_PUNTOS, False),
        ("fundente", r.flux_pct, caso.fundente_pct, TOL_FUNDENTE_PUNTOS, False),
    )
    out = []
    for clave, modelo, planta, tol, relativa in datos:
        delta_pct = 100.0 * (modelo - planta) / planta
        delta_p = modelo - planta
        dentro = abs(delta_pct if relativa else delta_p) <= tol
        out.append(FilaFlash(clave, modelo, planta, delta_pct, delta_p, tol, dentro))
    return out
