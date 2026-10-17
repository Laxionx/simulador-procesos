"""Las animaciones de la app salen del cálculo, no de un dibujo aparte: el ritmo de las burbujas,
el grosor de la espuma, el espesor del depósito y los rótulos se deducen de los números que
calculan `procesos.flotacion` y `procesos.ew`. Cada fórmula de animación tiene una prueba que
falla si se la cambia (mutaciones comprobadas a mano, ver el commit)."""

import re
import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import calculo  # noqa: E402
import ew_svg  # noqa: E402
import flotacion_svg as fsvg  # noqa: E402
from dibujo import es  # noqa: E402

from procesos import Flotation, Stream  # noqa: E402
from procesos.ew import FARADAY  # noqa: E402
from procesos.flotacion import cells_recovery  # noqa: E402

F = calculo.FlotationParams
E = calculo.EWParams
DURATION = re.compile(r'class="pc-rise" style="--d:[\d.]+px;animation-duration:([\d.]+)s')
BANCO_A_MODELADO = (55.0, 87.3, 92.8, 93.8, 93.9)  # Vinnett et al. 2022, constante única
LEYENDA = "esquema, no a escala: las cantidades sí son del cálculo"


def _durations(svg_text: str) -> list[float]:
    return [float(x) for x in DURATION.findall(svg_text)]


def _loaded(durations: list[float]) -> list[float]:
    """Duraciones de las burbujas cargadas (las del arrastre de la ganga tienen ritmo fijo)."""
    return sorted({d for d in durations if d != fsvg.GANGUE_RISE_S})


def _froth(svg_text: str, kind: str) -> dict[int, float]:
    pat = rf'class="pc-froth-{kind}" data-cell="(\d+)" [^>]*? height="([\d.]+)"'
    return {int(i): float(h) for i, h in re.findall(pat, svg_text)}


# ------------------------------------------------------------------ flotación
@pytest.mark.parametrize("k", [0.1, 0.35, 1.0, 2.0])
def test_ritmo_de_las_burbujas_cargadas_es_proporcional_a_k(k):
    assert fsvg.bubble_rate(k) == pytest.approx(fsvg.BUBBLE_RATE_PER_K * k, rel=1e-12)
    svg_text = fsvg.flotation_svg(calculo.run_flotation(F(k=k)))
    loaded = _loaded(_durations(svg_text))
    assert loaded, "no hay burbujas cargadas dibujadas"
    for d in loaded:  # llegadas por segundo = burbujas del ciclo / duración = ritmo del cálculo
        assert fsvg.BUBBLES_PER_CELL / d == pytest.approx(fsvg.bubble_rate(k), rel=1e-3)


def test_duplicar_k_duplica_el_ritmo_dibujado():
    slow = _loaded(_durations(fsvg.flotation_svg(calculo.run_flotation(F(k=0.2)))))
    fast = _loaded(_durations(fsvg.flotation_svg(calculo.run_flotation(F(k=0.4)))))
    assert slow[0] == pytest.approx(2 * fast[0], rel=1e-3)


def _loaded_per_cell(svg_text: str) -> dict[int, int]:
    counts: dict[int, int] = {}
    for cell in re.findall(r'class="pc-loaded" data-cell="(\d+)"', svg_text):
        counts[int(cell)] = counts.get(int(cell), 0) + 1
    return counts


@pytest.mark.parametrize("params", [F(), F(cells=5, k=1.0), F(cells=15, tau_min=1.0, k=0.1)])
def test_burbujas_cargadas_por_celda_son_proporcionales_al_cu_que_manda(params):
    view = calculo.run_flotation(params)
    svg_text = fsvg.flotation_svg(view)
    counts = _loaded_per_cell(svg_text)
    n = [counts.get(i + 1, 0) for i in range(params.cells)]
    assert n == fsvg.loaded_counts(view)
    assert n == sorted(n, reverse=True)  # no crece a lo largo del banco
    assert n[0] == fsvg.BUBBLES_PER_CELL  # la celda con más Cu lleva todas
    top = max(view.cu_t_h)
    for count, mass in zip(n, view.cu_t_h, strict=True):  # proporcional, salvo el redondeo
        assert abs(count - fsvg.BUBBLES_PER_CELL * mass / top) <= 0.5 + 1e-9
    still = _loaded_per_cell(fsvg.flotation_svg(view, paused=True))
    assert still == counts


def test_en_la_ultima_celda_casi_no_flota_cu():
    view = calculo.run_flotation(F())
    n = fsvg.loaded_counts(view)
    assert n[-1] <= 1 and n[0] == 6  # la celda 9 casi no tiene Cu que cargar


def test_la_ganga_no_tiene_ritmo_cinetico():
    # el arrastre fijo sube siempre igual, cambien la k o su recuperación
    for params in (F(k=0.1), F(k=2.0), F(gangue_recovery=0.3)):
        ds = _durations(fsvg.flotation_svg(calculo.run_flotation(params)))
        assert fsvg.GANGUE_RISE_S in ds


@pytest.mark.parametrize("params", [F(), F(cells=4, k=1.2), F(cells=15, gangue_recovery=0.2)])
def test_grosor_de_la_espuma_es_proporcional_a_la_masa_al_concentrado(params):
    view = calculo.run_flotation(params)
    svg_text = fsvg.flotation_svg(view)
    cu, gangue = _froth(svg_text, "cu"), _froth(svg_text, "gangue")
    scale = fsvg.FROTH_MAX_PX / max(view.solids_t_h)
    totals = []
    for i in range(params.cells):
        assert gangue.get(i + 1, 0.0) == pytest.approx(view.gangue_t_h[i] * scale, abs=0.006)
        assert cu.get(i + 1, 0.0) == pytest.approx(view.cu_t_h[i] * scale, abs=0.006)
        totals.append(cu.get(i + 1, 0.0) + gangue.get(i + 1, 0.0))
        assert totals[-1] == pytest.approx(view.solids_t_h[i] * scale, abs=0.012)
    assert max(totals) == pytest.approx(fsvg.FROTH_MAX_PX, abs=0.012)


def test_suma_por_celda_es_el_total_del_modelo():
    p = F()
    view = calculo.run_flotation(p)
    unit = Flotation(
        "B", ("A",), ("C", "R"), {"CuFeS2": (p.r_inf, p.k)}, p.cells, tau_min=p.tau_min,
        fixed={"SiO2": p.gangue_recovery, "H2O": calculo.WATER_RECOVERY},
    )  # fmt: skip
    conc, _ = unit.compute([Stream(calculo.FEED_KG_H)], calculo.FLOTATION_CATALOG)
    assert sum(view.cu_t_h) * 1000 == pytest.approx(conc.flow("CuFeS2"), rel=1e-9)
    assert sum(view.gangue_t_h) * 1000 == pytest.approx(conc.flow("SiO2"), rel=1e-9)
    assert sum(view.water_t_h) * 1000 == pytest.approx(conc.flow("H2O"), rel=1e-9)
    assert view.concentrate_t_h * 1000 == pytest.approx(
        conc.flow("CuFeS2") + conc.flow("SiO2"), rel=1e-9
    )


def test_ley_de_cu_del_concentrado_es_cu_contenido_sobre_solidos():
    view = calculo.run_flotation(F())
    cu_kg = sum(view.cu_t_h) * 0.3463  # 63,546 / 183,5 de Cu en la calcopirita
    assert view.cu_grade_pct == pytest.approx(100 * cu_kg / view.concentrate_t_h, rel=1e-3)
    assert 10 < view.cu_grade_pct < 13  # concentrado rougher, antes de la limpieza


def test_recuperacion_acumulada_sale_de_cells_recovery():
    p = F(cells=7, tau_min=3.3, r_inf=0.9, k=0.5)
    view = calculo.run_flotation(p)
    for i, r in enumerate(view.cu_cumulative, start=1):
        assert r == pytest.approx(cells_recovery("primer_orden", 0.9, 0.5, 3.3, i), rel=1e-12)
    inc = [b - a for a, b in zip([0.0, *view.cu_cumulative], view.cu_cumulative, strict=False)]
    assert all(x > 0 for x in inc) and inc == sorted(inc, reverse=True)  # cada celda, menos


def test_reparto_parejo_de_la_ganga_deja_una_fraccion_constante_de_lo_que_queda():
    masses = calculo.per_cell_mass(585.1, 0.05, 9)
    left = 585.1
    fractions = []
    for m in masses:
        fractions.append(m / left)
        left -= m
    assert fractions == pytest.approx([1 - 0.95 ** (1 / 9)] * 9, rel=1e-12)
    assert sum(masses) == pytest.approx(585.1 * 0.05, rel=1e-12)


def test_el_ejemplo_reproduce_el_banco_a_de_vinnett():
    view = calculo.run_flotation(F())
    for n, expected in zip(calculo.MEASURED_CELLS, BANCO_A_MODELADO, strict=True):
        assert 100 * view.cu_cumulative[n - 1] == pytest.approx(expected, abs=1.0)
    assert 100 * view.recoveries["CuFeS2"] == pytest.approx(94.0, abs=0.1)


def test_el_esquema_de_flotacion_trae_los_valores_calculados_y_la_leyenda():
    view = calculo.run_flotation(F())
    svg_text = fsvg.flotation_svg(view)
    assert f"{100 * view.recoveries['CuFeS2']:.1f} %" in svg_text
    assert es(view.concentrate_t_h) in svg_text
    assert es(view.cu_grade_pct) in svg_text
    assert LEYENDA in svg_text
    assert "arrastre fijo, supuesto del ejemplo; reparto parejo entre celdas" in svg_text
    for t_h in view.solids_t_h:
        assert es(t_h, 1) in svg_text
    assert f"{view.params.cells} celdas en serie" in svg_text


def test_la_version_quieta_de_flotacion_no_se_mueve_y_conserva_los_datos():
    view = calculo.run_flotation(F())
    still, moving = fsvg.flotation_svg(view, paused=True), fsvg.flotation_svg(view)
    assert "animation" not in still and "pc-rise" not in still
    assert "@keyframes" in moving and "prefers-reduced-motion" in moving
    assert _froth(still, "cu") == _froth(moving, "cu")


# ------------------------------------------------------------------ electroobtención
def _faraday_kg(j, eff, face_m2, days):
    return eff * j * 2 * face_m2 * days * 86400 * 63.546 / (2 * 96485.33212) / 1000


@pytest.mark.parametrize(
    "p",
    [E(), E(current_density=400, efficiency=0.85, cycle_days=3, face_area_m2=0.7),
     E(cycle_days=10, face_area_m2=1.5)],
)  # fmt: skip
def test_masa_por_catodo_es_faraday_por_eficiencia(p):
    view = calculo.run_ew(p)
    expected = _faraday_kg(p.current_density, p.efficiency, p.face_area_m2, p.cycle_days)
    assert view.cathode_kg == pytest.approx(expected, rel=1e-9)
    assert view.cathode_kg == pytest.approx(
        p.efficiency * view.current_a * p.cycle_days * 86400 * 63.546 / (2 * FARADAY) / 1000,
        rel=1e-9,
    )


@pytest.mark.parametrize("p", [E(), E(current_density=200, cycle_days=10, face_area_m2=0.8)])
def test_espesor_por_cara_es_masa_sobre_densidad_por_area(p):
    view = calculo.run_ew(p)
    area_cm2 = 2 * p.face_area_m2 * 1e4  # las dos caras
    mm = view.cathode_kg * 1000 / (8.96 * area_cm2) * 10
    assert view.thickness_mm == pytest.approx(mm, rel=1e-9)
    assert 3 < calculo.run_ew(E()).thickness_mm < 10  # cátodos comerciales: unos 5-7 mm


@pytest.mark.parametrize("days", [1, 7, 10])
def test_el_deposito_dibujado_es_el_espesor_calculado_por_el_factor_declarado(days):
    view = calculo.run_ew(E(cycle_days=days))
    svg_text = ew_svg.ew_svg(view)
    widths = [float(w) for w in re.findall(r'data-deposit-px="([\d.]+)"', svg_text)]
    assert len(widths) == 10  # 5 cátodos × 2 caras
    for w in widths:
        assert w == pytest.approx(view.thickness_mm * ew_svg.DEPOSIT_PX_PER_MM, abs=0.001)
    assert ew_svg.deposit_px(2.0) == pytest.approx(2.0 * ew_svg.DEPOSIT_PX_PER_MM, rel=1e-12)


def test_el_deposito_nunca_toca_al_anodo_dentro_de_los_limites_de_los_controles():
    from controles import BY_KEY

    worst = calculo.run_ew(
        E(current_density=BY_KEY["j"].hi, efficiency=0.99, cycle_days=BY_KEY["days"].hi,
          face_area_m2=BY_KEY["area"].lo)
    )  # fmt: skip
    gap = ew_svg.PITCH - ew_svg.ANODE_PX / 2 - ew_svg.BLANK_PX / 2
    assert ew_svg.deposit_px(worst.thickness_mm) < gap


def test_el_esquema_de_ew_trae_kg_mm_corriente_voltaje_y_leyenda():
    view = calculo.run_ew(E())
    svg_text = ew_svg.ew_svg(view)
    r = view.result
    for expected in (
        f"{es(view.cathode_kg, 1)} kg", f"{es(view.thickness_mm, 2)} mm",
        f"{es(r.current_a, 0)} A", f"{es(r.cell_voltage, 2)} V", f"{es(r.power_kw, 2)} kW",
        f"{es(r.specific_energy_kwh_t, 0)} kWh/t", LEYENDA, "ilustrativas",
    ):  # fmt: skip
        assert expected in svg_text
    assert f"animation-duration:{ew_svg.CYCLE_S:g}s" in svg_text


def test_ejemplo_dentro_del_rango_industrial():
    view = calculo.run_ew(E())
    assert 1.9 <= view.result.cell_voltage <= 2.3
    assert 1800 <= view.result.specific_energy_kwh_t <= 2200
    assert view.warnings == ()


def test_los_componentes_suman_el_voltaje():
    view = calculo.run_ew(E(current_density=380, temp_c=60))
    assert sum(view.result.components.values()) == pytest.approx(view.result.cell_voltage)


def test_fuera_de_la_correlacion_avisa_en_vez_de_callar():
    view = calculo.run_ew(E(temp_c=35))
    assert any("fuera del rango" in w for w in view.warnings)


def test_composicion_imposible_falla_con_mensaje_en_vez_de_trazas():
    with pytest.raises(ValueError):
        calculo.run_ew(E(cu_g_l=float("nan")))
    with pytest.raises(ValueError):
        calculo.run_ew(E(cu_g_l=900.0, acid_g_l=900.0))


def test_la_version_quieta_del_catodo_no_se_mueve():
    view = calculo.run_ew(E())
    still, moving = ew_svg.ew_svg(view, paused=True), ew_svg.ew_svg(view)
    assert "animation" not in still and "pc-grow" not in still
    assert "@keyframes pc-grow" in moving
    widths = r'data-deposit-px="([\d.]+)"'
    assert re.findall(widths, still) == re.findall(widths, moving)


def test_ningun_esquema_ejecuta_codigo():
    for s in (fsvg.flotation_svg(calculo.run_flotation(F())), ew_svg.ew_svg(calculo.run_ew(E()))):
        low = s.lower()
        assert "<script" not in low and "onload" not in low and "javascript:" not in low
