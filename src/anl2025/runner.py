from random import choice, random
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


def run_session(
    # center
    center_type: str = "Boulware2025",
    center_reserved_value: float = 0.0,
    center_ufun_type: str | type[CenterUFun] = "MaxCenterUFun",
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
    nsteps: int = 100,
    # mechanism params
    keep_order: bool = False,
    share_ufuns: bool = False,
    atomic: bool = False,
    sequential=False,
    # output and logging
    output: Path | None = Path.home() / "negmas" / "anl2025" / "session",
    name: str = "",
    dry: bool = True,
    method="serial",
    verbose: bool = False,
) -> SessionResults:
    sample_edges = nedges > 0
    if not sample_edges:
        nedges = len(edge_types)
    ufuns = [generate_multi_issue_ufuns(nissues, nvalues) for _ in range(nedges)]
    d = edge_reserved_value_max - edge_reserved_value_min
    edge_ufuns = [_[0] for _ in ufuns]
    for u in edge_ufuns:
        u.reserved_value = random() * d + edge_reserved_value_min
    # side ufuns are utilities of the center on individual threads (may or may not be used, see next comment)
    side_ufuns = tuple(_[1] for _ in ufuns)
    # create center ufun using side-ufuns if possible and without them otherwise.
    utype = get_ufun_class(center_ufun_type)
    try:
        center_ufun = utype(
            ufuns=side_ufuns,
            reserved_value=center_reserved_value,
            outcome_spaces=tuple(u.outcome_space for u in side_ufuns),  # type: ignore
        )
    except TypeError:
        center_ufun = utype(
            reserved_value=center_reserved_value,
            outcome_spaces=tuple(u.outcome_space for u in side_ufuns),  # type: ignore
        )

    def type_name(x):
        if isinstance(x, Boulware2025):
            return "Boulware2025"
        if not issubclass(x.default_negotiator_type, ControlledNegotiator):
            return f"ANL2025({x.default_negotiator_type.__name__})"
        return x.__class__.__name__.split(".")[-1]

    center = get_agent_class(center_type)(id="center", ufun=center_ufun)

    if verbose:
        print(f"Adding center of type {type_name(center)}")
    agents = [get_agent_class(_) for _ in edge_types]
    mechanisms: list[SAOMechanism] = []
    edges: list[ANL2025Negotiator] = []
    if verbose:
        print(
            f"Will use the following agents for edges\n{[_.__name__ if not isinstance(_, str) else _.split('.')[-1] for _ in agents]}"
        )
    for i, (edge_ufun, side_ufun) in enumerate(
        zip(edge_ufuns, center_ufun.side_ufuns(nedges), strict=True)
    ):
        if sample_edges:
            edget = choice(agents)
        else:
            edget = agents[i % len(edge_types)]
        edge = edget(ufun=edge_ufun, id=f"edge{i}", n_edges=nedges)
        edges.append(edge)
        m = SAOMechanism(
            outcome_space=edge_ufun.outcome_space,
            one_offer_per_step=atomic,
            name=f"n{i}",
            n_steps=nsteps,
        )
        m.id = m.name = f"n{i}"
        if verbose:
            print(f"Adding edge {i} of type {type_name(edge)} (thread: {m.name})")
        m.add(
            center.create_negotiator(
                cntxt=dict(center=True, ufun=side_ufun),
                ufun=side_ufun,
                id=f"s{i}",
                private_info=dict(opponent_ufun=edge_ufun) if share_ufuns else dict(),
            )
        )
        m.negotiators[-1].id = m.negotiators[-1].name = f"s{i}"
        m.add(
            edge.create_negotiator(
                cntxt=dict(center=False, ufun=edge_ufun),
                ufun=edge_ufun,
                id=f"e{i}",
                private_info=dict(opponent_ufun=side_ufun) if share_ufuns else dict(),
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

    if sequential:
        ordering = [i for i in range(nedges) for _ in range(nsteps)]
    SAOMechanism.runall(mechanisms, method=method, keep_order=keep_order, ordering=ordering)  # type: ignore
    if not name:
        name = unique_name("session", sep=".")
    if output:
        base = output / name
        (base / "log").mkdir(parents=True, exist_ok=True)
        (base / "plots").mkdir(parents=True, exist_ok=True)
        for i, (m, u) in enumerate(zip(mechanisms, center_ufun.side_ufuns(len(edges)))):
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
