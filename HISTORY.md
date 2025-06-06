# Change Log


## 0.1.6 (2025-06-06)
* bugfix: Incorrect center utility for Linear
* CLI: controlling fractions of generated scenarios. use --dinners/--target-quantity/--job-hunt/--others to control the fraction of each scenario type in the tournament. If any of these is given, the rest is considered zero.
* feature: naming scenarios by type
* feature: making tournament type mixture random
* feature: all types of scenarios in tournaments
## 0.1.5 (2025-05-30)


* bugfix: reporting partner exceptions
* bugfix: ensuring everyone runs center same n. times
* CLI: switching to weighted average scors
* Correcting exception reporting and more stats
  bugfix: exception text was always reported as partner exception!
  feature: We now save unweighted and weighted scores as well as the
  final-scores.
* feature: Adding error details and disabling normalization
* feature: Adding names to generated scenarios. make_multideal_scenario() now always adds a name for the scenario
* feature: Adding score normalization. run_session(), and Tournament.run() now take a normalize_scores parameter which defaults to True. If this is true, the scores of all sessions will be normalized before being saved to SesionInfo instances.
* feature: Adding JobHunt as an example scenario
* Documentation update

## 0.1.3 (2025-04-10)



- bugfix: adding example scenarios to distributed wheels
## 0.1.3 (2025-04-09)
- feature: Adding more information to tournament results
- bugfix: tournaments run with more competitors than edges
- docs: Correcting links to ANL2025Negotiator in tutorials
