from random import random
from anl_agents.anl2024 import Shochan, AgentRenting2024
from negmas.sao.controllers import SAOController, SAOState
from negmas import (
    ConcederTBNegotiator,
    DiscreteCartesianOutcomeSpace,
    ExtendedOutcome,
    LinearTBNegotiator,
    ResponseType,
)
from negmas.outcomes import Outcome
from negmas.sao.negotiators import AspirationNegotiator

__all__ = [
    "ANL2025Negotiator",
    "Random2025",
    "Boulware2025",
    "Linear2025",
    "Conceder2025",
    "Shochan2025",
    "AgentRenting2025",
]


class ANL2025Negotiator(SAOController):
    """
    Base class of all participant code.

    See the next two examples of how to implement it (`Boulware2025`, `Random2025`).
    """

    def __init__(self, *args, n_edges: int = 0, **kwargs):
        keargs["auto_kill"] = False
        super().__init__(*args, **kwargs)
        self._n_edges = n_edges

    def init(self):
        """Called after all mechanisms are created to initialize"""
        # self.negotiators can be used to access the threads.
        # Each has a negotiator object and a cntxt object.
        # We can pass anything in the cntxt. Currently, we pass the side ufun
        # Examples:
        # 1. Access the CenterUFun associated with the agent. For edge agents, this will be the single ufun it uses.
        # my_ufun = self.ufun
        # 2. Access the side ufun associated with each thread. For edge agents this will be the single ufun it uses.
        # my_side_ufuns = [info.context["ufun"] for neg_id, info in self.negotiators.items()]
        # 2. Access the side negotiators connected to different negotiation threads
        # my_side_negotiators = [info.negotiator for neg_id, info in self.negotiators.items()]

    def propose(
        self, negotiator_id: str, state: SAOState, dest: str | None = None
    ) -> Outcome | ExtendedOutcome | None:
        """Called to propose an offer for one of the edge negotiators

        Args:
            negotiator_id: The ID of the connection to the edge negotiator.
            state: The state of the negotiation with this edge negotiator.
            dest: The ID of the edge negotiator

        Returns:
            An outcome to offer. In ANL2025, `None` and `ExtendedOutcome` are not allowed
        """
        return super().propose(negotiator_id, state, dest)

    def respond(
        self, negotiator_id: str, state: SAOState, source: str | None = None
    ) -> ResponseType:
        """Called to respond to an offer from an edge negotiator

        Args:
            negotiator_id: The ID of the connection to the edge negotiator.
            state: The state of the negotiation with this edge negotiator.
            dest: The ID of the edge negotiator

        Returns:
            A response (Accept, Reject, or End_Negotiation)

        Remarks:
            - The current offer on the negotiation thread with this edge
              negotiator can be accessed as `state.current_offer`.
        """
        return super().respond(negotiator_id, state, source)

    def on_negotiation_start(self, negotiator_id: str, state: SAOState) -> None:
        """Called when a negotiation thread starts

        Args:
            negotiator_id: Connection ID to this negotiation thread
            state: The state of the negotiation thread at the start of the negotiation.
        """
        return super().on_negotiation_start(negotiator_id, state)

    def on_negotiation_end(self, negotiator_id: str, state: SAOState) -> None:
        """Called when a negotiation thread ends

        Args:
            negotiator_id: Connection ID to this negotiation thread
            state: The state of the negotiation thread at the end of the negotiation.
        """
        return super().on_negotiation_end(negotiator_id, state)


class Boulware2025(ANL2025Negotiator):
    """
    You can participate by an agent that runs any SAO negotiator independently for each thread.
    """

    def __init__(self, **kwargs):
        kwargs["default_negotiator_type"] = AspirationNegotiator
        super().__init__(**kwargs)


class Linear2025(ANL2025Negotiator):
    """
    You can participate by an agent that runs any SAO negotiator independently for each thread.
    """

    def __init__(self, **kwargs):
        kwargs["default_negotiator_type"] = LinearTBNegotiator
        super().__init__(**kwargs)


class Conceder2025(ANL2025Negotiator):
    """
    You can participate by an agent that runs any SAO negotiator independently for each thread.
    """

    def __init__(self, **kwargs):
        kwargs["default_negotiator_type"] = ConcederTBNegotiator
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


class Random2025(ANL2025Negotiator):
    """
    The most general way to implement an agent is to implement propose and respond.
    """

    p_end = 0.03
    p_reject = 0.999

    def propose(
        self, negotiator_id: str, state: SAOState, dest: str | None = None
    ) -> Outcome | None:
        """Proposes to the given partner (dest) using the side negotiator (negotiator_id).

        Remarks:
            - the mapping from negotiator_id to source is stable within a negotiation.
        """
        nmi = self.negotiators[negotiator_id].negotiator.nmi
        os: DiscreteCartesianOutcomeSpace = nmi.outcome_space
        return list(os.sample(1))[0]

    def respond(
        self, negotiator_id: str, state: SAOState, source: str | None = None
    ) -> ResponseType:
        """Responds to the given partner (source) using the side negotiator (negotiator_id).

        Remarks:
            - negotiator_id is the ID of the side negotiator representing this agent.
            - source: is the ID of the partner.
            - the mapping from negotiator_id to source is stable within a negotiation.

        """

        if random() < self.p_end:
            return ResponseType.END_NEGOTIATION

        if (
            random() < self.p_reject
            or float(self.ufun(state.current_offer)) < self.ufun.reserved_value  # type: ignore
        ):
            return ResponseType.REJECT_OFFER
        return ResponseType.ACCEPT_OFFER
