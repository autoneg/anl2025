from pathlib import Path
from typing import Annotated
import typer
from rich import print

from anl2025.ufun import CenterUFun
from .runner import run_session


def main(
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
    center_reserved_value: Annotated[
        float,
        typer.Option(
            help="Number of Edges (the M side of the 1-M negotiation session)",
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
        center_reserved_value=center_reserved_value,
        nedges=nedges,
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
        method="serial",
    )

    center_ufun = results.center.ufun
    assert isinstance(center_ufun, CenterUFun)
    side_ufuns = center_ufun.side_ufuns(len(results.edges))
    for i, (e, m, u) in enumerate(
        zip(results.edges, results.mechanisms, side_ufuns, strict=True)  # type: ignore
    ):
        print(
            f"{i:02}: Mechanism {m.name} between ({m.negotiator_ids}) ended in {m.current_step} ({m.relative_time:4.3}) with {m.agreement}: "
            f"Edge Utility = {e.ufun(m.agreement) if e.ufun else 'unknown'}, "
            f"Side Utility = {u(m.agreement) if u else 'unknown'}"
        )
    print(f"Center Utility: {results.center_utility}")


if __name__ == "__main__":
    typer.run(main)
