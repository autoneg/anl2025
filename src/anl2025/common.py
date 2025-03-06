from attrs import define
from random import random
from negmas.helpers.types import get_class

__all__ = [
    "RunParams",
    "TYPE_IDENTIFIER",
    "CENTER_FILE_NAME",
    "EDGES_FOLDER_NAME",
    "SIDES_FOLDER_NAME",
]

EPSILON = 1e-6
TYPE_IDENTIFIER = "type"
CENTER_FILE_NAME = "center.yml"
EDGES_FOLDER_NAME = "edges"
SIDES_FOLDER_NAME = "sides"
TYPES_MAP = dict(
    DiscreteCartesianOutcomeSpace="negmas.outcomes.DiscreteCartesianOutcomeSpace"
)

SEQUENTIAL_METHOD = "sequential"
DEFAULT_METHOD = SEQUENTIAL_METHOD


@define
class RunParams:
    """Defines the running parameters of the multi-deal negotiation like time-limits.

    Attributes:
        nsteps: Number of negotiation steps
        keep_order: Keep the order of  negotiation threads when scheduling next action
        share_ufuns: If given, agents can access partner ufuns through `self.opponeng_ufun`
        atomic: Every step is a single offer (if not given, on the other hand, every step is a complete round)
        method: the method to use for running all the sessions.  Acceptable options are: sequential,
                ordered, threads, processes. See `negmas.mechanisms.Mechanism.run_all()` for full details.
                ANL2025 uses the sequential option which means that a complete negotiation is finished before
                the next starts.
        time_limit: Number of seconds allowed per negotiation
    """

    # mechanism params
    nsteps: int = 100
    keep_order: bool = True
    share_ufuns: bool = False
    atomic: bool = False
    method: str = DEFAULT_METHOD
    time_limit: float | None = None


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
    """Samples a number if the given range"""
    if (mx - mn) > eps:
        return mn + (mx - mn) * random()
    return (mx + mn) / 2.0
