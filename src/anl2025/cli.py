from anl2025.scenario import MultidealScenario
from rich.table import Table
import importlib.metadata
from pathlib import Path
from negmas.outcomes.base_issue import unique_name
from negmas.serialization import dump
import pandas as pd
import anl2025
from typing import Annotated
from anl2025.tournament import Tournament
import typer
from rich import print

from anl2025.ufun import CenterUFun
from anl2025.common import TYPE_IDENTIFIER
from anl2025.runner import DEFAULT_METHOD, RunParams, run_generated_session, run_session


app = typer.Typer()
tournament = typer.Typer()
session = typer.Typer()

app.add_typer(
    tournament, name="tournament", help="Creates, manages and runs tournaments"
)

app.add_typer(
    session, name="session", help="Runs single sessions of multi-deal negotiations."
)


def get_package_version(name: str | None = None):
    if not name:
        name = __name__.split(".")[0]
    metadata = importlib.metadata.metadata(name)

    return metadata["Version"]


@app.command(help="Version information")
def version():
    print(f"ANL2025: {get_package_version()}, NegMAS: {get_package_version('negmas')}")


def do_make(
    path: Path | None,
    generated: int | None = None,
    competitor: list[str] = [
        "Boulware2025",
        "Random2025",
        "Linear2025",
        "Conceder2025",
    ],
    nissues: int = 3,
    nvalues: int = 7,
    center_ufun: str = "MaxCenterUFun",
    python_class_identifier: str = TYPE_IDENTIFIER,
    center_reserved_value_min: float = 0.0,
    center_reserved_value_max: float = 0.0,
    nedges: int = 3,
    edge_reserved_value_min: float = 0.1,
    edge_reserved_value_max: float = 0.4,
    nsteps: int = 100,
    keep_order: bool = True,
    atomic: bool = False,
    share_ufuns: bool = True,
    output: Path = Path.home() / "negmas" / "anl2025" / "tournament",
    separate_scenarios: bool = True,
    name: str = "auto",
    method: str = DEFAULT_METHOD,
    public_graph: bool = True,
):
    if generated is None:
        generated = 3 if path is None else 0
    if name == "auto":
        name = unique_name("t", sep="")
    if name:
        output = output / name

    def full_name(x: str) -> str:
        if x in anl2025.negotiator.__all__:
            return f"anl2025.negotiator.{x}"
        return x

    competitors = tuple(full_name(_) for _ in competitor)
    scenarios = []
    if path is not None:
        for f in path.glob("*.yml"):
            try:
                if f.is_file():
                    s = MultidealScenario.from_file(
                        f,
                        python_class_identifier=python_class_identifier,
                    )
                    if not s:
                        continue
                    scenarios.append(s)
            except Exception:
                pass
        for d in path.glob("**/*"):
            try:
                if d.is_dir():
                    s = MultidealScenario.from_folder(
                        d,
                        public_graph=public_graph,
                        python_class_identifier=python_class_identifier,
                    )
                    if not s:
                        continue
                    scenarios.append(s)
            except Exception:
                pass
    leave = False
    if not competitors:
        print("[red]No competitors[/red]!!")
        leave = True
    if not scenarios and not generated:
        print(
            "[red]No scenarios!![/red] No path to existing scenarios given (--scenarios-path) nor are you requesting generating of new paths (--generate)!!"
        )
        leave = True
    if leave:
        return None, None

    t = Tournament.from_scenarios(
        competitors=(competitors),
        scenarios=tuple(scenarios),
        run_params=RunParams(nsteps, keep_order, share_ufuns, atomic, method),
        n_generated=generated,
        nedges=nedges,
        nissues=nissues,
        nvalues=nvalues,
        center_reserved_value_min=center_reserved_value_min,
        center_reserved_value_max=center_reserved_value_max,
        center_ufun_type=center_ufun,
        edge_reserved_value_min=edge_reserved_value_min,
        edge_reserved_value_max=edge_reserved_value_max,
    )
    path = output / "info.yaml"
    t.save(
        path,
        separate_scenarios=separate_scenarios,
        python_class_identifier=python_class_identifier,
    )
    return t, path


def do_run(
    t: Tournament, nreps: int, output: Path, verbose: bool, dry: bool, njobs: int
):
    results = t.run(nreps, output, verbose, dry, n_jobs=njobs if njobs >= 0 else None)
    if len(results.scores) < 1:
        print(
            "No results found!! Make sure that you pass scenarios either using --scenarios or --generate"
        )
        return
    data = pd.DataFrame.from_records(results.scores)
    data["role"] = data["index"].apply(lambda x: "center" if x == 0 else "edge")
    data.to_csv(output / "scores.csv", index=False)
    dump(results.final_scores, output / "final_scores.yaml")
    print(f"Got {len(results.scores)} scores")
    df = data.groupby(["agent", "role"])["utility"].describe().reset_index()
    if len(df) > 0:
        assert isinstance(df, pd.DataFrame)
        print(df_to_table(df, "Score Summary", empty_repeated_values=("agent",)))
    # Create a table for display
    table = Table(title="Final Scores")
    table.add_column("Rank")
    table.add_column("Name", style="blue")
    table.add_column("Score")

    # Add rows to the table

    scores = results.final_scores
    sorted_scores = dict(sorted(scores.items(), key=lambda item: item[1], reverse=True))
    for i, (name, score) in enumerate(sorted_scores.items()):
        table.add_row(str(i + 1), name, f"{score:.3f}")

    # Print the table using rich
    print(table)


def df_to_table(
    df: pd.DataFrame,
    title: str,
    index: bool = False,
    empty_repeated_values: tuple[str, ...] = tuple(),
) -> Table:
    """Convert a pandas.DataFrame obj into a rich.Table obj.
    Args:
        df (DataFrame): A Pandas DataFrame to be converted to a rich Table.
        title: Title to show at the top
        index: Show or or do not show an index column
    Returns:
        Table: A rich Table instance populated with the DataFrame values.
    """
    table = Table(title=title)
    if index:
        table.add_column("index")

    # Add the columns
    for column in df.columns:
        table.add_column(str(column))

    # Add the rows
    previous_row = ["" for _ in range(len(df.columns))]
    for ind, value_list in enumerate(df.values.tolist()):
        row = [f"{x:.3f}" if isinstance(x, float) else str(x) for x in value_list]
        if empty_repeated_values:
            row = [
                a
                if (c not in empty_repeated_values) or (a != b and isinstance(a, str))
                else ""
                for (a, b, c) in zip(row, previous_row, df.columns)
            ]
        if index:
            table.add_row(str(ind), *row)
        else:
            table.add_row(*row)
        previous_row = row
    return table


@session.command(name="random", help="Runs a multi-deal negotiation session")
def run_random(
    nissues: Annotated[
        int,
        typer.Option(
            help="Number of negotiation issues", rich_help_panel="Outcome Space"
        ),
    ] = 3,
    nvalues: Annotated[
        int,
        typer.Option(
            help="Number of values per negotiation issue",
            rich_help_panel="Outcome Space",
        ),
    ] = 7,
    center: Annotated[
        str,
        typer.Option(help="The type of the center agent", rich_help_panel="Center"),
    ] = "Boulware2025",
    center_ufun: Annotated[
        str,
        typer.Option(
            help="The type of the center ufun: Any ufun defined in anl2025.ufun is OK. Examples are MaxCenterUFun and MeanSMCenterUFUn",
            rich_help_panel="Center",
        ),
    ] = "MaxCenterUFun",
    center_reserved_value_min: Annotated[
        float,
        typer.Option(
            help="Minimum value for the center reserved value",
            rich_help_panel="Center",
        ),
    ] = 0.0,
    center_reserved_value_max: Annotated[
        float,
        typer.Option(
            help="Maximim value for the center reserved value",
            rich_help_panel="Center",
        ),
    ] = 0.0,
    nedges: Annotated[
        int,
        typer.Option(
            help=(
                "Number of Edges (the M side of the 1-M negotiation session). "
                "If you pass this as 0, you can control the edges one by one using --edge"
            ),
            rich_help_panel="Protocol",
        ),
    ] = 10,
    edge: Annotated[
        list[str],
        typer.Option(
            help="Types to use for the edges. If nedges is 0, this will define all the edges in order (no randomization)",
            rich_help_panel="Edges",
        ),
    ] = [
        "Boulware2025",
        "Random2025",
        "Linear2025",
        "Conceder2025",
    ],
    edge_reserved_value_min: Annotated[
        float,
        typer.Option(
            help="Number of Edges (the M side of the 1-M negotiation session)",
            rich_help_panel="Edges",
        ),
    ] = 0.1,
    edge_reserved_value_max: Annotated[
        float,
        typer.Option(
            help="Number of Edges (the M side of the 1-M negotiation session)",
            rich_help_panel="Edges",
        ),
    ] = 0.4,
    nsteps: Annotated[
        int,
        typer.Option(
            help="Number of negotiation steps (see `atomic` for the exact meaning of this).",
            rich_help_panel="Protocol",
        ),
    ] = 100,
    keep_order: Annotated[
        bool,
        typer.Option(
            help="If given, the mechanisms will be advanced in order in every step.",
            rich_help_panel="Protocol",
        ),
    ] = True,
    atomic: Annotated[
        bool,
        typer.Option(
            help=(
                "If given, each step of a mechanism represents a single offer "
                "(from a center or an edge but not both). This may make the logs"
                " wrong though. If --no-atomic (default), a single step corresponds "
                "to one offer form the center and from an edge"
            ),
            rich_help_panel="Protocol",
        ),
    ] = False,
    share_ufuns: Annotated[
        bool,
        typer.Option(
            help="Whether or not to share partner ufun up to reserved value. If any ANL2024 agent is used as center or edge, this MUST be True (default)",
            rich_help_panel="Protocol",
        ),
    ] = True,
    dry: Annotated[
        bool,
        typer.Option(
            help="Dry-run. Does not really run anything.",
            rich_help_panel="Output and Logs",
        ),
    ] = False,
    output: Annotated[
        Path,
        typer.Option(
            help="A directory to store the negotiation logs and plots",
            rich_help_panel="Output",
        ),
    ] = Path.home() / "negmas" / "anl2025" / "session",
    name: Annotated[
        str,
        typer.Option(
            help="The name of this session (a random name will be created if not given)",
            rich_help_panel="Output and Logs",
        ),
    ] = "",
    verbose: Annotated[
        bool,
        typer.Option(help="Verbosity", rich_help_panel="Output and Logs"),
    ] = False,
):
    results = run_generated_session(
        center_type=center,
        center_reserved_value_min=center_reserved_value_min,
        center_reserved_value_max=center_reserved_value_max,
        nedges=nedges,
        center_ufun_type=center_ufun,
        edge_reserved_value_min=edge_reserved_value_min,
        edge_reserved_value_max=edge_reserved_value_max,
        edge_types=edge,  # type: ignore
        nissues=nissues,
        nvalues=nvalues,
        nsteps=nsteps,
        verbose=verbose,
        keep_order=keep_order,
        share_ufuns=share_ufuns,
        atomic=atomic,
        output=output,
        name=name,
        dry=dry,
        method=DEFAULT_METHOD,
    )

    cfun = results.center.ufun
    assert isinstance(cfun, CenterUFun)
    side_ufuns = cfun.side_ufuns()
    for i, (e, m, u) in enumerate(
        zip(results.edges, results.mechanisms, side_ufuns, strict=True)  # type: ignore
    ):
        print(
            f"{i:02}: Mechanism {m.name} between ({m.negotiator_ids}) ended in {m.current_step} ({m.relative_time:4.3}) with {m.agreement}: "
            f"Edge Utility = {e.ufun(m.agreement) if e.ufun else 'unknown'}, "
            # f"Side Utility = {u(m.agreement) if u else 'unknown'}"
        )
    print(f"Center Utility: {results.center_utility}")


@session.command(name="run", help="Runs a multi-deal negotiation session")
def run_scenario(
    path: Annotated[
        Path,
        typer.Argument(
            help="Path to a folder to load scenarios from",
            rich_help_panel="Tournament Control",
        ),
    ],
    center: Annotated[
        str,
        typer.Option(help="The type of the center agent", rich_help_panel="Center"),
    ] = "Boulware2025",
    edge: Annotated[
        list[str],
        typer.Option(
            help="Types to use for the edges. If nedges is 0, this will define all the edges in order (no randomization)",
            rich_help_panel="Edges",
        ),
    ] = [
        "Boulware2025",
        "Random2025",
        "Conceder2025",
        "Linear2025",
    ],
    nsteps: Annotated[
        int,
        typer.Option(
            help="Number of negotiation steps (see `atomic` for the exact meaning of this).",
            rich_help_panel="Protocol",
        ),
    ] = 100,
    keep_order: Annotated[
        bool,
        typer.Option(
            help="If given, the mechanisms will be advanced in order in every step.",
            rich_help_panel="Protocol",
        ),
    ] = True,
    atomic: Annotated[
        bool,
        typer.Option(
            help=(
                "If given, each step of a mechanism represents a single offer "
                "(from a center or an edge but not both). This may make the logs"
                " wrong though. If --no-atomic (default), a single step corresponds "
                "to one offer form the center and from an edge"
            ),
            rich_help_panel="Protocol",
        ),
    ] = False,
    share_ufuns: Annotated[
        bool,
        typer.Option(
            help="Whether or not to share partner ufun up to reserved value. If any ANL2024 agent is used as center or edge, this MUST be True (default)",
            rich_help_panel="Protocol",
        ),
    ] = True,
    dry: Annotated[
        bool,
        typer.Option(
            help="Dry-run. Does not really run anything.",
            rich_help_panel="Output and Logs",
        ),
    ] = False,
    output: Annotated[
        Path,
        typer.Option(
            help="A directory to store the negotiation logs and plots",
            rich_help_panel="Output",
        ),
    ] = Path.home() / "negmas" / "anl2025" / "session",
    name: Annotated[
        str,
        typer.Option(
            help="The name of this session (a random name will be created if not given)",
            rich_help_panel="Output and Logs",
        ),
    ] = "",
    verbose: Annotated[
        bool,
        typer.Option(help="Verbosity", rich_help_panel="Output and Logs"),
    ] = False,
):
    s = (
        MultidealScenario.from_file(path)
        if path.is_file()
        else MultidealScenario.from_folder(path)
    )
    if s is None:
        print(f"[red]ERROR: [/red] Cannot load scenario from {path}")
        return
    results = run_session(
        scenario=s,
        center_type=center,
        edge_types=edge,  # type: ignore
        nsteps=nsteps,
        verbose=verbose,
        keep_order=keep_order,
        share_ufuns=share_ufuns,
        atomic=atomic,
        output=output,
        name=name,
        dry=dry,
        method=DEFAULT_METHOD,
    )

    cfun = results.center.ufun
    assert isinstance(cfun, CenterUFun)
    side_ufuns = cfun.side_ufuns()
    for i, (e, m, u) in enumerate(
        zip(results.edges, results.mechanisms, side_ufuns, strict=True)  # type: ignore
    ):
        print(
            f"{i:02}: Mechanism {m.name} between ({m.negotiator_ids}) ended in {m.current_step} ({m.relative_time:4.3}) with {m.agreement}: "
            f"Edge Utility = {e.ufun(m.agreement) if e.ufun else 'unknown'}, "
            # f"Side Utility = {u(m.agreement) if u else 'unknown'}"
        )
    print(f"Center Utility: {results.center_utility}")


# @app.command()
# def tournament(ctx: typer.Context):
#     """
#     Manage tournaments.
#     """
#     # This function is called when the "tournament" command is invoked
#     # You can access the subcommand using ctx.invoked_subcommand
#     pass  # Add any logic you want to execute before subcommands


@tournament.command(help="Makes a tournament without running it")
def make(
    scenarios_path: Annotated[
        Path,
        typer.Option(
            help="Path to a folder to load scenarios from",
            rich_help_panel="Tournament Control",
        ),
    ] = None,  # type: ignore
    generate: Annotated[
        int,
        typer.Option(
            help="Number of random scenarios to generate",
            rich_help_panel="Tournament Control",
        ),
    ] = None,  # type: ignore
    competitor: Annotated[
        list[str],
        typer.Option(
            help="Competitor types",
            rich_help_panel="Edges",
        ),
    ] = [
        "Boulware2025",
        "Random2025",
        "Linear2025",
        "Conceder2025",
    ],
    nissues: Annotated[
        int,
        typer.Option(
            help="Number of negotiation issues", rich_help_panel="Outcome Space"
        ),
    ] = 3,
    nvalues: Annotated[
        int,
        typer.Option(
            help="Number of values per negotiation issue",
            rich_help_panel="Outcome Space",
        ),
    ] = 7,
    center_ufun: Annotated[
        str,
        typer.Option(
            help="The type of the center ufun: Any ufun defined in anl2025.ufun is OK. Examples are MaxCenterUFun and MeanSMCenterUFUn",
            rich_help_panel="Center",
        ),
    ] = "MaxCenterUFun",
    python_class_identifier: Annotated[
        str,
        typer.Option(
            help="The identifier identifying types in saved files.",
            rich_help_panel="Tournament Control",
        ),
    ] = TYPE_IDENTIFIER,
    center_reserved_value_min: Annotated[
        float,
        typer.Option(
            help="Minimum value for the center reserved value",
            rich_help_panel="Center",
        ),
    ] = 0.0,
    center_reserved_value_max: Annotated[
        float,
        typer.Option(
            help="Maximim value for the center reserved value",
            rich_help_panel="Center",
        ),
    ] = 0.0,
    nedges: Annotated[
        int,
        typer.Option(
            help=(
                "Number of Edges (the M side of the 1-M negotiation session). "
                "If you pass this as 0, you can control the edges one by one using --edge"
            ),
            rich_help_panel="Protocol",
        ),
    ] = 3,
    edge_reserved_value_min: Annotated[
        float,
        typer.Option(
            help="Number of Edges (the M side of the 1-M negotiation session)",
            rich_help_panel="Edges",
        ),
    ] = 0.1,
    edge_reserved_value_max: Annotated[
        float,
        typer.Option(
            help="Number of Edges (the M side of the 1-M negotiation session)",
            rich_help_panel="Edges",
        ),
    ] = 0.4,
    nsteps: Annotated[
        int,
        typer.Option(
            help="Number of negotiation steps (see `atomic` for the exact meaning of this).",
            rich_help_panel="Protocol",
        ),
    ] = 100,
    keep_order: Annotated[
        bool,
        typer.Option(
            help="If given, the mechanisms will be advanced in order in every step.",
            rich_help_panel="Protocol",
        ),
    ] = True,
    atomic: Annotated[
        bool,
        typer.Option(
            help=(
                "If given, each step of a mechanism represents a single offer "
                "(from a center or an edge but not both). This may make the logs"
                " wrong though. If --no-atomic (default), a single step corresponds "
                "to one offer form the center and from an edge"
            ),
            rich_help_panel="Protocol",
        ),
    ] = False,
    share_ufuns: Annotated[
        bool,
        typer.Option(
            help="Whether or not to share partner ufun up to reserved value. If any ANL2024 agent is used as center or edge, this MUST be True (default)",
            rich_help_panel="Protocol",
        ),
    ] = True,
    output: Annotated[
        Path,
        typer.Option(
            help="A directory to store the negotiation logs and plots",
            rich_help_panel="Output",
        ),
    ] = Path.home() / "negmas" / "anl2025" / "tournament",
    separate_scenarios: Annotated[
        bool,
        typer.Option(
            help="Save scenarios in separate folders in the output directory",
            rich_help_panel="Output",
        ),
    ] = True,
    name: Annotated[
        str,
        typer.Option(
            help="The name of this session (a random name will be created if not given)",
            rich_help_panel="Output and Logs",
        ),
    ] = "auto",
    method: Annotated[
        str,
        typer.Option(
            help="The method for conducting the multi-deal negotiation. Supported methods are sequential and ordered",
            rich_help_panel="Mechanism",
        ),
    ] = DEFAULT_METHOD,
):
    if scenarios_path is None and generate is None:
        print(
            "[red]ERROR[/red] You did not specify a scenarios path using --scenarios-path "
            "nor a number of scenarios to generate using --generate. Please specify at least one of them"
        )
    tournament, path = do_make(
        path=scenarios_path,
        generated=generate,
        competitor=competitor,
        nissues=nissues,
        nvalues=nvalues,
        center_ufun=center_ufun,
        python_class_identifier=python_class_identifier,
        center_reserved_value_min=center_reserved_value_min,
        center_reserved_value_max=center_reserved_value_max,
        nedges=nedges,
        edge_reserved_value_min=edge_reserved_value_min,
        edge_reserved_value_max=edge_reserved_value_max,
        nsteps=nsteps,
        keep_order=keep_order,
        atomic=atomic,
        share_ufuns=share_ufuns,
        output=output,
        separate_scenarios=separate_scenarios,
        name=name,
        method=method,
    )
    if tournament:
        print(f"Tournament information is saved in {path}. Use `run` to run it")


@tournament.command(help="Makes and executes a tournament")
def run(
    scenarios_path: Annotated[
        Path,
        typer.Option(
            help="Path to a folder to load scenarios from",
            rich_help_panel="Tournament Control",
        ),
    ] = None,  # type: ignore
    generate: Annotated[
        int,
        typer.Option(
            help="Number of random scenarios to generate",
            rich_help_panel="Tournament Control",
        ),
    ] = None,  # type: ignore
    competitor: Annotated[
        list[str],
        typer.Option(
            help="Competitor types",
            rich_help_panel="Edges",
        ),
    ] = [
        "Boulware2025",
        "Random2025",
        "Conceder2025",
        "Linear2025",
    ],
    nissues: Annotated[
        int,
        typer.Option(
            help="Number of negotiation issues", rich_help_panel="Outcome Space"
        ),
    ] = 3,
    nvalues: Annotated[
        int,
        typer.Option(
            help="Number of values per negotiation issue",
            rich_help_panel="Outcome Space",
        ),
    ] = 7,
    center_ufun: Annotated[
        str,
        typer.Option(
            help="The type of the center ufun: Any ufun defined in anl2025.ufun is OK. Examples are MaxCenterUFun and MeanSMCenterUFUn",
            rich_help_panel="Center",
        ),
    ] = "MaxCenterUFun",
    python_class_identifier: Annotated[
        str,
        typer.Option(
            help="The identifier identifying types in saved files.",
            rich_help_panel="Tournament Control",
        ),
    ] = TYPE_IDENTIFIER,
    center_reserved_value_min: Annotated[
        float,
        typer.Option(
            help="Minimum value for the center reserved value",
            rich_help_panel="Center",
        ),
    ] = 0.0,
    center_reserved_value_max: Annotated[
        float,
        typer.Option(
            help="Maximim value for the center reserved value",
            rich_help_panel="Center",
        ),
    ] = 0.0,
    nedges: Annotated[
        int,
        typer.Option(
            help=(
                "Number of Edges (the M side of the 1-M negotiation session). "
                "If you pass this as 0, you can control the edges one by one using --edge"
            ),
            rich_help_panel="Protocol",
        ),
    ] = 3,
    edge_reserved_value_min: Annotated[
        float,
        typer.Option(
            help="Number of Edges (the M side of the 1-M negotiation session)",
            rich_help_panel="Edges",
        ),
    ] = 0.1,
    edge_reserved_value_max: Annotated[
        float,
        typer.Option(
            help="Number of Edges (the M side of the 1-M negotiation session)",
            rich_help_panel="Edges",
        ),
    ] = 0.4,
    nsteps: Annotated[
        int,
        typer.Option(
            help="Number of negotiation steps (see `atomic` for the exact meaning of this).",
            rich_help_panel="Protocol",
        ),
    ] = 100,
    keep_order: Annotated[
        bool,
        typer.Option(
            help="If given, the mechanisms will be advanced in order in every step.",
            rich_help_panel="Protocol",
        ),
    ] = True,
    atomic: Annotated[
        bool,
        typer.Option(
            help=(
                "If given, each step of a mechanism represents a single offer "
                "(from a center or an edge but not both). This may make the logs"
                " wrong though. If --no-atomic (default), a single step corresponds "
                "to one offer form the center and from an edge"
            ),
            rich_help_panel="Protocol",
        ),
    ] = False,
    share_ufuns: Annotated[
        bool,
        typer.Option(
            help="Whether or not to share partner ufun up to reserved value. If any ANL2024 agent is used as center or edge, this MUST be True (default)",
            rich_help_panel="Protocol",
        ),
    ] = True,
    output: Annotated[
        Path,
        typer.Option(
            help="A directory to store the negotiation logs and plots",
            rich_help_panel="Output",
        ),
    ] = Path.home() / "negmas" / "anl2025" / "tournament",
    separate_scenarios: Annotated[
        bool,
        typer.Option(
            help="Save scenarios in separate folders in the output directory",
            rich_help_panel="Output",
        ),
    ] = True,
    name: Annotated[
        str,
        typer.Option(
            help="The name of this session (a random name will be created if not given)",
            rich_help_panel="Output and Logs",
        ),
    ] = "auto",
    method: Annotated[
        str,
        typer.Option(
            help="The method for conducting the multi-deal negotiation. Supported methods are sequential and ordered",
            rich_help_panel="Mechanism",
        ),
    ] = DEFAULT_METHOD,
    dry: Annotated[
        bool,
        typer.Option(
            help="Dry-run. Does not really run anything.",
            rich_help_panel="Output and Logs",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(help="Verbosity", rich_help_panel="Output and Logs"),
    ] = False,
    nreps: Annotated[
        int,
        typer.Option(
            help="Number of random shuffling repetitions",
            rich_help_panel="Tournament Control",
        ),
    ] = 2,
    njobs: Annotated[
        int,
        typer.Option(
            help="Parallelism. -1 for serial, 0 for maximum parallelism, int>0 for specific number of cores and float less than one for a fraction of cores available",
            rich_help_panel="Tournament Control",
        ),
    ] = 1,
):
    if scenarios_path is None and generate is None:
        print(
            "[red]ERROR[/red] You did not specify a scenarios path using --scenarios-path "
            "nor a number of scenarios to generate using --generate. Please specify at least one of them"
        )
    t, path = do_make(
        path=scenarios_path,
        generated=generate,
        competitor=competitor,
        nissues=nissues,
        nvalues=nvalues,
        center_ufun=center_ufun,
        python_class_identifier=python_class_identifier,
        center_reserved_value_min=center_reserved_value_min,
        center_reserved_value_max=center_reserved_value_max,
        nedges=nedges,
        edge_reserved_value_min=edge_reserved_value_min,
        edge_reserved_value_max=edge_reserved_value_max,
        nsteps=nsteps,
        keep_order=keep_order,
        atomic=atomic,
        share_ufuns=share_ufuns,
        output=output,
        separate_scenarios=separate_scenarios,
        name=name,
        method=method,
    )
    if not t or path is None:
        return
    print(f"Tournament information is saved in {path}. Use `run` to run it")
    do_run(t, nreps, path.parent, verbose, dry, njobs)


@tournament.command(help="Executes a tournament made using the make command.")
def execute(
    path: Annotated[
        Path,
        typer.Argument(
            help="Path to the saved yaml file with tournament info",
            rich_help_panel="Input",
        ),
    ],
    nreps: Annotated[
        int,
        typer.Option(
            help="Number of random shuffling repetitions",
            rich_help_panel="Tournament Control",
        ),
    ] = 2,
    dry: Annotated[
        bool,
        typer.Option(
            help="Dry-run. Does not really run anything.",
            rich_help_panel="Output and Logs",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(help="Verbosity", rich_help_panel="Output and Logs"),
    ] = False,
    njobs: Annotated[
        int,
        typer.Option(
            help="Parallelism. -1 for serial, 0 for maximum parallelism, int>0 for specific number of cores and float less than one for a fraction of cores available",
            rich_help_panel="Tournament Control",
        ),
    ] = 1,
    python_class_identifier: Annotated[
        str,
        typer.Option(
            help="The identifier identifying types in saved files.",
            rich_help_panel="Tournament Control",
        ),
    ] = TYPE_IDENTIFIER,
):
    t = Tournament.load(path, python_class_identifier=python_class_identifier)
    do_run(t, nreps, path.parent, verbose, dry, njobs)


if __name__ == "__main__":
    app()
