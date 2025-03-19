# Developing a negotiator
*The corresponding code for the tutorials can be found in the [ANL2025 Drive](https://drive.google.com/drive/folders/1xc5qt7XlZQQv6q1NVnu2vP6Ou-YOQUms?usp=drive_link) or at the ANL2025 Github repository.*


The agents for the ANL competition are simple extensions of [NegMAS](https://autoneg.github.io/negmas) negotiators. As such, they can be developed using any approach used to develop negotiators in NegMAS.

To develop a negotiator, you need to inherit from the [ANL2025Negotiator](http://www.yasserm.com/anl2025/reference/#anl2025.negotiator.ANL2025Negotiator) class and implement the [`propose()`](http://www.yasserm.com/anl2025/reference/#anl2025.negotiator.ANL2025Negotiator.propose) and [`respond()`](http://www.yasserm.com/anl2025/reference/#anl2025.negotiator.ANL2025Negotiator.respond).


*If you want to start developing your negotiator right away, you can download a template agent from [here](https://drive.google.com/drive/folders/1xc5qt7XlZQQv6q1NVnu2vP6Ou-YOQUms?usp=drive_link) and tweak the code yourself. If you want more instructions, keep reading.*


### A random negotiator
Here is an example of a random negotiator that implements the `propose()` and `respond()` methods. The negotiator accepts the bid with a certain probability (1-`p-reject`), and ends the negotiaiton with a very small probability (`p_end`). The agent proposes a random offer at each round, sampled from all the possible outcomes.




```python
from random import random
from negmas import Outcome, ResponseType, SAOState
from anl2025 import ANL2025Negotiator


class MyRandom2025(ANL2025Negotiator):
    p_end = 0.0003
    p_reject = 0.999

    def propose(
        self, negotiator_id: str, state: SAOState, dest: str | None = None
    ) -> Outcome | None:
        nmi = self.get_nmi_from_id(negotiator_id)
        sampled_bid = list(nmi.outcome_space.sample(1))[0]
        return sampled_bid

    def respond(
        self, negotiator_id: str, state: SAOState, source: str | None = None
    ) -> ResponseType:
        if random() < self.p_end:
            return ResponseType.END_NEGOTIATION

        if (
            random() < self.p_reject
            or float(self.ufun(state.current_offer)) < self.ufun.reserved_value  # type: ignore
        ):
            return ResponseType.REJECT_OFFER
        return ResponseType.ACCEPT_OFFER

    def get_nmi_from_id(self, negotiators_id):
        # the nmi is the negotiator mechanism interface, available for each subnegotiation. Here you can find any information about the ongoing or ended negotiation, like the agreement or the previous bids.
        return self.negotiators[negotiators_id].negotiator.nmi
```

If MyRandom2025 negotiator has the role of center agent, it has a list of `side-negotiators`: that are the *subnegotiators* that negotiate bilaterally with one opponent. There is one side-negotiator for each edge agent. You can find that list in `self.negotiators`, callable by their id. Each such side-negotiator is an object that logs all the information about its one-to-one negotiation. One of these functions is called `nmi`, short for negotiator mechanism interface, where you can find information such as the outcome space, the previous bids and possibly the agreement.

To test the agent, we use the functions as introduced in the tutorial *Run a negotiation*. We use a tournament to compare the results between the agents.


```python
from anl2025 import (
    make_multideal_scenario,
    run_session,
    anl2025_tournament,
    Boulware2025,
    Linear2025,
)

scenario = make_multideal_scenario(nedges=3)
competitors = [MyRandom2025, Boulware2025, Linear2025]
# results = run_session(center_type = MyRandom2025, edge_types = competitors, scenario = scenario)
# print(f"Center Utility: {results.center_utility}\nEdge Utilities: {results.edge_utilities}")
results = anl2025_tournament(
    [scenario], n_jobs=-1, competitors=(MyRandom2025, Boulware2025, Linear2025)
)
print(results.final_scores)
print(results.weighted_average)
```


    Output()



<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace"></pre>




    Output()



<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace"></pre>




<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace"><span style="font-weight: bold">{</span><span style="color: #008000; text-decoration-color: #008000">'Linear2025'</span>: <span style="color: #008080; text-decoration-color: #008080; font-weight: bold">3.3379090024210045</span>, <span style="color: #008000; text-decoration-color: #008000">'Boulware2025'</span>: <span style="color: #008080; text-decoration-color: #008080; font-weight: bold">6.367122481180888</span>, <span style="color: #008000; text-decoration-color: #008000">'__main__.MyRandom2025'</span>: <span style="color: #008080; text-decoration-color: #008080; font-weight: bold">1.2732016207516554</span><span style="font-weight: bold">}</span>
</pre>




<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace"><span style="font-weight: bold">{</span>
    <span style="color: #008000; text-decoration-color: #008000">'Linear2025'</span>: <span style="color: #008080; text-decoration-color: #008080; font-weight: bold">0.4960636619436116</span>,
    <span style="color: #008000; text-decoration-color: #008000">'Boulware2025'</span>: <span style="color: #008080; text-decoration-color: #008080; font-weight: bold">0.6799703016440113</span>,
    <span style="color: #008000; text-decoration-color: #008000">'__main__.MyRandom2025'</span>: <span style="color: #008080; text-decoration-color: #008080; font-weight: bold">0.12290548203451745</span>
<span style="font-weight: bold">}</span>
</pre>



As we can see from the results, does MyRandom not perform very well: it has a lower score than the builtin agents.

### The template agent
To give an example about the intuitions you can follow in designing your agent to get a better result, we provide you a template agent. This can form the basis of your own agent. Instead of bidding just anything, this agent tries to aim for the best bid: the target bid. The question is, what is the best target bid? Check out the template agent to see how it is implemented. You can download the template agent [here](https://drive.google.com/drive/folders/1xc5qt7XlZQQv6q1NVnu2vP6Ou-YOQUms?usp=drive_link).

As a suggestion, you can make the following folder structure on your own computer:

ANL 2025submission/
├── Code_for_tutorials2025/
│   ├── Tutorial_running_a_negotiation.py
│   └── ...
├── my_agent/
│   ├── helpers
│   ├── report
│   └── myagent.py
├── Official_test_scenarios/
│   ├── dinners
│   └── ...
└── venv/
    └── lib/
        ├── ...

To test the agent, you can either choose to run a session like above, or run myagent.py directly from your favorite IDE.

This example agent has many flaws. Can you spot them? Hint: is there just one best bid? And is the absolute best bid the only option to aim for?

Now, start tweaking the code and rebuild it, to make the best agent of the competition!


## Other Examples

The ANL package comes with some more example negotiators. These are not designed to be stong but to showcase how to use some of the features provided by the platform.


- [TimeBased2025, Boulware2025, Conceder2025, Linear2025](https://github.com/autoneg/anl2025/blob/main/src/anl2025/negotiator.py) Time-based strategies that are implemented by just setting construction parameters of an existing NegMAS negotiator
- [Shochan2025, AgentRenting2025](https://github.com/autoneg/anl2025/blob/main/src/anl2025/negotiator.py) are naive adaptations of two winners of last year's competition.

#### Note about running tournaments

- When running a tournament using `anl2025_tournament` inside a Jupyter Notebook, you **must** pass `njobs=-1` to force serial execution of negotiations. This is required because the multiprocessing library used by NegMAS does not play nicely with Jupyter Notebooks. If you run the tournament using the same method from a `.py` python script file, you can omit this argument to run a tournament using all available cores.
- When you pass `nologs=True`, no logs are stored for this tournament. If you omit this argument, a log will be created under `~/negmas/anl2025/tournaments` which can be visualized using the ANL visualizer by running:

```bash
anlv show
```

[Download Notebook](/anl2025/tutorials/notebooks/tutorial_develop.ipynb)
