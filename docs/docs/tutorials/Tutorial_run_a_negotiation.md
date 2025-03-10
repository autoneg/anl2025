# Running a single-thread negotiation

NegMAS has several built-in negotiation `Mechanisms`, negotiation agents (`Negotiators`), and `UtilityFunctions`. You can use these to run negotiations as follows.

Imagine a buyer and a seller negotiating over the price of a single object. First, we make an issue "price" with 50 discrete values. Note here, it is possible to create multiple issues, but we will not include that here. If you are interested, see the [NegMAS documentation](https://negmas.readthedocs.io/en/latest/tutorials/01.running_simple_negotiation.html) for a tutorial. (1)


```python
from negmas import (
    make_issue,
    SAOMechanism,
   TimeBasedConcedingNegotiator,
)
from anl.anl2024.negotiators import Boulware, Conceder, RVFitter
from negmas.preferences import LinearAdditiveUtilityFunction as UFun
from negmas.preferences.value_fun import IdentityFun, AffineFun
import matplotlib.pyplot as plt


# create negotiation agenda (issues)
issues = [
    make_issue(name="price", values=50),
]

# create the mechanism
session = SAOMechanism(issues=issues, n_steps=20)
```

The negotiation protocol in NegMAS is handled by a `Mechanism` object. Here we instantiate a`SAOMechanism` which implements the [Stacked Alternating Offers Protocol](https://ii.tudelft.nl/~catholijn/publications/sites/default/files/Aydogan2017_Chapter_AlternatingOffersProtocolsForM.pdf). In this protocol, negotiators exchange offers until an offer is accepted by all negotiators (in this case 2), a negotiators leaves the table ending the negotiation or a time-out condition is met. In the example above, we use a limit on the number of rounds of `20` (a step of a mechanism is an executed round).

Next, we define the utilities of the seller and the buyer. The utility function of the seller is defined by the ```
IdentityFun```  which means that the higher the price, the higher the utility function. The buyer's utility function is reversed. The last two lines make sure that utility is scaled between 0 and 1.


```python
seller_utility = UFun(
    values=[IdentityFun()],
    outcome_space=session.outcome_space,
)

buyer_utility = UFun(
    values=[AffineFun(slope=-1)],
    outcome_space=session.outcome_space,
)

seller_utility = seller_utility.normalize()
buyer_utility = buyer_utility.normalize()

```

Then we add two agents with a boulware strategy. The negotiation ends with status overview. For example, you can see if the negotiation timed-out, what agreement was found, and how long the negotiation took. Moreover, we output the full negotiation history. For a more visual representation, we can plot the session. This shows the bidding curve, but also the proximity to e.g. the Nash point.


```python
# create and add agent A and B
session.add(Boulware(name="seller"), ufun=seller_utility)
session.add(Boulware(name="buyer"), ufun=buyer_utility)

# run the negotiation and show the results
print(session.run())
session.plot(ylimits=(0.0, 1.01), show_reserved=False, mark_max_welfare_points=False)
plt.show()

```


<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace"><span style="color: #800080; text-decoration-color: #800080; font-weight: bold">SAOState</span><span style="font-weight: bold">(</span>
    <span style="color: #808000; text-decoration-color: #808000">running</span>=<span style="color: #ff0000; text-decoration-color: #ff0000; font-style: italic">False</span>,
    <span style="color: #808000; text-decoration-color: #808000">waiting</span>=<span style="color: #ff0000; text-decoration-color: #ff0000; font-style: italic">False</span>,
    <span style="color: #808000; text-decoration-color: #808000">started</span>=<span style="color: #00ff00; text-decoration-color: #00ff00; font-style: italic">True</span>,
    <span style="color: #808000; text-decoration-color: #808000">step</span>=<span style="color: #008080; text-decoration-color: #008080; font-weight: bold">18</span>,
    <span style="color: #808000; text-decoration-color: #808000">time</span>=<span style="color: #008080; text-decoration-color: #008080; font-weight: bold">0.004048299975693226</span>,
    <span style="color: #808000; text-decoration-color: #808000">relative_time</span>=<span style="color: #008080; text-decoration-color: #008080; font-weight: bold">0.9047619047619048</span>,
    <span style="color: #808000; text-decoration-color: #808000">broken</span>=<span style="color: #ff0000; text-decoration-color: #ff0000; font-style: italic">False</span>,
    <span style="color: #808000; text-decoration-color: #808000">timedout</span>=<span style="color: #ff0000; text-decoration-color: #ff0000; font-style: italic">False</span>,
    <span style="color: #808000; text-decoration-color: #808000">agreement</span>=<span style="font-weight: bold">(</span><span style="color: #008080; text-decoration-color: #008080; font-weight: bold">23</span>,<span style="font-weight: bold">)</span>,
    <span style="color: #808000; text-decoration-color: #808000">results</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
    <span style="color: #808000; text-decoration-color: #808000">n_negotiators</span>=<span style="color: #008080; text-decoration-color: #008080; font-weight: bold">2</span>,
    <span style="color: #808000; text-decoration-color: #808000">has_error</span>=<span style="color: #ff0000; text-decoration-color: #ff0000; font-style: italic">False</span>,
    <span style="color: #808000; text-decoration-color: #808000">error_details</span>=<span style="color: #008000; text-decoration-color: #008000">''</span>,
    <span style="color: #808000; text-decoration-color: #808000">erred_negotiator</span>=<span style="color: #008000; text-decoration-color: #008000">''</span>,
    <span style="color: #808000; text-decoration-color: #808000">erred_agent</span>=<span style="color: #008000; text-decoration-color: #008000">''</span>,
    <span style="color: #808000; text-decoration-color: #808000">threads</span>=<span style="font-weight: bold">{}</span>,
    <span style="color: #808000; text-decoration-color: #808000">last_thread</span>=<span style="color: #008000; text-decoration-color: #008000">''</span>,
    <span style="color: #808000; text-decoration-color: #808000">current_offer</span>=<span style="font-weight: bold">(</span><span style="color: #008080; text-decoration-color: #008080; font-weight: bold">23</span>,<span style="font-weight: bold">)</span>,
    <span style="color: #808000; text-decoration-color: #808000">current_proposer</span>=<span style="color: #008000; text-decoration-color: #008000">'seller-2515eb40-48b6-4a82-9178-804c70cfd3af'</span>,
    <span style="color: #808000; text-decoration-color: #808000">current_proposer_agent</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
    <span style="color: #808000; text-decoration-color: #808000">n_acceptances</span>=<span style="color: #008080; text-decoration-color: #008080; font-weight: bold">2</span>,
    <span style="color: #808000; text-decoration-color: #808000">new_offers</span>=<span style="font-weight: bold">[(</span><span style="color: #008000; text-decoration-color: #008000">'seller-2515eb40-48b6-4a82-9178-804c70cfd3af'</span>, <span style="font-weight: bold">(</span><span style="color: #008080; text-decoration-color: #008080; font-weight: bold">23</span>,<span style="font-weight: bold">))]</span>,
    <span style="color: #808000; text-decoration-color: #808000">new_offerer_agents</span>=<span style="font-weight: bold">[</span><span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="font-weight: bold">]</span>,
    <span style="color: #808000; text-decoration-color: #808000">last_negotiator</span>=<span style="color: #008000; text-decoration-color: #008000">'seller'</span>,
    <span style="color: #808000; text-decoration-color: #808000">current_data</span>=<span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span>,
    <span style="color: #808000; text-decoration-color: #808000">new_data</span>=<span style="font-weight: bold">[(</span><span style="color: #008000; text-decoration-color: #008000">'seller-2515eb40-48b6-4a82-9178-804c70cfd3af'</span>, <span style="color: #800080; text-decoration-color: #800080; font-style: italic">None</span><span style="font-weight: bold">)]</span>
<span style="font-weight: bold">)</span>
</pre>




    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_6_1.png)
    


# Running a Multi-deal negotiation

ANL 2025's challenge is to develop agents capable of negotiating sequentially a set of interrelated deals (Multi-deal negotiation). You can create and run a multi-deal negotiation using special tools provided by the anl2025 package.

## A random multideal-session


```python
from anl2025 import make_multideal_scenario

scenario = make_multideal_scenario(nedges=8)
```

**What just happened?**

We created a random multi-deal session with one center agent and 8 edge agents. The center agent negotiates with all the edge agents. Each one of these negotiations is called a **negotiation thread** and the whole set is called a **multideal negotiation**.

The following figure shows the structure of a typical such scenario (with 8 instead of 10 edge agents). Each one of the **edge agents** has its own utility function $e_i$ and is in the same kind of situation as the buyer and seller in the previous example.

The **center agent** faces a different challenge. It has one utility function defined for each **negotiation thread** called a **side utility function** ($s_i$). The overall utility of the center agent is some function (called the **combination function**) of the side utilities it gets in all the negotiation threads. 

```{note}
In ANL 2025, the center agent negotiates with the side agents sequentially. It completes a negotiation with one edge agent before starting the next negotiation with the next edge agent. At no time does the center agent have multiple negotiation threads running at the same time. 
```

The following figure shows the situation:

![Example](Slide2.jpeg)

The function `make_multideal_scenario` creates such a scenario. The combination function used by default is `max` (i.e. the center get the maximum utlility it gets in all negotiations) but you can easily change it. See the full documentation of `make_multideal_scenario` in the Reference for more details of how to control all aspects of scenario  generation.


```python
from anl2025 import run_session
results = run_session(scenario)

```


    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_10_0.png)
    



    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_10_1.png)
    



    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_10_2.png)
    



    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_10_3.png)
    



    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_10_4.png)
    



    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_10_5.png)
    



    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_10_6.png)
    



    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_10_7.png)
    



```python
print(f"Center utility: {results.center_utility}")
print(f"Edge Utilities: {results.edge_utilities}")
```


<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace">Center utility: <span style="color: #008080; text-decoration-color: #008080; font-weight: bold">0.6950491191272049</span>
</pre>




<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace">Edge Utilities: <span style="font-weight: bold">[</span><span style="color: #008080; text-decoration-color: #008080; font-weight: bold">0.5006916644920066</span>, <span style="color: #008080; text-decoration-color: #008080; font-weight: bold">0.2947158934301477</span>, <span style="color: #008080; text-decoration-color: #008080; font-weight: bold">0.3723437914967285</span>, <span style="color: #008080; text-decoration-color: #008080; font-weight: bold">0.536544338413959</span>, 
<span style="color: #008080; text-decoration-color: #008080; font-weight: bold">0.31903386564075864</span>, <span style="color: #008080; text-decoration-color: #008080; font-weight: bold">0.2488242204543755</span>, <span style="color: #008080; text-decoration-color: #008080; font-weight: bold">0.4726159991815505</span>, <span style="color: #008080; text-decoration-color: #008080; font-weight: bold">0.3048364027928087</span><span style="font-weight: bold">]</span>
</pre>



### A dinners' scheduling session

In the previous example, the center utility function was defined in terms of individual side utility functions (one per negotiation threads). A more general case is when the center utility function is defined directly in terms of the outcomes of negotiation threads without locally defined utility functions. The following figure shows an example of this kind of scenario:

![Global Utility Function Example](Slide1.jpeg)

The `anl2025` package allows you to create such scenarios using the `LambdaCenterUFun` class (See Reference). One class of these sceanrios is the **Dinners** scenarios in which one person (center agent) is negotiating with her friends (edge agents) about the day to go out for dinner. Each friend has her own utility function for different days. The cener agent has a utility for each combination of agreements (i.e. she may prefer to go out once every night except in Tuesdays,


```python
from anl2025 import make_dinners_scenario

results = run_session(make_dinners_scenario(n_friends=10))
```


    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_13_0.png)
    



    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_13_1.png)
    



    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_13_2.png)
    



    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_13_3.png)
    



    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_13_4.png)
    



    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_13_5.png)
    



    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_13_6.png)
    



    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_13_7.png)
    



    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_13_8.png)
    



    
![png](Tutorial_run_a_negotiation_files/Tutorial_run_a_negotiation_13_9.png)
    



```python

```


```python

```
[Download Notebook](/anl2025/tutorials/notebooks/Tutorial_run_a_negotiation.ipynb)
