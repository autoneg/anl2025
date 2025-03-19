from copy import deepcopy
from rich import print
from typing import Any
from random import choice
import pandas as pd
from attr import define, field
from pathlib import Path
import matplotlib.pyplot as plt
from negmas import ControlledNegotiator
from negmas.outcomes import Outcome
from negmas.sao import SAOMechanism
from negmas.helpers import unique_name

from anl2025.ufun import CenterUFun, make_side_ufun
from anl2025.negotiator import (
    ANL2025Negotiator,
    Boulware2025,
    Conceder2025,
    Linear2025,
    Random2025,
)
from anl2025.scenario import MultidealScenario, make_multideal_scenario
from anl2025.common import SEQUENTIAL_METHOD, get_agent_class, RunParams, DEFAULT_METHOD


__all__ = [
    "run_session",
    "run_generated_session",
    "SessionResults",
    "RunParams",
    "AssignedScenario",
    "assign_scenario",
]

TRACE_COLS = (
    "time",
    "relative_time",
    "step",
    "negotiator",
    "offer",
    "responses",
    "state",
)


@define
class SessionResults:
    """Results of a single multideal negotiation

    Attributes:
        mechanisms: The mechanisms representing negotiation threads.
        center: The center agent
        edges: Edge agents
        agreements:  Negotiation outcomes for all threads.
        center_utility: The utility received by the center.
        edge_utilities: The utilities of all edges.
    """

    mechanisms: list[SAOMechanism]
    center: ANL2025Negotiator
    edges: list[ANL2025Negotiator]
    agreements: list[Outcome | None]
    center_utility: float
    edge_utilities: list[float]


@define
class AssignedScenario:
    """A scenario with assigned agents ready to run.

    Attributes:
        scenario: The scenario
        run_params: `RunParams` controlling how the session is run
        center: The center agent
        edges: edge agents
    """

    scenario: MultidealScenario
    run_params: RunParams
    center: ANL2025Negotiator
    edges: list[ANL2025Negotiator]
    _saved_scenario: MultidealScenario = field(init=False)

    def __attrs_post_init__(self):
        self._saved_scenario = deepcopy(self.scenario)

    def run(
        self,
        name: str = "",
        output: Path | str | None = None,
        verbose: bool = False,
        dry: bool = False,
    ) -> SessionResults:
        """Runs a multi-deal negotiation and gets the results"""
        if output and isinstance(output, str):
            output = Path(output)

        def type_name(x):
            if isinstance(x, Boulware2025):
                return "Boulware2025"
            if not issubclass(x.default_negotiator_type, ControlledNegotiator):
                return f"ANL2025({x.default_negotiator_type.__name__})"
            return x.__class__.__name__.split(".")[-1]

        center = self.center
        edges = self.edges
        # edge_ufuns = [deepcopy(_) for _ in self.scenario.edge_ufuns]
        edge_ufuns = self.scenario.edge_ufuns
        center_ufun = self.scenario.center_ufun
        # center_ufun = deepcopy(self.scenario.center_ufun)
        # We MUST reconnect side ufuns for expected outcomes to work
        # center_ufun._effective_side_ufuns = tuple(
        #     make_side_ufun(center_ufun, i, None) for i in range(center_ufun.n_edges)
        # )
        # assume stationarity
        center_ufun.stationary = True
        center_ufun.stationary_sides = (
            center_ufun.stationary_sides or self.run_params.method == SEQUENTIAL_METHOD
        )
        len(edge_ufuns)
        if verbose:
            print(f"Adding center of type {type_name(center)}")

        mechanisms = []
        try:
            side_ufuns = center_ufun.side_ufuns()
        except Exception:
            side_ufuns = None
        if not side_ufuns:
            side_ufuns = [None] * len(edges)
        side_ufuns = [
            make_side_ufun(center_ufun, i, side) for i, side in enumerate(side_ufuns)
        ]
        for i, (edge_ufun, side_ufun, edge) in enumerate(
            zip(edge_ufuns, side_ufuns, edges, strict=True)
        ):
            m = SAOMechanism(
                outcome_space=edge_ufun.outcome_space,
                one_offer_per_step=self.run_params.atomic,
                name=f"n{i}",
                n_steps=self.run_params.nsteps,
                end_on_no_response=True,
            )
            m.id = m.name = f"n{i}"
            if verbose:
                print(f"Adding edge {i} of type {type_name(edge)} (thread: {m.name})")
            m.add(
                center.create_negotiator(
                    cntxt=dict(center=True, ufun=side_ufun, index=i),
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
                    cntxt=dict(center=False, ufun=edge_ufun, index=i),
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

        base = None
        if output:
            base = output / name
            (base / "log").mkdir(parents=True, exist_ok=True)
            (base / "plots").mkdir(parents=True, exist_ok=True)

        def plot_result(i, m, base=base):
            assert base is not None
            df = pd.DataFrame(data=m.full_trace, columns=TRACE_COLS)  # type: ignore
            df.to_csv(base / "log" / f"{m.id}.csv", index_label="index")
            m.plot(save_fig=True, path=str(base / "plots"), fig_name=f"n{i}.png")
            plt.close()

        SAOMechanism.runall(
            mechanisms,
            method=self.run_params.method,
            keep_order=self.run_params.keep_order,
            completion_callback=plot_result if output else None,
        )  # type: ignore
        if not name:
            name = unique_name("session", sep=".")
        agreements = [_.agreement for _ in mechanisms]

        return SessionResults(
            mechanisms=mechanisms,
            center=center,
            agreements=agreements,
            center_utility=float(self._saved_scenario.center_ufun(tuple(agreements))),
            edge_utilities=[
                float(edge_ufun(_)) if edge_ufun else float("nan")
                for edge_ufun, _ in zip(self._saved_scenario.edge_ufuns, agreements)
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
        Random2025,
        Linear2025,
        Conceder2025,
    ],
    edge_params: list[dict[str, Any]] | None = None,
    verbose: bool = False,
    sample_edges: bool = False,
) -> AssignedScenario:
    """Assigns a multidal scenario to negotiators

    Args:
        scenario: The multideal scenario
        run_params: Parameters controlling the session is run (See `RunParams`).
        center_type: Type of the center agent
        center_params: Optional parameters to pass to the center agent when it is being constructed
        edge_types: Types of edge agents
        edge_params: Optional parameters to pass to edge agents.
        verbose: Print progress
        sample_edges: If true, the `edge_types` will be used as a pool to sample from
                      instead of being assigned to edges in order

    Returns:
        An `AssignedScenario` ready to run.
    """
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


def run_generated_session(
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
        Random2025,
        Linear2025,
        Conceder2025,
    ],
    # outcome space
    nissues: int = 3,
    nvalues: int = 7,
    # mechanism params
    nsteps: int = 100,
    keep_order: bool = True,
    share_ufuns: bool = True,
    atomic: bool = False,
    # output and logging
    output: Path | str | None = Path.home() / "negmas" / "anl2025" / "session",
    name: str = "",
    dry: bool = False,
    method=DEFAULT_METHOD,
    verbose: bool = False,
) -> SessionResults:
    """Generates a multideal negotiation session and runs it.

    Args:
        method: the method to use for running all the sessions.
                Acceptable options are: sequential, ordered, threads, processes.
                See `negmas.mechanisms.Mechanism.run_all()` for full details.
        center_type: Type of the center agent
        center_params: Optional parameters to pass to the center agent.
        center_reserved_value_min: Minimum reserved value for the center agent.
        center_reserved_value_max: Maximum reserved value for the center agent.
        center_ufun_type: Type of the center agent ufun.
        center_ufun_params: Parameters to pass to the center agent ufun.
        nedges: Number of edges.
        edge_reserved_value_min: Minimum reserved value for edges.
        edge_reserved_value_max: Maximum reserved value for edges.
        edge_types: Types of edge agents
        nissues: Number of issues to use for each thread.
        nvalues: Number of values per issue for each thread.
        nsteps: Number of negotiation steps.
        keep_order: Keep the order of edges when advancing the negotiation.
        share_ufuns: If given, agents will have access to partner ufuns through `self.opponent_ufun`.
        atomic: If given, one step corresponds to one offer instead of a full round.
        output: Folder to store the logs and results within.
        name: Name of the session
        dry: IF true, nothing will be run.
        verbose: Print progress

    Returns:
        `SessionResults` giving the results of the multideal negotiation session.
    """
    if output and isinstance(output, str):
        output = Path(output)
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


def run_session(
    scenario: MultidealScenario,
    # center
    center_type: str | type[ANL2025Negotiator] = "Boulware2025",
    center_params: dict[str, Any] | None = None,
    # edges
    edge_types: list[str | type[ANL2025Negotiator]] = [
        Boulware2025,
        Linear2025,
        Conceder2025,
    ],
    # mechanism params
    nsteps: int = 100,
    keep_order: bool = True,
    share_ufuns: bool = True,
    atomic: bool = False,
    # output and logging
    output: Path | None = Path.home() / "negmas" / "anl2025" / "session",
    name: str = "",
    dry: bool = False,
    method=DEFAULT_METHOD,
    verbose: bool = False,
    sample_edges: bool = False,
) -> SessionResults:
    """Runs a multideal negotiation session and runs it.

    Args:
        scenario: The negotiation scenario (must be `MultidealScenario`).
        method: the method to use for running all the sessions.
                Acceptable options are: sequential, ordered, threads, processes.
                See `negmas.mechanisms.Mechanism.run_all()` for full details.
        center_type: Type of the center agent
        center_params: Optional parameters to pass to the center agent.
        center_ufun_type: Type of the center agent ufun.
        center_ufun_params: Parameters to pass to the center agent ufun.
        edge_types: Types of edge agents
        nsteps: Number of negotiation steps.
        keep_order: Keep the order of edges when advancing the negotiation.
        share_ufuns: If given, agents will have access to partner ufuns through `self.opponent_ufun`.
        atomic: If given, one step corresponds to one offer instead of a full round.
        output: Folder to store the logs and results within.
        name: Name of the session
        dry: IF true, nothing will be run.
        verbose: Print progress
        sample_edges: If true, the `edge_types` will be used as a pool to sample from otherwise edges will
                      be of the types defined by edge_types in order

    Returns:
        `SessionResults` giving the results of the multideal negotiation session.
    """
    if output and isinstance(output, str):
        output = Path(output)
    run_params = RunParams(
        nsteps=nsteps,
        keep_order=keep_order,
        share_ufuns=share_ufuns,
        atomic=atomic,
        method=method,
    )
    # if not sample_edges:
    #     assert (
    #         len(edge_types) == len(scenario.edge_ufuns)
    #     ), f"You are trying to run a session without sampling, but the number of provided edge types ({len(edge_types)}) is not equal to the number of edge ufuns in the scenario ({len(scenario.edge_ufuns)})."

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
