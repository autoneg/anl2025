3 threads
- (3, 4)     => DiscreteCartesianOutcomeSpace(ContiguousIssue(7), ConiguousIssue(5))
- None       => DiscreteCartesianOutcomeSpace(ContiguousIssue(7), ConiguousIssue(5))
- ("xyz",)   => DiscreteCartesianOutcomeSpace(CategoricalIssue(["ab", "xyz"]), )


HierarcchalCombiner

outcome_space:

DiscreteCartesianOutcomeSpace(
    OptionalIssue(CategoricalIssue([(0,0), (0,1), ..... (6,4)])),
    OptionalIssue(CategoricalIssue([(0,0), (0,1), ..... (6,4)])),
    OptionalIssue(CategoricalIssue([("ab",), ("xyz",)])),
)

filtered_outcome_space =  deepcopy(self.outcome_space)
filtered_outcome_space.issues[1] = CategoricalIssue([(0,1)])
filtered_outcome_space.extreme_outcomes()
