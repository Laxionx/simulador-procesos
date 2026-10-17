"""Horno flash y convertidor de la app: las alturas de capa, el área del baño, el grosor de los
flujos y el color salen del cálculo (`procesos.fusion` y `procesos.conversion`) y de las
densidades documentadas en `app/densidades.py`. Cada fórmula de animación tiene una prueba que
falla si se la cambia."""

import math
import re
import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import calculo_piro as cp  # noqa: E402
import colores  # noqa: E402
import convertidor_svg as csvg  # noqa: E402
import densidades  # noqa: E402
import fusion_svg as fsvg  # noqa: E402
import graficos  # noqa: E402
from dibujo import es  # noqa: E402

LEYENDA = "esquema, no a escala: las cantidades sí son del cálculo"
FL = cp.FlashParams
CV = cp.ConverterParams


# ------------------------------------------------------------------ densidades
def test_valores_tabulados_de_las_densidades():
    assert densidades.CU2S_G_CM3 == 5.18  # Nagamori 1968, Aalto TKK-MT-215, Tabla 9
    assert densidades.FES_G_CM3 == 3.80
    assert densidades.slag_density_g_cm3() == 3.7
    assert densidades.copper_density_g_cm3(1200.0) * 1000 == pytest.approx(7902.5, abs=0.5)
    # Assael et al. 2010, ec. 1: en el punto de fusión, 7997 kg/m³
    assert densidades.copper_density_g_cm3(1357.77 - 273.15) * 1000 == pytest.approx(7997.0)


def test_mezcla_ideal_de_la_mata():
    assert densidades.matte_density_g_cm3(50.0) == pytest.approx(4.56, abs=0.005)
    one_over = 0.5 / 79.85 * 100 / 5.18 + (1 - 0.5 / 79.85 * 100) / 3.80
    assert densidades.matte_density_g_cm3(50.0) == pytest.approx(1 / one_over, rel=1e-12)
    assert densidades.matte_density_g_cm3(0.0) == pytest.approx(3.80)  # FeS puro
    assert densidades.matte_density_g_cm3(79.85) == pytest.approx(5.18)  # Cu2S puro
    assert densidades.matte_density_g_cm3(120.0) == pytest.approx(5.18)  # w acotado a [0, 1]
    assert densidades.matte_density_g_cm3(-5.0) == pytest.approx(3.80)


def test_la_densidad_de_la_mata_crece_con_la_ley():
    grid = [densidades.matte_density_g_cm3(g) for g in range(0, 81, 5)]
    assert grid == sorted(grid) and len(set(grid)) == len(grid)


def test_el_cobre_liquido_es_menos_denso_al_calentarse():
    assert densidades.copper_density_g_cm3(1100) > densidades.copper_density_g_cm3(1300)


# ------------------------------------------------------------------ color por temperatura
def test_la_luminosidad_del_color_crece_con_la_temperatura():
    temps = range(400, 1801, 20)
    lum = [colores.luminance(colores.temperature_rgb(t)) for t in temps]
    assert lum == sorted(lum) and lum[0] < lum[-1]
    assert colores.temperature_rgb(100) == colores.temperature_rgb(500)  # satura abajo
    assert colores.temperature_rgb(3000) == colores.temperature_rgb(1700)  # y arriba


def test_el_color_del_esquema_es_la_funcion_de_la_temperatura_del_calculo():
    for t in (1250.0, 1325.0):
        view = cp.run_flash(FL(products_c=t))
        svg_text = fsvg.flash_svg(view)
        assert 'class="pc-matte" ' in svg_text
        assert f'fill="{colores.temperature_color(t)}"' in svg_text
        assert f'fill="{colores.darker(colores.temperature_color(t))}"' in svg_text
    cold = fsvg.flash_svg(cp.run_flash(FL(products_c=1250.0)))
    hot = fsvg.flash_svg(cp.run_flash(FL(products_c=1325.0)))
    assert cold != hot
    for t in (1150.0, 1300.0):
        view = cp.run_converter(CV(bath_c=t))
        assert f'fill="{colores.temperature_color(t)}"' in csvg.converter_svg(view)


# ------------------------------------------------------------------ horno flash
def _layer(svg_text: str, kind: str) -> float:
    return float(re.search(rf'class="pc-{kind}" [^>]*? height="([\d.]+)"', svg_text).group(1))


def test_el_ejemplo_del_horno_reproduce_la_mezcla_1():
    view = cp.run_flash(FL())
    r = view.result
    assert r.oxygen_nm3_t == pytest.approx(161.8, abs=0.1)
    assert r.matte_kg == pytest.approx(387, abs=1)
    assert r.slag_kg == pytest.approx(516, abs=1)
    assert r.so2_kg == pytest.approx(396, abs=1)
    assert r.enrichment_pct == pytest.approx(50.7, abs=0.1)


@pytest.mark.parametrize(
    "params",
    [
        FL(),
        FL(blend=3, matte_grade=66.6, slag_sio2=27.5),
        FL(blend=2, matte_grade=60, slag_sio2=32, heat_loss_mj_t=250),
    ],
)
def test_alto_de_cada_capa_es_kg_por_t_sobre_densidad_por_la_escala(params):
    view = cp.run_flash(params)
    svg_text = fsvg.flash_svg(view)
    matte = view.result.matte_kg / 1000 / densidades.matte_density_g_cm3(view.result.matte_grade)
    slag = view.result.slag_kg / 1000 / 3.7
    assert _layer(svg_text, "matte") == pytest.approx(matte * fsvg.PX_PER_M3_T, abs=0.006)
    assert _layer(svg_text, "slag") == pytest.approx(slag * fsvg.PX_PER_M3_T, abs=0.006)
    assert view.matte_m3_t == pytest.approx(matte, rel=1e-12)
    assert view.slag_m3_t == pytest.approx(slag, rel=1e-12)


def test_la_escoria_va_sobre_la_mata_y_juntas_caben_en_el_horno():
    view = cp.run_flash(FL())
    svg_text = fsvg.flash_svg(view)
    y_matte = float(re.search(r'class="pc-matte" [^>]*? y="([\d.]+)"', svg_text).group(1))
    y_slag = float(re.search(r'class="pc-slag" [^>]*? y="([\d.]+)"', svg_text).group(1))
    assert y_slag + _layer(svg_text, "slag") == pytest.approx(y_matte, abs=0.01)  # apiladas
    assert y_slag > fsvg.SETTLER_TOP  # dentro del asentador
    for blend in (1, 2, 3, 4):
        v = cp.run_flash(FL(blend=blend))
        assert sum(fsvg.layer_heights(v)) < fsvg.BATH_BOTTOM - fsvg.SETTLER_TOP


@pytest.mark.parametrize("blend", [1, 2, 3, 4])
def test_grosor_de_las_flechas_es_proporcional_al_caudal(blend):
    view = cp.run_flash(FL(blend=blend))
    svg_text = fsvg.flash_svg(view)
    o2, so2 = view.result.oxygen_nm3_t, view.result.so2_kg
    widths = {
        c: float(w)
        for c, w in re.findall(
            r'stroke="(#[0-9A-F]{6})" stroke-width="([\d.]+)"'
            r' stroke-linecap="round"',
            svg_text,
        )
    }
    assert widths["#3B82A6"] == pytest.approx(o2 * fsvg.O2_PX_PER_NM3_T, abs=0.006)
    assert widths["#B8B0A0"] == pytest.approx(so2 * fsvg.SO2_PX_PER_KG_T, abs=0.006)
    assert fsvg.o2_width(2 * o2) == pytest.approx(2 * fsvg.o2_width(o2), rel=1e-12)
    assert fsvg.gas_width(2 * so2) == pytest.approx(2 * fsvg.gas_width(so2), rel=1e-12)


def test_la_rapidez_de_las_rayitas_es_proporcional_al_caudal():
    view = cp.run_flash(FL())
    durations = {
        float(d) for d in re.findall(r"animation-duration:([\d.]+)s", fsvg.flash_svg(view))
    }
    o2, so2 = view.result.oxygen_nm3_t, view.result.so2_kg
    assert any(
        d == pytest.approx(36.0 / (fsvg.O2_SPEED_PER_NM3_T * o2), abs=1e-3) for d in durations
    )
    assert any(
        d == pytest.approx(36.0 / (fsvg.SO2_SPEED_PER_KG_T * so2), abs=1e-3) for d in durations
    )


def test_el_esquema_del_horno_trae_numeros_y_rotulos():
    view = cp.run_flash(FL())
    svg_text = fsvg.flash_svg(view)
    r = view.result
    for expected in (es(view.matte_kg_t, 0) + " kg/t", es(view.slag_kg_t, 0) + " kg/t",
                     es(view.matte_m3_t, 3), es(view.slag_m3_t, 3), es(r.oxygen_nm3_t, 1),
                     es(r.so2_kg, 0), LEYENDA, "color ilustrativo de la temperatura",
                     "ilustrativas", "aprox."):  # fmt: skip
        assert expected in svg_text
    still = fsvg.flash_svg(view, paused=True)
    assert "animation" not in still and "pc-dash" in still  # sin animación, las rayitas quietas
    assert _layer(still, "matte") == _layer(svg_text, "matte")


def test_flash_con_metas_imposibles_falla_con_mensaje():
    with pytest.raises(ValueError, match="imposible|no alcanza|rango"):
        cp.run_flash(FL(matte_grade=45, slag_sio2=22))


# ------------------------------------------------------------------ convertidor
def _keyframe_values(svg_text: str, name: str, pattern: str) -> list[float]:
    start = svg_text.index(f"@keyframes {name}{{")
    segment = svg_text[start : svg_text.index("@keyframes", start + 1)]
    values = [float(v) for v in re.findall(pattern, segment)]
    return values[0:6:2]  # cada estado aparece dos veces (entra y sale de su tramo)


def _segment_area(y: float) -> float:
    """Área (px²) del baño bajo la superficie y, con la fórmula del segmento circular."""
    r = csvg.INNER
    h = csvg.CY + r - y
    return r * r * math.acos((r - h) / r) - (r - h) * math.sqrt(2 * r * h - h * h)


def test_el_ejemplo_del_convertidor_reproduce_ilo():
    view = cp.run_converter(CV())
    carga, escoria, cobre = view.states
    assert escoria.air_nm3 == pytest.approx(66_085, abs=1)
    assert cobre.air_nm3 == pytest.approx(68_136, abs=1)
    assert view.flux_t == pytest.approx(6.6, abs=0.05)
    assert escoria.slag_t == pytest.approx(25.7, abs=0.05)
    assert escoria.lower_t == pytest.approx(77.2, abs=0.05)
    assert cobre.slag_t == pytest.approx(0.6, abs=0.05)
    assert cobre.lower_t == pytest.approx(61.1, abs=0.05)
    assert view.so2_t == pytest.approx(47.1, abs=0.05)


def test_volumen_de_cada_fase_es_toneladas_sobre_densidad():
    view = cp.run_converter(CV())
    carga, escoria, cobre = view.states
    assert carga.lower_m3 == pytest.approx(100.0 / densidades.matte_density_g_cm3(62.0))
    assert escoria.slag_m3 == pytest.approx(escoria.slag_t / 3.7)
    assert cobre.lower_g_cm3 == pytest.approx(7.9025, abs=0.0005)
    assert cobre.lower_m3 == pytest.approx(cobre.lower_t / cobre.lower_g_cm3)


@pytest.mark.parametrize("params", [CV(), CV(matte_grade=55, eff_slag=0.8), CV(matte_grade=70)])
def test_area_del_bano_en_el_esquema_es_el_volumen_por_la_escala(params):
    view = cp.run_converter(params)
    svg_text = csvg.converter_svg(view)
    y0 = csvg.CY - csvg.RAD
    lows = _keyframe_values(svg_text, "pc-low", r"translateY\((-?[\d.]+)px\)")
    tops = _keyframe_values(svg_text, "pc-top", r"translateY\((-?[\d.]+)px\)")
    assert len(lows) == len(tops) == 3
    for state, low, top in zip(view.states, lows, tops, strict=True):
        area_low = csvg.PX2_PER_M3 * state.lower_m3
        area_total = area_low + csvg.PX2_PER_M3 * state.slag_m3
        assert _segment_area(y0 + low) == pytest.approx(area_low, rel=2e-3)
        assert _segment_area(y0 + top) == pytest.approx(area_total, rel=2e-3)


def test_el_nivel_sube_con_el_volumen_y_la_escoria_queda_arriba():
    ys = [csvg.level_y(a) for a in (1000, 5000, 10_000, 20_000, 40_000)]
    assert ys == sorted(ys, reverse=True)  # más área, superficie más arriba (y menor)
    view = cp.run_converter(CV())
    for state in view.states:
        low, top = csvg.levels(state)
        assert top <= low
    assert csvg.levels(view.states[0])[0] == csvg.levels(view.states[0])[1]  # sin escoria
    with pytest.raises(ValueError):
        csvg.level_y(csvg.PX2_PER_M3 * 1e3)  # no cabe


def test_charge_angle_da_el_area_de_un_segmento_circular():
    for fraction in (0.05, 0.3, 0.5, 0.8):
        theta = csvg.charge_angle(fraction)
        assert (theta - math.sin(theta)) / (2 * math.pi) == pytest.approx(fraction, rel=1e-9)
    assert csvg.charge_angle(0.5) == pytest.approx(math.pi)  # medio círculo: θ = π


@pytest.mark.parametrize("params", [CV(), CV(eff_slag=0.9, eff_copper=0.6)])
def test_grosor_del_aire_y_del_so2_es_proporcional_a_cada_soplado(params):
    view = cp.run_converter(params)
    svg_text = csvg.converter_svg(view)
    air = _keyframe_values(svg_text, "pc-air", r"stroke-width:([\d.]+)")
    gas = _keyframe_values(svg_text, "pc-gas", r"stroke-width:([\d.]+)")
    _, escoria, cobre = view.states
    assert air[0] == 0 and gas[0] == 0  # antes de soplar
    assert air[1] == pytest.approx(escoria.air_nm3 * csvg.AIR_PX_PER_NM3, abs=0.006)
    assert air[2] == pytest.approx(cobre.air_nm3 * csvg.AIR_PX_PER_NM3, abs=0.006)
    assert gas[1] == pytest.approx(escoria.so2_t * csvg.SO2_PX_PER_T, abs=0.006)
    assert gas[2] == pytest.approx(cobre.so2_t * csvg.SO2_PX_PER_T, abs=0.006)


def test_menos_eficiencia_pide_mas_aire_y_se_dibuja_mas_grueso():
    low = cp.run_converter(CV(eff_slag=0.5)).states[1].air_nm3
    high = cp.run_converter(CV(eff_slag=0.9)).states[1].air_nm3
    assert low > high
    assert csvg.air_width(low) > csvg.air_width(high)


@pytest.mark.parametrize("params", [CV(), CV(matte_grade=50, eff_copper=0.5)])
def test_cada_soplado_cierra_por_masa(params):
    view = cp.run_converter(params)
    rows = graficos.converter_balance_rows(view)
    for stage in ("Soplado a escoria", "Soplado a cobre"):
        entra = sum(t for s, c, t in rows if s == stage and c.startswith("entra"))
        sale = sum(t for s, c, t in rows if s == stage and c.startswith("sale"))
        assert entra == pytest.approx(sale, rel=1e-9)


def test_el_esquema_del_convertidor_trae_numeros_rotulos_y_la_version_quieta():
    view = cp.run_converter(CV())
    svg_text = csvg.converter_svg(view)
    for state in view.states:
        assert es(state.lower_t, 1) in svg_text and es(state.lower_m3, 1) in svg_text
    for expected in (LEYENDA, "ilustrativas", "aprox.", "color ilustrativo de la temperatura",
                     "@keyframes pc-low", "prefers-reduced-motion"):  # fmt: skip
        assert expected in svg_text
    still = csvg.converter_svg(view, paused=True)
    assert "@keyframes" not in still and "pc-low" not in still
    assert LEYENDA in still and "estado 2 de 3" in still


def test_convertidor_con_carga_imposible_falla_con_mensaje():
    with pytest.raises(ValueError):
        cp.run_converter(CV(matte_grade=85.0))


def test_los_esquemas_nuevos_no_ejecutan_codigo():
    for s in (fsvg.flash_svg(cp.run_flash(FL())), csvg.converter_svg(cp.run_converter(CV()))):
        low = s.lower()
        assert "<script" not in low and "onload" not in low and "javascript:" not in low
