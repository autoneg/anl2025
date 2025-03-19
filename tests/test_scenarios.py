import shutil
from itertools import product
from pathlib import Path
from anl2025.inout import load_multideal_scenario
from anl2025.negotiator import Random2025
from anl2025.runner import MultidealScenario, run_session
from anl2025.scenarios.dinners import make_dinners_scenario
from anl2025.scenarios.job_hunt import make_job_hunt_scenario
from anl2025.scenarios.target_quantity import make_target_quantity_scenario
from anl2025.ufun import FlatteningCombiner, HierarchicalCombiner, LambdaCenterUFun
from negmas import DiscreteCartesianOutcomeSpace, UtilityFunction
import pytest

from hypothesis import given, strategies as st, example, settings


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
    run_session(scenario)


@settings(deadline=5000)
@given(n_friends=st.integers(1, 4), n_days=st.integers(1, 7))
@example(n_friends=1, n_days=1)
def test_load_multideal_dinner_created(n_friends, n_days):
    scenario = make_dinners_scenario(n_friends=n_friends, n_days=n_days)
    assert len(scenario.center_ufun.outcome_spaces) == n_friends
    assert scenario.center_ufun.outcome_space
    assert scenario.center_ufun.outcome_space.cardinality == pow(n_days + 1, n_friends)
    assert isinstance(scenario, MultidealScenario)
    assert isinstance(scenario.center_ufun, LambdaCenterUFun)
    assert all(isinstance(_, UtilityFunction) for _ in scenario.edge_ufuns)
    assert scenario.side_ufuns is None
    assert scenario.name == "dinners"
    assert scenario.center_ufun.n_edges == n_friends
    assert all(_.n_edges == n_friends for _ in scenario.edge_ufuns)  # type: ignore
    assert (
        scenario.center_ufun.outcome_spaces
        and len(scenario.center_ufun.outcome_spaces) == n_friends
    )
    assert isinstance(scenario.center_ufun.outcome_space, DiscreteCartesianOutcomeSpace)
    assert all(
        isinstance(_, DiscreteCartesianOutcomeSpace)
        for _ in scenario.center_ufun.outcome_spaces
    )
    assert len(scenario.center_ufun.outcome_space.issues) == n_friends
    if isinstance(scenario.center_ufun._combiner, FlatteningCombiner):
        assert (scenario.center_ufun.outcome_space.issues[0].cardinality) == n_days
    elif isinstance(scenario.center_ufun._combiner, HierarchicalCombiner):
        assert (scenario.center_ufun.outcome_space.issues[0].cardinality) == n_days + 1
    os = scenario.center_ufun.outcome_spaces[0]
    assert isinstance(os, DiscreteCartesianOutcomeSpace)
    full_outcomes = list(
        product(
            *(os.enumerate() for os in scenario.center_ufun.outcome_spaces)  # type: ignore
        )
    )
    assert len(full_outcomes) == pow(n_days, n_friends)
    all_outcomes = scenario.center_ufun.outcome_space.enumerate()  # type: ignore
    for agreements in all_outcomes:
        assert 0 <= scenario.center_ufun(agreements) <= 1
        for edge_ufun, outcome in zip(scenario.edge_ufuns, agreements):
            assert 0 <= edge_ufun(outcome) <= 1
    run_session(scenario)


def test_make_job_hunt_all_rand():
    scenario = make_job_hunt_scenario()
    # Path(__file__).parent.parent / "scenarios" / "job_hunt"
    run_session(scenario, edge_types=[Random2025], center_type=Random2025)


def test_make_job_hunt():
    scenario = make_job_hunt_scenario()
    path = Path(__file__).parent.parent / "scenarios" / "job_hunt"
    shutil.rmtree(path)
    run_session(scenario)
    scenario.to_folder(path)
    s2 = MultidealScenario.from_folder(path)
    assert s2 is not None
    run_session(s2)


def test_make_target_quantity():
    scenario = make_target_quantity_scenario()
    path = Path(__file__).parent.parent / "scenarios" / "target_quantity"
    shutil.rmtree(path, ignore_errors=True)
    run_session(scenario)
    scenario.to_folder(path)
    s2 = MultidealScenario.from_folder(path)
    assert s2 is not None
    run_session(s2)


def test_read_simplified_dinners():
    path = Path(__file__).parent.parent / "scenarios" / "dinners"
    scenario = MultidealScenario.from_folder(path)
    assert scenario
    run_session(scenario)
    dst = Path(__file__).parent.parent / "scenarios" / "dinners_saved"
    shutil.rmtree(dst, ignore_errors=True)
    scenario.to_folder(dst)
    s2 = MultidealScenario.from_folder(dst)
    assert s2 is not None
    run_session(s2)


def test_read_simplified_target_quantity():
    path = Path(__file__).parent.parent / "scenarios" / "TargetQuantity"
    scenario = MultidealScenario.from_folder(path)
    assert scenario
    run_session(scenario)
    dst = Path(__file__).parent.parent / "scenarios" / "TargetQuantitySaved"
    shutil.rmtree(dst, ignore_errors=True)
    scenario.to_folder(dst)
    s2 = MultidealScenario.from_folder(dst)
    assert s2 is not None
    run_session(s2)


def test_read_simplified_job_hunt():
    path = Path(__file__).parent.parent / "scenarios" / "job_hunt_target"
    scenario = MultidealScenario.from_folder(path)
    assert scenario
    run_session(scenario)
    dst = Path(__file__).parent.parent / "scenarios" / "job_hunt_saved"
    shutil.rmtree(dst, ignore_errors=True)
    scenario.to_folder(dst)
    s2 = MultidealScenario.from_folder(dst)
    assert s2 is not None
    run_session(s2)
