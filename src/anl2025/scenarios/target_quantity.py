import random
from itertools import product
from numpy import argmin
from typing import Iterable
from negmas import LinearAdditiveUtilityFunction, TableFun
from negmas.outcomes import (
    make_os,
    make_issue,
    DiscreteCartesianOutcomeSpace,
    ContiguousIssue,
)
from anl2025.ufun import LambdaCenterUFun
from anl2025.scenario import MultidealScenario


__all__ = ["make_target_quantity_scenario"]

FloatRange = tuple[float, float] | float
IntRange = tuple[int, int] | list[int] | int


def float_in(x: FloatRange):
    if isinstance(x, Iterable):
        return x[0] + (x[1] - x[0]) * random.random()
    return x


def int_in(x: IntRange):
    if isinstance(x, Iterable):
        return random.randint(min(x), max(x))
    return x


class TargetEvaluator:
    """Evaluates the center utility value of a set of agreements/disagreements"""

    def __init__(self, values: dict[int, float], reserved_value=0.0):
        self.reserved_value = reserved_value
        self.values = {int(k): float(v) for k, v in values.items()}

    def __call__(self, agreements):
        if not agreements:
            return self.reserved_value

        # outings = dict(zip(self.days, itertools.repeat(0)))
        quantity_sum = 0
        for agreement in agreements:
            if agreement is None:
                continue
            quantity_sum += int(agreement[0])
        return float(self.values.get(quantity_sum, self.reserved_value))


def make_values(
    qs: list[int], target: int, shortfall: FloatRange, excess: FloatRange
) -> dict[int, float]:
    if target not in qs:
        dists = [abs(_ - target) for _ in qs]
        target = int(argmin(dists))
    else:
        target = qs.index(target)
    if target > max(qs):
        target = max(qs)
    if target < min(qs):
        target = min(qs)
    values = [0.0] * len(qs)
    values[target] = 1.0
    for i in range(target - 1, -1, -1):
        values[i] = max(0.0, values[i + 1] - float_in(shortfall))
    for i in range(target + 1, len(values)):
        values[i] = max(0.0, values[i - 1] - float_in(excess))
    return dict(zip(qs, values))


def make_target_quantity_scenario(
    n_suppliers: IntRange = 4,
    quantity: IntRange = (1, 5),
    target_quantity: IntRange = (2, 20),
    shortfall_penalty: FloatRange = (0.1, 0.3),
    excess_penalty: FloatRange = (0.1, 0.4),
    public_graph: bool = True,
    supplier_names: list[str] | None = None,
    collector_name: str = "Collector",
    collector_reserved_value: FloatRange = 0.0,
    supplier_reserved_values: FloatRange = 0.0,
    supplier_shortfall_penalty: FloatRange | None = (0.3, 0.9),
    supplier_excess_penalty: FloatRange | None = (0.3, 0.9),
) -> MultidealScenario:
    """Creates a target-quantity type scenario

    Args:
        n_suppliers: Number of suppliers (sources/sellers)
        quantity: The range of values for each supplier (if an integer, then the range is (0, quanityt-1))
        target_quantity: The target quantity of the collector (buyer)
        shortfall_penalty: The collector's penalty for buying an item less than target. Can be a range to sample form it
        excess_penalty: The penalty for buying an item more than target. Can be a range to sample form it
        public_graph: Whether edges (suppliers) know n_edges and outcome-spaces of the center (collector)
        supplier_names: Names of suppliers
        collector_name: Name of the collector
        collector_reserved_value: Range or a single value for collector's reserved value
        supplier_reserved_values: Range or a single value for supplier's reserved value
        supplier_shortfall_penalty: suppliers' penalty for buying an item less than their target. Can be a range to sample form it
        supplier_excess_penalty: suppliers' penalty for buying an item more than their target. Can be a range to sample form it

    Remarks:
        - Supplier's target value is sampled uniformly from the range of values
    """
    n_suppliers = int_in(n_suppliers)
    if supplier_shortfall_penalty is None:
        supplier_shortfall_penalty = shortfall_penalty
    if supplier_excess_penalty is None:
        supplier_excess_penalty = excess_penalty
    if supplier_names is None:
        supplier_names = [f"supplier{_+1:02}" for _ in range(n_suppliers)]
    os = make_os([make_issue(quantity, name="quantity")], name="TargetQantity")
    assert isinstance(os, DiscreteCartesianOutcomeSpace)
    quantities = list(os.issues[0].all)
    if isinstance(os.issues[0], ContiguousIssue):
        totals = list(range(n_suppliers * os.issues[0].max_value + 1))
    else:
        totals = sorted(
            list(set([sum(_) for _ in product(*([[0] + quantities] * n_suppliers))]))
        )
    center_ufun = LambdaCenterUFun(
        n_edges=n_suppliers,
        outcome_space=os,
        evaluator=TargetEvaluator(
            values=make_values(
                totals, int_in(target_quantity), shortfall_penalty, excess_penalty
            )
        ),
        name=collector_name,
        reserved_value=float_in(collector_reserved_value),
    )
    edge_ufuns = tuple(
        LinearAdditiveUtilityFunction(
            outcome_space=os,
            reserved_value=float_in(supplier_reserved_values),
            values=(
                TableFun(
                    make_values(
                        quantities,
                        int_in((os.issues[0].min_value, os.issues[0].max_value)),
                        float_in(supplier_shortfall_penalty),
                        float_in(supplier_excess_penalty),
                    )
                ),
            ),
            weights=(1.0,),
            name=name,
        )
        for name in supplier_names
    )

    return MultidealScenario(center_ufun, edge_ufuns, public_graph=public_graph)
