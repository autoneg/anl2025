from random import choice, random
from typing import Any
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
from negmas.sao.controllers import ControlledSAONegotiator, SAOController, SAOState
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


class CenterUFun(UtilityFunction):
    """
    Base class of center utility functions.

    It simply received a tuple of negotiation results and returns a float
    """

    def eval(self, offer: tuple[Outcome | None] | None) -> float: ...


class MaxCenterUFun(CenterUFun):
    """
    The max center ufun.

    The utility of the center is the maximum of the utilities it got in each negotiation (called side utilities)
    """

    def __init__(self, *args, ufuns: tuple[BaseUtilityFunction, ...], **kwargs):
        super().__init__(*args, **kwargs)
        self.ufuns = ufuns

    def eval(self, offer: tuple[Outcome | None] | None) -> float:
        if not offer:
            return self.reserved_value
        return max(float(u(_)) for u, _ in zip(self.ufuns, offer))


class ANL2025Negotiator(SAOController):
    """
    Base class of all participant code.

    See the next two examples of how to implement it.
    """

    def __init__(
        self,
        ufun: CenterUFun | BaseUtilityFunction,
        default_negotiator_type=ControlledSAONegotiator,
        default_negotiator_params: dict[str, Any] | None = None,
        *args,
        **kwargs,
    ):
        super().__init__(
            default_negotiator_type=default_negotiator_type,
            default_negotiator_params=default_negotiator_params,
            ufun=ufun,
            *args,
            **kwargs,
        )
        self.__ufun = ufun

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


P_END = 0.03
P_REJECT = 0.999


class RandomNegotiator(ANL2025Negotiator):
    """
    The most general way to implement an agent is to implement propose and respond.
    """

    def propose(self, negotiator_id: str, state: SAOState) -> Outcome | None:
        """Proposes to the given negotiator"""
        nmi = self.negotiators[negotiator_id].negotiator.nmi
        os: DiscreteCartesianOutcomeSpace = nmi.outcome_space
        return list(os.sample(1))[0]

    def respond(
        self, negotiator_id: str, state: SAOState, source: str | None = None
    ) -> ResponseType:
        """Responds to the given negotiator"""

        if random() < P_END:
            return ResponseType.END_NEGOTIATION

        if random() < P_REJECT:
            return ResponseType.REJECT_OFFER
        return ResponseType.ACCEPT_OFFER


def main(
    nedges: int = 10,
    nissues: int = 3,
    nvalues: int = 7,
    nsteps: int = 100,
    center_reserved_value: float = 0.0,
    edge_reserved_value_min: float = 0.1,
    edge_reserved_value_max: float = 0.4,
    method: str = "serial",
    output: Path = Path.home() / "negmas" / "anl2025" / "session",
    center_type: str = "Boulware2025",
    use_random: bool = True,
    use_anl2024: bool = False,
    use_boulware: bool = True,
    keep_order: bool = False,
    atomic: bool = False,
    dry: bool = False,
    name: str = "",
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
        edge = choice(agents)(ufun=edge_ufun, id=f"edge{i}")
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
                private_info=dict(opponent_ufun=edge_ufun),
            )
        )
        m.negotiators[-1].id = m.negotiators[-1].name = f"s{i}"
        m.add(
            edge.create_negotiator(
                cntxt=dict(center=False, ufun=edge_ufun),
                ufun=edge_ufun,
                id=f"e{i}",
                private_info=dict(opponent_ufun=side_ufun),
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
