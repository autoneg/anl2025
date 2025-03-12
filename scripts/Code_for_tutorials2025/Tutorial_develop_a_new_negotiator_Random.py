from random import random
from negmas import Outcome, ResponseType, SAOState
from anl2025 import ANL2025Negotiator


class MyRandom2025(ANL2025Negotiator):
    p_end = 0.0003
    p_reject = 0.999

    def propose(
        self, negotiator_id: str, state: SAOState, dest: str | None = None
    ) -> Outcome | None:
        nmi = self.get_nmi_from_id(negotiator_id)
        sampled_bid = list(nmi.outcome_space.sample(1))[0]
        return sampled_bid

    def respond(
        self, negotiator_id: str, state: SAOState, source: str | None = None
    ) -> ResponseType:
        if random() < self.p_end:
            return ResponseType.END_NEGOTIATION

        if (
            random() < self.p_reject
            or float(self.ufun(state.current_offer)) < self.ufun.reserved_value  # type: ignore
        ):
            return ResponseType.REJECT_OFFER
        return ResponseType.ACCEPT_OFFER

    def get_nmi_from_id(self, negotiators_id):
        # the nmi is the negotiator mechanism interface, available for each subnegotiation. Here you can find any information about the ongoing or ended negotiation, like the agreement or the previous bids.
        return self.negotiators[negotiators_id].negotiator.nmi
