from collections import defaultdict
from attr import asdict, field
from multiprocessing import cpu_count
from concurrent.futures import ProcessPoolExecutor, as_completed
from negmas.helpers import unique_name
from negmas.serialization import dump
from rich import print
from rich.progress import track
from collections.abc import Sequence
from typing import TypedDict
from pathlib import Path
from typing import Self
import random
from anl2025.ufun import CenterUFun
from negmas.helpers.types import get_class, get_full_type_name
from negmas.serialization import serialize, deserialize
from negmas.helpers.inout import load
from typing import Any
from anl2025.negotiator import ANL2025Negotiator
from anl2025.negotiator import (
    TimeBased2025,
    Random2025,
    Boulware2025,
    Linear2025,
    Conceder2025,
)
from anl2025.runner import (
    AssignedScenario,
    MultidealScenario,
    RunParams,
    SessionResults,
    assign_scenario,
    make_multideal_scenario,
)
from anl2025.common import DEFAULT_METHOD, TYPE_IDENTIFIER
from attr import define

__all__ = [
    "Tournament",
    "TournamentResults",
    "anl2025_tournament",
    "DEFAULT_TOURNAMENT_PATH",
    "DEFAULT_ANL2025_COMPETITORS",
]

DEFAULT_TOURNAMENT_PATH = Path.home() / "negmas" / "anl2025" / "tournaments"
"""Default location to store tournament logs"""

DEFAULT_ANL2025_COMPETITORS = (
    TimeBased2025,
    Random2025,
    Boulware2025,
    Linear2025,
    Conceder2025,
    # IndependentBoulware2025,
    # IndependentLinear2025,
    # IndependentConceder2025,
)


def scenario_maker(
    nedges: int = 3,
    nissues: int = 3,
    nvalues: int = 7,
    # edge ufuns
    center_reserved_value_min: float = 0.0,
    center_reserved_value_max: float = 0.0,
    # edge ufuns
    edge_reserved_value_min: float = 0.1,
    edge_reserved_value_max: float = 0.4,
    # others parameters
    center_ufun_type: str | type[CenterUFun] = "MaxCenterUFun",
    center_ufun_params: dict[str, Any] | None = None,
    # fractions of different types
    dinners: float | None = None,
    job_hunt: float | None = None,
    target_quantity: float | None = None,
    others: float | None = None,
    verbose: bool = False,
) -> MultidealScenario:
    """
    Generates a MultidealScenario with customizable parameters for negotiation tournaments.

    Args:
        nedges (int): Number of edges (agents) in the scenario. Always used.
        nissues (int): Number of negotiation issues. Maybe ignored for some scenarios.
        nvalues (int): Number of possible values per issue. Maybe ignored for some scenarios.
        center_reserved_value_min (float): Minimum reserved value for the center agent.
        center_reserved_value_max (float): Maximum reserved value for the center agent.
        edge_reserved_value_min (float): Minimum reserved value for edge agents.
        edge_reserved_value_max (float): Maximum reserved value for edge agents.
        center_ufun_type (str | type[CenterUFun]): Utility function type for the center agent.
        center_ufun_params (dict[str, Any] | None): Parameters for the center agent's utility function.
        dinners (float): Fraction of scenarios with "dinners" type.
        job_hunt (float): Fraction of scenarios with "job_hunt" type.
        target_quantity (float): Fraction of scenarios with "target_quantity" type.
        others (float): Fraction of scenarios with other types.

    Returns:
        MultidealScenario: The generated scenario object.
    """
    if dinners is None:
        dinners = random.random()
    if job_hunt is None:
        job_hunt = random.random()
    if target_quantity is None:
        target_quantity = random.random()
    if others is None:
        others = random.random()
    s = dinners + job_hunt + target_quantity + others
    assert s > 0, "The sum of scenario weights must be positive"
    dinners /= s
    job_hunt /= s
    target_quantity /= s
    others /= s
    r = random.random()
    if r <= others:
        if verbose:
            print("Generating a random scenario")
        return make_multideal_scenario(
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
    if r <= others + dinners:
        if verbose:
            print("Generating a dinners scenario")
        from anl2025.scenarios.dinners import make_dinners_scenario

        return make_dinners_scenario(
            n_friends=nedges,
            n_days=nedges,
            center_reserved_value=(
                center_reserved_value_min,
                center_reserved_value_max,
            ),
            edge_reserved_values=(edge_reserved_value_min, edge_reserved_value_max),
            values=None,
            public_graph=True,
        )
    if r <= others + dinners + job_hunt:
        if verbose:
            print("Generating a job hunt scenario")
        from anl2025.scenarios.job_hunt import make_job_hunt_scenario

        return make_job_hunt_scenario(
            n_employers=nedges,
            work_days=nvalues,
            salary=[50 * (2 + _) for _ in range(nvalues)],
        )
    from anl2025.scenarios.target_quantity import make_target_quantity_scenario

    if verbose:
        print("Generating a target quantity scenario")
    return make_target_quantity_scenario(
        n_suppliers=nedges,
        quantity=(1, nvalues + 1),
        target_quantity=(2, nvalues * nedges),
        collector_reserved_value=(center_reserved_value_min, center_reserved_value_max),
        supplier_reserved_values=(edge_reserved_value_min, edge_reserved_value_max),
    )


class ScoreRecord(TypedDict):
    """Score of a single run for a single agent

    Attributes:
        agent: The agent being scored
        utility: Utility of the agent
        partner_average_utility: Average utilities of agent partners
        scenario: The scenario on which this score was received.
        repetition: The repetition number of this run.
        rotation: The rotation number of this run.
        scenario_index: Index of the scenario.
        index: Index of the agent. center = 0 and edges start at 1
        errors: Number of errors of this agent
        partner_errors: Number of errors of the opponent (partner)
        mechanism_errors: Number of mechanism errors
    """

    agent: str
    utility: float
    partner_average_utility: float
    scenario: str
    repetition: int
    rotation: int
    scenario_index: int
    index: int
    errors: int
    partner_errors: int
    mechanism_errors: int
    time: float
    self_error_details: str
    partner_error_details: str
    mechanism_error_details: str


@define
class JobInfo:
    assigned: AssignedScenario
    output: Path | None
    sname: str
    rep_index: int
    competitor_index: int
    scenario_index: int
    center: type
    center_params: dict[str, Any] | None
    edges: tuple[type, ...] | list[type]
    edge_params: tuple[dict, ...] | list[dict]
    edge_info: list[tuple[type, dict[str, Any] | None]]
    nedges_counted: int


@define
class SessionInfo:
    """Information of a single negotiation during a tournament"""

    scenario_name: str
    repetition: int
    rotation: int
    center_type_name: str
    center_params: dict[str, Any]
    edge_type_names: list[str]
    edge_params: list[dict[str, Any] | None] | tuple[dict[str, Any] | None, ...]
    results: SessionResults
    path: Path | None = None


@define
class TournamentResults:
    """Results of a tournament"""

    final_scores: dict[
        str, float
    ]  # Accumulated scores of each agent with center utilities multiplied by the center multiplier
    final_scoresE: dict[
        str, float
    ]  # Average scores of each agent when it played as edge
    final_scoresC: dict[
        str, float
    ]  # Average scores of each agent when it played as center
    center_count: dict[str, float]  # Number of times each agent played as center
    edge_count: dict[str, float]  # Number of times each agent played as edge
    weighted_average: dict[
        str, float
    ]  # Average score of each agent normalizing by the number of times it played as center or edge (e.g. 0.5)
    unweighted_average: dict[
        str, float
    ]  # Average score of each agent without normalizing by the number of times it played as center or edge (e.g. final_scores/(edge_count+center_count))
    scores: list[ScoreRecord]  # Raw scores of agents in all negotiations
    session_results: list[SessionInfo]
    path: Path | None = None
    n_threads_succeeded: int = field(init=False)
    n_threads_timedout: int = field(init=False)
    n_threads_failed: int = field(init=False)

    def __attrs_post_init__(self):
        self.n_threads_succeeded = sum(
            [_.results.n_succeeded for _ in self.session_results]
        )
        self.n_threads_timedout = sum(
            [_.results.n_timedout for _ in self.session_results]
        )
        self.n_threads_failed = sum([_.results.n_failed for _ in self.session_results])


def run_session(
    job: JobInfo, dry: bool, verbose: bool, normalize_scores: bool = False
) -> tuple[JobInfo, SessionInfo]:
    if verbose:
        print(f"Scenario {job.assigned.scenario.name}")
    assigned = job.assigned
    output = job.output
    sname = job.sname
    i = job.rep_index
    j = job.competitor_index
    center = job.center
    center_params = job.center_params
    edges = job.edges
    edge_params = job.edge_params
    r = assigned.run(
        output=output,
        name=f"{sname}_{j}_{i}",
        dry=dry,
        verbose=verbose,
        normalize_scores=normalize_scores,
    )
    return job, SessionInfo(
        scenario_name=sname,
        repetition=i,
        rotation=j,
        center_type_name=get_full_type_name(center),
        center_params=center_params if center_params else dict(),
        edge_type_names=[get_full_type_name(_) for _ in edges],
        edge_params=edge_params,  # type: ignore
        results=r,
    )


def anl2025_tournament(
    scenarios: tuple[MultidealScenario, ...],
    competitors: tuple[str | type[ANL2025Negotiator], ...],
    n_repetitions: int = 3,
    n_steps: int = 100,
    competitor_params: tuple[dict[str, Any] | None, ...] | None = None,
    path: Path | str | None = None,
    no_double_scores: bool = True,
    non_comptitor_types: tuple[str | type[ANL2025Negotiator], ...] | None = None,
    non_comptitor_params: tuple[dict[str, Any], ...] | None = None,
    n_jobs: int | float | None = 0,
    center_multiplier: float | None = None,
    edge_multiplier: float = 1,
    verbose: bool = False,
    dry: bool = False,
    keep_order: bool = True,
    share_ufuns: bool = False,
    atomic: bool = False,
    method: str = DEFAULT_METHOD,
) -> TournamentResults:
    """Creates and runs a tournament.

    Args:
        scenarios: The scenarios to use for the tournament
        competitors: The competitor negotiators
        n_repetitions: Number of repetitions of each configuration of agents
        n_steps: Number of steps of each negotiation
        competitor_params: Optional parameters to use for constructing the competitors
        path: Path to store logs and results of the tournament.
        no_double_scores: Avoid having the same agent in multiple positions in the same negotiation
        non_comptitor_types: Types to use to fill missing edge locations if not enough competitors are available
        non_comptitor_params: Paramters of non-competitor-types
        n_jobs: Number of parallel jobs to use.
                None (and negative numbers) mean serially, 0 means use all cores, fractions mean fraction of available
                cores, integers mean exact number of cores
        center_multiplier: A number to multiply center utilities with before calculating the score. Can be used
                           to give more or less value to being a center. If None, it will be equal to the number of edges.
        edge_multiplier: A number to multiply edge utilities with before calculating the score. Can be used
                           to give more or less value to being an edge
        verbose: Print progress messages
        dry: If given, the tournament will be created but will not be run.
        keep_order: Keep the order of edges when running a session
        share_ufuns: Allow negotiators to access partner utility function as `self.opponent_ufun`
        atomic: If true, every step is on offer, otherwise, every step is a complete round (two offers)
        method: The method for stepping negotiation threads. All methods supported by `negmas.Mechanism.runall()`
                are supported including sequential which means completing one negotiation before starting the next.

    Returns:
        [TODO:return]
    """
    run_params = RunParams(
        nsteps=n_steps,
        keep_order=keep_order,
        share_ufuns=share_ufuns,
        atomic=atomic,
        method=method,
    )
    tournament = Tournament(
        competitors=competitors,
        scenarios=scenarios,
        run_params=run_params,
        competitor_params=competitor_params,
    )
    return tournament.run(
        path=path,
        n_repetitions=n_repetitions,
        verbose=verbose,
        dry=dry,
        no_double_scores=no_double_scores,
        non_comptitor_types=non_comptitor_types,
        non_comptitor_params=non_comptitor_params,
        n_jobs=n_jobs,
        center_multiplier=center_multiplier,
        edge_multiplier=edge_multiplier,
    )


def make_tournament_name():
    return unique_name("t", sep="_")


@define
class Tournament:
    """Represents a tournament

    Attributes:
        competitors: the competing agents of type `ANL2025Negotiator` each
        scenarios: the scenarios in which the competitors are tested
        run_params: parameters controlling the tournament run (See `RunParams`)
        competitor_params: Parameters to pass to the competitors
    """

    competitors: tuple[str | type[ANL2025Negotiator], ...]
    scenarios: tuple[MultidealScenario, ...]
    run_params: RunParams
    competitor_params: tuple[dict[str, Any] | None, ...] | None = None
    name: str = field(factory=make_tournament_name)

    @classmethod
    def from_scenarios(
        cls,
        competitors: Sequence[str | type[ANL2025Negotiator]],
        run_params: RunParams,
        scenarios: tuple[MultidealScenario, ...] = tuple(),
        n_generated: int = 0,
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
        name: str | None = None,
        verbose: bool = False,
        # fractions of different scenario types to generate
        fraction_dinners: float | None = None,
        fraction_job_hunt: float | None = None,
        fraction_target_quantity: float | None = None,
        fraction_others: float | None = None,
    ) -> Self:
        """Loads a tournament from the given scenarios (optionally generating new ones)

        Args:
            competitors: Competing agents
            run_params: `RunParams` controlling the timing of each multideal negotiation
            scenarios: An optional tuple of predefined scenarios (`MultidealScenario`)
            n_generated: Number of new scenarios to generate
            nedges: Number of negotiation threads (only used if `n_generated` > 0)
            nissues:Number of negotiation issues per thread (only used if `n_generated` > 0)
            nvalues: Number of values per issue (only used if `n_generated` > 0)
            center_reserved_value_min: Minimum reserved value of the center for generated scenarios.
            center_reserved_value_max: Maximum reserved value of the center for generated scenarios.
            center_ufun_type: center agent ufun for generated scenarios.
            center_ufun_params: center agent ufun params for generated scenarios.
            edge_reserved_value_min: Minimum reserved value of  edges for generated scenarios.
            edge_reserved_value_max: Maximum reserved value of  edges for generated scenarios.
            competitor_params: Optional competitor paramters
            verbose: Print progress messages
            generated_dinners: fraction of generated scenarios that are dinners scenarios
            generated_job_hunt: fraction of generated scenarios that are job hunt scenarios
            generated_target_quantity: fraction of generated scenarios that are target quantity scenarios
            generated_others: fraction of generated scenarios that are random scenarios

        Returns:
            A `Tournament` ready to run
        """
        # if nedges > len(competitors):
        #     raise ValueError(
        #         f"We have {len(competitors)} competitors which is not enough for {nedges} edges"
        #     )
        return cls(
            name=name if name else make_tournament_name(),
            competitors=tuple(competitors),
            competitor_params=competitor_params,
            run_params=run_params,
            scenarios=tuple(
                list(scenarios)
                + [
                    scenario_maker(
                        nedges=nedges,
                        nissues=nissues,
                        nvalues=nvalues,
                        center_reserved_value_min=center_reserved_value_min,
                        center_reserved_value_max=center_reserved_value_max,
                        center_ufun_type=center_ufun_type,
                        center_ufun_params=center_ufun_params,
                        edge_reserved_value_min=edge_reserved_value_min,
                        edge_reserved_value_max=edge_reserved_value_max,
                        verbose=verbose,
                        dinners=fraction_dinners,
                        others=fraction_others,
                        target_quantity=fraction_target_quantity,
                        job_hunt=fraction_job_hunt,
                    )
                    for _ in range(n_generated)
                ]
            ),
        )

    def __attrs_post_init__(self):
        if not self.competitor_params:
            self.competitor_params = tuple(dict() for _ in range(len(self.competitors)))
        self.competitor_params = tuple(
            dict() if not _ else _ for _ in self.competitor_params
        )

    def save(
        self,
        path: Path | str,
        separate_scenarios: bool = False,
        python_class_identifier=TYPE_IDENTIFIER,
    ):
        """
        Saves the tournament information.

        Args:
            path: A file to save information about the tournament to
            separate_scenarios: If `True`, scenarios will be saved inside a `scenarios` folder beside the path given otherwise they will be included in the file
        """
        path = path if isinstance(path, Path) else Path(path)
        data = dict(
            competitors=[get_full_type_name(_) for _ in self.competitors],
            run_params=asdict(self.run_params),
            competitor_params=None
            if not self.competitor_params
            else [
                serialize(_, python_class_identifier=python_class_identifier)
                for _ in self.competitor_params
            ],
        )
        if separate_scenarios:
            base = path.resolve().parent / "scenarios"
            for i, s in enumerate(self.scenarios):
                name = s.name if s.name else f"s{i:03}"
                dst = base
                dst.mkdir(parents=True, exist_ok=True)
                dump(
                    serialize(s, python_class_identifier=python_class_identifier),
                    dst / f"{name}.yaml",
                )
        else:
            data["scenarios"] = [
                serialize(_, python_class_identifier=python_class_identifier)
                for _ in self.scenarios
            ]
        dump(data, path)

    @classmethod
    def load(cls, path: Path | str, python_class_identifier=TYPE_IDENTIFIER):
        """Loads the tournament information."""

        path = path if isinstance(path, Path) else Path(path)
        info = load(path)
        base = path.resolve().parent / "scenarios"
        if "scenarios" not in info:
            info["scenarios"] = []
        else:
            info["scenarios"] = list(info["scenarios"])

        if base.exists():
            info["scenarios"] += [
                deserialize(f, python_class_identifier=python_class_identifier)
                for f in base.glob("*.yaml")
            ]

        return cls(
            competitors=info["competitors"],
            scenarios=[
                deserialize(_, python_class_identifier=python_class_identifier)
                for _ in info["scenarios"]
            ],  # type: ignore
            run_params=RunParams(**info["run_params"]),
            competitor_params=None  # type: ignore
            if not info.get("competitor_params", None)
            else deserialize(
                info["competitor_params"],
                python_class_identifier=python_class_identifier,
            ),
        )

    def run(
        self,
        n_repetitions: int,
        path: Path | str | None = None,
        verbose: bool = False,
        dry: bool = False,
        no_double_scores: bool = True,
        non_comptitor_types: tuple[str | type[ANL2025Negotiator], ...] | None = None,
        non_comptitor_params: tuple[dict[str, Any], ...] | None = None,
        n_jobs: int | float | None = 0,
        center_multiplier: float | None = None,
        edge_multiplier: float = 1,
        normalize_scores: bool = False,
    ) -> TournamentResults:
        """Run the tournament

        Args:
            n_repetitions: Number of repetitions of rotations over scenarios
            path: Path to save the results to
            verbose: Print progress
            dry: Do not really run the negotiations.
            no_double_scores: Avoid having the same agent in multiple positions in the same negotiation
            non_comptitor_types: Types to use to fill missing edge locations if not enough competitors are available
            non_comptitor_params: Paramters of non-competitor-types
            n_jobs: Number of parallel jobs to use.
                    None (and negative numbers) mean serially, 0 means use all cores, fractions mean fraction of available
                    cores, integers mean exact number of cores
            center_multiplier: A number to multiply center utilities with before calculating the score. Can be used
                               to give more or less value to being a center. If None, it will be equal to the number of edges.
            edge_multiplier: A number to multiply edge utilities with before calculating the score. Can be used
                               to give more or less value to being an edge

        Returns:
            `TournamentResults` with all scores and final-scores
        """
        if path is not None:
            path = path if isinstance(path, Path) else Path(path)
        if n_jobs is not None:
            if isinstance(n_jobs, float) and n_jobs < 1.0:
                n_jobs = int(0.5 + cpu_count() * n_jobs)
            elif isinstance(n_jobs, float):
                n_jobs = int(0.5 + n_jobs)
            if n_jobs < 0:
                n_jobs = None
            elif n_jobs == 0:
                n_jobs = cpu_count()

        results = []
        assert isinstance(self.competitor_params, tuple)
        acc_scores = defaultdict(float)
        raw_scores = defaultdict(float)
        weighted_scores_center = defaultdict(float)
        weighted_scores_edge = defaultdict(float)
        count_edge = defaultdict(float)
        count_center = defaultdict(float)

        scores = []
        center_multiplier_val = center_multiplier

        def type_name(x):
            return get_full_type_name(x).replace("anl2025.negotiator.", "")

        if non_comptitor_types:
            non_comptitor_types = tuple(get_class(_) for _ in non_comptitor_types)
            non_comptitor_params = (
                non_comptitor_params
                if non_comptitor_params
                else tuple(dict() for _ in range(len(non_comptitor_types)))
            )
            non_competitors = [
                (n, p)
                for n, p in zip(non_comptitor_types, non_comptitor_params, strict=True)
            ]
        else:
            non_competitors = None

        jobs = []

        for i in track(range(n_repetitions), "Preparing Negotiation Sessions"):
            competitors = [
                (get_class(c), p)
                for c, p in zip(self.competitors, self.competitor_params, strict=True)
            ]
            for k, scenario in enumerate(self.scenarios):
                nedges = len(scenario.edge_ufuns)
                sname = scenario.name if scenario.name else f"s{k:03}"
                random.shuffle(competitors)
                # put each competitor in center once per scenario
                for j in range(len(competitors)):
                    if len(competitors) >= nedges + 1:
                        players = [_ for _ in competitors]
                        # players = competitors[: nedges + 1]
                    else:
                        # add extra players at the end if not enough competitors are available
                        players = competitors + list(
                            random.choices(
                                non_competitors if non_competitors else competitors,
                                k=nedges + 1 - len(competitors),
                            )
                        )
                    # ignore the randomly added edges if no-double-scores is set
                    nedges_counted = (
                        nedges
                        if not no_double_scores
                        else min(len(competitors) - 1, nedges)
                    )
                    if path:
                        output = path / "results" / sname / f"r{j:03}t{i:03}"
                    else:
                        output = None
                    # if verbose:
                    #     print(f"{j=}, {players=}")
                    center, center_params = players[j]
                    edge_info = [_ for _ in players[:j] + players[j + 1 :]][
                        : nedges + 1
                    ]
                    # not sure if the following shuffle is useful!
                    # It tries to randomize the order of the edges to avoid
                    # having a systematic bias but we randomize competitors anyway.
                    random.shuffle(edge_info)
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
                    jobs.append(
                        JobInfo(
                            assigned,
                            output,
                            sname,
                            i,
                            j,
                            k,
                            center,
                            center_params,
                            edges,
                            edge_params,
                            edge_info,
                            nedges_counted,
                        )
                    )
                    # This rotation guarantees that every competitor is
                    # the center once per scenario per repetition
                    # competitors = [competitors[-1]] + competitors[:-1]
        if verbose:
            print(f"Will run {len(jobs)} negotiations")

        def process_info(job: JobInfo, info: SessionInfo):
            center_multiplier = (
                center_multiplier_val
                if center_multiplier_val is not None
                else len(job.edge_info)
            )
            r = info.results
            center_ids = [m.nmi.annotation["center_id"] for m in r.mechanisms]
            edge_ids = [m.nmi.annotation["edge_id"] for m in r.mechanisms]
            results.append(info)
            center, center_params = job.center, job.center_params
            cname = (
                type_name(center)
                if not center_params
                else f"{type_name(center)}_{hash(str(center_params))}"
            )
            mean_edge_utility = sum(r.edge_utilities) / len(r.edge_utilities)
            scores.append(
                dict(
                    agent=cname,
                    utility=r.center_utility * center_multiplier,
                    partner_average_utility=mean_edge_utility,
                    scenario=job.sname,
                    repetition=job.rep_index,
                    rotation=job.competitor_index,
                    scenario_index=job.scenario_index,
                    index=0,
                    time=r.total_time,
                    errors=sum(
                        [
                            m.state.has_error and m.state.erred_negotiator == cid
                            for m, cid in zip(r.mechanisms, center_ids)
                        ]
                    ),
                    self_error_details="".join(
                        [
                            f"{m.state.error_details}\n"
                            if m.state.erred_negotiator == cid
                            else ""
                            for m, cid in zip(r.mechanisms, center_ids)
                        ]
                    ),
                    partner_error_details="".join(
                        [
                            f"{m.state.error_details}\n"
                            if m.state.erred_negotiator != cid
                            else ""
                            for m, cid in zip(r.mechanisms, center_ids)
                        ]
                    ),
                    partner_errors=sum(
                        [
                            m.state.has_error and m.state.erred_negotiator != cid
                            for m, cid in zip(r.mechanisms, center_ids)
                        ]
                    ),
                    # TODO: get the correct number of mechanism errors
                    mechanism_errors=0,
                    mechanism_error_details="",
                )
            )
            acc_scores[cname] += r.center_utility * center_multiplier
            raw_scores[cname] += r.center_utility
            weighted_scores_center[cname] += r.center_utility * center_multiplier
            count_center[cname] += 1
            for e, (c, p) in enumerate(job.edge_info[: job.nedges_counted]):
                ename = type_name(c) if not p else f"{type_name(c)}_{hash(str(p))}"
                scores.append(
                    dict(
                        agent=ename,
                        utility=r.edge_utilities[e] * edge_multiplier,
                        partner_average_utility=r.center_utility,
                        scenario=job.sname,
                        repetition=job.rep_index,
                        rotation=job.competitor_index,
                        scenario_index=job.scenario_index,
                        index=e + 1,
                        time=r.times[e],
                        errors=sum(
                            [
                                m.state.has_error and m.state.erred_negotiator == eid
                                for m, eid in zip(r.mechanisms, edge_ids)
                            ]
                        ),
                        partner_errors=sum(
                            [
                                m.state.has_error and m.state.erred_negotiator != eid
                                for m, eid in zip(r.mechanisms, edge_ids)
                            ]
                        ),
                        self_error_details="".join(
                            [
                                f"{m.state.error_details}\n"
                                if m.state.erred_negotiator == eid
                                else ""
                                for m, eid in zip(r.mechanisms, edge_ids)
                            ]
                        ),
                        partner_error_details="".join(
                            [
                                f"{m.state.error_details}\n"
                                if m.state.erred_negotiator != eid
                                else ""
                                for m, eid in zip(r.mechanisms, edge_ids)
                            ]
                        ),
                        # TODO: get the correct number of mechanism errors
                        mechanism_errors=0,
                    )
                )
                acc_scores[ename] += r.edge_utilities[e] * edge_multiplier
                raw_scores[ename] += r.edge_utilities[e]
                weighted_scores_edge[ename] += r.edge_utilities[e] * edge_multiplier
                count_edge[ename] += 1

            if verbose:
                print(f"Center Utility: {r.center_utility}")
                print(f"Edge Utilities: {r.edge_utilities}")
                print(f"Agreement: {r.agreements}")

        if n_jobs is None:
            for job in track(jobs, "Running Negotiations"):
                job, info = run_session(job, dry, verbose, normalize_scores)
                process_info(job, info)
        else:
            assert n_jobs > 0
            with ProcessPoolExecutor(max_workers=n_jobs) as executor:
                # Submit all jobs and store the futures
                futures = [
                    executor.submit(run_session, job, dry, verbose, normalize_scores)
                    for job in jobs
                ]

                # Process results as they become available
                for future in as_completed(futures):
                    try:
                        job, info = future.result()
                        process_info(job, info)
                    except Exception as e:
                        print(f"Job failed with exception: {e}")

        # weighted_average_* are the average scores of each agent when they are in the center or edge position
        weighted_average = {}
        for agent in acc_scores.keys():
            weighted_average_edge = (
                weighted_scores_edge[agent] / count_edge[agent]
                if count_edge[agent] > 0
                else 0
            )
            weighted_average_center = (
                weighted_scores_center[agent] / count_center[agent]
                if count_center[agent] > 0
                else 0
            )
            weighted_average[agent] = 0.5 * (
                weighted_average_center + weighted_average_edge
            )
        # total count for each agent
        count: dict[str, float] = dict()
        for k, v in count_edge.items():
            count[k] = v
        for k, v in count_center.items():
            count[k] += v

        return TournamentResults(
            final_scores={k: v for k, v in acc_scores.items()},
            edge_count={k: v for k, v in count_edge.items()},
            center_count={k: v for k, v in count_center.items()},
            final_scoresC={k: v for k, v in weighted_scores_center.items()},
            final_scoresE={k: v for k, v in weighted_scores_edge.items()},
            weighted_average={k: v for k, v in weighted_average.items()},
            unweighted_average={
                k: (v / count[k]) if count[k] else v for k, v in acc_scores.items()
            },
            scores=scores,
            session_results=results,
            path=path,
        )
