# An adaptive heuristic agent over cooperative VNS: design (step 0)

*An example of the paper on heuristic agents (§6.2, "A first agent"). Tags: [C] epistemic, [ω] ontological, [τ] eschatological (see the [README of the examples of ZTES](https://github.com/ztes-team/ztes-minimal/blob/main/examples/README.md)).*

**What this example adds.** In [`vns`](../vns/DESIGN.md) the forms of the searchers are put in force by the experimenter, as governed changes in the plan before the searchers start. Here the system puts them in force itself, during the run. One more abstraction, `adapt`, reads the returns of the finished rounds in the record after every round. When they exceed a tolerance, its candidate carries the next form of the searchers. That form is first the asymmetric neighborhood, a change of ontology alone. If the returns go on, it is then the strict form, whose criterion admits a certificate relative to the record, a change of criterion and of the ontology bound to it. The change is admitted by the criterion of `adapt`, which is the authority over what may be changed and on what evidence. τ_root then admits the carried versions, as it admits a file of the plan. They are in force from that event on. The evidence, the decision and the authority are all in the record, and the record replays. ZTES has no kind of abstraction for this: `adapt` is an ordinary abstraction whose candidate carries specifications ([specifications carried by a candidate](https://github.com/ztes-team/ztes-minimal/blob/main/docs/writing-a-system.md#specifications-carried-by-a-candidate)).

## 1. Problem

The problem is that of `vns`: fri26 from TSPLIB (26 cities, optimum 937), S = 3 searchers, R = 10 rounds, neighborhoods N₁ to N₃ (KMAX = 3) and random seed 7. The searchers start in the synchronous form (ontology v1, criterion v1 of `vns`). The tolerance of the agent is TOLERANCE = 2 returns under one form.

The question is the one §6.2 of the paper starts from: the forms of `vns` are decisions made by the experimenter, and the experiments do not contain the sensor that triggers a change. Here the sensor is the indicator `returns` of `vns`: a certificate of the very tour its round shook, so that the descent went back. Under the symmetric neighborhood a return occurs in round 1 in 38 of the 40 seeds 1–40. The evidence for the change is therefore in the record early, and the agent can act on it without knowing the instance in advance.

## 2. Decomposition into binary relations

| Relation | Meaning | Kind |
|---|---|---|
| draw, tour ↦ improving 2-opt neighbor, tour ↦ "no 2-opt neighbor is shorter", shake, merge | as in `vns` | as in `vns` |
| finished rounds ↦ returns since the current form came into force | the sensor of the agent | function of C |
| (returns, form) ↦ decision | keep the form, or put the next one in force from the next round | function |
| decision ↦ specifications it carries | the versions of the next form, as written in the files | function |
| decision ↦ admissible | the authority: the evidence is the record's, the change is the next form only and only past the tolerance | predicate |

## 3. Lifting: the abstractions

| Abstraction | [ω] candidate | [τ] criterion | Horizon |
|---|---|---|---|
| `draw` | as in `vns` | as in `vns` | `draw` |
| `search_1`, `search_2`, `search_3` | v1: the step of synchronous VNS (ontology v1 of `vns`), and after the certificate of round r < R − 1 ⊥ until `adapt` has decided for round r. v2: the same with the asymmetric neighborhood (v3 of `vns`). v3: the strict asymmetric neighborhood (v4 of `vns`), bound to criterion v2 | v1: a step of VNS. v2: also a certificate relative to the record (criterion v2 of `vns`) | ω: own lineage, `draw`, `incumbent`, `adapt`; v2 and v3 also `search_1`–`search_3` |
| `incumbent` | as in `vns` | as in `vns` | own lineage, `search_1`–`search_3` |
| `adapt` | after round r, once its incumbent is recorded: the returns of the rounds since the current form came into force; past TOLERANCE, the next form, carried, in force from round r + 1; otherwise nothing carried. ⊥ after round R − 2 | one decision per finished round, in order; the returns are those of the record; the form is kept with nothing carried, or the next form is put in force from the next round, carrying exactly its specifications, and only past TOLERANCE | own lineage, `incumbent`, `search_1`–`search_3` |
| `kpi` | the indicators of `vns`, and the rounds at which a new form came into force | each indicator equal to its definition | the searchers, `incumbent`, `adapt`, `profile` |

A decision records the round r, the returns it was taken on, the form in force after it (0, 1, 2), the round since which that form is in force, and the specifications it carries (a field of type `{"list": "specification"}`).

The forms are ordinary files of the searchers: `ontology.v2.json`, `ontology.v3.json` and `criterion.v2.json`. The plan records only version 1. The constant `STAGES` of `adapt` names the files of each form:

```json
"STAGES": [
  {"$specifications": ["search_1/ontology.v2", "search_2/ontology.v2", "search_3/ontology.v2"]},
  {"$specifications": ["search_1/criterion.v2", "search_1/ontology.v3", "search_2/criterion.v2", "search_2/ontology.v3",
                       "search_3/criterion.v2", "search_3/ontology.v3"]}]
```

When the system is loaded, each reference becomes the list of those specifications in their recorded form. The specifications of `adapt` thus contain, in full, every version they may carry.

## 4. Design decisions and what they illustrate

- **The agent is an ordinary abstraction.** Z₀ knows no kind of abstraction: any candidate may carry specifications, and every carried one is judged by τ_root as a file of the plan is. What makes `adapt` the agent is only what its ontology proposes and what its criterion admits.
- **The criterion is the authority, the ontology the strategy (D2).** The criterion of `adapt` does not compute the decision. It admits keeping the form at any time. It admits the next form only past the tolerance, carrying exactly the versions of that form. It admits nothing else: no other abstraction, no other version, no change of `adapt` itself. The ontology decides to change as soon as it may. A more cautious ontology, which waited longer, would be admitted by the same criterion.
- **The sensor is read from the record.** The returns since the current form came into force are computed over the recorded steps, by the definition of the indicator `returns` of `vns`. Every decision records the value it was taken on, and the criterion checks it again, so a decision cannot rest on evidence the record does not hold. R2 checks it a third time.
- **A change takes effect at the start of a round.** After its certificate of round r a searcher waits until `adapt` has decided for round r. The agent decides once the incumbent of round r is recorded, and then every searcher has certified round r. The decision therefore reads a complete horizon, and the change it carries is at the same position of every lineage under every schedule (Theorem K). This is the pattern the design of the mechanism names: the proposer decides at every point where a decision is due, also when it changes nothing, and the abstractions it may change wait for that decision. The cost is one more wait per round, visible in the profile.
- **Two kinds of change, in the order of their cost.** The first form changes three ontologies and no criterion: the neighborhood is resolved against the record, and every step admitted afterwards would have been admitted before. The second form widens admission. It carries criterion v2 of each searcher and then the ontology v3 bound to it, in one candidate. Z₀ binds each carried ontology to the criterion carried before it, as phase 2 binds an ontology to its criterion. The agent widens the criterion only when the narrower one has gone on costing returns.
- **Every earlier judgment stands.** The steps of rounds 0–2 were judged by criterion v1 and remain so. Replay judges each event under the versions in force at its position, including the decisions that changed them.

## 5. Plan

Phases 1 and 2, phase 3 until terminal, one KPI step. No governed change appears in the plan: the plan records version 1 of every abstraction, and the record shows every later version as carried by a decision of `adapt`.

## 6. Expected end

393 events. The decisions of `adapt` with seed 7:

| After round | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|
| returns since the current form | 0 | 1 | **3** | 0 | 0 | 2 | **4** | 0 | 0 |
| form in force afterwards | 0 | 0 | 1 | 1 | 1 | 1 | 2 | 2 | 2 |
| carries | | | ontology v2 of the three searchers | | | | criterion v2 and ontology v3 of each | | |

Every step of rounds 0–2 is proposed by ontology v1, rounds 3–6 by ontology v2, and rounds 7–9 by ontology v3 under criterion v2. The incumbent improves four times: 1,004 (searcher 1, round 0), 985 (searcher 1, round 1), 974 (searcher 2, round 3, the first round of the asymmetric form), and 937 (searcher 3, round 4), the optimum, as under the fixed forms v3 and v4 of `vns`. `draw` is closed; the searchers, `incumbent` and `adapt` wait. The workers give, under random schedules, the lineages of the agenda.

Over seeds 1–40, against the fixed forms of `vns` (each a separate run with the same seed; `python scripts/sweeps.py agent`):

| Form | Reaches 937 | Mean final length | Returns per run | Relative certificates | Moves |
|---|---|---|---|---|---|
| v1, synchronous (fixed) | 22 | 946.5 | 15.25 | 0 | 299.5 |
| v3, asymmetric (fixed) | 28 | 942.7 | 12.8 | 0 | 325.2 |
| v4, strict (fixed) | 27 | 943.2 | 0.05 | 15.5 | 306.1 |
| adaptive, tolerance 0 | 23 | 945.1 | 3.7 | 11.7 | 305.1 |
| adaptive, tolerance 1 | 24 | 944.6 | 5.1 | 10.2 | 306.1 |
| **adaptive, tolerance 2 (the plan)** | **25** | **944.1** | **7.2** | **7.8** | **310.9** |
| adaptive, tolerance 3 | 26 | 943.8 | 9.2 | 5.6 | 311.5 |
| adaptive, tolerance 4 | 26 | 943.8 | 11.1 | 3.4 | 312.5 |

With tolerance 2 the agent ends shorter than the form it starts with (v1) in 7 seeds and longer in 2. It ends shorter than the fixed asymmetric form v3 in 2 seeds and longer in 6. On this instance it therefore does not beat the best form chosen in hindsight. The evidence that triggers a change appears in nearly every run, as early as round 1, so the choice made in hindsight is to change at once. The differences in quality between the tolerances are within the variation of 40 seeds. The tolerance does decide the mix of the two kinds of change: as it rises from 0 to 4, the returns rise from 3.7 to 11.1 per run and the relative certificates fall from 11.7 to 3.4. In other words, the tolerance sets how long the agent accepts the way back before it widens the criterion. With every tolerance the agent changes form at least once in every run.

## 7. Files

```
system.json                      the system of vns, the agent, TOLERANCE, the type Decision, bindings, plan, expect
lib.py                           lib.py of vns, the wait for the decision, the sensor, the decision and its criterion
abstractions/draw/               as in vns
abstractions/search_1/ … _3/     abstraction.json (I); [ω] v1 synchronous, v2 asymmetric, v3 strict, each waiting for the
                                 decision of its round   [τ] v1 a step of VNS, v2 also a certificate relative to the record.
                                 v2, v3 and criterion v2 are not in the plan: the agent carries them
abstractions/incumbent/          as in vns
abstractions/adapt/              abstraction.json (STAGES, its bindings); [ω] the decision   [τ] the authority
abstractions/kpi/                [ω] indicators   [τ] each equal to its definition
```

## 8. Execution indicators (KPI)

```
rounds 10, moves 265, returns 7, relative 5, optima 30, shakes_by_k [15, 9, 3], better_by_k [2, 1, 0],
best 937, found_by [3, 4], optimum 937, gap_permille 0, search_invocations 434, search_not_yet 109,
changes [3, 7], form 2
```

`changes` gives the rounds from which a new form was in force, and `form` the last form. The returns are 3 in rounds 0–2 under v1, 4 in rounds 3–6 under v2, and none in rounds 7–9 under v3, where the strict descent certifies five tours relative to the record instead. The searchers are at Not Yet 109 times (108 in `vns`). Under the agenda, 8 of these are waits for the decision of their round, between the incumbent of that round and the decision. The other waits are for the incumbent, as in `vns`. `adapt` is at Not Yet 101 times, waiting for the incumbent of the next round. That is the price of a decision at every round, in invocations that append nothing.

## References

- Mladenović, N.; Hansen, P. Variable neighborhood search. *Computers & Operations Research* 1997, 24, 1097–1100.
- Battiti, R.; Brunato, M.; Mascia, F. *Reactive Search and Intelligent Optimization*. Springer, 2008.
- Burke, E.K.; Gendreau, M.; Hyde, M.; Kendall, G.; Ochoa, G.; Özcan, E.; Qu, R. Hyper-heuristics: a survey of the state of the art. *Journal of the Operational Research Society* 2013, 64, 1695–1724.
- Reinelt, G. TSPLIB: A traveling salesman problem library. *ORSA Journal on Computing* 1991, 3, 376–384.
