from pathlib import Path

from anl2025.runner import MultidealScenario
from .common import TYPE_IDENTIFIER


def load_multideal_scenario(
    folder: Path,
    name: str | None = None,
    edges_know_details: bool = True,
    python_class_identifier: str = TYPE_IDENTIFIER,
    type_marker=f"{TYPE_IDENTIFIER}:",
) -> MultidealScenario | None:
    """
    Loads a multi-deal scenario from the given folder.

    Args:
        folder: The path to load the scenario from
        name: The name to give to the scenario. If not given, the folder name
        edges_know_details: If given, edge ufuns will have `n_edges`, `outcome_spaces` members
                            that reveal the number of edges in total and the outcome space for each
                            negotiation thread.
        python_class_identifier: the key in the yaml to define a type.
        type_marker: A marker at the beginning of a string to define a type (for future proofing).
    """
    return MultidealScenario.from_folder(
        folder,
        name=name,
        edges_know_details=edges_know_details,
        python_class_identifier=python_class_identifier,
        type_marker=type_marker,
    )
