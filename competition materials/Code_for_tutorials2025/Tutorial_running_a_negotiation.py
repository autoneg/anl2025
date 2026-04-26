"""
This is the code that is part of Tutorial 1 for the ANL 2025 competition, see URL.

This code is free to use or update given that proper attribution is given to
the authors and the ANAC 2025 ANL competition.
"""
import pathlib

from anl2025.scenario import MultidealScenario
from anl2025 import (
    run_session,
    make_job_hunt_scenario,
    make_target_quantity_scenario,
    load_example_scenario,
)
from anl2025.tournament import anl2025_tournament
from anl2025.ufun import CenterUFun
from anl2025.negotiator import Boulware2025, Random2025, Linear2025
from anl2025.scenario import make_multideal_scenario


def run_negotiation():
    # scenarios
    # You can also use an absolute path
    path = pathlib.Path("../official_test_scenarios/TargetQuantity_example")
    # path = pathlib.Path("../official_test_scenarios/dinners")
    # path = pathlib.Path("../official_test_scenarios/job_hunt_target")

    # agents:
    centeragent = Boulware2025
    edgeagents = [
        Random2025,
        Random2025,
        Linear2025,
        Boulware2025,
    ]

    # Load scenario, you can do this from a path:
    if False:
        scenario = (
            MultidealScenario.from_file(path)
            if path.is_file()
            else MultidealScenario.from_folder(path)
        )

    # or load the example scenario directly:
    scenario = load_example_scenario("TargetQuantity")

    print(scenario)

    results = run_session(
        scenario=scenario,
        center_type=centeragent,
        edge_types=edgeagents,  # type: ignore
        nsteps=10,
        #  verbose=verbose,
        #  keep_order=keep_order,
        #  share_ufuns=share_ufuns,
        #  atomic=atomic,
        #  output=output,
        #  dry=dry,
        #  method=DEFAULT_METHOD,
        #  sample_edges=False,
    )

    # print some results
    print(f"Center utility: {results.center_utility}")
    print(f"Edge Utilities: {results.edge_utilities}")
    print(f"Agreement: {results.agreements}")

    # extra: for nicer lay-outing and more results:
    cfun = results.center.ufun

    assert isinstance(cfun, CenterUFun)
    side_ufuns = cfun.side_ufuns()

    for i, (e, m, u) in enumerate(
        zip(results.edges, results.mechanisms, side_ufuns, strict=True)  # type: ignore
    ):
        print(
            f"{i:02}: Mechanism {m.name} between ({m.negotiator_ids}) ended in {m.current_step} ({m.relative_time:4.3}) with {m.agreement}: "
            f"Edge Utility = {e.ufun(m.agreement) if e.ufun else 'unknown'}, "
            f"Side Utility = {u(m.agreement) if u else 'unknown'}"
        )
        for outcome in m.outcome_space.enumerate_or_sample():
            print(f"Outcome: {outcome} SUtility: {u(outcome)}")
    print(f"Center Utility: {results.center_utility}")


def run_tournament():
    generated_scenario = make_multideal_scenario(nedges=3)
    path = pathlib.Path("../official_test_scenarios/dinners")
    scenario = MultidealScenario.from_folder(path)

    results = anl2025_tournament(
        scenarios=[scenario, generated_scenario],
        n_jobs=-1,
        competitors=(Random2025, Boulware2025, Linear2025),
        verbose=False,
        #  no_double_scores=False,
    )
    print(results.final_scores)
    print(results.weighted_average)


def run_generated_negotiation():
    scenario = make_multideal_scenario(nedges=8)
    scenario = make_job_hunt_scenario()
    scenario = make_target_quantity_scenario()
    results = run_session(scenario)
    print(f"Center utility: {results.center_utility}")
    print(f"Edge Utilities: {results.edge_utilities}")


if __name__ == "__main__":
    run_negotiation()
    # run_generated_negotiation()
    # run_tournament()
