# Cities beside the searchers: a Held–Karp bound that proves the incumbent optimal: design (step 0)

*A candidate for the paper on heuristic agents. The companion of [`vns`](../vns/DESIGN.md), whose
searchers it keeps unchanged; only what is new is described here. Tags: [C] epistemic, [ω]
ontological, [τ] eschatological.*

**What this example adds.** Heterogeneous agents in one record, and many of them. In `vns` the
agents are searchers, each owning a whole tour: a tour is a global object, and only an agent that
sees all of it can propose one. Here the cities are agents too. They do not search for a tour;
each holds a price (a potential) and moves it until the cheapest relaxed structure, a 1-tree,
becomes as heavy as a tour. This is the dual of the problem, and its variables are indexed by the
cities. The searchers (the primal) give the cities the length to aim at; the cities give the
searchers a status: the incumbent is optimal. That claim, about all 25!/2 tours of fri26, becomes
one admitted event of the record, and it replays.

## 1. The bound

The instance is fri26, as in `vns` (optimum 937). A 1-tree is a spanning tree of the cities
1..25 together with two edges at city 0; every tour is a 1-tree in which every city has degree 2.
With a potential π_c for every city and the weights d(a, b) + π_a + π_b, every tour weighs its
length plus 2·Σπ, so the weight of a minimum 1-tree minus 2·Σπ is a lower bound for every π
(Held and Karp 1970). Raising the potential of a city of degree above 2 and lowering that of a
leaf (a subgradient step) raises the bound; on fri26 it reaches the optimum.

ZTES has no floating point (values are integers or rationals), so lengths are scaled by SC = 100
and every potential and every bound is an integer. The bound is exact: "936.10, so no tour is
shorter than 937" involves no rounding.

## 2. Lifting

| Abstraction | Role | ω proposes | τ admits |
|---|---|---|---|
| `draw`, `search_1`–`search_3`, `incumbent` | the searchers of `vns`, synchronous (ontology v1) | as in `vns` | as in `vns` |
| `city_0`–`city_25` | the cities: one potential each | its potential for the next round: a subgradient step aimed at the incumbent | a potential that moves in the direction of the city's coordinate of the subgradient (up above degree 2, down at degree 1, unchanged at 2) |
| `tree` | the 1-tree of each round | the minimum 1-tree (Prim) under the potentials the cities recorded for that round, and its bound | a 1-tree that spans the cities, is minimum, and states its bound truly |
| `proof` | the status of the incumbent | the first round whose best bound proves the incumbent of the coupled round optimal | once, if true |
| `kpi` | indicators | measured over the record, on demand | equal to their definition |

The 26 city abstractions differ only in their number I; `generate.py` writes them from one
template, and also the lists of `system.json` that name them.

**Rounds and their coupling.** Round t of the cities is: the tree of round t (under the potentials
of round t; in round 0 all are 0), then the 26 potentials of round t + 1. A city waits for the
tree of its round, and the tree waits for all 26 potentials. The step of round t aims at the
incumbent of round min(t, R − 1) of the searchers, and a city waits for it: the cities of round t
cannot run ahead of the searchers' round t. Every horizon is complete before it is read, so by
Theorem K every lineage has the same history under every schedule of the workers, as in the
synchronous form of `vns`.

**The step.** Each city computes the same step size, (2 / 2^h)·(SC·U − L) / Σ(deg − 2)², where U
is the length aimed at, L the bound of the round, and h the number of halvings, one whenever 30
rounds in a row have not raised the best bound (Held, Wolfe and Crowder 1974). h is not kept in a
variable; each city reads it from the recorded bounds (D1). The cities stop when the best bound so
far proves the incumbent of the coupled round optimal, when the 1-tree is a tour, after 12
halvings, or after 1,000 rounds. City 0 is the special city of the 1-tree, always of degree 2, so
its potential stays 0; it is kept as an abstraction for uniformity, and records 0 in every round.

**What the criteria know (D2).** The criterion of a city does not know the size of the step: every
potential gives a valid bound, so it admits any move in the right direction. The criterion of the
tree admits any minimum 1-tree, not only Prim's, and checks its bound. The criterion of the proof
checks that the cited bound is the best recorded up to its round and that its ceiling reaches the
length of the incumbent. Since every recorded bound is that of an admitted minimum 1-tree, the
proof is true; once in a prefix it is in every extension (an upper set of the prefix order).

## 3. Results

| Form | Cities aim at | Proof in round | Bound | Trees | Events | Run, replay |
|---|---|---|---|---|---|---|
| plan (v1) | the incumbent of the coupled round | 18 | 936.10 → 937 | 19 | 934 | 0.8 s, 0.7 s |
| v2 | the starting tour (1,140) | 330 | 936.18 → 937 | 331 | 9,384 | 3.2 s, 2.3 s |

Under v1 the bound is 824.00 with all potentials 0, falls to 638.22 after the first, large step,
passes 900 in round 8 and reaches 936.10 in round 18. The incumbent is 937 from round 4 of the
searchers (as in `vns`), and the proof cites the incumbent of round 9. Under the agenda the
searchers end at event 683 and the proof is event 927: the first ten rounds of the cities wait for
the rounds of the searchers.

Ontology v2 of the cities aims the step at the starting tour instead of the incumbent; the
criteria are the same, and the incumbent still decides when to stop. The bound then needs 330
rounds instead of 18: the incumbent shortens the work of the cities eighteenfold. The searchers do
not read the cities, so their history is the same under both forms.

Profile under the agenda (invocations, admitted, Pending): the cities 898, 468, 430 (deferred
resolution ratio 47.9 %); the tree 38, 19, 19; the searchers 441, 333, 108 and the incumbent 116,
10, 106, as in `vns`. No candidate is refused except the one draw refused when its budget closes.

By workers (one per abstraction, 33 in all), under random schedules and with workers killed and
started again, every lineage has the history it has under the agenda.

## 4. Limits and next steps

The Held–Karp bound need not reach the optimum. If it does not, the proof abstraction stays
Pending, and the record decides nothing about optimality: that is not the modal status Not Yet,
which would assert that a proof is attainable.

The coupling, one round of the cities per round of the searchers until the last, is a choice;
others are possible, and one that reads the incumbent as it stands makes the course depend on the
schedule, as in the asynchronous form of `vns`. The searchers could also read the proof and stop
(a governed change of their ontology); here they do not, so that the two forms of the cities can
be compared on the same searchers.

On an asymmetric instance the 1-tree does not apply. Its counterpart, with the cities as agents,
is the assignment relaxation solved by an auction (Bertsekas): each city bids for its successor,
and the prices are recorded. On ftv38 the assignment bound is 1,438 (6 % below the optimum), so it
does not prove optimality by itself, but its cycles, patched, give a starting tour, and the
auction has synchronous and asynchronous forms.

## 5. Tests

`tests/test_vns_hk.py`: the checks ZTES applies to each of its examples (well formed, expected end,
R2, an interrupted run continues to the same record, by workers on memory, disk and Redis, the same
histories under random schedules and with killed workers), and:

- the generator reproduces the city abstractions and `system.json`;
- every tree is a minimum 1-tree (Kruskal, written in the test) and states its bound truly;
- every bound is at most SC times the length of every tour the searchers recorded, and the proof
  (round 18, bound 93,610, length 937) is true, and no earlier round proves it;
- every potential moves in the direction of its coordinate of the subgradient;
- the criteria know nothing of the strategy: a longer step in the same direction is admitted, a
  step against it refused; a 1-tree that is not minimum and a false bound are refused; a proof of
  938, or one cited from round 17, is refused;
- v2 has the criteria of v1 and proves 937 only in round 330.

## References

- Held, M.; Karp, R.M. The traveling-salesman problem and minimum spanning trees. *Operations Research* 1970, 18, 1138–1162.
- Held, M.; Wolfe, P.; Crowder, H.P. Validation of subgradient optimization. *Mathematical Programming* 1974, 6, 62–88.
- Bertsekas, D.P. The auction algorithm: a distributed relaxation method for the assignment problem. *Annals of Operations Research* 1988, 14, 105–123.
