import sys
import copy
from typing import Any, Optional
from negmas.preferences import UtilityFunction
from attr import define, field
from pathlib import Path
from negmas.serialization import serialize, deserialize
from negmas.preferences.generators import generate_multi_issue_ufuns

from negmas.helpers.inout import load, dump
from anl2025.ufun import CenterUFun, SideUFunAdapter
from anl2025.common import (
    TYPES_MAP,
    CENTER_FILE_NAME,
    EDGES_FOLDER_NAME,
    SIDES_FOLDER_NAME,
    TYPE_IDENTIFIER,
    sample_between,
    get_ufun_class,
)


__all__ = ["MultidealScenario", "make_multideal_scenario"]

EPSILON = 1e-6
TRACE_COLS = (
    "time",
    "relative_time",
    "step",
    "negotiator",
    "offer",
    "responses",
    "state",
)


def type_name_adapter(x: str, types_map=TYPES_MAP) -> str:
    if x in types_map:
        return TYPES_MAP[x]
    if x.endswith(("OutcomeSpace", "Issue")) and "." not in x:
        return f"negmas.outcomes.{x}"
    if x.endswith(("CenterUFun",)) and "." not in x:
        return f"anl2025.ufun.{x}"
    if x.endswith(("UtilityFunction", "Fun")) and "." not in x:
        return f"negmas.preferences.{x}"
    return x


@define
class MultidealScenario:
    """Defines the multi-deal scenario by setting utility functions (and implicitly outcome-spaces)"""

    center_ufun: CenterUFun
    edge_ufuns: tuple[UtilityFunction, ...]
    side_ufuns: tuple[UtilityFunction, ...] | None = None
    name: str = ""
    public_graph: bool = True
    code_files: dict[str, str] = field(factory=dict)

    def __attrs_post_init__(self):
        if self.public_graph:
            for e in self.edge_ufuns:
                e.n_edges = self.center_ufun.n_edges  # type: ignore
                e.oucome_spaces = [  # type: ignore
                    copy.deepcopy(_) for _ in self.center_ufun.outcome_spaces
                ]

    def save(
        self,
        base: Path | str,
        as_folder: bool = True,
        python_class_identifier: str = TYPE_IDENTIFIER,
    ):
        base = Path(base)
        name = self.name if self.name else "scenario"
        if as_folder:
            return self.to_folder(
                folder=base / name,
                mkdir=False,
                python_class_identifier=python_class_identifier,
            )
        return self.to_file(
            path=base / f"{name}.yml", python_class_identifier=python_class_identifier
        )

    @classmethod
    def from_folder(
        cls,
        folder: Path | str,
        name: str | None = None,
        public_graph: bool = True,
        python_class_identifier: str = TYPE_IDENTIFIER,
        type_marker=f"{TYPE_IDENTIFIER}:",
    ) -> Optional["MultidealScenario"]:
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
        folder = Path(folder)
        folder = folder.resolve()
        center_file = folder / CENTER_FILE_NAME
        if not center_file.is_file():
            return None
        code_files = dict()
        for f in folder.glob("**/*.py"):
            path = str(f.relative_to(folder))
            with open(f, "r") as file:
                code_files[path] = file.read()
        if code_files:
            sys.path.append(str(folder.resolve()))
        dparams = dict(
            python_class_identifier=python_class_identifier,
            type_marker=type_marker,
            type_name_adapter=type_name_adapter,
        )
        center_ufun = deserialize(load(center_file), **dparams)  # type: ignore
        assert isinstance(
            center_ufun, CenterUFun
        ), f"{type(center_ufun)} but expected a CenterUFun \n{center_ufun}"

        def load_ufuns(f: Path | str) -> tuple[UtilityFunction, ...] | None:
            f = Path(f)
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
                if isinstance(u, SideUFunAdapter):
                    u._base_ufun.outcome_space = os
        if public_graph:
            for u in edge_ufuns:
                u.n_edges = center_ufun.n_edges  # type: ignore
                u.outcome_spaces = tuple(  # type: ignore
                    copy.deepcopy(_) for _ in center_ufun.outcome_spaces
                )
        side_ufuns = load_ufuns(folder / SIDES_FOLDER_NAME)

        return cls(
            center_ufun=center_ufun,
            edge_ufuns=tuple(edge_ufuns),
            side_ufuns=side_ufuns,
            name=folder.name if name is None else name,
            code_files=code_files,
        )

    def to_folder(
        self,
        folder: Path | str,
        python_class_identifier: str = TYPE_IDENTIFIER,
        mkdir: bool = False,
    ):
        folder = Path(folder)
        if mkdir:
            name = self.name if self.name else "scenario"
            folder = folder / name
        folder.mkdir(parents=True, exist_ok=True)
        for path, code in self.code_files.items():
            full_path = folder / path
            full_path.parent.mkdir(exist_ok=True, parents=True)
            with open(full_path, "w") as f:
                f.write(code)

        dump(
            serialize(
                self.center_ufun, python_class_identifier=python_class_identifier
            ),
            folder / CENTER_FILE_NAME,
        )

        def save(fname, ufuns):
            if ufuns is None:
                return
            base = folder / fname
            base.mkdir(parents=True, exist_ok=True)
            for u in ufuns:
                dump(
                    serialize(u, python_class_identifier=python_class_identifier),
                    base / f"{u.name}.yml",
                )

        save(EDGES_FOLDER_NAME, self.edge_ufuns)
        save(SIDES_FOLDER_NAME, self.side_ufuns)

    def to_dict(self, python_class_identifier=TYPE_IDENTIFIER) -> dict[str, Any]:
        """Converts the scenario to a dictionary"""
        return dict(
            name=self.name,
            center_ufun=serialize(
                self.center_ufun, python_class_identifier=python_class_identifier
            ),
            edge_ufuns=serialize(
                self.edge_ufuns, python_class_identifier=python_class_identifier
            ),
            side_ufuns=serialize(
                self.side_ufuns, python_class_identifier=python_class_identifier
            ),
        )

    @classmethod
    def from_dict(
        cls, d: dict[str, Any], python_class_identifier=TYPE_IDENTIFIER
    ) -> Optional["MultidealScenario"]:
        return deserialize(d, python_class_identifier=python_class_identifier)  # type: ignore

    def to_file(self, path: Path | str, python_class_identifier=TYPE_IDENTIFIER):
        dump(self.to_dict(python_class_identifier=python_class_identifier), path)

    @classmethod
    def from_file(
        cls, path: Path | str, python_class_identifier=TYPE_IDENTIFIER
    ) -> Optional["MultidealScenario"]:
        return cls.to_dict(load(path), python_class_identifier=python_class_identifier)  # type: ignore


def make_multideal_scenario(
    nedges: int = 5,
    nissues: int = 3,
    nvalues: int = 7,
    # edge ufuns
    center_reserved_value_min: float = 0.0,
    center_reserved_value_max: float = 0.0,
    center_ufun_type: str | type[CenterUFun] = "LinearCombinationCenterUFun",
    center_ufun_params: dict[str, Any] | None = None,
    # edge ufuns
    edge_reserved_value_min: float = 0.1,
    edge_reserved_value_max: float = 0.4,
) -> MultidealScenario:
    ufuns = [generate_multi_issue_ufuns(nissues, nvalues) for _ in range(nedges)]
    edge_ufuns = [_[0] for _ in ufuns]
    for u in edge_ufuns:
        u.reserved_value = sample_between(
            edge_reserved_value_min, edge_reserved_value_max
        )
    # side ufuns are utilities of the center on individual threads (may or may not be used, see next comment)
    side_ufuns = tuple(_[1] for _ in ufuns)
    # create center ufun using side-ufuns if possible and without them otherwise.
    center_r = sample_between(center_reserved_value_min, center_reserved_value_max)
    utype = get_ufun_class(center_ufun_type)
    center_ufun_params = center_ufun_params if center_ufun_params else dict()
    try:
        center_ufun = utype(
            side_ufuns=side_ufuns,
            reserved_value=center_r,
            outcome_spaces=tuple(u.outcome_space for u in side_ufuns),  # type: ignore
            **center_ufun_params,
        )
    except TypeError:
        try:
            center_ufun = utype(
                ufuns=side_ufuns,
                reserved_value=center_r,
                outcome_spaces=tuple(u.outcome_space for u in side_ufuns),  # type: ignore
                **center_ufun_params,
            )
        except TypeError:
            # if the center ufun does not take `ufuns` as an input, do not pass it
            center_ufun = utype(
                reserved_value=center_r,
                outcome_spaces=tuple(u.outcome_space for u in side_ufuns),  # type: ignore
                **center_ufun_params,
            )

    return MultidealScenario(
        center_ufun=center_ufun,
        side_ufuns=side_ufuns,
        edge_ufuns=tuple(edge_ufuns),
    )
