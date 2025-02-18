# ANL 2025 Reference
This package provides a wrapper around NegMAS functionality to generate and run tournaments a la ANL 2025 competition.
You mostly only need to use `anl2025_tournament` in your code. The other helpers are provided to allow for a finer control over the scenarios used.


## Negotiators (Agents)

The package provides few example negotiators. Of special importance is the `MiCRO` negotiator which provides a full implementation of a recently proposed behavioral strategy.
Other negotiators are just wrappers over negotiators provided by NegMAS.


::: anl2025.negotiator.ANL2025Negotiator

::: anl2025.negotiator.RandomNegotiator

::: anl2025.negotiator.Boulware2025

::: anl2025.negotiator.Shochan2025

::: anl2025.negotiator.AgentRenting2025

## Utility Functions


::: anl2025.ufun.CenterUFun

::: anl2025.ufun.FlatCenterUFun

::: anl2025.ufun.LambdaCenterUFun

::: anl2025.ufun.LambdaUtilityFunction

::: anl2025.ufun.MaxCenterUFun

::: anl2025.ufun.MeanSMCenterUFun

::: anl2025.ufun.SideUFun

::: anl2025.ufun.SingleAgreementSideUFunMixin

::: anl2025.ufun.UtilityCombiningCenterUFun

### Utility Function Helpers
::: anl2025.ufun.convert_to_center_ufun

::: anl2025.ufun.flatten_outcome_spaces

::: anl2025.ufun.unflatten_outcome_space

## Scenarios

::: anl2025.scenario.MultidealScenario

::: anl2025.scenario.make_multideal_scenario

## Sessions

::: anl2025.runner.run_session

::: anl2025.runner.run_generated_session

::: anl2025.runner.RunParams

::: anl2025.runner.SessionResults

## Tournaments

::: anl2025.tournament.Tournament





