from random import random
from negmas.helpers.types import get_class

EPSILON = 1e-6
TYPE_IDENTIFIER = "type"
CENTER_FILE_NAME = "center.yml"
EDGES_FOLDER_NAME = "edges"
SIDES_FILDER_NAME = "sides"
TYPES_MAP = dict(
    DiscreteCartesianOutcomeSpace="negmas.outcomes.DiscreteCartesianOutcomeSpace"
)


def get_ufun_class(x: str | type) -> type:
    """Returns the type of the agent"""
    if not isinstance(x, str):
        return x
    return get_class(x, module_name="anl2025.ufun")


def get_agent_class(x: str | type) -> type:
    """Returns the type of the agent"""
    if not isinstance(x, str):
        return x
    return get_class(x, module_name="anl2025.negotiator")


def sample_between(mn: float, mx: float, eps: float = EPSILON) -> float:
    if (mx - mn) > eps:
        return mn + (mx - mn) * random()
    return (mx + mn) / 2.0
