from abc import ABC, abstractmethod
from random import choice, random
from typing import Annotated
from anl_agents.anl2024 import Shochan, AgentRenting2024
import pandas as pd
from rich import print
from pathlib import Path
import typer
from negmas.helpers.strings import unique_name
from negmas.preferences import BaseUtilityFunction
from negmas.preferences.generators import generate_multi_issue_ufuns
from negmas.negotiators import ControlledNegotiator
from negmas.preferences import UtilityFunction
from negmas.sao.controllers import ABC, SAOController, SAOState, abstractmethod
from negmas import (
    DiscreteCartesianOutcomeSpace,
    ResponseType,
    SAOMechanism,
)
from negmas.outcomes import Outcome
from negmas.sao.negotiators import AspirationNegotiator

TRACE_COLS = (
    "time",
    "relative_time",
    "step",
    "negotiator",
    "offer",
    "responses",
    "state",
)


class CenterUFun(UtilityFunction, ABC):
    """
    Base class of center utility functions.

    It simply received a tuple of negotiation results and returns a float
    """

    @abstractmethod
    def eval(self, offer: tuple[Outcome | None] | None) -> float:
        """
        Evaluates the utility of a given set of offers.

        Remarks:
            - Order matters: The order of outcomes in the offer is stable over all calls.
            - A missing offer is represented by `None`
        """


class CenterUFunWithEdgeUFuns(CenterUFun):
    """
    A center ufun with a sub-ufun defined for each thread.

    The utility of the center is a function of the ufuns of the edges.
    """

    def __init__(self, *args, ufuns: tuple[BaseUtilityFunction, ...], **kwargs):
        super().__init__(*args, **kwargs)
        self.ufuns = ufuns

    @abstractmethod
    def combine(self, values: tuple[float, ...]) -> float:
        """Combines the utilities of all negotiation  threads into a single value"""

    def eval(self, offer: tuple[Outcome | None] | None) -> float:
        if not offer:
            return self.reserved_value
        return self.combine(tuple(float(u(_)) for u, _ in zip(self.ufuns, offer)))


class MaxCenterUFun(CenterUFunWithEdgeUFuns):
    """
    The max center ufun.

    The utility of the center is the maximum of the utilities it got in each negotiation (called side utilities)
    """

    def combine(self, values: tuple[float, ...]) -> float:
        return max(values)


class ANL2025Negotiator(SAOController):
    """
    Base class of all participant code.

    See the next two examples of how to implement it.
    """

    def __init__(self, *args, n_edges: int = 0, **kwargs):
        super().__init__(*args, **kwargs)
        self._n_edges = n_edges

    def init(self):
        """Called after all mechanisms are created to initialize"""
        # self.negotiators can be used to access the threads.
        # Each has a negotiator object and a cntxt object.
        # We can pass anything in the cntxt. Currently, we pass the side ufun
        # Examples:
        # 1. Access the CenterUFun associated with the agent. For edge agents, this will be the single ufun it uses.
        _ = self.ufun
        # 2. Access the side ufun associated with each thread. For edge agents this will be the single ufun it uses.
        _ = [info.context["ufun"] for neg_id, info in self.negotiators.items()]
        # 2. Access the side negotiators connected to different negotiation threads
        _ = [info.negotiator for neg_id, info in self.negotiators.items()]


class Boulware2025(ANL2025Negotiator):
    """
    You can participate by an agent that runs any SAO negotiator independently for each thread.
    """

    def __init__(self, **kwargs):
        kwargs["default_negotiator_type"] = AspirationNegotiator
        super().__init__(**kwargs)


class AgentRenting2025(ANL2025Negotiator):
    """
    You can participate by an agent that runs any SAO negotiator independently for each thread.
    """

    def __init__(self, **kwargs):
        kwargs["default_negotiator_type"] = AgentRenting2024
        super().__init__(**kwargs)


class Shochan2025(ANL2025Negotiator):
    """
    You can participate by an agent that runs any SAO negotiator independently for each thread.
    """

    def __init__(self, **kwargs):
        kwargs["default_negotiator_type"] = Shochan
        super().__init__(**kwargs)


class RandomNegotiator(ANL2025Negotiator):
    """
    The most general way to implement an agent is to implement propose and respond.
    """

    p_end = 0.03
    p_reject = 0.999

    def propose(
        self, negotiator_id: str, state: SAOState, dest: str | None = None
    ) -> Outcome | None:
        """
        Proposes to the given partner (dest) using the side negotiator (negotiator_id).

        Remarks:
            - the mapping from negotiator_id to source is stable within a negotiation.
        """
        nmi = self.negotiators[negotiator_id].negotiator.nmi
        os: DiscreteCartesianOutcomeSpace = nmi.outcome_space
        return list(os.sample(1))[0]

    def respond(
        self, negotiator_id: str, state: SAOState, source: str | None = None
    ) -> ResponseType:
        """
        Responds to the given partner (source) using the side negotiator (negotiator_id).

        Remarks:
            - negotiator_id is the ID of the side negotiator representing this agent.
            - source: is the ID of the partner.
            - the mapping from negotiator_id to source is stable within a negotiation.

        """

        if random() < self.p_end:
            return ResponseType.END_NEGOTIATION

        if random() < self.p_reject:
            return ResponseType.REJECT_OFFER
        return ResponseType.ACCEPT_OFFER


def main(
    nedges: Annotated[
        int,
        typer.Option(
            help="Number of Edges (the M side of the 1-M negotiation session)"
        ),
    ] = 10,
    nissues: Annotated[int, typer.Option(help="Number of negotiation issues")] = 3,
    nvalues: Annotated[
        int, typer.Option(help="Number of values per negotiation issue")
    ] = 7,
    nsteps: Annotated[
        int,
        typer.Option(
            help="Number of negotiation steps (see `atomic` for the exact meaning of this)."
        ),
    ] = 100,
    center_reserved_value: Annotated[
        float,
        typer.Option(
            help="Number of Edges (the M side of the 1-M negotiation session)"
        ),
    ] = 0.0,
    edge_reserved_value_min: Annotated[
        float,
        typer.Option(
            help="Number of Edges (the M side of the 1-M negotiation session)"
        ),
    ] = 0.1,
    edge_reserved_value_max: Annotated[
        float,
        typer.Option(
            help="Number of Edges (the M side of the 1-M negotiation session)"
        ),
    ] = 0.4,
    method: Annotated[
        str,
        typer.Option(
            help="The concurrency method for running each thread WITHIN a negotiation step. The only supported option is `serial`"
        ),
    ] = "serial",
    output: Annotated[
        Path,
        typer.Option(help="A directory to store the negotiation logs and plots"),
    ] = Path.home() / "negmas" / "anl2025" / "session",
    center_type: Annotated[
        str,
        typer.Option(help="The type of the center agent"),
    ] = "Boulware2025",
    use_random: Annotated[
        bool,
        typer.Option(help="Allow the RandomNegotiator in the edges."),
    ] = True,
    use_anl2024: Annotated[
        bool,
        typer.Option(
            help="Allow ANL2024 negotiators in the edges (will use Shochan2025 and AgentRenting2025)"
        ),
    ] = False,
    use_boulware: Annotated[
        bool,
        typer.Option(help="Allow the Boulware2025 agent in the edges"),
    ] = True,
    keep_order: Annotated[
        bool,
        typer.Option(
            help="If given, the mechanisms will be advanced in order in every step."
        ),
    ] = True,
    atomic: Annotated[
        bool,
        typer.Option(
            help=(
                "If given, each step of a mechanism represents a single offer "
                "(from a center or an edge but not both). This may make the logs"
                " wrong though. If --no-atomic (default), a single step corresponds "
                "to one offer form the center and from an edge"
            )
        ),
    ] = False,
    share_ufuns: Annotated[
        bool | None,
        typer.Option(
            help="Whether or not to share partner ufun up to reserved value. If any ANL2024 agent is used as center or edge, this MUST be True (default)"
        ),
    ] = True,
    dry: Annotated[
        bool,
        typer.Option(help="Dry-run. Does not really run anything."),
    ] = False,
    name: Annotated[
        str,
        typer.Option(
            help="The name of this session (a random name will be created if not given)"
        ),
    ] = "",
):
    ufuns = [generate_multi_issue_ufuns(nissues, nvalues) for _ in range(nedges)]
    d = edge_reserved_value_max - edge_reserved_value_min
    edge_ufuns = [_[0] for _ in ufuns]
    for u in edge_ufuns:
        u.reserved_value = random() * d + edge_reserved_value_min
    side_ufuns = tuple(_[1] for _ in ufuns)
    # os = make_os([make_issue(randint(3, 7)) for _ in range(nissues)])
    # edge_ufuns = [
    #     U.random(os, reserved_value=random() * d + edge_reserved_value_min)
    #     for _ in range(nedges)
    # ]  # tuple(U.random(os) for _ in range(nedges)),
    center_ufun = MaxCenterUFun(ufuns=side_ufuns, reserved_value=center_reserved_value)

    def type_name(x):
        if isinstance(x, Boulware2025):
            return "Boulware2025"
        if not issubclass(x.default_negotiator_type, ControlledNegotiator):
            return f"ANL2025({x.default_negotiator_type.__name__})"
        return x.__class__.__name__.split(".")[-1]

    center = eval(center_type)(id="center", ufun=center_ufun)
    print(f"Adding center of type {type_name(center)}")
    agents = [RandomNegotiator] if use_random else []  # type: ignore
    if use_anl2024:
        agents += [Shochan2025, AgentRenting2025]
    if use_boulware:
        agents.append(Boulware2025)  # type: ignore
    mechanisms: list[SAOMechanism] = []
    edges: list[ANL2025Negotiator] = []
    print(f"Will use the following agents for edges\n{[_.__name__ for _ in agents]}")
    for i, (edge_ufun, side_ufun) in enumerate(zip(edge_ufuns, center_ufun.ufuns)):
        edge = choice(agents)(ufun=edge_ufun, id=f"edge{i}", n_edges=nedges)
        edges.append(edge)
        m = SAOMechanism(
            outcome_space=edge_ufun.outcome_space,
            one_offer_per_step=atomic,
            name=f"n{i}",
            n_steps=nsteps,
        )
        m.id = m.name = f"n{i}"
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
    center.init()
    for edge in edges:
        edge.init()
    if dry:
        print("Dry run: negotiations will not  be executed")

    SAOMechanism.runall(mechanisms, method=method, keep_order=keep_order)  # type: ignore
    if not name:
        name = unique_name("session", sep=".")
    base = output / name
    (base / "log").mkdir(parents=True, exist_ok=True)
    (base / "plots").mkdir(parents=True, exist_ok=True)
    for i, (e, m, u) in enumerate(zip(edges, mechanisms, center_ufun.ufuns)):
        print(
            f"Mechanism {m.name} between ({m.negotiator_ids}) ended in {m.current_step} ({m.relative_time:4.3}) with {m.agreement}: "
            f"Edge Utility = {e.ufun(m.agreement) if e.ufun else 'unknown'}, "
            f"Side Utility = {u(m.agreement) if u else 'unknown'}"
        )
        df = pd.DataFrame(data=m.full_trace, columns=TRACE_COLS)  # type: ignore
        df.to_csv(base / "log" / f"{m.id}.csv", index_label="index")
        m.plot(save_fig=True, path=str(base / "plots"), fig_name=f"n{i}.png")
    print(f"Center Utility: {center_ufun(tuple(_.agreement for _ in mechanisms))}")


if __name__ == "__main__":
    typer.run(main)
