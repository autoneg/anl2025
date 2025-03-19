from anl2025 import (
    make_multideal_scenario,
    run_session,
    anl2025_tournament,
    Boulware2025,
    Linear2025,
    Random2025,
)
from Code_for_tutorials2025.Tutorial_develop_a_new_negotiator_Random import MyRandom2025
from myagent.myagent import NewNegotiator


# testing the agent
def run_a_tournament():
    scenario = make_multideal_scenario(nedges=3)
    # competitors = [MyRandom2025, Boulware2025, Linear2025]
    # results = run_session(center_type = MyRandom2025, edge_types = competitors, scenario = scenario)
    # print(f"Center Utility: {results.center_utility}\nEdge Utilities: {results.edge_utilities}")
    results = anl2025_tournament(
        [scenario], n_jobs=-1, competitors=(MyRandom2025, Boulware2025, Linear2025)
    )
    print(results.final_scores)
    print(results.weighted_average)


def run_a_session_with_template_agent():
    scenario = make_multideal_scenario(nedges=3, nissues=2, nvalues=2)
    competitors = [Random2025, Boulware2025, Linear2025]
    results = run_session(
        center_type=NewNegotiator, edge_types=competitors, scenario=scenario
    )
    print(
        f"Center Utility: {results.center_utility}\nEdge Utilities: {results.edge_utilities}"
    )
    # results = anl2025_tournament([scenario], n_jobs=-1, competitors=(NewNegotiator, Boulware2025, Linear2025))
    # print(results.final_scores)
    # print(results.weighted_average)


if __name__ == "__main__":
    # run_a_tournament()
    run_a_session_with_template_agent()
