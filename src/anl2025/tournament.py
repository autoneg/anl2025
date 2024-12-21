from collections import defaultdict
from rich import print
from collections.abc import Sequence
from typing import TypedDict
from pathlib import Path
from typing import Self
import random
from anl2025.ufun import CenterUFun
from negmas.helpers.types import get_class
from typing import Any
from anl2025.negotiator import ANL2025Negotiator
from anl2025.runner import (
    MultidealScenario,
    RunParams,
    SessionResults,
    assign_scenario,
    make_multideal_scenario,
)
from attr import define
from negmas.preferences.preferences import get_full_type_name


class ScoreRecord(TypedDict):
    agent: str
    utility: float
    partner_average_utility: float
    scenario: str
    repetition: int
    rotation: int
    scenario_index: int
    role: str


@define
class SessionInfo:
    """Information of a single negotiation during a tournament"""

    scenario_name: str
    repetition: int
    rotation: int
    center_type_name: str
    center_params: dict[str, Any]
    edge_type_names: list[str]
    edge_params: list[dict[str, Any]]
    results: SessionResults
    path: Path | None = None


@define
class TournamentResults:
    """Results of a tournament"""

    final_scores: dict[str, float]
    scores: list[ScoreRecord]
    session_results: list[SessionInfo]


@define
class Tournament:
    competitors: tuple[str | type[ANL2025Negotiator], ...]
    scenarios: tuple[MultidealScenario, ...]
    run_params: RunParams
    competitor_params: tuple[dict[str, Any] | None, ...] | None = None

    @classmethod
    def from_generated_scenarios(
        cls,
        competitors: Sequence[str | type[ANL2025Negotiator]],
        run_params: RunParams,
        n_scenarios: int = 10,
        nedges: int = 3,
        nissues: int = 3,
        nvalues: int = 7,
        # edge ufuns
        center_reserved_value_min: float = 0.0,
        center_reserved_value_max: float = 0.0,
        center_ufun_type: str | type[CenterUFun] = "MaxCenterUFun",
        center_ufun_params: dict[str, Any] | None = None,
        # edge ufuns
        edge_reserved_value_min: float = 0.1,
        edge_reserved_value_max: float = 0.4,
        competitor_params: tuple[dict[str, Any] | None, ...] | None = None,
    ) -> Self:
        if nedges > len(competitors):
            raise ValueError(
                f"We have {len(competitors)} competitors which is not enough for {nedges} edges"
            )
        return cls(
            competitors=tuple(competitors),
            competitor_params=competitor_params,
            run_params=run_params,
            scenarios=tuple(
                make_multideal_scenario(
                    nedges=nedges,
                    nissues=nissues,
                    nvalues=nvalues,
                    center_reserved_value_min=center_reserved_value_min,
                    center_reserved_value_max=center_reserved_value_max,
                    center_ufun_type=center_ufun_type,
                    center_ufun_params=center_ufun_params,
                    edge_reserved_value_min=edge_reserved_value_min,
                    edge_reserved_value_max=edge_reserved_value_max,
                )
                for _ in range(n_scenarios)
            ),
        )

    def __attrs_post_init__(self):
        if not self.competitor_params:
            self.competitor_params = tuple(dict() for _ in range(len(self.competitors)))
        self.competitor_params = tuple(
            dict() if not _ else _ for _ in self.competitor_params
        )

    def save(self, path: Path):
        """Saves the tournament information"""

    def load(self, path: Path):
        """Loads the tournament information"""

    def run(
        self, n_repetitions: int, path: Path, verbose: bool = False, dry: bool = False
    ) -> TournamentResults:
        """Runs the tournament"""

        results = []
        assert isinstance(self.competitor_params, tuple)
        final_scores = defaultdict(float)
        scores = []

        def type_name(x):
            return get_full_type_name(x).replace("anl2025.negotiator.", "")

        for i in range(n_repetitions):
            for k, scenario in enumerate(self.scenarios):
                nedges = len(scenario.edge_ufuns)
                sname = scenario.name if scenario.name else f"s{k:03}"
                players = [
                    (get_class(c), p)
                    for c, p in zip(
                        self.competitors, self.competitor_params, strict=True
                    )
                ]
                random.shuffle(players)
                if len(players) >= nedges + 1:
                    players = players[: nedges + 1]
                else:
                    players = players + list(
                        random.choices(players, k=nedges + 1 - len(players))
                    )
                for j in range(len(players)):
                    output = path / "results" / sname / f"r{j:03}t{i:03}"
                    center, center_params = players[j]
                    edge_info = players[:j] + players[j + 1 :]
                    edges = [_[0] for _ in edge_info]
                    edge_params = [_[1] if _[1] else dict() for _ in edge_info]
                    assigned = assign_scenario(
                        scenario=scenario,
                        run_params=self.run_params,
                        center_type=center,
                        center_params=center_params,
                        edge_types=edges,  # type: ignore
                        edge_params=edge_params,
                        verbose=verbose,
                        sample_edges=False,
                    )
                    r = assigned.run(
                        output=output,
                        name=f"{sname}_{j}_{i}",
                        dry=dry,
                        verbose=verbose,
                    )
                    results.append(
                        SessionInfo(
                            scenario_name=sname,
                            repetition=i,
                            rotation=j,
                            center_type_name=get_full_type_name(center),
                            center_params=center_params if center_params else dict(),
                            edge_type_names=[get_full_type_name(_) for _ in edges],
                            edge_params=edge_params,
                            results=r,
                        )
                    )
                    cname = (
                        type_name(center)
                        if not center_params
                        else f"{type_name(center)}_{hash(str(center_params))}"
                    )
                    mean_edge_utility = sum(r.edge_utilities) / len(r.edge_utilities)
                    scores.append(
                        dict(
                            agent=cname,
                            utility=r.center_utility,
                            partner_average_utility=mean_edge_utility,
                            scenario=sname,
                            repetition=i,
                            rotation=j,
                            scenario_index=k,
                            role="center",
                        )
                    )
                    final_scores[cname] += r.center_utility
                    for e, (c, p) in enumerate(edge_info):
                        cname = (
                            type_name(c) if not p else f"{type_name(c)}_{hash(str(p))}"
                        )
                        scores.append(
                            dict(
                                agent=cname,
                                utility=r.edge_utilities[e],
                                partner_average_utility=r.center_utility,
                                scenario=sname,
                                repetition=i,
                                rotation=j,
                                scenario_index=k,
                                role=f"edge{e}",
                            )
                        )
                        final_scores[cname] += r.edge_utilities[e]
                    players = [players[-1]] + players[:-1]
                    if verbose:
                        print(f"Center Utility: {r.center_utility}")
                        print(f"Edge Utilities: {r.edge_utilities}")
        return TournamentResults(
            final_scores={
                k: v / (len(self.scenarios) * n_repetitions)
                for k, v in final_scores.items()
            },
            scores=scores,
            session_results=results,
        )
