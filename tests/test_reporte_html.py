"""Fase 4 (B4): costo operativo, diagrama de flujo y reporte HTML. Fijado ANTES de correr:

- Costo operativo contra un cálculo a mano (planta con calores dados): 1e-9 relativo.
- El HTML se analiza sin errores, no carga nada externo y escapa los nombres que vienen del YAML.
- El diagrama tiene un nodo por equipo, una flecha por cada conexión y marca los reciclos.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

import pytest

from procesos import load_plant
from procesos.costs import operating_cost
from procesos.diagram import flowsheet_svg
from procesos.html_report import html_report
from procesos.plant_io import PlantFileError

EXAMPLES = Path(__file__).resolve().parents[1] / "ejemplos"

PLANTA = """
nombre: Prueba de costos
balance_de_calor: true
especies:
  - {nombre: SiO2, fase: s}
  - {nombre: H2O, fase: l}
alimentaciones:
  Mineral: {flujos: {SiO2: 50000.0}, temperatura: 20}
  Agua: {flujos: {H2O: 10000.0}, temperatura: 20}
equipos:
  - {tipo: mezclador, nombre: Mezcla, entradas: [Mineral, Agua], salidas: [Pulpa]}
  - {tipo: calentador, nombre: Calentador, entradas: [Pulpa], salidas: [Caliente], calor_kw: 500}
  - {tipo: calentador, nombre: Enfriador, entradas: [Caliente], salidas: [Producto], calor_kw: -200}
costos:
  moneda: USD
  por_tonelada_de: {corriente: Mineral}
  precios_por_t: {H2O: 0.5}
  calor_por_kwh: 0.03
  frio_por_kwh: 0.01
  fijo_por_h: 30
"""


def _solved(text: str = PLANTA):
    plant = load_plant(text)
    return plant, plant.flowsheet.solve()


def test_costo_operativo_contra_calculo_a_mano():
    plant, solution = _solved()
    report = operating_cost(plant.flowsheet, solution, plant.costs)
    # agua 10 t/h × 0,5 + calor 500 kW × 0,03 + frío 200 kW × 0,01 + fijo 30 = 52 USD/h
    assert report.total_per_h == pytest.approx(52.0, rel=1e-9)
    assert report.basis_t_h == pytest.approx(50.0, rel=1e-9)
    assert report.per_tonne == pytest.approx(52.0 / 50.0, rel=1e-9)
    concepts = {line.concept: line.cost_per_h for line in report.lines}
    assert concepts["H2O"] == pytest.approx(5.0) and concepts[
        "Calor · Calentador"
    ] == pytest.approx(15)
    assert concepts["Frío · Enfriador"] == pytest.approx(2.0)


def test_costo_por_tonelada_de_elemento_contenido():
    plant, solution = _solved(
        PLANTA.replace("{corriente: Mineral}", "{corriente: Producto, elemento: Si}")
    )
    report = operating_cost(plant.flowsheet, solution, plant.costs)
    si_t_h = 50.0 * 28.0855 / (28.0855 + 2 * 15.999)
    assert report.basis_t_h == pytest.approx(si_t_h, rel=1e-4)
    assert report.per_tonne == pytest.approx(52.0 / si_t_h, rel=1e-4)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (("{H2O: 0.5}", "{H2O: -1}"), "negativo"),
        (("{H2O: 0.5}", "{CO2: 3}"), "CO2"),
        (("{H2O: 0.5}", "{SiO2: 3, H2O: 0.5}"), None),  # el mineral también puede tener precio
        (("{corriente: Mineral}", "{corriente: Nada}"), "Nada"),
        (("{corriente: Mineral}", "{corriente: Mineral, elemento: Cu}"), "Cu"),
    ],
)
def test_errores_de_costos(change, message):
    text = PLANTA.replace(*change)
    if message is None:
        plant, solution = _solved(text)
        assert operating_cost(plant.flowsheet, solution, plant.costs).total_per_h > 52.0
        return
    with pytest.raises((PlantFileError, ValueError), match=message):
        plant, solution = _solved(text)
        operating_cost(plant.flowsheet, solution, plant.costs)


class _Strict(HTMLParser):
    VOID = {"meta", "br", "hr", "img", "link", "input", "col", "path", "line", "rect", "circle",
            "polygon", "polyline", "stop", "use"}  # fmt: skip

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.tags: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.tags.append(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        assert self.stack and self.stack[-1] == tag, f"cierre {tag} sin abrir: {self.stack[-3:]}"
        self.stack.pop()


def _parse(text: str) -> _Strict:
    parser = _Strict()
    parser.feed(text)
    parser.close()
    assert parser.stack == [], parser.stack
    return parser


def test_reporte_html_bien_formado_y_autocontenido():
    plant, solution = _solved()
    text = html_report(plant, plant.flowsheet, solution)
    parsed = _parse(text)
    assert "svg" in parsed.tags and "table" in parsed.tags
    for forbidden in ("<script", "http://", "https://", "src=", "@import"):
        assert forbidden not in text
    for unit in plant.flowsheet.units:
        assert unit.name in text
    assert "1.04" in text or "1,04" in text  # costo por tonelada
    assert "capital" in text.lower()  # la nota de por qué no se estima


def test_nombres_del_yaml_se_escapan():
    hostile = PLANTA.replace("Prueba de costos", '"<script>alert(1)</script>"').replace(
        "nombre: Mezcla", 'nombre: "Mezcla <b>&"'
    )
    plant, solution = _solved(hostile)
    text = html_report(plant, plant.flowsheet, solution)
    assert "<script>" not in text and "<b>&" not in text
    assert "&lt;script&gt;" in text and "Mezcla &lt;b&gt;&amp;" in text
    _parse(text)


def test_diagrama_nodos_flechas_y_reciclos():
    plant = load_plant(EXAMPLES / "reciclo_simple.yaml")
    flowsheet = plant.flowsheet
    svg = flowsheet_svg(flowsheet)
    _parse(svg)
    assert svg.count('class="equipo"') == len(flowsheet.units)
    connections = sum(len(u.inputs) for u in flowsheet.units) + len(flowsheet.products)
    assert svg.count('class="flecha') == connections
    assert svg.count('class="flecha reciclo"') == len(flowsheet.tears) >= 1


def test_ejemplos_generan_reporte(tmp_path):
    from procesos.cli import main

    for name in ("lixiviacion_con_calor.yaml", "reciclo_simple.yaml", "concentradora_cu.yaml"):
        out = tmp_path / f"{name}.html"
        assert main(["resolver", str(EXAMPLES / name), "--html", str(out)]) == 0
        _parse(out.read_text(encoding="utf-8"))
