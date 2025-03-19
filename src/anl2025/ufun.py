from abc import ABC, abstractmethod
from copy import deepcopy
from attrs import define, field
from collections import defaultdict
from typing import Any, Iterable, Protocol
from negmas.inout import get_full_type_name
from negmas.outcomes.optional_issue import OptionalIssue
from negmas.serialization import serialize, deserialize
from collections.abc import Sequence, Callable
from enum import Enum
from typing import TypeVar
from negmas.preferences import UtilityFunction, BaseUtilityFunction
from negmas.outcomes import (
    CartesianOutcomeSpace,
    EnumeratingOutcomeSpace,
    Outcome,
    OutcomeSpace,
    make_os,
    make_issue,
)
from negmas.warnings import warn
import numpy as np
from anl2025.common import TYPE_IDENTIFIER

TRACE_COLS = (
    "time",
    "relative_time",
    "step",
    "negotiator",
    "offer",
    "responses",
    "state",
)

__all__ = [
    "CenterUFunCategory",
    "CenterUFun",
    "FlatCenterUFun",
    "LambdaCenterUFun",
    "LambdaUtilityFunction",
    "MaxCenterUFun",
    "LinearCombinationCenterUFun",
    "MeanSMCenterUFun",
    "SideUFun",
    "SingleAgreementSideUFunMixin",
    "UtilityCombiningCenterUFun",
    "FlatteningCombiner",
    "HierarchicalCombiner",
    "DefaultCombiner",
    "OSCombiner",
    "convert_to_center_ufun",
    "make_side_ufun",
]

TUFun = TypeVar("TUFun", bound=UtilityFunction)
CenterEvaluator = Callable[[tuple[Outcome | None, ...] | None], float]
EdgeEvaluator = Callable[[Outcome | None], float]


class CenterUFunCategory(Enum):
    """The type of the center utility function.

    Remarks:
        - `Global`  means that side ufuns are not defined. Note that
          the `side_ufuns` function may still return `SideUfun` objects
          but these will be the global ufun in case all other negotiation
          threads end in disagreement.
        - `Local` means that side ufuns are defined.

    """

    Global = 0
    Local = 1


# def flatten_outcome_spaces(
#     outcome_spaces: tuple[OutcomeSpace, ...],
#     add_index_to_issue_names: bool = False,
#     add_os_to_issue_name: bool = False,
# ) -> CartesianOutcomeSpace:
#     """Generates a single outcome-space which is the Cartesian product of input outcome_spaces."""
#
#     def _name(i: int, os_name: str | None, issue_name: str | None) -> str:
#         x = issue_name if issue_name else ""
#         if add_os_to_issue_name and os_name:
#             x = f"{os_name}:{x}"
#         if add_index_to_issue_names:
#             x = f"{x}:{i+1}"
#         return x
#
#     values, names, nissues = [], [], []
#     for i, os in enumerate(outcome_spaces):
#         if isinstance(os, EnumeratingOutcomeSpace):
#             values.append(list(os.enumerate()))
#             names.append(_name(i, "", os.name))
#             nissues.append(1)
#         elif isinstance(os, CartesianOutcomeSpace):
#             for issue in os.issues:
#                 values.append(issue.values)
#                 names.append(_name(i, os.name, issue.name))
#             nissues.append(len(os.issues))
#         else:
#             raise TypeError(
#                 f"Outcome space of type {type(os)} cannot be combined with other outcome-spaces"
#             )
#     return make_os([make_issue(v, n) for v, n in zip(values, names)])


def unflatten_outcome_space(
    outcome_space: CartesianOutcomeSpace, nissues: tuple[int, ...] | list[int]
) -> tuple[CartesianOutcomeSpace, ...]:
    """Distributes the issues of an outcome-space into a tuple of outcome-spaces."""
    nissues = list(nissues)
    beg = [0] + nissues[:-1]
    end = nissues
    return tuple(
        make_os(outcome_space.issues[i:j], name=f"OS{i}")
        for i, j in zip(beg, end, strict=True)
    )


class OSCombiner(Protocol):
    def __init__(self, outcome_spaces: tuple[OutcomeSpace, ...]) -> None: ...

    def combined_space(self) -> CartesianOutcomeSpace: ...

    def separated_spaces(self) -> tuple[OutcomeSpace, ...]: ...

    def combined_outcome(
        self, outcomes: tuple[Outcome | None, ...] | Outcome | None
    ) -> Outcome | None: ...

    def separated_outcomes(
        self, outcome: Outcome | None
    ) -> tuple[Outcome | None, ...] | None: ...


def _calc_n_issues(outcome_spaces: tuple[OutcomeSpace, ...]):
    return tuple(
        1 if isinstance(_, EnumeratingOutcomeSpace) else len(_.issues)  # type: ignore
        for _ in outcome_spaces
    )


def is_separated(x: Outcome | tuple[Outcome | None, ...]) -> bool:
    if x is None:
        return True
    if all(_ is None for _ in x):
        return True
    types = set(type(_) for _ in x if _ is not None)
    if all(issubclass(_, tuple) for _ in types):
        return True
    return False


def is_combined(x: Outcome | tuple[Outcome | None, ...]) -> bool:
    if x is None:
        return True
    if any(_ is None for _ in x):
        return False
    types = set(type(_) for _ in x if _ is not None)
    if all(issubclass(_, tuple) for _ in types):
        return False
    return True


@define
class FlatteningCombiner(OSCombiner):
    outcome_spaces: tuple[OutcomeSpace, ...]
    issue_name_format: str = "%osname%:%issuename%"
    combined_name: str = "combined"
    outcome_space: CartesianOutcomeSpace = field(init=False, default=None)

    def __attrs_post_init__(self):
        def _name(i: int, os_name: str | None, issue_name: str | None) -> str:
            x = (
                self.issue_name_format.replace(
                    "%issuename%", issue_name if issue_name is not None else "issue"
                )
                .replace("%osname%", os_name if os_name is not None else "os")
                .replace("%index%", str(i + 1))
            )
            if not x:
                x = "issue"
            return x

        values, names = [], []
        for i, os in enumerate(self.outcome_spaces):
            if isinstance(os, EnumeratingOutcomeSpace):
                values.append(list(os.enumerate()))
                names.append(_name(i, "", os.name))
            elif isinstance(os, CartesianOutcomeSpace):
                for issue in os.issues:
                    values.append(issue.values)
                    names.append(_name(i, os.name, issue.name))
            else:
                raise TypeError(
                    f"Outcome space of type {type(os)} cannot be combined with other outcome-spaces"
                )
        self.outcome_space = make_os(
            [make_issue(v, n) for v, n in zip(values, names)], name=self.combined_name
        )

    def separated_spaces(self) -> tuple[OutcomeSpace, ...]:
        return self.outcome_spaces

    def combined_space(self) -> CartesianOutcomeSpace:
        return self.outcome_space

    def combined_outcome(
        self, outcomes: tuple[Outcome | None, ...] | Outcome | None
    ) -> Outcome | None:
        if not outcomes:
            return outcomes
        if is_combined(outcomes):
            return outcomes
        values = []
        for x, os in zip(outcomes, self.outcome_spaces, strict=True):
            if x is None:
                values += [None] * len(os.issues)  # type: ignore
                continue
            values += list(x)
        return tuple(values)

    def separated_outcomes(
        self, outcome: Outcome | None
    ) -> tuple[Outcome | None, ...] | None:
        if not outcome:
            return outcome
        if is_separated(outcome):
            return outcome
        nxt = 0
        vals = []
        for os in self.outcome_spaces:
            n = len(os.issues)  # type: ignore
            x = outcome[nxt : nxt + n]
            if all(_ is None for _ in x):
                vals.append(None)
            else:
                vals.append(x)
            nxt += n
        return tuple(vals)


@define
class HierarchicalCombiner(OSCombiner):
    outcome_spaces: tuple[OutcomeSpace, ...]
    issue_name_format: str = "agreement%index%"
    combined_name: str = "combined"
    outcome_space: CartesianOutcomeSpace = field(init=False, default=None)

    def __attrs_post_init__(self):
        def _name(i: int, os_name: str | None) -> str:
            x = self.issue_name_format.replace(
                "%osname%", os_name if os_name is not None else "os"
            ).replace("%index%", str(i + 1))
            if not x:
                x = "agreement"
            return x

        values, names = [], []
        for i, os in enumerate(self.outcome_spaces):
            values.append(list(os.enumerate()))  # type: ignore
            names.append(_name(i, os.name))  # type: ignore
        self.outcome_space = make_os(  # type: ignore
            [OptionalIssue(make_issue(v, n), n) for v, n in zip(values, names)],
            name=self.combined_name,
        )

    def separated_spaces(self) -> tuple[OutcomeSpace, ...]:
        return self.outcome_spaces

    def combined_space(self) -> CartesianOutcomeSpace:
        return self.outcome_space

    def combined_outcome(
        self, outcomes: tuple[Outcome | None, ...] | Outcome | None
    ) -> Outcome | None:
        return outcomes

    def separated_outcomes(
        self, outcome: Outcome | None
    ) -> tuple[Outcome | None, ...] | None:
        return outcome


DefaultCombiner = HierarchicalCombiner


def convert_to_center_ufun(
    ufun: UtilityFunction,
    nissues: tuple[int],
    combiner_type: type[OSCombiner] = DefaultCombiner,
    side_evaluators: list[EdgeEvaluator] | None = None,
) -> "CenterUFun":
    """Creates a center ufun from any standard ufun with ufuns side ufuns"""
    assert ufun.outcome_space and isinstance(ufun.outcome_space, CartesianOutcomeSpace)
    evaluator = ufun
    if side_evaluators is not None:
        return LocalEvaluationCenterUFun(
            outcome_spaces=unflatten_outcome_space(ufun.outcome_space, nissues),
            evaluator=evaluator,
            side_evaluators=tuple(side_evaluators),
            combiner_type=combiner_type,
        )
    return LambdaCenterUFun(
        outcome_spaces=unflatten_outcome_space(ufun.outcome_space, nissues),
        evaluator=evaluator,
        combiner_type=combiner_type,
    )


class CenterUFun(UtilityFunction, ABC):
    """
    Base class of center utility functions.

    Remarks:
        - Can be constructed by either passing a single `outcome_space` and `n_edges` or a tuple of `outcome_spaces`
        - It's eval() method  receives a tuple of negotiation results and returns a float
    """

    def __init__(
        self,
        *args,
        outcome_spaces: tuple[CartesianOutcomeSpace, ...] = (),
        n_edges: int = 0,
        combiner_type: type[OSCombiner] = DefaultCombiner,
        expected_outcomes: tuple[Outcome | None, ...]
        | list[Outcome | None]
        | None = None,
        stationary: bool = True,
        stationary_sides: bool | None = None,
        side_ufuns: tuple[BaseUtilityFunction | None, ...] | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        if not outcome_spaces and self.outcome_space:
            outcome_spaces = tuple([self.outcome_space] * n_edges)
        self._combiner = combiner_type(outcome_spaces)
        self._outcome_spaces = self._combiner.separated_spaces()
        self.n_edges = len(outcome_spaces)
        self.stationary = stationary
        self.stationary_sides = (
            stationary_sides if stationary_sides is not None else stationary
        )
        self.__kwargs = dict(
            reserved_value=self.reserved_value,
            owner=self.owner,
            invalid_value=self._invalid_value,
            name=self.name,
            id=self.id,
        )
        self.__nissues = _calc_n_issues(self._outcome_spaces)
        try:
            self.outcome_space = self._combiner.combined_space()
        except Exception:
            warn("Failed to find the Cartesian product of input outcome spaces")
            self.outcome_space, self.__nissues = None, tuple()
        self._expected: list[Outcome | None] = (
            list(expected_outcomes)
            if expected_outcomes
            else ([None for _ in range(self.n_edges)])
        )

        if side_ufuns is None:
            ufuns = tuple(None for _ in range(self.n_edges))
        else:
            ufuns = tuple(deepcopy(_) for _ in side_ufuns)
        self._effective_side_ufuns = tuple(
            make_side_ufun(self, i, side) for i, side in enumerate(ufuns)
        )

    def is_stationary(self) -> bool:
        return self.stationary

    def set_expected_outcome(self, index: int, outcome: Outcome | None) -> None:
        # print(f"Setting expected outcome for {index} to {outcome}")
        self._expected[index] = outcome
        # print(f"{self._expected}")

    @property
    def outcome_spaces(self) -> tuple[OutcomeSpace, ...]:
        return self._outcome_spaces

    def eval_with_expected(self, offer: Outcome | None, use_expected=True) -> float:
        """Calculates the utility of a set of offers with control over whether or not to use stored expected outcomes."""
        outcomes = self._combiner.separated_outcomes(offer)
        if outcomes:
            if use_expected:
                outcomes = tuple(
                    outcome if outcome else expected
                    for outcome, expected in zip(outcomes, self._expected, strict=True)
                )
            if all(_ is None for _ in outcomes):
                outcomes = None
        if outcomes is None:
            return self.reserved_value
        return self.eval(outcomes)

    def __call__(self, offer: Outcome | None, use_expected=True) -> float:
        """Entry point to calculate the utility of a set of offers (called by the mechanism).

        Override to avoid using expected outcomes."""

        return self.eval_with_expected(offer, use_expected=use_expected)

    @abstractmethod
    def eval(self, offer: tuple[Outcome | None, ...] | Outcome | None) -> float:
        """
        Evaluates the utility of a given set of offers.

        Remarks:
            - Order matters: The order of outcomes in the offer is stable over all calls.
            - A missing offer is represented by `None`
        """

    @abstractmethod
    def ufun_type(self) -> CenterUFunCategory:
        """Returns the center ufun category.

        Currently, we have two categories (Global and Local). See `CenterUFunCategory` for
        their definitions.
        """
        ...

    def side_ufuns(self) -> tuple[BaseUtilityFunction | None, ...]:
        """Should return an independent ufun for each side negotiator of the center."""
        ufuns = self._effective_side_ufuns
        # Make sure that these side ufuns are connected to self
        for i, u in enumerate(ufuns):
            if id(u._center_ufun) == id(self):
                continue
            u._center_ufun = self
            u._index = i
            u._n_edges = self.n_edges
        return ufuns

    def to_dict(self, python_class_identifier=TYPE_IDENTIFIER) -> dict[str, Any]:
        return {
            python_class_identifier: get_full_type_name(type(self)),
            "outcome_spaces": serialize(
                self._outcome_spaces, python_class_identifier=python_class_identifier
            ),
            "name": self.name,
            "reserved_value": self.reserved_value,
        }

    @classmethod
    def from_dict(cls, d, python_class_identifier=TYPE_IDENTIFIER):
        d.pop(python_class_identifier, None)
        for f in ("outcome_spaces", "ufuns"):
            if f in d:
                d[f] = deserialize(
                    d[f], python_class_identifier=python_class_identifier
                )
        return cls(**d)
        # type_ = d.pop(python_class_identifier, cls)
        # # cls = get_class(type_) if isinstance(type_, str) else type_
        # return cls(**d)


class LambdaCenterUFun(CenterUFun):
    """
    A center utility function that implements an arbitrary evaluator
    """

    def __init__(self, *args, evaluator: CenterEvaluator, **kwargs):
        super().__init__(*args, **kwargs)
        self._evaluator = evaluator

    def eval(self, offer: tuple[Outcome | None, ...] | Outcome | None) -> float:
        return self._evaluator(self._combiner.separated_outcomes(offer))

    def ufun_type(self) -> CenterUFunCategory:
        return CenterUFunCategory.Global

    def to_dict(self, python_class_identifier=TYPE_IDENTIFIER) -> dict[str, Any]:
        return super().to_dict(python_class_identifier) | dict(
            evaluator=serialize(
                self._evaluator, python_class_identifier=python_class_identifier
            )
        )


class LambdaUtilityFunction(UtilityFunction):
    """A utility function that implements an arbitrary mapping"""

    def __init__(self, *args, evaluator: EdgeEvaluator, **kwargs):
        super().__init__(*args, **kwargs)
        self._evaluator = evaluator

    def __call__(self, offer: Outcome | None) -> float:
        return self._evaluator(offer)

    def eval(self, offer: Outcome) -> float:
        return self._evaluator(offer)

    def to_dict(self, python_class_identifier=TYPE_IDENTIFIER) -> dict[str, Any]:
        return super().to_dict(python_class_identifier) | dict(
            evaluator=serialize(
                self._evaluator, python_class_identifier=python_class_identifier
            )
        )


class SideUFun(BaseUtilityFunction):
    """
    Side ufun corresponding to the i's component of a center ufun.
    """

    def __init__(
        self,
        *args,
        center_ufun: CenterUFun,
        index: int,
        n_edges: int,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._center_ufun = center_ufun
        self._index = index
        self._n_edges = n_edges

    def is_stationary(self) -> bool:
        return self._center_ufun.stationary_sides

    def set_expected_outcome(
        self, outcome: Outcome | None, index: int | None = None
    ) -> None:
        if index is None:
            index = self._index
        self._center_ufun.set_expected_outcome(index, outcome)

    def eval(self, offer: Outcome | None) -> float:
        exp_outcome = [_ for _ in self._center_ufun._expected]
        offers = [_ for _ in self._center_ufun._expected]
        offers[self._index] = offer

        # For all offers that are after the current agent, set to None:
        for i in range(self._index + 1, self._n_edges):
            # if offers[i] is not None:
            # print(
            #     f"{self._index=}: {i} has a none None outcome ({offers[i]=})\n{offers=}"
            # )
            # raise AssertionError(
            #     f"{self._index=}: {i} has a none None outcome ({offers[i]=})\n{offers=}"
            # )
            self.set_expected_outcome(None, i)
            offers[i] = None
        u = self._center_ufun(tuple(offers))

        # restore expected_outcome:
        for i in range(self._index + 1, self._n_edges):
            self.set_expected_outcome(exp_outcome[i], i)

        return u


def make_side_ufun(
    center: CenterUFun, index: int, side: BaseUtilityFunction | None
) -> SideUFun:
    """Creates a side-ufun for the center at the given index."""
    if side is None:
        side_ufun = SideUFun(center_ufun=center, n_edges=center.n_edges, index=index)
        side_ufun.reserved_value = side_ufun.eval(None)  # type: ignore
    elif isinstance(side, SideUFun):
        side_ufun = side
        side_ufun._center_ufun = center
        side_ufun._index = index
        side_ufun._n_edges = center.n_edges
        side_ufun.reserved_value = side_ufun.eval(None)  # type: ignore
    else:
        side_ufun = SideUFunAdapter(
            center_ufun=center,
            n_edges=center.n_edges,
            index=index,
            base_ufun=side,
            name=side.name,
            id=side.id,
            outcome_space=side.outcome_space,
            reserved_value=side.reserved_value,
            invalid_value=side._invalid_value,
            owner=side.owner,
            type_name=side.type_name,
            reserved_outcome=side.reserved_outcome,
        )
    return side_ufun


class LocalEvaluationCenterUFun(CenterUFun):
    """
    A center utility function that implements an arbitrary evaluator applied to side evaluators
    """

    def __init__(
        self,
        *args,
        evaluator: CenterEvaluator,
        side_evaluators: EdgeEvaluator | Sequence[EdgeEvaluator] | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._evaluator = evaluator
        if not side_evaluators:
            self._side_ufuns = None
            return
        if not isinstance(side_evaluators, Sequence):
            evaluators = [side_evaluators] * len(self._outcome_spaces)
        else:
            evaluators = list(side_evaluators)
        sides: list[LambdaUtilityFunction] = []
        for e, o in zip(evaluators, self._outcome_spaces):
            sides.append(LambdaUtilityFunction(outcome_space=o, evaluator=e))
        self._side_ufuns: tuple[LambdaUtilityFunction, ...] | None = tuple(sides)

    def to_dict(self, python_class_identifier=TYPE_IDENTIFIER) -> dict[str, Any]:
        return super().to_dict(python_class_identifier) | dict(
            side_evaluators=[_._evaluator for _ in self._side_ufuns]
            if self._side_ufuns
            else None,
            evaluator=self._evaluator,
        )

    def eval(self, offer: tuple[Outcome | None, ...] | Outcome | None) -> float:
        return self._evaluator(self._combiner.separated_outcomes(offer))

    def ufun_type(self) -> CenterUFunCategory:
        return CenterUFunCategory.Local


class FlatCenterUFun(UtilityFunction):
    """
    A flattened version of a center ufun.

    A normal CenterUFun takes outcomes as a tuple of outcomes (one for each edge).
    A flattened version of the same ufun takes input as just a single outcome containing
    a concatenation of the outcomes in all edges.

    Example:

        ```python
        x = CenterUFun(...)
        y = x.flatten()

        x(((1, 0.5), (3, true), (7,))) == y((1, 0.5, 3, true, 7))
        ```
    """

    def __init__(
        self, *args, base_ufun: CenterUFun, nissues: tuple[int, ...], **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.__base = base_ufun
        self.__nissues = list(nissues)

    def _unflatten(
        self, outcome: Outcome | tuple[Outcome | None, ...] | None
    ) -> tuple[Outcome | None, ...] | None:
        if outcome is None:
            return None

        if isinstance(outcome, tuple) and isinstance(outcome[0], Outcome):
            return outcome

        beg = [0] + self.__nissues[:-1]
        end = self.__nissues
        outcomes = []
        for i, j in zip(beg, end, strict=True):
            x = outcome[i:j]
            if all(_ is None for _ in x):
                outcomes.append(None)
            else:
                outcomes.append(tuple(x))
        return tuple(outcomes)

    def eval(self, offer: Outcome | tuple[Outcome | None] | None) -> float:
        return self.__base.eval(self._unflatten(offer))


class UtilityCombiningCenterUFun(CenterUFun):
    """
    A center ufun with a side-ufun defined for each thread.

    The utility of the center is a function of the ufuns of the edges.
    """

    def __init__(self, *args, side_ufuns: tuple[BaseUtilityFunction, ...], **kwargs):
        super().__init__(*args, **kwargs)
        self.ufuns = tuple(deepcopy(_) for _ in side_ufuns)
        # This is already done in CenterUFun now
        # self._effective_side_ufuns = tuple(
        #     make_side_ufun(self, i, side) for i, side in enumerate(self.ufuns)
        # )

    @abstractmethod
    def combine(self, values: Sequence[float]) -> float:
        """Combines the utilities of all negotiation  threads into a single value"""

    def eval(self, offer: tuple[Outcome | None, ...] | Outcome | None) -> float:
        offer = self._combiner.separated_outcomes(offer)
        if not offer:
            return self.reserved_value
        return self.combine(tuple(float(u(_)) for u, _ in zip(self.ufuns, offer)))

    def ufun_type(self) -> CenterUFunCategory:
        return CenterUFunCategory.Local

    def to_dict(self, python_class_identifier=TYPE_IDENTIFIER) -> dict[str, Any]:
        return super().to_dict(python_class_identifier) | {
            "side_ufuns": serialize(
                self.ufuns, python_class_identifier=python_class_identifier
            ),
            python_class_identifier: get_full_type_name(type(self)),
        }


class MaxCenterUFun(UtilityCombiningCenterUFun):
    """
    The max center ufun.

    The utility of the center is the maximum of the utilities it got in each negotiation (called side utilities)
    """

    def set_expected_outcome(self, index: int, outcome: Outcome | None) -> None:
        # sets the reserved value of all sides
        super().set_expected_outcome(index, outcome)
        r = None
        try:
            set_ufun = self._effective_side_ufuns[index]
        except Exception:
            return

        if isinstance(set_ufun, SideUFunAdapter):
            r = float(set_ufun._base_ufun(outcome))
        elif isinstance(set_ufun, SideUFun):
            return
        if r is None:
            return
        for i, side in enumerate(self._effective_side_ufuns):
            if side is None or i == index:
                continue
            side.reserved_value = max(side.reserved_value, r)
            if isinstance(side, SideUFunAdapter):
                side._base_ufun.reserved_value = max(side._base_ufun.reserved_value, r)

    def combine(self, values: Sequence[float]) -> float:
        return max(values)


class LinearCombinationCenterUFun(UtilityCombiningCenterUFun):
    """
    Linear combination of the side utility values

    The utility of the center is the maximum of the utilities it got in each negotiation (called side utilities)
    """

    def __init__(self, *args, weights: tuple[float, ...] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(weights, Iterable):
            s = sum(weights)
            if s:
                weights = tuple(_ / s for _ in weights)
        self._weights = weights

    def combine(self, values: Sequence[float]) -> float:
        if self._weights is None:
            self._weights = np.random.rand(len(values))
            s = self._weights.sum()
            self._weights = tuple((self._weights / s).tolist())
        return sum(a * b for a, b in zip(values, self._weights, strict=True))


class SideUFunAdapter(SideUFun):
    """Adapts any ufun to be usable as a side-ufun"""

    def __init__(
        self,
        *args,
        base_ufun: BaseUtilityFunction,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._base_ufun = base_ufun

    def to_stationary(self, *args, **kwargs):
        return self._base_ufun.to_stationary(*args, **kwargs)

    def extreme_outcomes(self, *args, **kwargs):
        return self._base_ufun.extreme_outcomes(*args, **kwargs)

    def minmax(self, *args, **kwargs):
        return self._base_ufun.minmax(*args, **kwargs)

    def eval_normalized(self, *args, **kwargs):
        return self._base_ufun.eval_normalized(*args, **kwargs)

    def invert(self, *args, **kwargs):
        return self._base_ufun.invert(*args, **kwargs)

    def scale_by(self, *args, **kwargs):
        return self._base_ufun.scale_by(*args, **kwargs)

    def scale_min_for(self, *args, **kwargs):
        return self._base_ufun.scale_min_for(*args, **kwargs)

    def scale_min(self, *args, **kwargs):
        return self._base_ufun.scale_min(*args, **kwargs)

    def scale_max(self, *args, **kwargs):
        return self._base_ufun.scale_max(*args, **kwargs)

    def normalize_for(self, *args, **kwargs):
        return self._base_ufun.normalize_for(*args, **kwargs)

    def normalize(self, *args, **kwargs):
        return self._base_ufun.normalize(*args, **kwargs)

    def shift_by(self, *args, **kwargs):
        return self._base_ufun.shift_by(*args, **kwargs)

    def shift_min_for(self, *args, **kwargs):
        return self._base_ufun.shift_min_for(*args, **kwargs)

    def shift_max_for(self, *args, **kwargs):
        return self._base_ufun.shift_max_for(*args, **kwargs)

    def argrank_with_weights(self, *args, **kwargs):
        return self._base_ufun.argrank_with_weights(*args, **kwargs)

    def argrank(self, *args, **kwargs):
        return self._base_ufun.argrank(*args, **kwargs)

    def rank_with_weights(self, *args, **kwargs):
        return self._base_ufun.rank_with_weights(*args, **kwargs)

    def rank(self, *args, **kwargs):
        return self._base_ufun.rank(*args, **kwargs)

    def eu(self, *args, **kwargs):
        return self._base_ufun.eu(*args, **kwargs)

    def to_dict(self, *args, **kwargs):
        return self._base_ufun.to_dict(*args, **kwargs)

    def sample_outcome_with_utility(self, *args, **kwargs):
        return self._base_ufun.sample_outcome_with_utility(*args, **kwargs)

    def to_xml_str(self, *args, **kwargs):
        return self._base_ufun.to_xml_str(*args, **kwargs)

    def to_genius(self, *args, **kwargs):
        return self._base_ufun.to_genius(*args, **kwargs)

    def difference_prob(self, *args, **kwargs):
        return self._base_ufun.difference_prob(*args, **kwargs)

    def is_not_worse(self, *args, **kwargs):
        return self._base_ufun.is_not_worse(*args, **kwargs)

    def difference(self, *args, **kwargs):
        return self._base_ufun.difference(*args, **kwargs)

    def max(self):
        return self._base_ufun.max()

    def min(self):
        return self._base_ufun.min()

    def best(self):
        return self._base_ufun.best()

    def worst(self):
        return self._base_ufun.worst()

    def is_volatile(self):
        return self._base_ufun.is_volatile()

    def is_session_dependent(self):
        return self._base_ufun.is_session_dependent()

    def is_state_dependent(self):
        return self._base_ufun.is_state_dependent()

    def scale_max_for(self, *args, **kwargs):
        return self._base_ufun.scale_max_for(*args, **kwargs)

    def to_crisp(self):
        return self._base_ufun.to_crisp()

    def to_prob(self):
        return self._base_ufun.to_prob()

    @property
    def reserved_distribution(self):
        return self._base_ufun.reserved_distribution

    def is_stationary(self):
        return self._base_ufun.is_stationary()

    def changes(self):
        return self._base_ufun.changes()

    def reset_changes(self) -> None:
        return self._base_ufun.reset_changes()

    @property
    def base_type(self) -> str:
        return self._base_ufun.base_type

    def is_better(self, first: Outcome | None, second: Outcome | None) -> bool:
        return self._base_ufun.is_better(first, second)

    def is_equivalent(self, first: Outcome | None, second: Outcome | None) -> bool:
        return self._base_ufun.is_equivalent(first, second)

    def is_not_better(self, first: Outcome | None, second: Outcome | None) -> bool:
        return self._base_ufun.is_not_better(first, second)

    def is_worse(self, first: Outcome | None, second: Outcome | None) -> bool:
        return self._base_ufun.is_worse(first, second)

    @property
    def type(self) -> str:
        return self._base_ufun.type


class SingleAgreementSideUFunMixin:
    """Can be mixed with any CenterUFun that is not a combining ufun to create side_ufuns that assume failure on all other negotiations.

    See Also:
        `MeanSMCenterUFun`
    """

    # def side_ufuns(self) -> tuple[BaseUtilityFunction, ...]:
    #     """Should return an independent ufun for each side negotiator of the center"""
    #     return tuple(
    #         SideUFun(center_ufun=self, n_edges=self.n_edges, index=i)  # type: ignore
    #         for i in range(self.n_edges)  # type: ignore
    #     )

    def ufun_type(self) -> CenterUFunCategory:
        return CenterUFunCategory.Local


class MeanSMCenterUFun(SingleAgreementSideUFunMixin, CenterUFun):
    """A ufun that just  returns the average mean+std dev. in each issue of the agreements as the utility value"""

    def eval(self, offer: tuple[Outcome | None, ...] | Outcome | None) -> float:
        offer = self._combiner.separated_outcomes(offer)
        if not offer:
            return 0.0
        n_edges = len(offer)
        if n_edges < 2:
            return 0.1
        vals = defaultdict(lambda: [0.0] * n_edges)
        for e, outcome in enumerate(offer):
            if not outcome:
                continue
            for i, v in enumerate(outcome):
                try:
                    vals[e][i] = float(v[1:])
                except Exception:
                    pass

        return float(sum(np.mean(x) + np.std(x) for x in vals.values())) / len(vals)
