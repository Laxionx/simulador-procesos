"""Flotación cinética. Tolerancias fijadas ANTES de correr (12-10):

Datos: Vinnett, Pino-Muñoz, Yianatos, Díaz y Henríquez (2022), Physicochem. Probl. Miner.
Process. 58(5), 152420 (acceso abierto). Bancos rougher de Minera Los Pelambres: A (9 celdas,
τ = 4,1 min por celda) y B (6 celdas, τ = 6,4 min), con la recuperación de Cu medida celda a
celda (Tablas B1 y B2) y los parámetros ajustados con mezcla perfecta (Tabla 3).

V1. Con sus parámetros, reproducir sus recuperaciones modeladas (mezcla perfecta, constante única
    y rectangular): ±1,0 punto, porque los parámetros vienen redondeados.
V2. Ajustar sus recuperaciones MEDIDAS con fit_kinetics y obtener sus parámetros: R∞ ±1 punto y
    k (k media en el rectangular) ±5 %.
La predicción de laboratorio a planta del brief no se valida: no hay datos abiertos accesibles
(ver docs/flotacion.md).
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.integrate import quad

from procesos import Catalog, Flotation, Flowsheet, Stream, fit_kinetics, load_plant, make_species
from procesos.flotacion import batch_recovery, cells_recovery
from procesos.report import element_balance, flotation_report

BANCOS = {  # banco: (τ por celda, celdas, medida %, modelo PM constante única %, PM rectangular %)
    "A": (4.1, [1, 3, 5, 7, 9], [55.5, 86.7, 91.9, 94.2, 94.7],
          [55.0, 87.3, 92.8, 93.8, 93.9], [56.1, 85.4, 91.9, 94.3, 95.5]),
    "B": (6.4, [1, 2, 3, 4, 5, 6], [60.1, 81.2, 86.6, 90.5, 94.2, 94.2],
          [59.3, 80.9, 88.8, 91.7, 92.7, 93.1], [60.4, 80.1, 87.7, 91.2, 93.1, 94.3]),
}  # fmt: skip
TABLA_3 = {  # banco: {modelo: (R∞ %, k media 1/min)}, mezcla perfecta
    "A": {"primer_orden": (94.0, 0.35), "rectangular": (99.1, 0.42)},
    "B": {"primer_orden": (93.3, 0.27), "rectangular": (98.9, 0.33)},
}


def _k(model: str, k_mean: float) -> float:
    return k_mean if model == "primer_orden" else 2 * k_mean


# ------------------------------------------------------------------ V1 y V2 (Los Pelambres)


@pytest.mark.parametrize("model", ["primer_orden", "rectangular"])
@pytest.mark.parametrize("banco", ["A", "B"])
def test_v1_reproduce_las_recuperaciones_modeladas(banco, model):
    tau, cells, _, src, rect = BANCOS[banco]
    r_inf, k_mean = TABLA_3[banco][model]
    published = src if model == "primer_orden" else rect
    for n, expected in zip(cells, published, strict=True):
        ours = 100 * cells_recovery(model, r_inf / 100, _k(model, k_mean), tau, n)
        assert ours == pytest.approx(expected, abs=1.0), (banco, model, n)


@pytest.mark.parametrize("model", ["primer_orden", "rectangular"])
@pytest.mark.parametrize("banco", ["A", "B"])
def test_v2_ajuste_de_las_recuperaciones_medidas(banco, model):
    tau, cells, measured, _, _ = BANCOS[banco]
    fit = fit_kinetics(cells, [m / 100 for m in measured], model, tau)
    r_inf, k_mean = TABLA_3[banco][model]
    assert 100 * fit.r_inf == pytest.approx(r_inf, abs=1.0)
    assert fit.k_mean == pytest.approx(k_mean, rel=0.05)


# ------------------------------------------------------------------ guardas matemáticas


@pytest.mark.parametrize("model", ["primer_orden", "rectangular"])
def test_muchas_celdas_tienden_al_batch(model):
    t, n = 12.0, 100_000
    assert cells_recovery(model, 0.9, 0.5, t / n, n) == pytest.approx(
        batch_recovery(model, 0.9, 0.5, t), rel=1e-4
    )


@pytest.mark.parametrize("cells", [1, 2, 5])
def test_rectangular_es_el_promedio_de_la_constante_unica(cells):
    kmax, tau = 0.8, 3.0
    mean, _ = quad(lambda k: cells_recovery("primer_orden", 1.0, k, tau, cells), 0.0, kmax)
    assert cells_recovery("rectangular", 1.0, kmax, tau, cells) == pytest.approx(
        mean / kmax, rel=1e-9
    )
    batch, _ = quad(lambda k: batch_recovery("primer_orden", 1.0, k, 5.0), 0.0, kmax)
    assert batch_recovery("rectangular", 1.0, kmax, 5.0) == pytest.approx(batch / kmax, rel=1e-9)


@pytest.mark.parametrize("model", ["primer_orden", "rectangular"])
def test_ajuste_batch_recupera_parametros_sinteticos(model):
    times = [0.5, 1, 2, 4, 8, 16, 30]
    data = [batch_recovery(model, 0.87, 0.6, t) for t in times]
    fit = fit_kinetics(times, data, model)
    assert fit.r_inf == pytest.approx(0.87, rel=1e-6)
    assert fit.k == pytest.approx(0.6, rel=1e-6)
    assert fit.rmse < 1e-9


def test_ajuste_rechaza_datos_imposibles():
    with pytest.raises(ValueError):
        fit_kinetics([1, 2], [0.5, 0.6])
    with pytest.raises(ValueError):
        fit_kinetics([1, 2, 3], [50, 60, 70])  # en %, no fracción
    with pytest.raises(ValueError):
        cells_recovery("otro", 1.0, 1.0, 1.0, 1)
    with pytest.raises(ValueError):
        cells_recovery("primer_orden", 1.0, 1.0, 1.0, 0)


# ------------------------------------------------------------------ equipo


SPECIES = [("CuFeS2", "s"), ("SiO2", "s"), ("H2O", "l")]
CATALOG = Catalog([make_species(n, phase=p) for n, p in SPECIES])
FEED = Stream({"CuFeS2": 14_900.0, "SiO2": 585_100.0, "H2O": 1_114_000.0})


def _unit(**kw) -> Flotation:
    args = {"kinetics": {"CuFeS2": (0.94, 0.35)}, "cells": 9, "tau_min": 4.1,
            "fixed": {"H2O": 0.10, "SiO2": 0.05}}  # fmt: skip
    args.update(kw)
    return Flotation("Rougher", ("Alim",), ("Conc", "Relave"), **args)


def test_equipo_recupera_segun_el_modelo_y_cierra():
    sheet = Flowsheet(CATALOG, [_unit()], {"Alim": FEED})
    solution = sheet.solve()
    conc = solution.streams["Conc"]
    expected = cells_recovery("primer_orden", 0.94, 0.35, 4.1, 9)
    assert conc.flow("CuFeS2") == pytest.approx(14_900.0 * expected, rel=1e-12)
    assert conc.flow("SiO2") == pytest.approx(585_100.0 * 0.05, rel=1e-12)
    assert all(r.relative_error < 1e-12 for r in element_balance(sheet, solution))


def test_tiempo_de_residencia_desde_el_volumen_de_celda():
    unit = _unit(tau_min=None, cell_volume_m3=130.0, air_fraction=0.15)
    q = (600_000.0 / 2.7 + 1_114_000.0 / 1.0) / 1000.0 / 60.0  # m³/min
    assert unit.solve([FEED], CATALOG).tau_min == pytest.approx(130.0 * 0.85 / q, rel=1e-12)


def test_factor_de_escalamiento_divide_las_k():
    slow = _unit(scale_up=2.5).solve([FEED], CATALOG).recoveries["CuFeS2"]
    assert slow == pytest.approx(cells_recovery("primer_orden", 0.94, 0.35 / 2.5, 4.1, 9))


def test_parametros_y_datos_imposibles():
    assert _unit().with_parameter("k:CuFeS2", 0.5).kinetics["CuFeS2"] == (0.94, 0.5)
    assert _unit().with_parameter("factor_escalamiento", 2.0).scale_up == 2.0
    assert _unit().with_parameter("tiempo_residencia", 3.0).tau_min == 3.0
    with pytest.raises(KeyError):
        _unit().with_parameter("k:SiO2", 0.1)
    for bad in ({"cells": 0}, {"tau_min": None}, {"kinetics": {"CuFeS2": (1.2, 0.3)}},
                {"kinetics": {"CuFeS2": (0.9, -0.3)}}, {"model": "otro"}):  # fmt: skip
        with pytest.raises(ValueError):
            _unit(**bad)


def test_ejemplo_banco_pelambres():
    plant = load_plant("ejemplos/flotacion_pelambres.yaml")
    solution = plant.flowsheet.solve()
    (_, result), = flotation_report(plant.flowsheet, solution)  # fmt: skip
    assert result.cells == 9 and math.isclose(result.tau_min, 4.1)
    assert 100 * result.recoveries["CuFeS2"] == pytest.approx(93.97, abs=0.01)
    assert np.isfinite(result.tau_min)


def test_linea_de_comandos_ajusta_un_banco(tmp_path, capsys):
    from procesos.cli import main

    tau, cells, measured, _, _ = BANCOS["A"]
    datos = tmp_path / "banco_a.csv"
    lines = ["celda;recuperacion"] + [f"{n};{m}" for n, m in zip(cells, measured, strict=True)]
    datos.write_text("\n".join(lines), encoding="utf-8")
    assert main(["ajustar", str(datos), "--tau", str(tau)]) == 0
    out = capsys.readouterr().out
    assert "R∞ = 93.96 %" in out and "k = 0.3456" in out
