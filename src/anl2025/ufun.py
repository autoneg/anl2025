from abc import ABC, abstractmethod
from negmas.preferences import BaseUtilityFunction
from negmas.preferences import UtilityFunction
from negmas.sao.controllers import ABC, abstractmethod
from negmas.outcomes import Outcome


TRACE_COLS = (
    "time",
    "relative_time",
    "step",
    "negotiator",
    "offer",
    "responses",
    "state",
)

__all__ = ["CenterUFunWithEdgeUFuns", "CenterUFun", "MaxCenterUFun"]


class CenterUFun(UtilityFunction, ABC):
    """
    Base class of center utility functions.

    It simply received a tuple of negotiation results and returns a float
    """

    @abstractmethod
    def eval(self, offer: tuple[Outcome | None] | None) -> float:
        """
        Evaluates the utility of a given set of offers.

        Remarks:
            - Order matters: The order of outcomes in the offer is stable over all calls.
            - A missing offer is represented by `None`
        """

    @abstractmethod
    def side_ufuns(self, n_sides: int) -> tuple[BaseUtilityFunction, ...]:
        """Should return an independent ufun for each side negotiator of the center"""


class CenterUFunWithEdgeUFuns(CenterUFun):
    """
    A center ufun with a sub-ufun defined for each thread.

    The utility of the center is a function of the ufuns of the edges.
    """

    def __init__(self, *args, ufuns: tuple[BaseUtilityFunction, ...], **kwargs):
        super().__init__(*args, **kwargs)
        self._ufuns = ufuns

    @abstractmethod
    def combine(self, values: tuple[float, ...]) -> float:
        """Combines the utilities of all negotiation  threads into a single value"""

    def eval(self, offer: tuple[Outcome | None] | None) -> float:
        if not offer:
            return self.reserved_value
        return self.combine(tuple(float(u(_)) for u, _ in zip(self._ufuns, offer)))

    def side_ufuns(self, n_sides: int) -> tuple[BaseUtilityFunction, ...]:
        assert (
            n_sides == len(self._ufuns)
        ), f"Initialized with {len(self._ufuns)} ufuns but you are asking for ufuns for {n_sides} side negotiators."
        return self._ufuns


class MaxCenterUFun(CenterUFunWithEdgeUFuns):
    """
    The max center ufun.

    The utility of the center is the maximum of the utilities it got in each negotiation (called side utilities)
    """

    def combine(self, values: tuple[float, ...]) -> float:
        return max(values)
