from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Sequence
from itertools import chain
from negmas.preferences import BaseUtilityFunction
from negmas.preferences import UtilityFunction
from negmas.sao.controllers import ABC, abstractmethod
from negmas.outcomes import Outcome, OutcomeSpace, make_os
from negmas.warnings import warn
import numpy as np


TRACE_COLS = (
    "time",
    "relative_time",
    "step",
    "negotiator",
    "offer",
    "responses",
    "state",
)

__all__ = [
    "UtilityCombiningCenterUFun",
    "CenterUFun",
    "MaxCenterUFun",
    "MeanSMCenterUFun",
    "SideUFun",
    "SingleAgreementSideUFunMixin",
]


class CenterUFun(UtilityFunction, ABC):
    """
    Base class of center utility functions.

    It simply received a tuple of negotiation results and returns a float
    """

    def __init__(self, *args, outcome_spaces: tuple[OutcomeSpace, ...] = (), **kwargs):
        super().__init__(*args, **kwargs)
        self._outcome_spaces = outcome_spaces
        try:
            self.outcome_space = make_os(chain(_.issues for _ in outcome_spaces))  # type: ignore
        except Exception:
            warn("Failed to find the Cartesian product of input outcome spaces")
            self.outcome_space = None

    @abstractmethod
    def eval(self, offer: tuple[Outcome | None, ...] | None) -> float:
        """
        Evaluates the utility of a given set of offers.

        Remarks:
            - Order matters: The order of outcomes in the offer is stable over all calls.
            - A missing offer is represented by `None`
        """

    @abstractmethod
    def side_ufuns(self, n_edges: int) -> tuple[BaseUtilityFunction, ...]:
        """Should return an independent ufun for each side negotiator of the center."""


class UtilityCombiningCenterUFun(CenterUFun):
    """
    A center ufun with a side-ufun defined for each thread.

    The utility of the center is a function of the ufuns of the edges.
    """

    def __init__(self, *args, ufuns: tuple[BaseUtilityFunction, ...], **kwargs):
        super().__init__(*args, **kwargs)
        self._ufuns = ufuns

    @abstractmethod
    def combine(self, values: Sequence[float]) -> float:
        """Combines the utilities of all negotiation  threads into a single value"""

    def eval(self, offer: tuple[Outcome | None, ...] | None) -> float:
        if not offer:
            return self.reserved_value
        return self.combine(tuple(float(u(_)) for u, _ in zip(self._ufuns, offer)))

    def side_ufuns(self, n_edges: int) -> tuple[BaseUtilityFunction, ...]:
        assert (
            n_edges == len(self._ufuns)
        ), f"Initialized with {len(self._ufuns)} ufuns but you are asking for ufuns for {n_edges} side negotiators."
        return self._ufuns


class MaxCenterUFun(UtilityCombiningCenterUFun):
    """
    The max center ufun.

    The utility of the center is the maximum of the utilities it got in each negotiation (called side utilities)
    """

    def combine(self, values: Sequence[float]) -> float:
        return max(values)


class SideUFun(BaseUtilityFunction):
    """
    Side ufun corresponding to the i's component of a center ufun.
    """

    def __init__(
        self, *args, center_ufun: CenterUFun, index: int, n_edges: int, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.__center_ufun = center_ufun
        self.__index = index
        self.__n_edges = n_edges

    def eval(self, offer: Outcome | None) -> float:
        offers: list[Outcome | None] = [None] * self.__n_edges
        offers[self.__index] = offer
        return self.__center_ufun(tuple(offers))


class SingleAgreementSideUFunMixin:
    """Can be mixed with any CenterUFun that is not a combining ufun to create side_ufuns that assume failure on all other negotiations.

    See Also:
        `MeanSMCenterUFun`
    """

    def side_ufuns(self, n_edges: int) -> tuple[BaseUtilityFunction, ...]:
        """Should return an independent ufun for each side negotiator of the center"""
        return tuple(
            SideUFun(center_ufun=self, n_edges=n_edges, index=i)  # type: ignore
            for i in range(n_edges)
        )


class MeanSMCenterUFun(SingleAgreementSideUFunMixin, CenterUFun):
    """A ufun that just returns returns the average mean+std dev. in each issue of the agreements as the utility value"""

    def eval(self, offer: tuple[Outcome | None, ...] | None) -> float:
        if not offer:
            return 0.0
        n_edges = len(offer)
        if n_edges < 2:
            return 0.1
        vals = defaultdict(lambda: [0.0] * n_edges)
        for e, outcome in enumerate(offer):
            if not outcome:
                continue
            for i, v in enumerate(outcome):
                try:
                    vals[e][i] = float(v[1:])
                except Exception:
                    pass

        return float(sum(np.mean(x) + np.std(x) for x in vals.values())) / len(vals)
