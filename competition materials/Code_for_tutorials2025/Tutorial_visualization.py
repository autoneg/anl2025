"""
This is the code that is part of Tutorial 1 for the ANL 2025 competition, see URL.

This code is free to use or update given that proper attribution is given to
the authors and the ANAC 2025 ANL competition.
"""


from anl2025 import run_session, load_example_scenario
from anl2025.ufun import CenterUFun
from anl2025.negotiator import Boulware2025, Linear2025
import matplotlib.pyplot as plt


def run_negotiation():
    # agents:
    centeragent = Boulware2025
    edgeagents = [
        Linear2025,
        Linear2025,
        Boulware2025,
        Boulware2025,
    ]

    scenario = load_example_scenario("TargetQuantity")
    print(scenario)

    results = run_session(
        scenario=scenario,
        center_type=centeragent,
        edge_types=edgeagents,  # type: ignore
        nsteps=10,
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

    return results


def visualize(results):
    for i, m in enumerate(results.mechanisms):
        plot_result(i, m)


def plot_result(m):
    m.plot(save_fig=False)
    plt.show()
    plt.close()


if __name__ == "__main__":
    results = run_negotiation()
    visualize(results)
