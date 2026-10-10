"""Simulador de procesos metalúrgicos implementado desde la literatura.

Fase 1: balance de masa con reacciones, reciclos y lazos de control.
"""

from .control import ControlError, Controller, Goal, Manipulated, solve_with_controllers
from .flowsheet import ConvergenceError, Flowsheet, Solution
from .plant_io import Plant, PlantFileError, load_plant
from .reactions import Reaction, check_balance, parse_equation
from .species import Catalog, Species, make_species
from .stream import Stream, element_flows, mix, moles
from .units import Mixer, Reactor, Separator, Splitter

__all__ = [
    "Catalog",
    "ControlError",
    "Controller",
    "ConvergenceError",
    "Flowsheet",
    "Goal",
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
    "check_balance",
    "element_flows",
    "load_plant",
    "make_species",
    "mix",
    "moles",
    "parse_equation",
    "solve_with_controllers",
]
