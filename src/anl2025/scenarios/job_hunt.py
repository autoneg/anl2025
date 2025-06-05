from negmas.outcomes import make_os, make_issue, DiscreteCartesianOutcomeSpace
from negmas.helpers import unique_name
from anl2025.ufun import MaxCenterUFun
from anl2025.scenario import MultidealScenario
from negmas.preferences.generators import generate_ufuns_for

__all__ = ["make_job_hunt_scenario"]


def make_job_hunt_scenario(
    n_employers: int = 4,
    work_days: tuple[int, int] | int = 6,
    salary: tuple[int, int] | list[int] = [100, 150, 200, 250, 300],
    public_graph: bool = True,
    employer_names: list[str] | None = None,
    employee_name: str = "Employee",
    name: str | None = None,
) -> MultidealScenario:
    """Creates a job hunt scenario with multiple employers and a single employee.

    Args:
        n_employers: Number of employers (edges)
        work_days: Number of work days (issue) or a range of values for work days
        salary: Salary values (issue) or a list of possible salary values
        public_graph: Makes the graph public, i.e., edges know the outcome space and number of edges
        employer_names: Employer names. If not given, we will use employer01, employer02, etc.
        employee_name: Employee name (the center of the scenario)
        name: Name of the scenario. If not given, it will be generated automatically and will start with "job-hunt".

    Returns:
        A MultidealScenario instance representing the job hunt scenario.
    """
    if employer_names is None:
        employer_names = [f"employer{_ + 1:02}" for _ in range(n_employers)]
    os = make_os(
        [make_issue(work_days, name="days"), make_issue(salary, name="salary")],
        name="JobHunt",
    )
    assert isinstance(os, DiscreteCartesianOutcomeSpace)
    ufun_pairs = [
        generate_ufuns_for(os, ufun_names=(f"with_{ename}", f"{ename}"))
        for ename in employer_names
    ]
    side_ufuns = tuple(_[0] for _ in ufun_pairs)
    edge_ufuns = tuple(_[1] for _ in ufun_pairs)
    center_ufun = MaxCenterUFun(
        side_ufuns=side_ufuns,
        n_edges=n_employers,
        outcome_space=os,
        reserved_value=0.0,
        name=employee_name,
    )

    return MultidealScenario(
        center_ufun,
        edge_ufuns,
        side_ufuns=side_ufuns,
        public_graph=public_graph,
        name=name if name else unique_name("job-hunt", add_time=False, sep="_"),
    )
