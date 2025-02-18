# ANL 2025 Documentation

This repository is the official platform for running ANAC Automated Negotiation Leagues (starting 2025). It will contain a module
called `anlXXXX` for the competition run in year XXXX. For example anl2025 will contain all files related to the
2025's version of the competition.

This package is a thin-wrapper around the [NegMAS](https://negmas.readthedocs.io) library for automated negotiation. Its main goal is to provide the following functionalities:

1. A method for generating scenarios to run tournaments in the same settings as in the ANL competition. These functions are always called `anl20XX_tournament` for year `20XX`.
1. A CLI for running tournaments called `anl`.
<!-- 1. A visualizer for inspecting tournament results and negotiations in details called `anlv`. -->
1. A place to hold the official implementation of every strategy submitted to the ANL competition after each year. These can be found in the module `anl.anl20XX.negotiators` for year `20XX`.

The official website for the ANL competition is: [https://scml.cs.brown.edu/anl](https://scml.cs.brown.edu/anl)

## Quick start

```bash
pip install anl2025
```

You can also install the in-development version with::

```bash
pip install git+https://github.com/yasserfarouk/anl2025tmp.git
```

## CLI

After installation, you can try running a tournament using the CLI:

```bash
anl tournament run --generate=5
```

To find all the parameters you can customize for running tournaments run:

```bash
anl tournament run --help
```

You can run the following command to check the versions of ANL and NegMAS on your machine:

```bash
anl2025 version
```

You should get at least these versions:

```bash
anl: 0.1.5 (NegMAS: 0.10.9)
```


## Contributing

!!! info
This is not required to participate in the ANL competition

If you would like to contribute to ANL, please clone [the repo](https://github.com/autoneg/anl2025), then run:

```python
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install -r docs/requirements.txt
python -m pip install -e .
```

You can then submit Pull Requests which will be carefully reviewed.

If you have an issue, please report it [here](https://github.com/autoneg/anl2025/issues).
If you have something to discuss, please report it [here](https://github.com/autoneg/anl2025/discussions).
