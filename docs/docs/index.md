# ANL 2025 Documentation

This repository is the official platform for running ANAC Automated Negotiation Leagues for year 2025.
This package is a thin-wrapper around the [NegMAS](https://negmas.readthedocs.io) library for automated negotiation. Its main goal is to provide the following functionalities:

1. A method for generating scenarios to run tournaments in the same settings as in the ANL competition. These functions are always called `anl2025_tournament` for year `2025`.
1. A command line interface (CLI) for running tournaments called `anl`.
1. A place to hold the official implementation of every strategy submitted to the ANL competition after each year. These can be found in the module `anl.anl2025.negotiator` for year `2025`.

The official website for the ANL competition is: [https://anac.cs.brown.edu/anl](https://anac.cs.brown.edu/anl)

## Challenge ANL 2025
The Automated Negotiating Agent Competition (ANAC) is an international tournament that has been running since 2010 to bring together researchers from the negotiation community. In the Automated Negotiation League (ANL), participants explore the strategies and difficulties in creating efficient agents whose primary purpose is to negotiate with other agent's strategies. Every year, the league presents a different challenge for the participating agents. This year's challenge is:

**Design and build a negotiation agent for sequential multi-deal negotiation. The agent encounters multiple opponents in sequence and is rewarded for the specific combination of the deals made in each negotiation.**

Steps to be taken from here:

1. Check out the call for participation [here](https://drive.google.com/drive/folders/1xc5qt7XlZQQv6q1NVnu2vP6Ou-YOQUms?usp=drive_link).
1. Install the ANL2025 package (see installation guide).
1. Download the official test scenarios, code for tutorials and the template agent code from [here](https://drive.google.com/drive/folders/1xc5qt7XlZQQv6q1NVnu2vP6Ou-YOQUms?usp=drive_link).
1. Do the tutorials to get started!

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
anl: 0.1.4 (NegMAS: 0.11.3)
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
