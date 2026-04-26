#### all functions below are hulp functions for the functions above. They are not necessary to implement the agent, but they can be useful." ####

import itertools


def set_id_dict(self):
    """Creates a dictionary that maps the index of the negotiation to the negotiator id. The index of the negotiation is the order in which the negotiation happen in sequence.
    This dictionary allows us to find the right id for easy access to further information about the specific negotiation."""
    for id in self.negotiators.keys():
        index = self.negotiators[id].context["index"]
        self.id_dict[index] = id


def did_negotiation_end(self):
    """The function finished_negotiators checks how many threads are finished. If that number changes, then the next negotiation has started."""
    if self.current_neg_index != len(self.finished_negotiators):
        self.current_neg_index = len(self.finished_negotiators)
        return True
    return False


def get_current_negotiation_index(self):
    """Returns the index of the current negotiation. An index 0 means the first negotiation in the sequence, index 1 the second, etc."""
    return len(self.finished_negotiators)


def get_agreement_at_index(self, index):
    """The nmi is the negotiator mechanism interface, available for each subnegotiation.
    Here you can find any information about the ongoing or ended negotiation, like the agreement or the previous bids."""
    nmi = get_nmi_from_index(self, index)
    agreement = nmi.state.agreement
    # print(agreement)
    return agreement


def get_outcome_space_from_index(self, index):
    """This function returns the outcome space of the subnegotiation with the given index."""
    outcomes = self.ufun.outcome_spaces[index].enumerate_or_sample()
    #  print(outcomes)

    # Each subnegotiation can also end in disagreement aka outcome None. Therefore, we add this to all outcomes.
    outcomes.append(None)

    return outcomes


def get_number_of_subnegotiations(self):
    """Returns the total number of (sub)negotiations that the agent is involved in. For edge agents, this is 1."""
    return len(self.negotiators)


def cartesian_product(arrays):
    """This function returns the cartesian product of the given arrays."""
    cartesian_product = list(itertools.product(*arrays))
    #  print(cartesian_product)
    return cartesian_product


def is_edge_agent(self):
    """Returns True if the agent is an edge agent, False otherwise, then the agent is a center agent."""
    if self.id.__contains__("edge"):
        return True
    return False


def all_possible_bids_with_agreements_fixed(self):
    """This function returns all the bids that are still possible to achieve, given the agreements that were made in the previous negotiations."""

    # Once a negotiation has ended, the bids in the previous negotiations cannot be changed.
    # Therefore, this function helps to construct all the bids that can still be achieved, fixing the agreements of the previous negotiations.

    # If the agent is an edge agent, there is just one bid to be made, so we can just return the outcome space of the utility function.
    # Watch out, the structure of the outcomes for an edge agent is different from for a center agent.

    if is_edge_agent(self):
        return self.ufun.outcome_space.enumerate_or_sample()

    possible_outcomes = []
    neg_index = get_current_negotiation_index(self)

    # As the previous agreements are fixed, these are added first.
    for i in range(neg_index):
        possible_outcomes.append([get_agreement_at_index(self, i)])

    # The coming negotiations (with index higher than the current negotiation index) can still be anything, so we just list all possibilities there.
    n = get_number_of_subnegotiations(self)
    for i in range(neg_index, n):
        possible_outcomes.append(get_outcome_space_from_index(self, i))
    # print(possible_outcomes)

    # The cartesian product constructs the combinations of all possible outcomes.
    adapted_outcomes = cartesian_product(possible_outcomes)
    return adapted_outcomes


def find_best_bid_in_outcomespace(self):
    """Fixing previous agreements, this functions returns the best bid that can still be achieved."""
    # get outcome space with all bids with fixed agreements
    updated_outcomes = all_possible_bids_with_agreements_fixed(self)

    # this function is also in self.ufun.extreme_outcomes()
    mn, mx = float("inf"), float("-inf")
    _worst, best = None, None
    for o in updated_outcomes:
        u = self.ufun(o)
        if u < mn:
            _worst, mn = o, u
        if u > mx:
            best, mx = o, u
    return best


def get_target_bid_at_current_index(self):
    """Returns the bid for the current subnegotiation, with the target_bid as source."""
    index = get_current_negotiation_index(self)
    # An edge agents bid is only one bid, not a tuple of bids. Therefore, we can just return the target bid.
    if is_edge_agent(self):
        return self.target_bid
    return self.target_bid[index]


def get_nmi_from_index(self, index):
    """
    This function returns the nmi of the subnegotiation with the given index.
    The nmi is the negotiator mechanism interface per subnegotiation. Here you can find any information about the ongoing or ended negotiation, like the agreement or the previous bids.
    """
    negotiator_id = get_negid_from_index(self, index)
    return self.negotiators[negotiator_id].negotiator.nmi


def get_negid_from_index(self, index):
    """This function returns the negotiator id of the subnegotiation with the given index."""
    return self.id_dict[index]
