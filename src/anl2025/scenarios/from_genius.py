import pathlib
from pathlib import Path
from negmas.inout import Scenario
from anl2025.runner import run_session
from negmas.helpers import unique_name
from negmas.outcomes import make_os
from anl2025.scenario import MultidealScenario
from anl2025.ufun import HierarchicalCombiner, LambdaCenterUFun
from anl2025.common import (
    sample_between,
)
from negmas.preferences.crisp.linear import LinearAdditiveUtilityFunction


def load_party(number):
    path_to_folder = pathlib.Path(__file__).parent / f"Party{number}"
    scen = Scenario.load(path_to_folder)
    assert scen is not None
    scen.normalize()
    scen.info.update({"name": f"Party{number}"})
    return scen


def make_multideal_scenario_from_genius(
    scenario: Scenario | Path | str | None = None,
    center_reserved_value_min: float = 0.0,
    center_reserved_value_max: float = 0.0,
    # edge ufuns
    edge_reserved_value_min: float = 0.0,
    edge_reserved_value_max: float = 0.0,
    name: str | None = None,
    verbose=False,
) -> MultidealScenario:
    if scenario is None:
        scenario = load_party(10)
    else:
        scenario = load_party(int(scenario))
    nedges = scenario.n_issues
    outcome_spaces = []
    for i in range(nedges):
        outcome_spaces.append(make_os([scenario.issues[i]]))

    # outcome space for center agent
    outcome_spaces = tuple(outcome_spaces)
    DefaultCombiner = HierarchicalCombiner
    center_rv = sample_between(center_reserved_value_min, center_reserved_value_max)
    center_ufun = LambdaCenterUFun(
        outcome_spaces=outcome_spaces,
        evaluator=GeniusEvaluator(scenario.ufuns[0]),
        combiner_type=DefaultCombiner,
        reserved_value=center_rv,
    )
    if verbose:
        for outcome in center_ufun.outcome_space.enumerate_or_sample():
            print(outcome)
            print(f"Utility: {center_ufun(outcome)}")

    edge_ufuns = []
    # for each edge agent, make a table function for the one issue that concerns this agent.
    for i in range(nedges):
        f = LinearAdditiveUtilityFunction(
            values=[scenario.ufuns[1].values[i]],
            weights=[1.0],
            outcome_space=outcome_spaces[i],
            reserved_value=sample_between(
                edge_reserved_value_min, edge_reserved_value_max
            ),
        )
        edge_ufuns.append(f.normalize())

    return MultidealScenario(
        name=scenario.name
        if name
        else unique_name(
            f"s{center_ufun.outcome_space.cardinality}", add_time=False, sep=""
        ),
        center_ufun=center_ufun,
        edge_ufuns=tuple(edge_ufuns),
    )


class GeniusEvaluator:
    """Evaluates the center utility value of a set of agreements/disagreements"""

    # If one of the agreements is None, it returns 0.

    def __init__(self, center_ufun):
        self.center_ufun = center_ufun

    def __call__(self, agreements):
        if not agreements:
            return self.center_ufun.reserved_value
        if any(agreement is None for agreement in agreements):
            return self.center_ufun.reserved_value
        return float(self.center_ufun(tuple(agreements)))


if __name__ == "__main__":
    scenario = make_multideal_scenario_from_genius()
    results = run_session(scenario, verbose=True)
    print(f"Center utility: {results.center_utility}")
    print(f"Edge Utilities: {results.edge_utilities}")
    print(f"Agreement: {results.agreements}")
