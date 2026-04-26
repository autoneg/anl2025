from anl2025.scenarios.dinners import make_dinners_scenario
from anl2025.ufun import FlatteningCombiner, HierarchicalCombiner
from negmas import DiscreteCartesianOutcomeSpace, make_issue, make_os


def test_flatten_unflatten():
    outcome_spaces = (
        make_os(([make_issue(4), make_issue(5)])),
        make_os(([make_issue(2), make_issue(3), make_issue(5)])),
        make_os(([make_issue(["a", "b"]), make_issue("a", "b")])),
        make_os(([make_issue("a", "b")])),
        make_os(([make_issue(4), make_issue(["zz", "aa"])])),
    )
    assert all(isinstance(_, DiscreteCartesianOutcomeSpace) for _ in outcome_spaces)
    x = ((0, 1), None, ("x", "xyz"), ("34",), (4, "zz"))
    f = (0, 1, None, None, None, "x", "xyz", "34", 4, "zz")
    flattener = FlatteningCombiner(outcome_spaces)
    y = flattener.combined_outcome(x)
    assert y == f, f"{y=}\n{f=}"
    yy = flattener.combined_outcome(x)
    assert y == yy, f"{y=}\n{yy=}"
    yy = flattener.combined_outcome(x)
    assert y == yy, f"{y=}\n{yy=}"
    z = flattener.separated_outcomes(y)
    assert z == x, f"{z=}\n{x=}"
    zz = flattener.separated_outcomes(z)
    assert zz == z, f"{zz=}\n{z=}"


def test_center_ufun_extremes():
    n_days, n_friends = 2, 3
    scenario = make_dinners_scenario(n_friends=n_friends, n_days=n_days)
    center = scenario.center_ufun
    worst, best = center.extreme_outcomes()
    assert center._combiner.combined_outcome(worst) == worst
    assert center._combiner.combined_outcome(best) == best
    mn, mx = center.minmax()
    assert mn == 0
    assert mn < mx
    assert abs(center(worst) - mn) < 1e-3
    assert abs(center(best) - mx) < 1e-3
    assert isinstance(center.outcome_space, DiscreteCartesianOutcomeSpace)
    assert all(
        isinstance(_, DiscreteCartesianOutcomeSpace) for _ in center.outcome_spaces
    )
    if isinstance(center._combiner, FlatteningCombiner):
        assert len(center.outcome_space.issues) == sum(
            len(_.issues)  # type: ignore
            for _ in center.outcome_spaces
        )
    elif isinstance(center._combiner, HierarchicalCombiner):
        assert len(center.outcome_space.issues) == len(center.outcome_spaces)
    assert center.outcome_space.cardinality == pow(n_days + 1, n_friends)
    outcomes = list(center.outcome_space.enumerate())
    for outcome in outcomes:
        edge_outcomes = center._combiner.separated_outcomes(outcome)
        assert edge_outcomes is not None
        assert center.outcome_spaces is not None and len(edge_outcomes) == len(
            center.outcome_spaces
        )
        for edge_outcome, os in zip(edge_outcomes, center.outcome_spaces, strict=True):
            assert edge_outcome is None or edge_outcome in os
