"""Lectura de una planta descrita en YAML (ver ``ejemplos/``)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .control import Controller, Goal, Manipulated
from .flowsheet import Flowsheet
from .reactions import Reaction, parse_equation
from .species import Catalog, make_species
from .stream import STANDARD_PRESSURE, STANDARD_TEMPERATURE, Stream
from .thermo_data import DEFAULT_THERMO
from .units import Heater, Mixer, Reactor, Separator, Splitter, Unit


@dataclass(frozen=True)
class Plant:
    name: str
    flowsheet: Flowsheet
    controllers: tuple[Controller, ...]


class PlantFileError(ValueError):
    """El archivo de la planta no cumple el formato; el mensaje indica dónde."""


def _require(data: Mapping[str, Any], key: str, where: str) -> Any:
    if not isinstance(data, Mapping) or key not in data:
        raise PlantFileError(f"{where}: falta el campo {key!r}")
    return data[key]


def _names(value: Any, where: str) -> tuple[str, ...]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise PlantFileError(f"{where}: debe ser una lista de nombres de corrientes")
    return tuple(value)


def _stream(data: Any, where: str) -> Stream:
    flows = _require(data, "flujos", where)
    if not isinstance(flows, Mapping):
        raise PlantFileError(f"{where}.flujos: debe ser un mapa especie → kg/h")
    try:
        return Stream(
            {str(k): float(v) for k, v in flows.items()},
            float(data.get("temperatura", STANDARD_TEMPERATURE)),
            float(data.get("presion", STANDARD_PRESSURE)),
        )
    except (TypeError, ValueError) as error:
        raise PlantFileError(f"{where}: {error}") from error


def _unit(data: Any, index: int) -> Unit:
    where = f"equipos[{index}]"
    kind = _require(data, "tipo", where)
    name = str(_require(data, "nombre", where))
    where = f"equipo {name!r}"
    inputs = _names(_require(data, "entradas", where), f"{where}.entradas")
    outputs = _names(_require(data, "salidas", where), f"{where}.salidas")
    try:
        if kind == "mezclador":
            return Mixer(name, inputs, outputs)
        if kind == "divisor":
            fractions = tuple(float(f) for f in _require(data, "fracciones", where))
            return Splitter(name, inputs, outputs, fractions)
        if kind == "separador":
            recoveries = {
                str(k): float(v) for k, v in _require(data, "recuperaciones", where).items()
            }
            return Separator(name, inputs, outputs, recoveries, float(data.get("por_defecto", 0.0)))
        if kind == "reactor":
            reactions = []
            for item in _require(data, "reacciones", where):
                equation = str(_require(item, "ecuacion", f"{where}.reacciones"))
                reactions.append(
                    Reaction(
                        parse_equation(equation),
                        str(_require(item, "clave", where)),
                        float(_require(item, "conversion", where)),
                        equation,
                    )
                )
            temperature = data.get("temperatura")
            return Reactor(
                name,
                inputs,
                outputs,
                tuple(reactions),
                None if temperature is None else float(temperature),
            )
        if kind == "calentador":
            temperature, duty = data.get("temperatura"), data.get("calor_kw")
            return Heater(
                name,
                inputs,
                outputs,
                None if temperature is None else float(temperature),
                None if duty is None else float(duty),
            )
    except (TypeError, ValueError, AttributeError) as error:
        raise PlantFileError(f"{where}: {error}") from error
    raise PlantFileError(
        f"{where}: tipo desconocido {kind!r} (mezclador, divisor, separador, reactor, calentador)"
    )


def _controller(data: Any, index: int) -> Controller:
    where = f"controladores[{index}]"
    name = str(_require(data, "nombre", where))
    adjust = _require(data, "ajustar", f"controlador {name!r}")
    goal = _require(data, "meta", f"controlador {name!r}")
    try:
        if "alimentacion" in adjust:
            manipulated = Manipulated(
                "alimentacion",
                str(adjust["alimentacion"]),
                str(adjust["especie"]),
                float(adjust["minimo"]),
                float(adjust["maximo"]),
            )
        else:
            manipulated = Manipulated(
                "equipo",
                str(adjust["equipo"]),
                str(adjust["parametro"]),
                float(adjust["minimo"]),
                float(adjust["maximo"]),
            )
        return Controller(
            name,
            manipulated,
            Goal(
                str(goal["corriente"]),
                str(goal["propiedad"]),
                float(goal["valor"]),
                goal.get("especie"),
            ),
        )
    except KeyError as error:
        raise PlantFileError(f"controlador {name!r}: falta el campo {error.args[0]!r}") from error
    except (TypeError, ValueError) as error:
        raise PlantFileError(f"controlador {name!r}: {error}") from error


def load_plant(source: str | Path) -> Plant:
    """Carga una planta desde la ruta de un ``.yaml`` o desde el texto YAML."""
    text = (
        Path(source).read_text(encoding="utf-8")
        if Path(str(source)).suffix in (".yaml", ".yml")
        else str(source)
    )
    data = yaml.safe_load(text)
    if not isinstance(data, Mapping):
        raise PlantFileError(
            "El archivo debe ser un mapa YAML con especies, alimentaciones y equipos"
        )
    try:
        species = [
            make_species(str(_require(s, "nombre", "especies")), s.get("formula"), s.get("fase"))
            if isinstance(s, Mapping)
            else make_species(str(s))
            for s in _require(data, "especies", "planta")
        ]
        thermo = DEFAULT_THERMO if data.get("balance_de_calor", False) else None
        catalog = Catalog(species, thermo)
    except ValueError as error:
        raise PlantFileError(f"especies: {error}") from error
    feeds = {
        str(k): _stream(v, f"alimentacion {k!r}")
        for k, v in _require(data, "alimentaciones", "planta").items()
    }
    units = [_unit(u, i) for i, u in enumerate(_require(data, "equipos", "planta"))]
    tears = data.get("cortes")
    try:
        flowsheet = Flowsheet(
            catalog, units, feeds, None if tears is None else _names(tears, "cortes")
        )
    except ValueError as error:
        raise PlantFileError(f"planta: {error}") from error
    controllers = tuple(_controller(c, i) for i, c in enumerate(data.get("controladores") or []))
    return Plant(str(data.get("nombre", "Planta sin nombre")), flowsheet, controllers)
