"""App «Planta completa» del simulador de procesos: equipos metalúrgicos animados según su
cálculo real. Pestañas: Guía, Flotación, Horno flash, Convertidor y Electroobtención (se suma
un equipo agregando una entrada a TABS)."""

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

from procesos.fusion_datos import PAPER_MODEL  # noqa: E402

st.set_page_config(page_title="Simulador de planta de cobre", layout="wide")


def flotation_tab(params: FlotationParams, animate: bool) -> None:
    ficha(FLOT)
    try:
        view = run_flotation(params)
    except (ValueError, ArithmeticError) as exc:
        st.error(f"No se pudo calcular el banco con estos datos: {exc}")
        return
    rec = view.recoveries
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Recuperación de Cu (CuFeS₂)", f"{es(100 * rec['CuFeS2'])} %")
    c2.metric("Recuperación de SiO₂ (supuesto)", f"{es(100 * rec['SiO2'])} %")
    c3.metric("Concentrado (t/h de sólidos)", es(view.concentrate_t_h))
    c4.metric("Ley de Cu del concentrado", f"{es(view.cu_grade_pct)} %")
    st.html(as_images(flotation_svg(view, paused=not animate), flotation_svg(view, paused=True),
                      "Banco de flotación con celdas en serie"))  # fmt: skip
    st.caption(
        "Las burbujas cargadas de Cu suben al ritmo de su constante cinética k. La espuma de "
        "cada celda es tan gruesa como los t/h de sólidos que manda al concentrado. La SiO₂ y el "
        "agua no tienen cinética en el modelo: solo se conoce su recuperación total, y se reparte "
        "pareja entre celdas (supuesto del ejemplo)."
    )
    st.plotly_chart(recovery_figure(view), width="stretch")
    st.caption(
        "Los puntos medidos son los del banco A de Los Pelambres (9 celdas, τ de 4,1 min): solo "
        "se comparan con el modelo si los datos son los del ejemplo."
    )
    table = {
        "Celda": list(range(1, params.cells + 1)),
        "CuFeS₂ al concentrado (t/h)": [round(x, 3) for x in view.cu_t_h],
        "SiO₂ al concentrado (t/h)": [round(x, 3) for x in view.gangue_t_h],
        "Agua al concentrado (t/h)": [round(x, 3) for x in view.water_t_h],
        "Cu recuperado acumulado (%)": [round(100 * x, 1) for x in view.cu_cumulative],
    }
    st.dataframe(table, hide_index=True)
    st.caption("La suma de cada columna por celda es lo que el modelo da para el banco entero.")


def ew_tab(params: EWParams, animate: bool) -> None:
    ficha(EW)
    try:
        view = run_ew(params)
    except (ValueError, ArithmeticError) as exc:
        st.error(f"No se pudo calcular la celda con estos datos: {exc}")
        return
    for warning in view.warnings:
        st.warning(warning)
    res = view.result
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Corriente (un cátodo)", f"{es(res.current_a, 0)} A")
    c2.metric("Voltaje de celda", f"{es(res.cell_voltage, 2)} V")
    c3.metric("Potencia (un cátodo)", f"{es(res.power_kw, 2)} kW")
    c4.metric("Energía específica", f"{es(res.specific_energy_kwh_t, 0)} kWh/t")
    st.html(as_images(ew_svg(view, paused=not animate), ew_svg(view, paused=True),
                      "Celda de electroobtención con cátodos que engordan"))  # fmt: skip
    st.caption(
        f"Cada cátodo termina el ciclo con **{es(view.cathode_kg, 1)} kg** de cobre y "
        f"**{es(view.thickness_mm, 2)} mm** por cara (Faraday × eficiencia; espesor = masa ÷ "
        "(densidad del Cu × área de las dos caras)). El dibujo exagera el espesor; los números "
        "son los reales."
    )
    st.plotly_chart(voltage_figure(view), width="stretch")


def flash_tab(params: FlashParams, animate: bool) -> None:
    ficha(FLASH)
    try:
        view = run_flash(params)
    except ValueError as exc:  # SmeltingError y datos fuera del rango termodinámico
        st.error(f"No se pudo calcular el horno con estos datos: {exc}")
        return
    r = view.result
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mata (kg/t de concentrado)", es(view.matte_kg_t, 0))
    c2.metric("Escoria (kg/t)", es(view.slag_kg_t, 0))
    c3.metric("O₂ técnico (Nm³/t)", es(r.oxygen_nm3_t, 1))
    c4.metric("SO₂ (kg/t)", es(r.so2_kg, 0))
    st.html(as_images(flash_svg(view, paused=not animate), flash_svg(view, paused=True),
                      "Horno flash con torre de reacción y asentador"))  # fmt: skip
    st.caption(
        f"Mata: {es(view.matte_m3_t, 3)} m³ por t de concentrado; escoria: {es(view.slag_m3_t, 3)} "
        "m³. El alto de cada capa es proporcional a ese volumen (kg ÷ densidad). Densidades "
        "de dibujo: mata 4,8 g/cm³ por mezcla ideal (±10 %), escoria 3,7 g/cm³ (aprox.)."
    )
    oc, oe, flux, grade, sio2, loss = view.plant
    paper_oc, paper_oe, paper_flux = PAPER_MODEL[f"Mezcla {params.blend}"]
    st.markdown(f"**Modelo frente a la planta** (mezcla {params.blend}, Bacedoni et al. 2020)")
    st.dataframe(
        {
            "": ["Consumo de O₂ (Nm³/t)", "O₂ en el aire (% vol.)", "Fundente (% de la carga)"],
            "Este cálculo": [round(r.oxygen_nm3_t, 1), round(r.enrichment_pct, 1),
                             round(r.flux_pct, 2)],
            "Modelo del artículo (Tabla 14)": [paper_oc, paper_oe, paper_flux],
            "Planta (Tabla 13)": [oc, oe, flux],
        },
        hide_index=True,
    )  # fmt: skip
    st.caption(
        f"La planta operó esta mezcla con mata de {es(grade)} % Cu, {es(sio2)} % de SiO₂ en la "
        f"escoria y {es(loss)} MJ/t de pérdida; los controles no cambian solos al elegir la "
        "mezcla. El modelo del artículo tampoco iguala el consumo de O₂ medido."
    )


def converter_tab(params: ConverterParams, animate: bool) -> None:
    ficha(CONV)
    try:
        view = run_converter(params)
    except ValueError as exc:  # ConversionError y datos fuera del rango termodinámico
        st.error(f"No se pudo calcular el convertidor con estos datos: {exc}")
        return
    carga, escoria, cobre = view.states
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Aire total (Nm³ por 100 t de mata)", es(escoria.air_nm3 + cobre.air_nm3, 0))
    c2.metric("Fundente (t)", es(view.flux_t, 1))
    c3.metric("Blíster (t)", es(cobre.lower_t, 1))
    c4.metric("SO₂ (t)", es(view.so2_t, 1))
    st.html(as_images(converter_svg(view, paused=not animate), converter_svg(view, paused=True),
                      "Convertidor Peirce-Smith en corte transversal"))  # fmt: skip
    st.caption(
        f"Volumen del baño: {es(carga.lower_m3, 1)} m³ de mata al cargar; "
        f"{es(escoria.lower_m3 + escoria.slag_m3, 1)} m³ al fin del soplado a escoria "
        f"({es(escoria.lower_m3, 1)} de metal blanco y {es(escoria.slag_m3, 1)} de escoria); "
        f"{es(cobre.lower_m3 + cobre.slag_m3, 1)} m³ al fin del soplado a cobre "
        f"({es(cobre.lower_m3, 1)} de blíster y {es(cobre.slag_m3, 1)} de escoria)."
    )
    st.plotly_chart(converter_figure(view), width="stretch")
    st.caption(
        "Cada soplado cierra por masa: lo que entra, con el O₂ que reacciona, es lo que sale."
    )


TABS = (
    ("Guía", None),
    (FLOT, flotation_tab),
    (FLASH, flash_tab),
    (CONV, converter_tab),
    (EW, ew_tab),
)


def main() -> None:
    st.title("Simulador de planta de cobre")
    st.caption(
        "Equipos animados según su cálculo real, desde ecuaciones publicadas. Empieza por la "
        "**Guía**; los datos se cambian en la barra lateral."
    )
    st.html(MOTION_CSS)
    flot_params, ew_params, flash_params, conv_params = sidebar_config()
    animate = st.toggle(
        "Mover los equipos", value=True,
        help="Apaga las animaciones de los esquemas. También se apagan solas si el sistema "
        "tiene activado «reducir movimiento».",
    )  # fmt: skip
    params = {FLOT: flot_params, EW: ew_params, FLASH: flash_params, CONV: conv_params}
    for tab, (name, draw) in zip(st.tabs([n for n, _ in TABS]), TABS, strict=True):
        with tab:
            if draw is None:
                guide_tab()
            else:
                draw(params[name], animate)


main()
