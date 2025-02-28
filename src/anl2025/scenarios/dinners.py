__all__ = ["make_dinners_scenario"]

import itertools
import random
from typing import Iterable
import numpy as np
from anl2025.scenario import MultidealScenario
from anl2025.ufun import LambdaCenterUFun
from negmas import LinearUtilityAggregationFunction, make_issue, make_os

__all__ = ["make_dinners_scenario"]


class DinnersEvaluator:
    """Evaluates the center utility value of a set of agreements/disagreements"""

    def __init__(
        self,
        n_days: int,
        n_friends: int,
        reserved_value=0.0,
        values: dict[tuple[int, ...], float] | None = None,
    ):
        self.days = list(range(n_days))
        if values is None:
            # days = [self.days for _ in range(n_friends)]
            days = [[0, 1]] * n_days
            all_days = list(itertools.product(*days))
            v = np.random.rand(len(all_days))
            mn, mx = np.min(v), np.max(v)
            if np.all(np.abs(mx - mn)) > 1e-6:
                v -= mn
                v /= mx - mn
            else:
                v[:] = 1.0
            v[np.isnan(v)] = reserved_value
            values = dict(zip(all_days, v.tolist()))

        self.reserved_value = reserved_value
        self.n_days = len(self.days)
        self.values = values

    def __call__(self, agreements):
        if not agreements:
            return self.reserved_value
        outings = dict(zip(self.days, itertools.repeat(0)))
        for agreement in agreements:
            if agreement is None:
                continue
            # day is a tuple of one value which is the day selected
            outings[agreement[0]] += 1
        x = tuple(outings[day] for day in self.days)
        return self.values.get(x, self.reserved_value)


def make_dinners_scenario(
    n_friends: int = 3,
    n_days: int | None = None,
    friend_names: tuple[str, ...] | None = None,
    center_reserved_value: tuple[float, float] | float = 0.0,
    edge_reserved_values: tuple[float, float] = (0.0, 0.5),
    values: dict[tuple[int, ...], float] | None = None,
    public_graph: bool = True,
) -> MultidealScenario:
    """Creates a variation of the Dinners multideal scenario

    Args:
        n_friends: Number of friends.
        n_days: Number of days. If `None`, it will be the same as `n_friends`
        friend_names: Optionally, list of friend names (otherwise we will use Friend{i})
        center_reserved_value: The reserved value of the center. Either a number of a min-max range
        edge_reserved_valus: The reserved value of the friends (edges). Always, a min-max range
        values: A mapping from the number of dinners per day (a tuple of n_days integers) to utility value of the center
        public_graph: Should edges know n_edges and outcome_spaces?

    Returns:
        An initialized `MultidealScenario`.
    """
    if n_days is None:
        n_days = n_friends
    if not friend_names:
        friend_names = tuple(f"Friend{i+1}" for i in range(n_friends))
    assert (
        len(friend_names) == n_friends
    ), f"You passed {len(friend_names)} friend names but {n_friends=}"
    outcome_spaces = [
        make_os([make_issue(n_days, name="Day")], name=f"{name}Day")
        for name in friend_names
    ]
    if not isinstance(center_reserved_value, Iterable):
        r = float(center_reserved_value)
    else:
        r = center_reserved_value[0] + random.random() * (
            center_reserved_value[-1] - center_reserved_value[0]
        )
    return MultidealScenario(
        name="dinners",
        edge_ufuns=tuple(
            LinearUtilityAggregationFunction.random(
                os, reserved_value=edge_reserved_values, normalized=True
            )
            for os in outcome_spaces
        ),
        center_ufun=LambdaCenterUFun(
            outcome_spaces=outcome_spaces,
            evaluator=DinnersEvaluator(
                reserved_value=r,
                n_days=n_days,
                n_friends=n_friends,
                values=values,
            ),
            reserved_value=r,
        ),
        public_graph=public_graph,
    )
