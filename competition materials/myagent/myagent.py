"""
**Submitted to ANAC 2025 Automated Negotiation League**
*Team* type your team name here
*Authors* type your team member names with their emails here

This code is free to use or update given that proper attribution is given to
the authors and the ANAC 2025 ANL competition.
"""
from negmas.outcomes import Outcome

from .helpers.helperfunctions import (
    set_id_dict,
    did_negotiation_end,
    get_target_bid_at_current_index,
    is_edge_agent,
    find_best_bid_in_outcomespace,
)
# be careful: When running directly from this file, change the relative import to an absolute import. When submitting, use relative imports.
# from helpers.helperfunctions import set_id_dict, ...

from anl2025.negotiator import ANL2025Negotiator
from negmas.sao.controllers import SAOState
from negmas import (
    ResponseType,
)


class NewNegotiator(ANL2025Negotiator):
    """
    Your agent code. This is the ONLY class you need to implement
    This example agent aims for the absolute best bid available. As a center agent, it adapts its strategy after each negotiation, by aiming for the best bid GIVEN the previous outcomes.
    """

    """
       The most general way to implement an agent is to implement propose and respond.
       """

    def init(self):
        """Executed when the agent is created. In ANL2025, all agents are initialized before the tournament starts."""
        # print("init")

        # Initalize variables
        self.current_neg_index = -1
        self.target_bid = None

        # Make a dictionary that maps the index of the negotiation to the negotiator id. The index of the negotiation is the order in which the negotiation happen in sequence.
        self.id_dict = {}
        set_id_dict(self)

    def propose(
        self, negotiator_id: str, state: SAOState, dest: str | None = None
    ) -> Outcome | None:
        """Proposes to the given partner (dest) using the side negotiator (negotiator_id).

        Remarks:
            - You can use the negotiator_id to identify what side negotiator is currently proposing. This id is stable within a negotiation.
        """
        # If the negotiation has ended, update the strategy. The subnegotiator may of may not have found an agreement: this affects the strategy for the rest of the negotiation.
        if did_negotiation_end(self):
            self._update_strategy()

        bid = get_target_bid_at_current_index(self)

        # if you want to end the negotiation, return None
        return bid

    def respond(
        self, negotiator_id: str, state: SAOState, source: str | None = None
    ) -> ResponseType:
        """Responds to the given partner (source) using the side negotiator (negotiator_id).

        Remarks:
            - negotiator_id is the ID of the side negotiator representing this agent.
            - source: is the ID of the partner.
            - the mapping from negotiator_id to source is stable within a negotiation.

        """
        if did_negotiation_end(self):
            self._update_strategy()

        # This agent is very stubborn: it only accepts an offer if it is EXACTLY the target bid it wants to have.
        if state.current_offer is get_target_bid_at_current_index(self):
            return ResponseType.ACCEPT_OFFER

        return ResponseType.REJECT_OFFER
        # You can also return ResponseType.END_NEGOTIATION to end the negotiation.

    def _update_strategy(self) -> None:
        """Update the strategy of the agent after a negotiation has ended."""
        # if your current role is the edge agent, use the strategy as if your centeragent is in it's last subnegotiation.
        # In this case, just get the best bid from the utility function.
        if is_edge_agent(self):
            # note that the edge utility function has a slightly different structure than a center utility function.
            _, best_bid = self.ufun.extreme_outcomes()
        else:
            # get the best bid from the outcomes that are still possible to achieve.
            best_bid = find_best_bid_in_outcomespace(self)

        self.target_bid = best_bid
        # print(self.target_bid)


# if you want to do a very small test, use the parameter small=True here. Otherwise, you can use the default parameters.
if __name__ == "__main__":
    from helpers.runner import run_a_tournament
    # Be careful here. When running directly from this file, relative imports give an error, e.g. import .helpers.helpfunctions.
    # Change relative imports (i.e. starting with a .) at the top of the file. However, one should use relative imports when submitting the agent!

    run_a_tournament(NewNegotiator, small=True)
