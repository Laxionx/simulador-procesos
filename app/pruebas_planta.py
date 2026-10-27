"""«Prueba esto» de las pestañas de equipo: experimentos que parten del ejemplo de la barra lateral
(los valores por defecto de `controles.DATOS`), con cifras calculadas en vivo por el modelo y un
botón que pone el cambio en los controles. Cada experimento declara lo que afirma su texto:
`direcciones` (magnitud → +1 sube, −1 baja, 0 no cambia) y el `nivel` del panel «Estado de la
operación» tras el cambio; `tests/test_estado_planta.py` verifica las dos cosas.

Los cambios están en las unidades de los controles de la barra lateral (porcentajes en %)."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache

from calculo import run_ew, run_flotation
from calculo_piro import run_converter, run_flash
from controles import CONV, EW, FLASH, FLOT, PREFIX, armar_params, valores_ejemplo
from dibujo import es
from estado import Fila, Prueba, peor_nivel
from estado_planta import filas_convertidor, filas_ew, filas_flash, filas_flotacion
from i18n import num_g, t

SLUG = {FLOT: "flot", FLASH: "flash", CONV: "conv", EW: "ew"}  # prefijo de claves de texto


@dataclass(frozen=True)
class Experimento:
    """Un cambio al ejemplo y lo que afirma su texto."""

    equipo: str
    clave: str
    cambios: dict[str, float]  # clave de `DATOS` → valor nuevo
    direcciones: dict[str, int]  # magnitud → +1 sube / −1 baja / 0 igual
    nivel: str = "ok"  # peor nivel del panel tras aplicar el cambio
    decimales: dict[str, int] = field(default_factory=dict)  # más cifras donde el cambio es chico


EXPERIMENTOS: tuple[Experimento, ...] = (
    Experimento(FLOT, "celdas", {"cells": 4},
                {"rec": -1, "relave": +1, "ley": -1, "conc": -1}),
    Experimento(FLOT, "saturado", {"tau": 6.4}, {"rec": +1}, decimales={"rec": 2}),
    Experimento(FLOT, "ganga", {"gangue": 10.0},
                {"rec": 0, "conc": +1, "ley": -1}),
    Experimento(FLASH, "mata", {"f_grade": 66.0},
                {"oc": +1, "enr": -1, "mata": -1, "so2": +1}),
    Experimento(FLASH, "perdida", {"f_loss": 240.0},
                {"oc": 0, "enr": +1, "fund": 0}, nivel="aviso"),
    Experimento(FLASH, "silice", {"f_sio2": 30.0},
                {"fund": +1, "esc": +1}),
    Experimento(CONV, "mata", {"c_grade": 66.0},
                {"aire": -1, "fund": -1, "blis": +1, "so2": -1}),
    Experimento(CONV, "eficiencia", {"c_eff_slag": 50.0},
                {"aire": +1, "blis": 0, "fund": 0, "so2": 0}, nivel="aviso"),
    Experimento(CONV, "bano", {"c_bath": 1250.0},
                {"aire": 0, "blis": 0, "m3": +1}),
    Experimento(EW, "corriente", {"j": 400.0},
                {"kg": +1, "mm": +1, "v": +1, "kwh": +1}),
    Experimento(EW, "eficiencia", {"eff": 85.0},
                {"kg": -1, "v": 0, "kwh": +1}),
    Experimento(EW, "temp", {"temp": 35.0},
                {"v": +1, "kg": 0}, nivel="aviso"),
)  # fmt: skip

# Cifras decimales con que cada magnitud entra al texto.
DECIMALES = {
    FLOT: {"rec": 1, "ley": 1, "conc": 1, "relave": 2},
    FLASH: {"oc": 1, "enr": 1, "fund": 2, "mata": 0, "esc": 0, "so2": 0},
    CONV: {"aire": 0, "fund": 1, "blis": 1, "so2": 1, "m3": 2},
    EW: {"kg": 1, "mm": 1, "v": 2, "kwh": 0},
}


@dataclass(frozen=True)
class Medicion:
    """Las magnitudes de un equipo con unos datos, y el peor nivel de su panel."""

    magnitudes: dict[str, float]
    filas: tuple[Fila, ...]

    @property
    def nivel(self) -> str:
        return peor_nivel(list(self.filas))


def medir(equipo: str, cambios: dict[str, float] | None = None) -> Medicion:
    """Calcula `equipo` con el ejemplo de la barra lateral más `cambios`."""
    flot, ew, flash, conv = armar_params({**valores_ejemplo(), **(cambios or {})})
    if equipo == FLOT:
        v = run_flotation(flot)
        mags = {"rec": 100.0 * v.recoveries["CuFeS2"], "ley": v.cu_grade_pct,
                "conc": v.concentrate_t_h, "relave": v.cu_tails_t_h}  # fmt: skip
        filas = filas_flotacion(v)
    elif equipo == FLASH:
        fv = run_flash(flash)
        r = fv.result
        mags = {"oc": r.oxygen_nm3_t, "enr": r.enrichment_pct, "fund": r.flux_pct,
                "mata": r.matte_kg, "esc": r.slag_kg, "so2": r.so2_kg}  # fmt: skip
        filas = filas_flash(fv)
    elif equipo == CONV:
        cv = run_converter(conv)
        mags = {"aire": cv.states[1].air_nm3 + cv.states[2].air_nm3, "fund": cv.flux_t,
                "blis": cv.states[2].lower_t, "so2": cv.so2_t,
                "m3": cv.states[2].lower_m3}  # fmt: skip
        filas = filas_convertidor(cv)
    else:
        ev = run_ew(ew)
        mags = {"kg": ev.cathode_kg, "mm": ev.thickness_mm, "v": ev.result.cell_voltage,
                "kwh": ev.result.specific_energy_kwh_t}  # fmt: skip
        filas = filas_ew(ev)
    return Medicion(mags, tuple(filas))


@cache
def _ejemplo(equipo: str) -> Medicion:
    return medir(equipo)


@cache
def pares(equipo: str) -> tuple[tuple[Experimento, Medicion, Medicion], ...]:
    """(experimento, ejemplo, tras el cambio) de cada experimento del equipo."""
    return tuple((e, _ejemplo(equipo), medir(equipo, e.cambios))
                 for e in EXPERIMENTOS if e.equipo == equipo)  # fmt: skip


def numeros(e: Experimento, a: Medicion, b: Medicion) -> dict[str, str]:
    """Las cifras del texto: de cada magnitud, `{m}0` (ejemplo), `{m}1` (tras el cambio), `{m}d`
    (diferencia absoluta) y `{m}p` (cambio relativo, %); de cada control, `{c}0` y `{c}1`."""
    out: dict[str, str] = {}
    for m, antes in a.magnitudes.items():
        dec = e.decimales.get(m, DECIMALES[e.equipo][m])
        despues = b.magnitudes[m]
        out[f"{m}0"], out[f"{m}1"] = es(antes, dec), es(despues, dec)
        out[f"{m}d"] = es(abs(despues - antes), dec)
        out[f"{m}p"] = es(abs(100.0 * (despues / antes - 1.0)), 1) if antes else ""
    example = valores_ejemplo()
    for c, nuevo in e.cambios.items():
        out[f"{c}0"], out[f"{c}1"] = num_g(example[c]), num_g(nuevo)
    return out


def pruebas_de(equipo: str) -> list[Prueba]:
    """Los experimentos de un equipo, con los números del modelo y los valores que fija su botón."""
    slug = SLUG[equipo]
    return [
        Prueba(
            e.clave,
            t("exp." + slug + "." + e.clave + ".titulo"),
            t("exp." + slug + "." + e.clave + ".texto", **numeros(e, a, b)),
            {PREFIX + c: v for c, v in e.cambios.items()},
        )  # fmt: skip
        for e, a, b in pares(equipo)
    ]
