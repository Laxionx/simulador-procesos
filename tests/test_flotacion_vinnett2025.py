"""Cinética de flotación batch contra Vinnett et al. (2025), un segundo conjunto abierto.

Vinnett, Esteban, Orellana, Rivera y Benítez (2025), «On the sensitivity of kinetic modeling to
the selection of flotation intervals in batch tests», Minerals 15(6), 583, CC BY. Tabla 1: tres
ensayos batch de cobre (P80 de 150, 212 y 300 µm), recuperación media de 0,5 a 32 min.

Los parámetros que ajustaron los autores están solo en figuras: se comprueba lo que el texto da en
cifras (la recuperación a 8 min de su escalamiento por tiempos) y sus conclusiones. Cortes fijados
antes de correr; ver docs/flotacion.md.
"""

import numpy as np
import pytest

from procesos.flotacion import cells_recovery, fit_kinetics

T_MIN = np.array([0.5, 1.5, 4.0, 10.0, 16.0, 24.0, 32.0])
RECOVERY = {  # Tabla 1, recuperación media (%) por P80 (µm)
    150: (50.2, 68.9, 79.8, 84.3, 85.9, 87.2, 87.9),
    212: (37.1, 59.2, 72.0, 76.2, 77.8, 79.1, 80.0),
    300: (34.4, 59.4, 67.6, 70.6, 72.2, 73.2, 73.7),
}
AT_8_MIN = {150: 83, 212: 75, 300: 70}  # texto: base del escalamiento por tiempos (20 min / 2,5)
P80S = list(RECOVERY)


def _fit(p80: int, model: str, keep: np.ndarray | None = None):
    rec = np.array(RECOVERY[p80]) / 100.0
    mask = np.ones(len(T_MIN), bool) if keep is None else keep
    return fit_kinetics(T_MIN[mask], rec[mask], model=model)


def _most_sensitive(p80: int, model: str) -> int:
    """Intervalo (1 = el primero) cuya omisión más mueve R∞ respecto del ajuste con los 7."""
    base = _fit(p80, model).r_inf
    moves = [abs(_fit(p80, model, np.arange(len(T_MIN)) != i).r_inf - base)
             for i in range(len(T_MIN))]  # fmt: skip
    return int(np.argmax(moves)) + 1


@pytest.mark.parametrize("p80", P80S)
def test_la_recuperacion_a_8_min_es_la_de_los_autores(p80):
    r = float(np.interp(8.0, T_MIN, RECOVERY[p80]))
    assert r == pytest.approx(AT_8_MIN[p80], abs=0.5)


@pytest.mark.parametrize("p80", P80S)
def test_el_rectangular_ajusta_mejor_que_el_primer_orden(p80):
    assert _fit(p80, "rectangular").rmse < _fit(p80, "primer_orden").rmse


@pytest.mark.parametrize("p80", P80S)
def test_en_el_rectangular_manda_el_primer_intervalo(p80):
    assert _most_sensitive(p80, "rectangular") == 1


def test_en_el_primer_orden_manda_uno_de_los_dos_primeros_intervalos_con_p80_150():
    assert _most_sensitive(150, "primer_orden") in (1, 2)


@pytest.mark.parametrize("p80", [212, 300])
@pytest.mark.xfail(
    strict=True,
    reason="Con P80 212 y 300 µm el R∞ de primer orden se mueve más al omitir el 3.er intervalo; "
    "los autores miran también la forma de f(k), y aquí solo R∞ (ver docs/flotacion.md)",
)
def test_en_el_primer_orden_manda_uno_de_los_dos_primeros_intervalos(p80):
    assert _most_sensitive(p80, "primer_orden") in (1, 2)


@pytest.mark.parametrize(
    "p80,model,r_inf,k",
    [
        (150, "primer_orden", 84.3, 1.553), (150, "rectangular", 87.0, 3.830),
        (212, "primer_orden", 77.0, 1.122), (212, "rectangular", 79.8, 2.696),
        (300, "primer_orden", 71.5, 1.245), (300, "rectangular", 74.1, 2.970),
    ],
)  # fmt: skip
def test_parametros_ajustados_documentados(p80, model, r_inf, k):
    fit = _fit(p80, model)
    assert fit.r_inf * 100 == pytest.approx(r_inf, abs=0.05)
    assert fit.k == pytest.approx(k, abs=0.0005)


@pytest.mark.parametrize("p80,expected", [(150, 85.6), (212, 78.0), (300, 72.6)])
def test_escalamiento_informativo_a_6_celdas(p80, expected):
    # Informativo, sin corte: 20 min en 6 mezcladores (3,33 min por celda) con el rectangular;
    # queda sobre el atajo por tiempos de los autores (recuperación de laboratorio a 8 min).
    fit = _fit(p80, "rectangular")
    scaled = cells_recovery("rectangular", fit.r_inf, fit.k, 20.0 / 6, 6) * 100
    assert scaled == pytest.approx(expected, abs=0.05)
    assert scaled > AT_8_MIN[p80]
