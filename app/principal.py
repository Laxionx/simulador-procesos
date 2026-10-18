"""App «Planta completa» (Full plant) del simulador de procesos: equipos metalúrgicos animados
según su cálculo real, en español e inglés (`?lang=en`). Pestañas: Guía, Flotación, Horno flash,
Convertidor y Electroobtención (se suma un equipo agregando una entrada a TABS)."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Streamlit Community Cloud instala solo requirements.txt: el paquete se importa desde la raíz,
# y los módulos de la app, desde esta carpeta.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

from calculo import EWParams, FlotationParams, run_ew, run_flotation  # noqa: E402
from calculo_piro import ConverterParams, FlashParams, run_converter, run_flash  # noqa: E402
from controles import CONV, EW, FLASH, FLOT, sidebar_config  # noqa: E402
from convertidor_svg import converter_svg  # noqa: E402
from dibujo import MOTION_CSS, as_images, es  # noqa: E402
from ew_svg import ew_svg  # noqa: E402
from flotacion_svg import flotation_svg  # noqa: E402
from fusion_svg import flash_svg  # noqa: E402
from graficos import converter_figure, recovery_figure, voltage_figure  # noqa: E402
from guia import ficha, guide_tab  # noqa: E402
from i18n import activate, sidebar_selector, t, tr_error, tw  # noqa: E402

from procesos.fusion_datos import PAPER_MODEL  # noqa: E402

activate()  # idioma de esta corrida: la sesión o `?lang=` (solo es o en)
st.set_page_config(page_title=t("page.title"), layout="wide")


def flotation_tab(params: FlotationParams, animate: bool) -> None:
    ficha(FLOT)
    try:
        view = run_flotation(params)
    except (ValueError, ArithmeticError) as exc:
        st.error(t("flot.err", exc=tr_error(str(exc))))
        return
    rec = view.recoveries
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("flot.m1"), f"{es(100 * rec['CuFeS2'])} %")
    c2.metric(t("flot.m2"), f"{es(100 * rec['SiO2'])} %")
    c3.metric(t("flot.m3"), es(view.concentrate_t_h))
    c4.metric(t("flot.m4"), f"{es(view.cu_grade_pct)} %")
    st.html(as_images(flotation_svg(view, paused=not animate), flotation_svg(view, paused=True),
                      t("flot.alt")))  # fmt: skip
    st.caption(t("flot.cap1"))
    st.plotly_chart(recovery_figure(view), width="stretch")
    st.caption(t("flot.cap2"))
    table = {
        t("flot.col.cell"): list(range(1, params.cells + 1)),
        t("flot.col.cu"): [round(x, 3) for x in view.cu_t_h],
        t("flot.col.sio2"): [round(x, 3) for x in view.gangue_t_h],
        t("flot.col.water"): [round(x, 3) for x in view.water_t_h],
        t("flot.col.cum"): [round(100 * x, 1) for x in view.cu_cumulative],
    }
    st.dataframe(table, hide_index=True)
    st.caption(t("flot.cap3"))


def ew_tab(params: EWParams, animate: bool) -> None:
    ficha(EW)
    try:
        view = run_ew(params)
    except (ValueError, ArithmeticError) as exc:
        st.error(t("ew.err", exc=tr_error(str(exc))))
        return
    for warning in view.warnings:
        st.warning(tw(warning))
    res = view.result
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("ew.m1"), f"{es(res.current_a, 0)} A")
    c2.metric(t("ew.m2"), f"{es(res.cell_voltage, 2)} V")
    c3.metric(t("ew.m3"), f"{es(res.power_kw, 2)} kW")
    c4.metric(t("ew.m4"), f"{es(res.specific_energy_kwh_t, 0)} kWh/t")
    st.html(as_images(ew_svg(view, paused=not animate), ew_svg(view, paused=True),
                      t("ew.alt")))  # fmt: skip
    st.caption(t("ew.cap", kg=es(view.cathode_kg, 1), mm=es(view.thickness_mm, 2)))
    st.plotly_chart(voltage_figure(view), width="stretch")


def flash_tab(params: FlashParams, animate: bool) -> None:
    ficha(FLASH)
    try:
        view = run_flash(params)
    except ValueError as exc:  # SmeltingError y datos fuera del rango termodinámico
        st.error(t("flash.err", exc=tr_error(str(exc))))
        return
    r = view.result
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("flash.m1"), es(view.matte_kg_t, 0))
    c2.metric(t("flash.m2"), es(view.slag_kg_t, 0))
    c3.metric(t("flash.m3"), es(r.oxygen_nm3_t, 1))
    c4.metric(t("flash.m4"), es(r.so2_kg, 0))
    st.html(as_images(flash_svg(view, paused=not animate), flash_svg(view, paused=True),
                      t("flash.alt")))  # fmt: skip
    st.caption(t("flash.cap", matte_m3=es(view.matte_m3_t, 3), slag_m3=es(view.slag_m3_t, 3)))
    oc, oe, flux, grade, sio2, loss = view.plant
    paper_oc, paper_oe, paper_flux = PAPER_MODEL[f"Mezcla {params.blend}"]
    st.markdown(t("flash.head", blend=params.blend))
    st.dataframe(
        {
            "": [t("flash.row.o2"), t("flash.row.air"), t("flash.row.flux")],
            t("flash.col.this"): [round(r.oxygen_nm3_t, 1), round(r.enrichment_pct, 1),
                                  round(r.flux_pct, 2)],
            t("flash.col.paper"): [paper_oc, paper_oe, paper_flux],
            t("flash.col.plant"): [oc, oe, flux],
        },
        hide_index=True,
    )  # fmt: skip
    st.caption(t("flash.cap2", grade=es(grade), sio2=es(sio2), loss=es(loss)))


def converter_tab(params: ConverterParams, animate: bool) -> None:
    ficha(CONV)
    try:
        view = run_converter(params)
    except ValueError as exc:  # ConversionError y datos fuera del rango termodinámico
        st.error(t("conv.err", exc=tr_error(str(exc))))
        return
    carga, escoria, cobre = view.states
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("conv.m1"), es(escoria.air_nm3 + cobre.air_nm3, 0))
    c2.metric(t("conv.m2"), es(view.flux_t, 1))
    c3.metric(t("conv.m3"), es(cobre.lower_t, 1))
    c4.metric(t("conv.m4"), es(view.so2_t, 1))
    st.html(as_images(converter_svg(view, paused=not animate), converter_svg(view, paused=True),
                      t("conv.alt")))  # fmt: skip
    st.caption(
        t(
            "conv.cap",
            charge=es(carga.lower_m3, 1),
            slag_end=es(escoria.lower_m3 + escoria.slag_m3, 1),
            white=es(escoria.lower_m3, 1),
            slag=es(escoria.slag_m3, 1),
            cu_end=es(cobre.lower_m3 + cobre.slag_m3, 1),
            blister=es(cobre.lower_m3, 1),
            slag2=es(cobre.slag_m3, 1),
        )  # fmt: skip
    )
    st.plotly_chart(converter_figure(view), width="stretch")
    st.caption(t("conv.cap2"))


TABS = (
    ("tab.guide", None),
    (FLOT, flotation_tab),
    (FLASH, flash_tab),
    (CONV, converter_tab),
    (EW, ew_tab),
)


def main() -> None:
    sidebar_selector()
    st.title(t("app.title"))
    st.caption(t("app.caption"))
    st.html(MOTION_CSS)
    flot_params, ew_params, flash_params, conv_params = sidebar_config()
    animate = st.toggle(t("toggle.label"), value=True, help=t("toggle.help"))
    params = {FLOT: flot_params, EW: ew_params, FLASH: flash_params, CONV: conv_params}
    names = [t(key) if key == "tab.guide" else t("group." + key) for key, _ in TABS]
    for tab, (key, draw) in zip(st.tabs(names), TABS, strict=True):
        with tab:
            if draw is None:
                guide_tab()
            else:
                draw(params[key], animate)


main()
