from rich.table import Table
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
from anl2025.runner import DEFAULT_METHOD, RunParams, run_session


app = typer.Typer()
tournament = typer.Typer()

app.add_typer(
    tournament, name="tournament", help="Creates, manages and runs tournaments"
)


def do_run(
    t: Tournament, nreps: int, output: Path, verbose: bool, dry: bool, njobs: int
):
    results = t.run(nreps, output, verbose, dry, n_jobs=njobs if njobs >= 0 else None)
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


@app.command(name="run", help="Runs a multi-deal negotiation session")
def run_multideal(
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
        "RandomNegotiator",
        "Shochan2025",
        "AgentRenting2025",
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
    results = run_session(
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
    side_ufuns = cfun.side_ufuns(len(results.edges))
    for i, (e, m, u) in enumerate(
        zip(results.edges, results.mechanisms, side_ufuns, strict=True)  # type: ignore
    ):
        print(
            f"{i:02}: Mechanism {m.name} between ({m.negotiator_ids}) ended in {m.current_step} ({m.relative_time:4.3}) with {m.agreement}: "
            f"Edge Utility = {e.ufun(m.agreement) if e.ufun else 'unknown'}, "
            f"Side Utility = {u(m.agreement) if u else 'unknown'}"
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


@tournament.command()
def make(
    scenarios: Annotated[
        int,
        typer.Option(help="Number of Scenarios", rich_help_panel="Tournament Control"),
    ] = 3,
    competitor: Annotated[
        list[str],
        typer.Option(
            help="Competitor types",
            rich_help_panel="Edges",
        ),
    ] = [
        "Boulware2025",
        "RandomNegotiator",
        "Shochan2025",
        "AgentRenting2025",
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
    ] = -1,
):
    if name == "auto":
        name = unique_name("t", sep="")
    if name:
        output = output / name

    def full_name(x: str) -> str:
        if x in anl2025.negotiator.__all__:
            return f"anl2025.negotiator.{x}"
        return x

    competitors = tuple(full_name(_) for _ in competitor)
    t = Tournament.from_generated_scenarios(
        competitors=(competitors),
        run_params=RunParams(nsteps, keep_order, share_ufuns, atomic, method),
        n_scenarios=scenarios,
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
    t.save(path)
    print(f"Tournament information is saved in {path}. Use `run` to run it")
    do_run(t, nreps, output, verbose, dry, njobs)


@tournament.command()
def run(
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
    output: Annotated[
        Path,
        typer.Option(
            help="A directory to store the negotiation logs and plots",
            rich_help_panel="Output",
        ),
    ] = Path.home() / "negmas" / "anl2025" / "tournament",
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
    ] = -1,
):
    t = Tournament.load(path)
    do_run(t, nreps, output, verbose, dry, njobs)


if __name__ == "__main__":
    app()
