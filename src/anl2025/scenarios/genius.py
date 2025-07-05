from negmas import (
    AffineUtilityFunction,
    IdentityFun,
    LinearFun,
    LinearUtilityAggregationFunction,
)
from negmas.inout import Scenario
from negmas.helpers import unique_name
from negmas.outcomes import make_os
from anl2025.scenario import MultidealScenario
from anl2025.ufun import LinearCombinationCenterUFun
from anl2025.common import (
    sample_between,
)
from negmas.preferences.crisp.linear import LinearAdditiveUtilityFunction

__all__ = ["make_multideal_scenario_from_genius"]


def _adjust_name(name: str) -> str:
    return name.split("/")[-1]


def make_multideal_scenario_from_genius(
    scenario: Scenario,
    center_reserved_value_min: float | None = 0.0,
    center_reserved_value_max: float | None = 0.3,
    # edge ufuns
    edge_reserved_value_min: float = 0.0,
    edge_reserved_value_max: float = 0.2,
    center_index: int = 0,
    edge_index: int = -1,
    name: str | None = None,
    public_graph: bool = True,
    allow_partial_agreements=False,
    verbose=False,
    n_edges_max: int | None = None,
    eps: float = 1e-6,
) -> MultidealScenario:
    if n_edges_max is None or n_edges_max >= scenario.n_issues:
        n_edges = scenario.n_issues
    else:
        raise NotImplementedError("Currently we only support one issue per edge")
    outcome_spaces = []
    if name is None:
        name = scenario.outcome_space.name
    if name is None:
        name = unique_name("genius", sep="")
    os = scenario.outcome_space
    edge_ufuns, side_ufuns, center_weights = [], [], []
    for i, issue in enumerate(os.issues):
        edge_os = make_os([issue], name=issue.name)
        outcome_spaces.append(edge_os)
        orig_edge_ufun = scenario.ufuns[edge_index]
        if isinstance(orig_edge_ufun, LinearAdditiveUtilityFunction):
            val = orig_edge_ufun.values[i]
        elif isinstance(orig_edge_ufun, (AffineUtilityFunction, LinearFun)):
            val = IdentityFun()
        else:
            raise ValueError(
                f"Cannot handle {type(orig_edge_ufun)} when creating edge ufuns"
            )
        center_weights.append(orig_edge_ufun.weights[i])
        rng = val.minmax(issue)
        edge_ufuns.append(
            LinearUtilityAggregationFunction(
                name=f"{_adjust_name(orig_edge_ufun.name)}_{issue.name}",
                values=[val],
                weights=[1.0],
                outcome_space=edge_os,
                reserved_value=sample_between(
                    edge_reserved_value_min * (rng[1] - rng[0]) + rng[0],
                    edge_reserved_value_max * (rng[1] - rng[0]) + rng[0],
                ),
            )
        )
        orig_center_ufun = scenario.ufuns[center_index]
        if isinstance(orig_center_ufun, LinearAdditiveUtilityFunction):
            val = orig_center_ufun.values[i]
        elif isinstance(orig_center_ufun, (AffineUtilityFunction, LinearFun)):
            val = IdentityFun()
        else:
            raise ValueError(
                f"Cannot handle {type(orig_center_ufun)} when creating center ufuns"
            )
        rng = val.minmax(issue)
        side_ufuns.append(
            LinearUtilityAggregationFunction(
                name=f"{_adjust_name(orig_center_ufun.name)}_{issue.name}",
                values=[val],
                weights=[1.0],
                outcome_space=edge_os,
                reserved_value=0.0,
            )
        )

    outcome_spaces = tuple(outcome_spaces)
    center_min_max = scenario.ufuns[center_index].minmax(os)

    center_ufun = LinearCombinationCenterUFun(
        name=_adjust_name(scenario.ufuns[center_index].name),
        side_ufuns=tuple(side_ufuns),
        weights=tuple(center_weights),
        outcome_spaces=outcome_spaces,
        n_edges=n_edges,
        reserved_value=sample_between(
            center_reserved_value_min * (center_min_max[1] - center_min_max[0])
            + center_min_max[0],
            center_reserved_value_max * (center_min_max[1] - center_min_max[0])
            + center_min_max[0],
            eps=eps,
        )
        if center_reserved_value_min is not None
        and center_reserved_value_max is not None
        else scenario.ufuns[center_index].reserved_value,
        allow_partial_agreements=allow_partial_agreements,
    )

    return MultidealScenario(
        name=name,
        center_ufun=center_ufun,
        edge_ufuns=tuple(edge_ufuns),
        public_graph=public_graph,
    )
