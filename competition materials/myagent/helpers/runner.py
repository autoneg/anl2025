"""
A helper function to run a tournament with your agent.

You only need to change the name of the class implementing your agent at the top of this file.
"""


def run_a_tournament(
    TestedNegotiator,
    n_repetitions=5,
    debug=False,
    nologs=False,
    small=False,
):
    """
    **Not needed for submission.** You can use this function to test your agent.

    Args:
       TestedNegotiator: Negotiator type to be tested
       n_repetitions: The number of repetitions of each scenario tested
       n_outcomes: Number of outcomes in the domain (makes sure this is between 900 and 1100)
       n_scenarios: Number of different scenarios generated
       debug: Pass True here to run the tournament in serial, increase verbosity, and fails on any exception
       nologs: If passed, no logs will be stored
       small: if set to True, the tournament will be very small and run in a few seconds.

    Returns:
        None

    Remarks:

        - This function will take several minutes to run.
        - To speed it up, use a smaller `n_repetitions` value

    """
    import time

    from anl2025 import (
        anl2025_tournament,
        DEFAULT_TOURNAMENT_PATH,
        DEFAULT_ANL2025_COMPETITORS,
        make_multideal_scenario,
    )

    from anl2025.negotiator import Conceder2025
    from negmas.helpers import humanize_time, unique_name
    from rich import print

    start = time.perf_counter()
    name = (
        unique_name(f"test{TestedNegotiator().type_name.split('.')[-1]}", sep="")
        if not nologs
        else None
    )

    scenarios = [
        make_multideal_scenario(nedges=3, nissues=2, nvalues=2) for _ in range(1)
    ]
    scenariosbig = [
        make_multideal_scenario(
            nedges=3,
        )
        for _ in range(2)
    ]
    if small:
        anl2025_tournament(
            competitors=tuple([TestedNegotiator]),
            scenarios=scenarios,
            non_comptitor_types=tuple([Conceder2025]),
            n_repetitions=1,
            n_jobs=-1 if debug else 0,
            verbose=False,
        ).final_scores
    else:
        anl2025_tournament(
            competitors=tuple([TestedNegotiator]),
            scenarios=scenariosbig,
            non_comptitor_types=tuple(list(DEFAULT_ANL2025_COMPETITORS)),
            n_repetitions=n_repetitions,
            n_jobs=-1 if debug else 0,
            verbose=True,
        ).final_scores
    print(f"Finished in {humanize_time(time.perf_counter() - start)}")
    if name is not None:
        print(f"You can see all logs at {DEFAULT_TOURNAMENT_PATH / name}")
