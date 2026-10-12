"""Cadena de concentrado a cátodo (4a → 4c). Tolerancias fijadas ANTES de correr (brief del 12-10):

1. Cierre de Cu y de S de punta a punta, 1e-9 relativo; el ZnS de la mata se informa aparte.
2. Coherencia con Ilo (10-K 2025 de Southern Copper, 2023-2025): el ácido potencial por t de
   concentrado queda dentro de 0,94-1,00 t/t ±15 % (0,80 a 1,15). Los concentrados son distintos
   (Atlantic Copper contra Toquepala y Cuajone), así que es coherencia, no validación.
3. Interfaces: lo que sale de cada etapa entra igual en la siguiente.
"""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest

from procesos.cadena import concentrate_to_cathode
from procesos.conversion_datos import ILO_10K
from procesos.fusion_datos import BLENDS, INDUSTRIAL


def _chain(blend: str, **kw):
    _oc, _oe, _flux, grade, sio2, loss = INDUSTRIAL[blend]
    return concentrate_to_cathode(BLENDS[blend], matte_grade=grade, slag_sio2=sio2,
                                  heat_loss_mj_t=loss, **kw)  # fmt: skip


@pytest.mark.parametrize("blend", list(BLENDS))
def test_cierre_de_cobre_y_azufre(blend):
    r = _chain(blend)
    assert sum(r.copper_t().values()) == pytest.approx(r.concentrate_cu_t, rel=1e-9)
    assert sum(r.sulfur_t().values()) == pytest.approx(r.concentrate_s_t, rel=1e-9)


ACID_RANGE = (
    min(a / c for c, _r, _an, _g, a in ILO_10K.values()) * 0.85,
    max(a / c for c, _r, _an, _g, a in ILO_10K.values()) * 1.15,
)


@pytest.mark.parametrize("blend", list(BLENDS))
def test_acido_coherente_con_ilo(blend):
    assert ACID_RANGE[0] <= _chain(blend).potential_acid_t <= ACID_RANGE[1]


def test_interfaces_entre_etapas():
    r = _chain("Mezcla 1")
    k = r.smelting.kmol
    matte = r.slag_blow.feeds[0].kmol()
    assert matte["Cu2S"] == pytest.approx(k["mata:Cu2S"], rel=1e-12)
    assert matte["FeS"] == pytest.approx(k["mata:FeS"], rel=1e-12)
    assert r.anode.blister_t == pytest.approx(r.copper_blow.mass_t("blister"), rel=1e-12)
    assert r.refining.anode_consumed == pytest.approx(1.0) and not r.refining.limited
    cathode_cu = r.refining.copper_kg_h / 1000
    assert cathode_cu < r.anode.anode_t * r.anode.anode_cu_pct / 100


def test_mas_cobre_en_escoria_baja_la_recuperacion():
    assert _chain("Mezcla 1", converter_slag_cu_pct=6.0).recovery < _chain("Mezcla 1").recovery


def test_ejemplo_corre(capsys):
    runpy.run_path(str(Path(__file__).parents[1] / "ejemplos" / "cadena_atlantic.py"))
    assert "cátodos" in capsys.readouterr().out


def test_acido_potencial_a_mano():
    r = _chain("Mezcla 2")
    s = r.sulfur_t()
    so2_s = s["SO2 de fusión"] + s["SO2 del convertidor"] + s["SO2 del horno de ánodos"]
    assert s["SO2 del horno de ánodos"] > 0
    assert r.potential_acid_t == pytest.approx(so2_s / 32.06 * 98.072, rel=1e-4)
