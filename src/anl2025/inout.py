import sys
import copy
from pathlib import Path

from anl2025.runner import MultidealScenario
from anl2025.ufun import CenterUFun
from negmas import UtilityFunction
from negmas.serialization import deserialize
from negmas.helpers.inout import load

CENTER_FILE_NAME = "center.yml"
EDGES_FOLDER_NAME = "edges"
SIDES_FILDER_NAME = "sides"
TYPES_MAP = dict(
    DiscreteCartesianOutcomeSpace="negmas.outcomes.DiscreteCartesianOutcomeSpace"
)


def type_name_adapter(x: str, types_map=TYPES_MAP) -> str:
    if x in types_map:
        return TYPES_MAP[x]
    if x.endswith(("OutcomeSpace", "Issue")) and "." not in x:
        return f"negmas.outcomes.{x}"
    if x.endswith(("UtilityFunction", "Fun")) and "." not in x:
        return f"negmas.preferences.{x}"
    return x


def load_multideal_scenario(
    folder: Path,
    name: str | None = None,
    edges_know_details: bool = True,
    python_class_identifier: str = "type",
    type_marker="type:",
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
    folder = folder.resolve()
    center_file = folder / CENTER_FILE_NAME
    if not center_file.is_file():
        return None
    dparams = dict(
        python_class_identifier=python_class_identifier,
        type_marker=type_marker,
        type_name_adapter=type_name_adapter,
    )
    sys.path.append(str(folder))
    center_ufun = deserialize(load(center_file), **dparams)  # type: ignore
    assert isinstance(center_ufun, CenterUFun)

    def load_ufuns(f: Path) -> tuple[UtilityFunction, ...] | None:
        if not f.is_dir():
            return None
        return tuple(
            deserialize(load(_), **dparams)  # type: ignore
            for _ in f.glob("*.yml")
        )

    edge_ufuns = load_ufuns(folder / EDGES_FOLDER_NAME)
    assert edge_ufuns
    for u, os in zip(edge_ufuns, center_ufun.outcome_spaces):
        if u.outcome_space is None:
            u.outcome_space = os
    if edges_know_details:
        for u in edge_ufuns:
            u.n_edges = center_ufun.n_edges  # type: ignore
            u.outcome_spaces = tuple(  # type: ignore
                copy.deepcopy(_) for _ in center_ufun.outcome_spaces
            )
    side_ufuns = load_ufuns(folder / SIDES_FILDER_NAME)

    return MultidealScenario(
        center_ufun=center_ufun,
        edge_ufuns=tuple(edge_ufuns),
        side_ufuns=side_ufuns,
        name=folder.name if name is None else name,
    )
