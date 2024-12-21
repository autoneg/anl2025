from random import choice, random
from typing import Any
from negmas.preferences import UtilityFunction
import pandas as pd
from rich import print
from attr import define
from pathlib import Path
from negmas.outcomes import Outcome
from negmas.helpers.strings import unique_name
from negmas.helpers.types import get_class
from negmas.preferences.generators import generate_multi_issue_ufuns
from negmas.negotiators import ControlledNegotiator
from negmas.sao import SAOMechanism
from anl2025.ufun import CenterUFun
from anl2025.negotiator import (
    ANL2025Negotiator,
    Boulware2025,
    Shochan2025,
    AgentRenting2025,
    RandomNegotiator,
)

__all__ = ["run_session", "SessionResults"]

TRACE_COLS = (
    "time",
    "relative_time",
    "step",
    "negotiator",
    "offer",
    "responses",
    "state",
)
EPSILON = 1e-6
DEFAULT_METHOD = "sequential"


def get_ufun_class(x: str | type[CenterUFun]) -> type[CenterUFun]:
    """Returns the type of the agent"""
    if not isinstance(x, str):
        return x
    return get_class(x, module_name="anl2025.ufun")


def get_agent_class(x: str | type[ANL2025Negotiator]) -> type[ANL2025Negotiator]:
    """Returns the type of the agent"""
    if not isinstance(x, str):
        return x
    return get_class(x, module_name="anl2025.negotiator")


@define
class SessionResults:
    mechanisms: list[SAOMechanism]
    center: ANL2025Negotiator
    edges: list[ANL2025Negotiator]
    agreements: list[Outcome | None]
    center_utility: float
    edge_utilities: list[float]


@define
class RunParams:
    """Defines the running parameters of the multi-deal negotiation like time-limits."""

    # mechanism params
    nsteps: int = 100
    keep_order: bool = False
    share_ufuns: bool = False
    atomic: bool = False
    method: str = DEFAULT_METHOD


@define
class MultidealScenario:
    """Defines the multi-deal scenario by setting utility functions (and implicitly outcome-spaces)"""

    center_ufun: CenterUFun
    edge_ufuns: tuple[UtilityFunction, ...]
    side_ufuns: tuple[UtilityFunction, ...] | None = None
    name: str = ""


@define
class AssignedScenario:
    """A scenario ready to be run"""

    scenario: MultidealScenario
    run_params: RunParams
    center: ANL2025Negotiator
    edges: list[ANL2025Negotiator]

    def run(
        self,
        name: str = "",
        output: Path | None = None,
        verbose: bool = False,
        dry: bool = False,
    ) -> SessionResults:
        """Runs a multi-deal negotiation and gets the results"""

        def type_name(x):
            if isinstance(x, Boulware2025):
                return "Boulware2025"
            if not issubclass(x.default_negotiator_type, ControlledNegotiator):
                return f"ANL2025({x.default_negotiator_type.__name__})"
            return x.__class__.__name__.split(".")[-1]

        center = self.center
        edges = self.edges
        edge_ufuns = self.scenario.edge_ufuns
        center_ufun = self.scenario.center_ufun
        nedges = len(edge_ufuns)
        if verbose:
            print(f"Adding center of type {type_name(center)}")

        mechanisms = []
        for i, (edge_ufun, side_ufun, edge) in enumerate(
            zip(edge_ufuns, center_ufun.side_ufuns(nedges), edges, strict=True)
        ):
            m = SAOMechanism(
                outcome_space=edge_ufun.outcome_space,
                one_offer_per_step=self.run_params.atomic,
                name=f"n{i}",
                n_steps=self.run_params.nsteps,
            )
            m.id = m.name = f"n{i}"
            if verbose:
                print(f"Adding edge {i} of type {type_name(edge)} (thread: {m.name})")
            m.add(
                center.create_negotiator(
                    cntxt=dict(center=True, ufun=side_ufun),
                    ufun=side_ufun,
                    id=f"s{i}",
                    private_info=dict(opponent_ufun=edge_ufun)
                    if self.run_params.share_ufuns
                    else dict(),
                )
            )
            m.negotiators[-1].id = m.negotiators[-1].name = f"s{i}"
            m.add(
                edge.create_negotiator(
                    cntxt=dict(center=False, ufun=edge_ufun),
                    ufun=edge_ufun,
                    id=f"e{i}",
                    private_info=dict(opponent_ufun=side_ufun)
                    if self.run_params.share_ufuns
                    else dict(),
                )
            )
            m.negotiators[-1].id = m.negotiators[-1].name = f"e{i}"
            mechanisms.append(m)
        assert isinstance(center.ufun, CenterUFun)
        center.init()
        for edge in edges:
            edge.init()
        if dry:
            return SessionResults(
                mechanisms=mechanisms,
                center=center,
                center_utility=0.0,
                edge_utilities=[0.0] * len(edges),
                edges=edges,
                agreements=[None] * len(edges),
            )

        SAOMechanism.runall(
            mechanisms,
            method=self.run_params.method,
            keep_order=self.run_params.keep_order,
        )  # type: ignore
        if not name:
            name = unique_name("session", sep=".")
        if output:
            base = output / name
            (base / "log").mkdir(parents=True, exist_ok=True)
            (base / "plots").mkdir(parents=True, exist_ok=True)
            for i, (m, u) in enumerate(
                zip(mechanisms, center_ufun.side_ufuns(len(edges)))
            ):
                df = pd.DataFrame(data=m.full_trace, columns=TRACE_COLS)  # type: ignore
                df.to_csv(base / "log" / f"{m.id}.csv", index_label="index")
                m.plot(save_fig=True, path=str(base / "plots"), fig_name=f"n{i}.png")
        agreements = [_.agreement for _ in mechanisms]

        return SessionResults(
            mechanisms=mechanisms,
            center=center,
            agreements=agreements,
            center_utility=float(center.ufun(tuple(agreements))),
            edge_utilities=[
                float(edge.ufun(_)) if edge.ufun else float("nan")
                for edge, _ in zip(edges, agreements)
            ],
            edges=edges,
        )


def assign_scenario(
    scenario: MultidealScenario,
    run_params: RunParams,
    center_type: str | type[ANL2025Negotiator] = "Boulware2025",
    center_params: dict[str, Any] | None = None,
    edge_types: list[str | type[ANL2025Negotiator]] = [
        Boulware2025,
        RandomNegotiator,
        Shochan2025,
        AgentRenting2025,
    ],
    edge_params: list[dict[str, Any]] | None = None,
    verbose: bool = False,
    sample_edges: bool = False,
) -> AssignedScenario:
    center_ufun = scenario.center_ufun
    edge_ufuns = scenario.edge_ufuns
    nedges = len(edge_ufuns)

    if not edge_params:
        edge_params = [dict() for _ in range(nedges)]
    center_params = center_params if center_params else dict()
    center = get_agent_class(center_type)(
        id="center", ufun=center_ufun, **center_params
    )

    agents = [get_agent_class(_) for _ in edge_types]
    edges: list[ANL2025Negotiator] = []
    if verbose:
        print(
            f"Will use the following agents for edges\n{[_.__name__ if not isinstance(_, str) else _.split('.')[-1] for _ in agents]}"
        )
    for i, (edge_ufun, edge_p) in enumerate(zip(edge_ufuns, edge_params)):
        if sample_edges:
            edget = choice(agents)
        else:
            edget = agents[i % len(edge_types)]
        edge = edget(ufun=edge_ufun, id=f"edge{i}", n_edges=nedges, **edge_p)
        edges.append(edge)
    assert isinstance(center.ufun, CenterUFun)
    return AssignedScenario(
        scenario=scenario,
        run_params=run_params,
        center=center,
        edges=edges,
    )


def make_multideal_scenario(
    nedges: int = 10,
    nissues: int = 3,
    nvalues: int = 7,
    # edge ufuns
    center_reserved_value_min: float = 0.0,
    center_reserved_value_max: float = 0.0,
    center_ufun_type: str | type[CenterUFun] = "MaxCenterUFun",
    center_ufun_params: dict[str, Any] | None = None,
    # edge ufuns
    edge_reserved_value_min: float = 0.1,
    edge_reserved_value_max: float = 0.4,
):
    ufuns = [generate_multi_issue_ufuns(nissues, nvalues) for _ in range(nedges)]
    edge_ufuns = [_[0] for _ in ufuns]
    for u in edge_ufuns:
        u.reserved_value = sample_between(
            edge_reserved_value_min, edge_reserved_value_max
        )
    # side ufuns are utilities of the center on individual threads (may or may not be used, see next comment)
    side_ufuns = tuple(_[1] for _ in ufuns)
    # create center ufun using side-ufuns if possible and without them otherwise.
    center_r = sample_between(center_reserved_value_min, center_reserved_value_max)
    utype = get_ufun_class(center_ufun_type)
    center_ufun_params = center_ufun_params if center_ufun_params else dict()
    try:
        center_ufun = utype(
            ufuns=side_ufuns,
            reserved_value=center_r,
            outcome_spaces=tuple(u.outcome_space for u in side_ufuns),  # type: ignore
            **center_ufun_params,
        )
    except TypeError:
        # if the center ufun does not take `ufuns` as an input, do not pass it
        center_ufun = utype(
            reserved_value=center_r,
            outcome_spaces=tuple(u.outcome_space for u in side_ufuns),  # type: ignore
            **center_ufun_params,
        )

    return MultidealScenario(
        center_ufun=center_ufun,
        side_ufuns=side_ufuns,
        edge_ufuns=tuple(edge_ufuns),
    )


def sample_between(mn: float, mx: float, eps: float = EPSILON) -> float:
    if (mx - mn) > eps:
        return mn + (mx - mn) * random()
    return (mx + mn) / 2.0


def run_session(
    # center
    center_type: str = "Boulware2025",
    center_params: dict[str, Any] | None = None,
    center_reserved_value_min: float = 0.0,
    center_reserved_value_max: float = 0.0,
    center_ufun_type: str | type[CenterUFun] = "MaxCenterUFun",
    center_ufun_params: dict[str, Any] | None = None,
    # edges
    nedges: int = 10,
    edge_reserved_value_min: float = 0.1,
    edge_reserved_value_max: float = 0.4,
    edge_types: list[str | type[ANL2025Negotiator]] = [
        Boulware2025,
        RandomNegotiator,
        Shochan2025,
        AgentRenting2025,
    ],
    # outcome space
    nissues: int = 3,
    nvalues: int = 7,
    # mechanism params
    nsteps: int = 100,
    keep_order: bool = False,
    share_ufuns: bool = False,
    atomic: bool = False,
    # output and logging
    output: Path | None = Path.home() / "negmas" / "anl2025" / "session",
    name: str = "",
    dry: bool = True,
    method="ordered",
    verbose: bool = False,
) -> SessionResults:
    sample_edges = nedges > 0
    if not sample_edges:
        nedges = len(edge_types)
    scenario = make_multideal_scenario(
        nedges=nedges,
        nissues=nissues,
        nvalues=nvalues,
        center_reserved_value_min=center_reserved_value_min,
        center_reserved_value_max=center_reserved_value_max,
        center_ufun_type=center_ufun_type,
        center_ufun_params=center_ufun_params,
        edge_reserved_value_min=edge_reserved_value_min,
        edge_reserved_value_max=edge_reserved_value_max,
    )
    run_params = RunParams(
        nsteps=nsteps,
        keep_order=keep_order,
        share_ufuns=share_ufuns,
        atomic=atomic,
        method=method,
    )
    assigned = assign_scenario(
        scenario=scenario,
        run_params=run_params,
        center_type=center_type,
        center_params=center_params,
        edge_types=edge_types,
        verbose=verbose,
        sample_edges=sample_edges,
    )
    return assigned.run(output=output, name=name, dry=dry, verbose=verbose)
