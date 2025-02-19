__all__ = ["make_dinners_scenario"]

import itertools
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
        reserved_value=0.0,
        values: dict[tuple[int, ...], float] | None = None,
    ):
        self.days = list(range(n_days))
        if values is None:
            all_days = list(itertools.product(self.days))
            v = np.random.rand(len(all_days))
            v -= np.min(v)
            v /= np.max(v)
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
        return self.values.get(
            tuple(outings[day] for day in self.days), self.reserved_value
        )


def make_dinners_scenario(
    n_friends: int = 3,
    n_days: int | None = 3,
    friend_names: tuple[str, ...] | None = None,
    center_reserved_value: float = 0.0,
    edge_reserved_value_range: tuple[float, float] = (0.0, 0.5),
    values: dict[tuple[int, ...], float] | None = None,
    public_graph: bool = True,
):
    if n_days is None:
        n_days = n_friends
    if not friend_names:
        friend_names = tuple(f"friend{i+1}" for i in range(n_days))
    assert (
        len(friend_names) == n_days
    ), f"You passed {len(friend_names)} friend names but {n_friends=}"
    outcome_spaces = [
        make_os([make_issue(n_days, name="Day")], name=f"{name}Day")
        for name in friend_names
    ]
    return MultidealScenario(
        name="dinners",
        edge_ufuns=tuple(
            LinearUtilityAggregationFunction.random(
                os, reserved_value=edge_reserved_value_range
            )
            for os in outcome_spaces
        ),
        center_ufun=LambdaCenterUFun(
            evaluator=DinnersEvaluator(
                reserved_value=center_reserved_value, n_days=n_days, values=values
            ),
            reserved_value=center_reserved_value,
            outcome_spaces=outcome_spaces,
        ),
        public_graph=public_graph,
    )
