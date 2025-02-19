from itertools import product
from pathlib import Path
from anl2025.inout import load_multideal_scenario
from anl2025.runner import MultidealScenario
from anl2025.scenarios.dinners import make_dinners_scenario
from anl2025.ufun import LambdaCenterUFun
from negmas import DiscreteCartesianOutcomeSpace, UtilityFunction
import pytest


@pytest.mark.parametrize("name", ("dinners", "dinners2"))
def test_load_multideal_dinner(name):
    scenario = load_multideal_scenario(
        Path(__file__).parent.parent / "scenarios" / name
    )
    assert isinstance(scenario, MultidealScenario)
    assert isinstance(scenario.center_ufun, LambdaCenterUFun)
    assert all(isinstance(_, UtilityFunction) for _ in scenario.edge_ufuns)
    assert scenario.side_ufuns is None
    assert scenario.name == name
    assert scenario.center_ufun.n_edges == 3
    assert all(_.n_edges == 3 for _ in scenario.edge_ufuns)  # type: ignore
    assert (
        scenario.center_ufun.outcome_spaces
        and len(scenario.center_ufun.outcome_spaces) == 3
    )
    assert isinstance(scenario.center_ufun.outcome_space, DiscreteCartesianOutcomeSpace)
    assert all(
        isinstance(_, DiscreteCartesianOutcomeSpace)
        for _ in scenario.center_ufun.outcome_spaces
    )
    assert len(scenario.center_ufun.outcome_space.issues) == 3
    os = scenario.center_ufun.outcome_spaces[0]
    assert isinstance(os, DiscreteCartesianOutcomeSpace)
    all_outcomes = list(
        product(
            *(os.enumerate() for os in scenario.center_ufun.outcome_spaces)  # type: ignore
        )
    )
    assert len(all_outcomes) == 3 * 3 * 3
    for agreements in all_outcomes:
        assert 0 <= scenario.center_ufun(agreements) <= 1
        for edge_ufun, outcome in zip(scenario.edge_ufuns, agreements):
            assert 0 <= edge_ufun(outcome) <= 1


def test_load_multideal_dinner_created():
    scenario = make_dinners_scenario(n_friends=3, n_days=3)
    assert isinstance(scenario, MultidealScenario)
    assert isinstance(scenario.center_ufun, LambdaCenterUFun)
    assert all(isinstance(_, UtilityFunction) for _ in scenario.edge_ufuns)
    assert scenario.side_ufuns is None
    assert scenario.name == "dinners"
    assert scenario.center_ufun.n_edges == 3
    assert all(_.n_edges == 3 for _ in scenario.edge_ufuns)  # type: ignore
    assert (
        scenario.center_ufun.outcome_spaces
        and len(scenario.center_ufun.outcome_spaces) == 3
    )
    assert isinstance(scenario.center_ufun.outcome_space, DiscreteCartesianOutcomeSpace)
    assert all(
        isinstance(_, DiscreteCartesianOutcomeSpace)
        for _ in scenario.center_ufun.outcome_spaces
    )
    assert len(scenario.center_ufun.outcome_space.issues) == 3
    os = scenario.center_ufun.outcome_spaces[0]
    assert isinstance(os, DiscreteCartesianOutcomeSpace)
    all_outcomes = list(
        product(
            *(os.enumerate() for os in scenario.center_ufun.outcome_spaces)  # type: ignore
        )
    )
    assert len(all_outcomes) == 3 * 3 * 3
    for agreements in all_outcomes:
        assert 0 <= scenario.center_ufun(agreements) <= 1
        for edge_ufun, outcome in zip(scenario.edge_ufuns, agreements):
            assert 0 <= edge_ufun(outcome) <= 1
