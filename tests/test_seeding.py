"""anl2025's randomness follows negmas's global seed (``NEGMAS_RAND_SEED``).

anl2025 draws all of its randomness from `random` and `numpy.random`, both of
which `negmas.helpers.rand.seed_all` seeds, so there is nothing of its own to
register. What it does need is a distinct seed per dispatched negotiation: the
tests below cover that and the end-to-end reproducibility it is meant to give.
"""

import random

import numpy as np
import pytest

rand = pytest.importorskip(
    "negmas.helpers.rand", reason="negmas is too old to have a global seed"
)

from anl2025.scenarios.dinners import make_dinners_scenario  # noqa: E402
from anl2025.tournament import _run_session_seeded  # noqa: E402


@pytest.fixture(autouse=True)
def _restore_global_random_state():
    """Keeps seeding here from leaking into the rest of the session."""
    state, np_state, seed = random.getstate(), np.random.get_state(), rand.get_seed()
    yield
    random.setstate(state)
    np.random.set_state(np_state)
    rand._seed = seed


def _dinner_values(seed):
    """The (randomly generated) utilities of a dinners scenario made under `seed`."""
    rand.seed_all(seed)
    scenario = make_dinners_scenario(n_friends=3, n_days=4)
    return [
        [float(u(o)) for o in u.outcome_space.enumerate_or_sample()]
        for u in scenario.edge_ufuns
    ]


def test_scenario_generation_is_reproducible_when_seeded():
    assert _dinner_values(42) == _dinner_values(42)
    assert _dinner_values(42) != _dinner_values(43)


def test_task_seeds_are_distinct_and_reproducible():
    rand.seed_all(42)
    seeds = [rand.task_seed(i) for i in range(8)]
    assert len(set(seeds)) == len(seeds), "tasks would share a random stream"
    rand.seed_all(42)
    assert [rand.task_seed(i) for i in range(8)] == seeds


def test_nothing_is_seeded_by_default():
    rand._seed = None
    assert rand.get_seed() is None
    assert rand.task_seed(0) is None


def test_run_session_seeded_seeds_the_worker(monkeypatch):
    """The wrapper applies the task's seed, and is a no-op without one."""
    seen = []
    monkeypatch.setattr(
        "anl2025.tournament.run_session", lambda *args: (random.random(), args)
    )

    rand.seed_all(42)
    for _ in range(2):
        seen.append(_run_session_seeded(rand.task_seed(3), None, False, False))  # type: ignore[arg-type]
    assert seen[0][0] == seen[1][0], "the same task did not repeat"
    assert seen[0][1] == (None, False, False, False), "arguments were not forwarded"

    assert _run_session_seeded(None, None, False, False)[0] != seen[0][0]  # type: ignore[arg-type]
