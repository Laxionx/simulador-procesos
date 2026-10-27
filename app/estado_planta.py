"""Chequeos del panel «Estado de la operación» de cada equipo. Solo de dos tipos: DEFINICIÓN o
validez del cálculo (cierre de balances, metas cumplidas, avisos que ya emite el modelo) y rangos
con FUENTE ya citada en el repo (`docs/`, `procesos/fusion_datos.py`). Cada chequeo lleva su
criterio y su fuente en la ayuda (claves `*.crit.*`); si un rango no tiene fuente, no va.

Los números salen de los resultados de `calculo.py` y `calculo_piro.py`; nada de lo que escribe el
visitante entra al texto (los avisos del modelo se traducen con `tw`)."""

from __future__ import annotations

from calculo import EWView, FlotationView, faraday_mass_kg
from calculo_piro import ConverterView, FlashView
from dibujo import es
from estado import Fila, cientifico
from graficos import converter_balance_rows
from i18n import t, tw

from procesos.fusion_datos import INDUSTRIAL, T_PRODUCTS_C

TOL_CIERRE = 1e-9  # relativa (flotación, masa) o en kmol (por elemento): docs/*.md, Validación
TOL_CALOR_MJ_T = 1e-6  # cierre de calor del horno (docs/fusion.md:90)
TOL_META = 1e-9  # ley de mata y SiO₂ de la escoria cumplidas (docs/fusion.md:91)
# Eficiencia de O₂ medida en Flin Flon (Kyllo 1995, Tabla IV-XII; docs/conversion.md:151)
EFF_ESCORIA_FLIN_FLON = (0.55, 0.68)
EFF_COBRE_FLIN_FLON = (0.72, 0.82)
# Voltaje de una celda típica de EW de cobre (Beukes y Badenhorst 2009; docs/ew.md:61)
VOLTAJE_TIPICO_V = (1.9, 2.3)
SEGUNDOS_POR_HORA = 3600.0


def _ok(dentro: bool, nivel_fuera: str = "aviso") -> str:
    return "ok" if dentro else nivel_fuera


# ------------------------------------------------------------------ flotación
def error_cierre_flot(view: FlotationView) -> float:
    """Error relativo máximo entre la suma celda a celda y lo que da el modelo para el banco
    entero (alimentación × recuperación), por especie."""
    por_especie = {"CuFeS2": view.cu_t_h, "SiO2": view.gangue_t_h, "H2O": view.water_t_h}
    return max(
        abs(sum(celdas) - view.feed_t_h[sp] * view.recoveries[sp]) / view.feed_t_h[sp]
        for sp, celdas in por_especie.items()
    )


def filas_flotacion(view: FlotationView) -> list[Fila]:
    rec, r_inf = view.recoveries["CuFeS2"], view.params.r_inf
    err = error_cierre_flot(view)
    filas = [
        Fila(_ok(err <= TOL_CIERRE, "mal"),
             t("flot.chk.cierre", err=cientifico(err), tol=cientifico(TOL_CIERRE)),
             t("flot.crit.cierre")),
        Fila(_ok(rec <= r_inf * (1.0 + TOL_CIERRE), "mal"),
             t("flot.chk.rinf", rec=es(100.0 * rec, 2), rinf=es(100.0 * r_inf, 2)),
             t("flot.crit.rinf")),
    ]  # fmt: skip
    return filas


# ------------------------------------------------------------------ horno flash
def _rango_publicado(columna: int) -> tuple[float, float]:
    """(mínimo, máximo) de una columna de la Tabla 13 (`INDUSTRIAL`) entre las cuatro mezclas."""
    valores = [fila[columna] for fila in INDUSTRIAL.values()]
    return min(valores), max(valores)


def filas_flash(view: FlashView) -> list[Fila]:
    p, r = view.params, view.result
    entra, sale = r.elements()
    err_el = max(abs(entra[e] - sale[e]) for e in entra)
    h_in, h_out = r.enthalpies()
    err_calor = abs(h_in - h_out - r.heat_loss_mj_t)
    err_meta = max(abs(r.matte_grade - p.matte_grade), abs(r.slag_sio2 - p.slag_sio2))
    variables = (
        ("grade", p.matte_grade, _rango_publicado(3)),
        ("sio2", p.slag_sio2, _rango_publicado(4)),
        ("loss", p.heat_loss_mj_t, _rango_publicado(5)),
    )
    fuera = [t("flash.var." + k) for k, v, (lo, hi) in variables if not lo <= v <= hi]
    rangos = {f"{k}_{lim}": es(x, 1) for k, _, (lo, hi) in variables for lim, x in
              (("lo", lo), ("hi", hi))}  # fmt: skip
    if fuera:
        cobertura = Fila("aviso", t("flash.chk.cobertura.fuera", lista=", ".join(fuera),
                                    **rangos), t("flash.crit.cobertura"))  # fmt: skip
    else:
        cobertura = Fila("ok", t("flash.chk.cobertura.ok", **rangos), t("flash.crit.cobertura"))
    temp_ok = abs(p.products_c - T_PRODUCTS_C) < TOL_CIERRE
    filas = [
        Fila(_ok(err_el <= TOL_CIERRE, "mal"),
             t("flash.chk.elementos", err=cientifico(err_el), tol=cientifico(TOL_CIERRE)),
             t("flash.crit.elementos")),
        Fila(_ok(err_calor <= TOL_CALOR_MJ_T, "mal"),
             t("flash.chk.calor", err=cientifico(err_calor), tol=cientifico(TOL_CALOR_MJ_T)),
             t("flash.crit.calor")),
        Fila(_ok(err_meta <= TOL_META, "mal"),
             t("flash.chk.metas", err=cientifico(err_meta), tol=cientifico(TOL_META)),
             t("flash.crit.metas")),
        cobertura,
        Fila(_ok(temp_ok), t("flash.chk.temp", temp=es(p.products_c, 0), ref=es(T_PRODUCTS_C, 0)),
             t("flash.crit.temp")),
    ]  # fmt: skip
    return filas


# ------------------------------------------------------------------ convertidor
def error_cierre_masa(view: ConverterView) -> float:
    """Error relativo máximo de masa de un soplado: (lo que entra − lo que sale) ÷ lo que entra,
    con las mismas cifras del gráfico de balance."""
    entra: dict[str, float] = {}
    sale: dict[str, float] = {}
    for soplado, concepto, tonelada in converter_balance_rows(view):
        lado = entra if concepto.startswith("entra") else sale
        lado[soplado] = lado.get(soplado, 0.0) + tonelada
    return max(abs(entra[s] - sale[s]) / entra[s] for s in entra)


def error_cierre_elementos(view: ConverterView) -> float:
    """Error máximo (kmol) del balance por elemento (Cu, Fe, S, O) de los dos soplados."""
    err = 0.0
    for etapa in view.stages:
        entra, sale = etapa.elements()
        err = max(err, *(abs(entra[e] - sale[e]) for e in entra))
    return err


def filas_convertidor(view: ConverterView) -> list[Fila]:
    p = view.params
    err_el, err_masa = error_cierre_elementos(view), error_cierre_masa(view)
    lo_e, hi_e = EFF_ESCORIA_FLIN_FLON
    lo_c, hi_c = EFF_COBRE_FLIN_FLON
    en_escoria = lo_e <= p.eff_slag <= hi_e
    en_cobre = lo_c <= p.eff_copper <= hi_c
    fuera = [t("conv.var." + k) for k, ok in (("escoria", en_escoria), ("cobre", en_cobre))
             if not ok]  # fmt: skip
    rangos = {"lo_e": es(100 * lo_e, 0), "hi_e": es(100 * hi_e, 0), "lo_c": es(100 * lo_c, 0),
              "hi_c": es(100 * hi_c, 0)}  # fmt: skip
    if fuera:
        eficiencia = Fila("aviso", t("conv.chk.eficiencia.fuera", lista=", ".join(fuera),
                                     **rangos), t("conv.crit.eficiencia"))  # fmt: skip
    else:
        eficiencia = Fila("ok", t("conv.chk.eficiencia.ok", **rangos), t("conv.crit.eficiencia"))
    return [
        Fila(_ok(err_el <= TOL_CIERRE, "mal"),
             t("conv.chk.elementos", err=cientifico(err_el), tol=cientifico(TOL_CIERRE)),
             t("conv.crit.elementos")),
        Fila(_ok(err_masa <= TOL_CIERRE, "mal"),
             t("conv.chk.masa", err=cientifico(err_masa), tol=cientifico(TOL_CIERRE)),
             t("conv.crit.masa")),
        eficiencia,
    ]  # fmt: skip


# ------------------------------------------------------------------ electroobtención
def filas_ew(view: EWView) -> list[Fila]:
    p, res = view.params, view.result
    faraday = faraday_mass_kg(p.current_density, p.efficiency, 2.0 * p.face_area_m2,
                              p.cycle_days * 24.0 * SEGUNDOS_POR_HORA)  # fmt: skip
    err = abs(view.cathode_kg - faraday) / faraday
    lo, hi = VOLTAJE_TIPICO_V
    filas = [Fila("aviso", tw(w), t("ew.crit.avisos")) for w in view.warnings]
    if not view.warnings:
        filas.append(Fila("ok", t("ew.chk.sin_avisos"), t("ew.crit.avisos")))
    filas += [
        Fila(_ok(err <= TOL_CIERRE, "mal"),
             t("ew.chk.faraday", kg=es(view.cathode_kg, 2), err=cientifico(err),
               tol=cientifico(TOL_CIERRE)), t("ew.crit.faraday")),
        Fila(_ok(lo <= res.cell_voltage <= hi),
             t("ew.chk.voltaje", v=es(res.cell_voltage, 2), lo=es(lo, 1), hi=es(hi, 1)),
             t("ew.crit.voltaje")),
    ]  # fmt: skip
    return filas
