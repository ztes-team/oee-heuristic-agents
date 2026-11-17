# Variable neighborhood search by cooperating searchers: design (step 0)

*Not in the paper on the calculus of execution (a candidate for the paper on heuristic agents). Tags: [C] epistemic, [ω] ontological, [τ] eschatological (see the [README of the examples of ZTES](https://github.com/ztes-team/ztes-minimal/blob/main/examples/README.md)).*

**What this example adds.** After [`aco-draw`](https://github.com/ztes-team/ztes-minimal/tree/main/examples/aco-draw) in ZTES, which lifts a population heuristic: a trajectory heuristic, variable neighborhood search (VNS), run by three cooperating searchers. Every loop of the method (the descent to a local optimum, the change of neighborhood, the rounds) is eschatological induction: the next step reads the previous one from the record. A local optimum is an admitted certificate. The two classical forms of cooperative parallel VNS are here one horizon apart, and the synchronous one gives the same record under every schedule, with no lock, no message and no master process. A third form adapts VNS to the asymmetric space of execution: the neighborhood of a tour is resolved against the record, so the descent does not take the way back to a tour the record already holds; the criterion stays the same. A fourth form adds a certificate relative to the record, admitted by a widened criterion.

VNS (Mladenović and Hansen 1997; Hansen and Mladenović 2001) alternates a random perturbation of
the current solution in the k-th neighborhood (the shake) with a local descent, and returns to the
first neighborhood when the solution improves. An imperative implementation keeps the current
solution, the best solution and k in variables, updated in nested loops. In the lifting nothing is
updated: the trajectory of a searcher is a lineage, the incumbent is a lineage, and k is read from
the record.

## 1. Problem

The instance is fri26 from TSPLIB (Reinelt 1991): 26 cities, symmetric integer distances given as
the lower triangle of the matrix, row by row, exactly as in the TSPLIB file. Its optimum, 937, is
the value published with TSPLIB; it was also confirmed with an exact formulation
(Dantzig–Fulkerson–Johnson with subtour cuts, solved by HiGHS), which is not part of the package.

The twelve cities of `tsp` and `aco` in ZTES are too few for this method: VNS reaches their optimum, 50, in
its first round, and nothing is left for cooperation to show.

Parameters: S = 3 searchers, R = 10 rounds, neighborhoods N₁, N₂, N₃ (KMAX = 3), random seed 7.
The local search is first improvement in the 2-opt neighborhood, whose 299 moves are taken in a
fixed order; N_k is reached by k 2-opt moves chosen by a recorded draw.

## 2. Decomposition into binary relations

| Relation | Meaning | Kind |
|---|---|---|
| draw | KMAX move indices below 299, supplied by the environment | not computed from C |
| tour ↦ improving 2-opt neighbor | one step of the descent | multivalued; resolved to the first in the fixed order |
| tour ↦ "no 2-opt neighbor is shorter" | the local optimum | a predicate, checked by the criterion |
| (certified tour, k, draw) ↦ shaken tour | the shake in N_k | function |
| certified optima of a round ↦ incumbent | the merge of the searchers | function |

A tour of fri26 has 299 2-opt neighbors, and many of them may be shorter. Taking the first in the
fixed order resolves the relation to one candidate without a choice function (D1).

## 3. Lifting: the abstractions

| Abstraction | [ω] candidate | [τ] criterion | Horizon |
|---|---|---|---|
| `draw` | boundary: the occurrence of the invocation | fewer than S·R draws so far; KMAX indices below 299 | `draw` |
| `search_1`, `search_2`, `search_3` | the next step of searcher i. After a certificate: a shake, in N_k, of the incumbent of the round just finished. After a shake or a move: the first improving 2-opt move, or the certificate if there is none. ⊥ while the incumbent of the round or the draw is not yet recorded, and after round R | a step of VNS from the previous one: a shake of the starting tour or of a certified local optimum, in N_k for some k ≤ KMAX, by the searcher's recorded draw of that round; an improving 2-opt move; or a certificate that no 2-opt move shortens the tour | ω: own lineage, `draw`, `incumbent`; τ: also `search_1`–`search_3` |
| `incumbent` | after round r: the shortest of the previous incumbent and the three certified optima of round r; ⊥ until all three are recorded | equal to that definition | own lineage, `search_1`–`search_3` |
| `kpi` | the indicators of the search (section 8) | each indicator equal to its definition | the searchers, `incumbent`, `profile` |

The three searchers are the same specification files; `abstraction.json` gives each its number I,
and the logic is written once, in `lib.py`. Searcher I uses draw r·S + I − 1 in round r. The table
describes ontology v1 and criterion v1, the plan of the example. The other versions of a searcher
are the forms of section 4: ontology v2 (asynchronous), v3 (asymmetric neighborhood), v4 (strict
asymmetric neighborhood, bound to criterion v2, which also admits a certificate relative to the record).

An event of a searcher records the round r, the neighborhood k, the kind of step (shake, move,
opt), the certified tour the round started from (`src`, as searcher and round, and its length),
the move index and the tour with its length.

## 4. Design decisions and what they illustrate

- **Every loop of VNS is interaction.** The descent (while an improving move exists), the change
  of neighborhood (k ← k + 1 up to KMAX) and the rounds are not loops in any body. Each step is an
  admitted event; the next invocation of the searcher reads it and proposes the following step
  (eschatological induction). Bodies contain only bounded scans over fixed finite sets (the 299
  moves, the k moves of a shake), which is what an effective realization is (S1.2). The record of a
  run is the trace of the algorithm, with no step left out.
- **A step, not a probe.** One could also record every evaluated move, so that the scan of the
  neighborhood would be interaction as well. On fri26 each certificate would then need 299
  recorded rejections, and every move the rejections before it: the run of this example would
  hold 45,778 recorded evaluations instead of 273 moves and 30 certificates, nearly all of them
  rejected moves, while proving nothing more, since the certificate is checked by τ in one judgment.
- **A local optimum is a certificate.** The claim that no 2-opt move shortens a tour, implicit in
  an imperative VNS, is an admitted event whose criterion checks all 299 moves; R2 checks it
  again. A run holds 30 such certificates.
- **D2: the criterion does not know the strategy.** τ admits any improving move, not only the
  first, and any shake of a certified tour in some N_k, not only a shake of the incumbent with the
  k of the rule. First improvement, the choice of the tour to shake and the k rule are ontology.
  The two forms of cooperation below therefore differ in three ontology versions and in no
  criterion (`test_asynchronous_cooperation_changes_three_ontologies_and_no_criterion` in
  `tests/test_vns.py`).
- **k is read from the record.** k = KMAX in round 0, which diversifies the starting points; then
  k = 1 if the tour to be shaken is shorter than the one shaken in the previous round, otherwise
  the next neighborhood, cyclically. This is the rule of basic VNS; no variable holds k, it is
  carried by the events of the round.
- **Chance is a boundary abstraction**, as in `aco-draw`. R2 re-judges every draw from the record
  and never asks the source.

**Two forms of cooperation, one horizon apart.**

| | Synchronous: `ontology.v1`, in the plan | Asynchronous: `ontology.v2` |
|---|---|---|
| a searcher shakes | the incumbent of the round it has just finished | the shortest optimum certified so far, as it stands |
| it reads | its lineage, `draw`, `incumbent` | its lineage, `draw`, all searchers |
| it waits | until every searcher has finished the round | never |
| classical counterpart | replicated-shaking VNS (García-López et al. 2002) | cooperative neighborhood VNS (Crainic et al. 2004) |
| the master process of the original | none: the complete horizon of `incumbent` | none: the record |
| with one worker per abstraction | every lineage has the same history under every schedule | another valid course under each schedule; every record replays |

In the synchronous form the incumbent of round r is computed only when the three certified optima
of round r are recorded (a complete horizon), and each searcher waits for it. All inputs of every
searcher are then determined by the record, so each lineage has the history it has under the
agenda, under any schedule of the workers and after any of them fails (Theorem K); only the
interleaving of the record differs. In the model there is no lock and no message; the one point of
synchronization is the conditional insert of the store, which gives C its single order.

The asynchronous form uses a certified optimum as soon as it exists. With seed 7 under the agenda
it reaches 953 in round 1, where the synchronous form has 985, and both reach 937 in round 4. Over
seeds 1–40 neither form is better on this instance: each reaches the optimum in 22 runs; the
synchronous form ends shorter in 6 seeds, the asynchronous in 8, and they are equal in 26. What the
choice decides is not the quality but whether the result depends on the schedule.

**The derivation of the result.** The optimum has a derivation in the record from the starting tour
(length 1,140), each link an admitted event judged on its prefix: searcher 1, round 0, shake in N₃
(event 12), 22 moves, certificate 1,004 (event 89); searcher 1, round 1, shake of that tour in N₁
(event 93), 2 moves, certificate 985 (event 105); searcher 3, round 4, shake of searcher 1's 985 in
N₃ by draw 14 (event 160), 30 moves, certificate 937 (event 220). With a kept record,
`python -m ztes explain DIR 220` shows why the last step was admitted.

**The asymmetric neighborhood (ontology v3).** VNS defines its neighborhoods on the space of
solutions, and the 2-opt neighborhood is symmetric: a move is its own inverse, so y ∈ N_k(x)
exactly when x ∈ N_k(y). The record shows what this costs. A shake in N₁ moves a local optimum by
one 2-opt move; the inverse of that move is an improving move of the shaken tour whenever the shake
lengthened it, first improvement often takes it, and the round ends by certifying the very tour it
shook. With seed 7 this happens
in 14 of the 30 rounds (the indicator `returns`), and 16 of the 30 certificates repeat an earlier one.

The space of execution is asymmetric: a prefix is extended and never retracted, and its Alexandrov
neighborhoods ↑C point only forward. Ontology v3 carries this into the search. The neighborhood of a
tour is resolved against the record (D1): the descent takes the first improving move to a tour the
finished rounds have not recorded, and the first improving move only when every improving one leads
to a recorded tour. As the record grows the neighborhood can only shrink,
C ≼ C′ ⇒ N(x | C′) ⊆ N(x | C). It reads only rounds that are finished when its round begins, a
complete horizon, so the synchronous form keeps the same record under every schedule. The
criterion is that of v1, which admits any improving move: the new form is a change of ontology alone (D2).

v3 reads the steps of all searchers through the binding `history`, declared `"frozen": true`: ZTES
decodes each recorded step once and shares it between invocations, instead of decoding the whole
history at every step (a cost that grows with the square of the record). The values are immutable,
so a tour in them is a tuple; `same_tour` compares element by element. v4 and criterion v2 read it
the same way. The histories are those of a plain binding; v3 runs in 0.21 s instead of 0.35 s.

With seed 7 the asymmetric form finds 974 in round 3 and reaches 937 in round 4, as v1 does, with
11 returns instead of 14. Over seeds 1–40 it reaches the optimum in 28 runs, v1 in 22; it ends
shorter than v1 in 9 seeds, longer in 1, and equal in 30, with 325 moves per run on average against
299: the gain does not come from more work but from not going back.

**The relative certificate (ontology v4, criterion v2).** v3 cannot always avoid the way back. When
every improving move of a tour leads to a recorded tour, criterion v1 still demands a descent to a
tour that no move shortens, and the searcher walks into known ground. Criterion v2 admits every step
v1 admits and, in addition, a certificate relative to the record: no move shortens the tour to a tour
the rounds before its own have not recorded. Once this holds on a prefix it holds on every extension:
the prefixes on which it holds form an upper set, open in the Alexandrov topology (Proposition 5(b)
of the paper). Since v1 admits a subset of what v2 admits, this governed change widens admission.
Ontology v4 is the strict descent bound to criterion v2: it never enters a recorded tour and
certifies relative to the record when nothing else is left.

With seed 7 the strict form has no return, 12 relative certificates and 255 moves instead of 273;
its incumbent goes as under v3. Over seeds 1–40 it has 2 returns in all, against 15.2 per run under
v1 and 12.8 under v3, and neither came from a descent: in both the draw repeated a move index, the
two equal 2-opt moves of a shake in N₂ cancelled, and the shake itself landed on the tour it shook.
The strict form reaches the optimum in 27 runs, and it ends shorter than v1 in 9 seeds and longer
in 2. Its quality is that of v3; what it changes is that the record no longer states the same thing
twice.

| Form | Ontology | Criterion | Seed 7: incumbent | returns | relative | moves | Seeds 1–40: optimum |
|---|---|---|---|---|---|---|---|
| synchronous (plan) | v1 | v1 | 1,004, 985, 937 | 14 | 0 | 273 | 22 |
| asynchronous | v2 | v1 | 1,004, 953, 937 | 19 | 0 | 280 | 22 |
| asymmetric | v3 | v1 | 1,004, 985, 974, 937 | 11 | 0 | 271 | 28 |
| asymmetric, strict | v4 | v2 | 1,004, 985, 974, 937 | 0 | 12 | 255 | 27 |

## 5. Plan

Phases 1 and 2; phase 3 until terminal; one KPI step. Every other form is the same plan with a
governed change of the three searchers before phase 3. τ_root records the versions of a
specification without gaps, so a plan that runs version v records the versions before it in the
same governed change: they are active for no invocation, and the record carries the lineage of the
searchers' ontology. An ontology is bound to the criterion active when it is recorded, so
criterion v2 is recorded before ontology v4.

```
asynchronous         govern search_i/ontology.v2
asymmetric           govern search_i/ontology.v2, search_i/ontology.v3
asymmetric, strict   govern search_i/ontology.v2, search_i/ontology.v3, search_i/criterion.v2, search_i/ontology.v4
```

for i = 1, 2, 3. The asynchronous form, for example:

```json
[{"phase": 1}, {"phase": 2},
 {"govern": ["search_1/ontology.v2", "search_2/ontology.v2", "search_3/ontology.v2"]},
 {"phase": 3}, {"kpi": true}]
```

## 6. Expected end

390 events. `draw` closed (budget of 30 draws); the three searchers and `incumbent` wait after round
R. The incumbent improves three times: 1,004 (searcher 1, round 0), 985 (searcher 1, round 1), 937
(searcher 3, round 4), the optimum. Because the synchronous form is independent of the schedule,
`expect` has no `any_schedule` part: the same events, states and final incumbent are checked when
phase 3 is run by workers.

Over seeds 1–40 the synchronous form ends at 937 in 22 runs, 953 in 8, 955 in 4, 961 and 974 in 2
each, 959 and 972 once each; its records have 336 to 494 events, and in 27 of the 40 runs more than
one searcher improves the incumbent. The asynchronous form run by workers with seed 7 gave records
of 370 to 432 events in our runs, all ending at 937; that end is not guaranteed. The synchronous
form, run by workers under 40 random schedules and in 20 runs with 3,155 workers killed and started
again, gave in every run the 390 events of the agenda and the same history of every lineage.
The asymmetric form (v3) and the strict form with criterion v2 (v4), each run by workers under 20
random schedules and in 10 runs with 1,617 and 1,517 workers killed, gave in every run the history of
every lineage that they give under the agenda, and every record replayed.

## 7. Files

```
system.json                      instance (LOWER, N, OPT), S, R, KMAX, START, the source of draw, bindings, plan, expect
lib.py                           the 2-opt neighborhood, the change of length of a move, first improvement, the shake,
                                 the step of a searcher, the asymmetric neighborhood, the criteria, the incumbent of a
                                 round, the indicators
abstractions/draw/               [ω] boundary   [τ] a well-formed draw within the budget
abstractions/search_1/ … _3/     abstraction.json (I); [ω] v1 synchronous, v2 asynchronous, v3 asymmetric,
                                 v4 asymmetric strict   [τ] v1 a step of VNS, v2 also a certificate relative to the record
abstractions/incumbent/          [ω] the best after a round, once all searchers finished it   [τ] equal to its definition
abstractions/kpi/                [ω] indicators   [τ] each equal to its definition
```

## 8. Execution indicators (KPI)

```
rounds 10, moves 273, returns 14, relative 0, optima 30, shakes_by_k [12, 9, 6], better_by_k [1, 0, 1],
best 937, found_by [3, 4], optimum 937, gap_permille 0, search_invocations 441, search_not_yet 108
```

`shakes_by_k` and `better_by_k` give, for each neighborhood, the shakes made in it after round 0
and the local optima reached from them that are shorter than the tour shaken: the statistics by
which VNS variants are compared, read from the record with no instrumentation. `returns` counts the
certificates of the very tour their round shook (the descent went back), and `relative` the
certificates relative to the record, whose tour some move still shortens; both are read from the
record and compare the forms of section 4 directly. The profile shows
the cost of synchronization: the searchers are at Not Yet 108 times, waiting for the incumbent of a
round or, at the end, after round R, and `incumbent` 106 times, waiting for the last searcher of a
round.

## References

- Mladenović, N.; Hansen, P. Variable neighborhood search. *Computers & Operations Research* 1997, 24, 1097–1100.
- Hansen, P.; Mladenović, N. Variable neighborhood search: Principles and applications. *European Journal of Operational Research* 2001, 130, 449–467.
- García-López, F.; Melián-Batista, B.; Moreno-Pérez, J.A.; Moreno-Vega, J.M. The parallel variable neighborhood search for the p-median problem. *Journal of Heuristics* 2002, 8, 375–388.
- Crainic, T.G.; Gendreau, M.; Hansen, P.; Mladenović, N. Cooperative parallel variable neighborhood search for the p-median. *Journal of Heuristics* 2004, 10, 293–314.
- Reinelt, G. TSPLIB: A traveling salesman problem library. *ORSA Journal on Computing* 1991, 3, 376–384.
