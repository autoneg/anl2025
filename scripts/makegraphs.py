"""
This is the code that is part of Tutorial 1 for the ANL 2025 competition, see URL.

This code is free to use or update given that proper attribution is given to
the authors and the ANAC 2025 ANL competition.
"""

import pathlib

from anl2025.negotiator import Linear2025
from anl2025.scenario import MultidealScenario
from anl2025 import run_session


class MyNegotiator(Linear2025):
    def propose(self, negotiator_id: str, state, dest: str | None = None):
        # if self.negotiators[negotiator_id][1]["center"] and any(self.ufun._expected):
        #     breakpoint()
        outcome = super().propose(negotiator_id, state, dest)
        ufun = self.negotiators[negotiator_id][1]["ufun"]

        if self.negotiators[negotiator_id][1]["center"]:
            print(
                f"{self.id} Offering {outcome} with side utility {ufun(outcome)} ({self.ufun._expected=})"
            )
        else:
            print(f"{self.id} Offering {outcome} with side utility {ufun(outcome)}")

        return outcome

    def thread_finalize(self, negotiator_id: str, state) -> None:
        super().thread_finalize(negotiator_id, state)
        _, cntxt = self.negotiators[negotiator_id]
        print(
            f"Thread for {negotiator_id} (index {cntxt['index']}) ended with {state.agreement}"
        )


def run_negotiation():
    # scenarios
    path = pathlib.Path(__file__).parent.parent / "scenarios" / "TargetQuantity"

    # agents:
    centeragent = MyNegotiator
    edgeagents = [MyNegotiator] * 4

    # Load scenario
    scen = (
        MultidealScenario.from_file(path)
        if path.is_file()
        else MultidealScenario.from_folder(path)
    )
    assert scen

    results = run_session(
        scenario=scen,
        center_type=centeragent,
        edge_types=edgeagents,  # type: ignore
        # sample_edges=True,
        nsteps=10,
    )
    # print some results
    print(f"Center Utility: {results.center_utility}")
    count = 0
    for edge in results.edges:
        print(f"Edge {edge.type_name} Utility: {results.edge_utilities[count]}")
        count += 1
    print(results.agreements)


if __name__ == "__main__":
    run_negotiation()
