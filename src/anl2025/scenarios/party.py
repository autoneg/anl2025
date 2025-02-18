from anl2025.ufun import CenterUFun
from negmas import (
    BaseUtilityFunction,
    DiscreteCartesianOutcomeSpace,
    MappingUtilityFunction,
    make_os,
    make_issue,
)
from negmas.outcomes import Outcome

__all__ = ["PartyCU"]


def make_party_os(n_days: int) -> DiscreteCartesianOutcomeSpace:
    return make_os([make_issue(2, f"day{i+1}") for i in range(n_days)])  # type: ignore


class PartyCU(CenterUFun):
    """
    The Center ufun for the Party domain.

    Args:
        values: A mapping from the number of outings per day for `n_days` to a real value.
        n_friends: Number of friends
    """

    def __init__(
        self,
        *args,
        values: dict[tuple[int, ...], float],
        n_friends: int = 3,
        **kwargs,
    ):
        n_days = len(values.keys().next())
        self.values, self.n_days, self.n_friends = values, n_days, n_friends
        outcome_space = make_party_os(n_days)

        super().__init__(
            *args,
            outcome_spaces=tuple([outcome_space for _ in range(n_friends)]),
            outcome_space=outcome_space,
            **kwargs,
        )

    def eval(self, offer: tuple[Outcome | None, ...] | None) -> float:
        if offer is None:
            return self.reserved_value
        outings = [0] * self.n_days
        for days in offer:
            if days is None:
                continue
            for i, v in enumerate(days):
                outings[i] += v
        return self.values.get(tuple(outings), self.reserved_value)

    def side_ufuns(self, n_edges: int) -> tuple[BaseUtilityFunction, ...]:
        """Returns the utility associated with getting a single agreement with one friend"""
        raise ValueError("No side ufuns are defined for the party domain")


class PartyEU(MappingUtilityFunction):
    """
    The Edge (friend) ufun for the Party domain.

    This is a standard `MappingUtilityFunction` with an added parameter,
    `n_friends` that gives the number of friends in the scenario
    """

    def __init__(self, *args, n_friends: int, **kwargs):
        super().__init__(*args, **kwargs)
        self.n_friends = n_friends
