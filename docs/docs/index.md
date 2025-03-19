# ANL 2025 Documentation

This repository is the official platform for running ANAC Automated Negotiation Leagues (starting 2025). It will contain a module
called `anlXXXX` for the competition run in year XXXX. For example anl2025 will contain all files related to the
2025's version of the competition.

This package is a thin-wrapper around the [NegMAS](https://negmas.readthedocs.io) library for automated negotiation. Its main goal is to provide the following functionalities:

1. A method for generating scenarios to run tournaments in the same settings as in the ANL competition. These functions are always called `anl20XX_tournament` for year `20XX`.
1. A command line interface (CLI) for running tournaments called `anl`.
<!-- 1. A visualizer for inspecting tournament results and negotiations in details called `anlv`. -->
1. A place to hold the official implementation of every strategy submitted to the ANL competition after each year. These can be found in the module `anl.anl20XX.negotiators` for year `20XX`.

The official website for the ANL competition is: [https://anac.cs.brown.edu/anl](https://anac.cs.brown.edu/anl)

## Challenge ANL 2025
The Automated Negotiating Agent Competition (ANAC) is an international tournament that has been running since 2010 to bring together researchers from the negotiation community. In the Automated Negotiation League (ANL), participants explore the strategies and difficulties in creating efficient agents whose primary purpose is to negotiate with other agent's strategies. Every year, the league presents a different challenge for the participating agents. This year's challenge is:

**Design and build a negotiation agent for sequential multi-deal negotiation. The agent encounters multiple opponents in sequence and is rewarded for the specific combination of the deals made in each negotiation.**

If you would like to read more on the challenge, check out the call for participation [here](https://drive.google.com/drive/folders/1xc5qt7XlZQQv6q1NVnu2vP6Ou-YOQUms?usp=drive_link).

## Quick start
*For a more detailed installation guide, please refer to the [Installation](https://autoneg.github.io/anl2025/install) page.*

```bash
pip install anl2025
```

You can also install the in-development version with::

```bash
pip install git+https://github.com/autoneg/anl2025.git
```

## Command Line Interface (CLI)

After installation, you can try running a tournament using the CLI:

```bash
anl tournament run --generate=5
```

To find all the parameters you can customize for running tournaments in the CLI, run:

```bash
anl tournament run --help
```

You can run the following command to check the versions of ANL and NegMAS on your machine:

```bash
anl2025 version
```

You should get at least these versions:

```bash
anl: 0.1.0 (NegMAS: 0.11.2)
```


## Contributing

!!! info
This is not required to participate in the ANL competition

If you would like to contribute to ANL, please clone [the repo](https://github.com/autoneg/anl2025), then run:

```bash
uv sync --all-extras --dev
```

You can then submit Pull Requests which will be carefully reviewed.

If you have an issue, please report it [here](https://github.com/autoneg/anl2025/issues).
If you have something to discuss, please report it [here](https://github.com/autoneg/anl2025/discussions).
