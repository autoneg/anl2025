# Preparing Development Environment

To participate in [ANL2025 2025](https://scml.cs.brown.edu/anl), you need to prepare a local development environment in your machine, download the [skeleton](https://autoneg.github.io/files/anl2025/anl2025.zip), and start hacking. This section of the documentation describes **two** ways to do that.


This is the recommended method. It requires you to use an installation of python *3.11* or later on your machine.

## 0. Installing Python
If -- for some reason -- you do not have python installed in your machine, start by installing it from [python.org](https://www.python.org/downloads/). You can also use any other method to install python 3.11 or later.

## 1. Creating and activating a virtual environment

!!! info
    optional but **highly** recommended

As always recommended, you should create a virtual environment for your development. You can use your IDE to do that or simply run the following command:
```bash
python -m venv .venv
```
You should always activate your virtual environment using:

=== "Windows"

    ``` source
    "venv\Scripts\activate"
    ```

=== "Linux/MacOS"

    ``` bash
    source .venv/bin/activate
    ```

Of course, you can use any other method for creating your virtual environment (e.g. [anaconda](https://www.anaconda.com), [hatch](https://github.com/pypa/hatch), [poetry](https://python-poetry.org), [pyenv](https://github.com/pyenv/pyenv), [virtualenv](https://virtualenv.pypa.io/en/latest/) or any similar method). Whatever method you use, it is highly recommended not to install packages (anl2025 or otherwise) directly on your base python system.

## 2. Installing the ANL2025 package
The second step is to install the `anl2025` package using:

```bash
python -m pip install anl2025
```

You can run the following command to check the versions of ANL and NegMAS on your machine:

```bash
anl2025 version
```

You should get at least these versions:

```bash
anl: 0.1.5 (NegMAS: 0.10.9)
```

For a test tournament, you can use the command line interface (CLI):

```bash
anl tournament run --generate=5
```

If no errors are shown, you have successfully installed ANL! You can now start developing your agent.



## 3. Development

The next step is to download the template from [here](https://drive.google.com/drive/folders/1xc5qt7XlZQQv6q1NVnu2vP6Ou-YOQUms?usp=drive_link). Please familiarize yourself with the competition rules available at the [competition website](https://scml.cs.brown.edu/anl).
After downloading and unpacking the template, you should do the following steps:

1. Modify the name of the single class in `myagent.py` (currently called `NewNegotiator`) to a representative name for your agent. We will use `NewNegotiator` here. You should then implement your agent logic by modifying this class.
    - Remember to change the name of the agent in the last line of the file to match your new class name (`NewNegotiator`).
2. Start developing your agent as will be explained later in the [tutorial](https://autoneg.github.io/anl2025/tutorials/tutorial/).
3. You can use the following ways to test your agent:
    - Run the following command to test your agent from the root folder of the extracted skeleton:
      ```bash
      python -m myagent.myagent
      ```
    - You can also use your favorite IDE, and run the `myagent.py` file directly.
    - Use the `anl2025` command line utility from the root folder of the extracted skeleton:
      ```bash
      anl2025 tournament run --generate=5
      ```
      This method is more flexible as you can control all aspects of the tournament to run.
      Use `anl2025 tournament run --help`  to see all available options.

    - You can directly call `anl2025_tournament()` passing your agent as one of the competitors. This is the most flexible method and will be used in the tutorial.
Check out the tutorials for more details!

5. Submit your agent to the [official submission website](https://scml.cs.brown.edu/anl):
    - Remember to update the `Class Name` (`NewNegotiator` in our case) and `Agent Module` (`myagent.myagent` in our case) in the submission form on the  [competition website](https://scml.cs.brown.edu/anl) to your own name.
    - If you need any libraries that are not already provided by `anl2025`, please include them in the `Dependencies` in a semi-colon separated list when submitting your agent.

