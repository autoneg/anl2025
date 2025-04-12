from pathlib import Path
from random import choice

from anl2025.scenario import MultidealScenario
from .dinners import *  # noqa: F403
from .job_hunt import *  # noqa: F403
from .target_quantity import *  # noqa: F403


__all__ = (
    dinners.__all__  # noqa: F405
    + job_hunt.__all__  # noqa: F405
    + target_quantity.__all__  # noqa: F405
    + ["load_example_scenario", "get_example_scenario_names"]
)  # type: ignore # noqa: F405


def _base_path():
    path = Path(__file__).parent
    if path.name == "scenarios":
        path = path.parent
    return path / "example_scenarios"


def load_example_scenario(name: str | None = None) -> MultidealScenario:
    """Loads an example scenario.

    Remarks:
        - Currently the following scenarios are available: Dinners, JobHunt and TargetQuantity.
        - If you do not pass any name a randomly chosen example scenario will be returned.
    """
    if not name:
        paths = [_.resolve() for _ in _base_path().glob("*") if _.is_dir()]
    else:
        paths = [_base_path() / name]
    s = MultidealScenario.from_folder(choice(paths))
    assert s is not None
    return s


def get_example_scenario_names() -> list[str]:
    """Returns a list of example scenario names."""
    return [_.name for _ in _base_path().glob("*") if _.is_dir()]
