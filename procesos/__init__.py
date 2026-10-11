"""Simulador de procesos metalúrgicos implementado desde la literatura.

Fase 1: balance de masa con reacciones, reciclos y lazos de control.
"""

from .control import ControlError, Controller, Goal, Manipulated, solve_with_controllers
from .ew import Electrowinning
from .flowsheet import ConvergenceError, Flowsheet, Solution
from .plant_io import Plant, PlantFileError, load_plant
from .reactions import Reaction, check_balance, parse_equation
from .species import Catalog, Species, make_species
from .stream import Stream, element_flows, mix, moles
from .thermo import ThermoDatabase, ThermoRecord, stream_enthalpy, temperature_for
from .thermo_data import DEFAULT_THERMO
from .units import Evaporator, Heater, Mixer, Reactor, Separator, Splitter

__all__ = [
    "Catalog",
    "ControlError",
    "DEFAULT_THERMO",
    "Electrowinning",
    "Evaporator",
    "Controller",
    "ConvergenceError",
    "Flowsheet",
    "Goal",
    "Heater",
    "Manipulated",
    "Mixer",
    "Plant",
    "PlantFileError",
    "Reaction",
    "Reactor",
    "Separator",
    "Solution",
    "Species",
    "Splitter",
    "Stream",
    "ThermoDatabase",
    "ThermoRecord",
    "check_balance",
    "element_flows",
    "load_plant",
    "make_species",
    "mix",
    "moles",
    "parse_equation",
    "solve_with_controllers",
    "stream_enthalpy",
    "temperature_for",
]
