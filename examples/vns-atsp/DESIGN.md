# Variable neighborhood search on an asymmetric instance: design (step 0)

*Not in the paper on the calculus of execution (a candidate for the paper on heuristic agents). The companion of [`vns`](../vns/DESIGN.md), whose design this one follows; only what differs is described here. Tags: [C] epistemic, [ω] ontological, [τ] eschatological.*

**What this example adds.** The same five abstractions, the same bindings, plan and criteria as `vns`, on an asymmetric instance. What changes is the instance and the neighborhood, and nothing in the lifting: a neighborhood is a relation, and the calculus does not ask whether it is symmetric. The asymmetric neighborhood of `vns` (ontology v3, the neighbors of a tour resolved against the record) carries over unchanged, and on this instance it reaches a shorter tour.

## 1. Problem

The instance is ftv38 from TSPLIB (Reinelt 1991), "Asymmetric TSP (Fischetti)": 39 cities, the full
matrix of integer distances exactly as in the TSPLIB file (its diagonal, 100000000, is never used).
For 694 of the 741 pairs of cities the two directions have different distances, so a tour and the
same cycle read backwards are two tours: the optimal tour has length 1,530, and backwards 2,483.
The optimum is the value published with TSPLIB; it was also confirmed with an exact formulation
(Dantzig–Fulkerson–Johnson on the directed graph with subtour cuts, solved by HiGHS), which is not
part of the package.

Parameters: S = 3 searchers, R = 20 rounds, KMAX = 3, random seed 2. The instance is harder than
fri26 for this method, hence twice the rounds: over seeds 1–40 no form reaches the optimum in 20
rounds, and the expected end is a gap.

## 2. The neighborhood

2-opt reverses a segment, and on an asymmetric instance every arc inside it changes direction: the
change of length is no longer the sum of four distances, and the reversed segment is mostly long.
The neighborhood here exchanges two adjacent segments, A B C D → A C B D (3-opt without reversal).
Three arcs are cut and three added, each in its own direction; every arc that is not cut keeps its
direction, and the change of length is computed in O(1). The moves (i, j, k) with
0 ≤ i < j < k ≤ 38 are taken in a fixed order: 9,139 of them. A shake in N_k is k such moves,
chosen by a recorded draw, so `draw` gives KMAX indices below 9,139.

As a relation the neighborhood is still symmetric (exchanging the two segments back is a move);
its cost is not. The asymmetry that matters for the search is again that of the record.

## 3. Lifting

As in `vns`, section 3: `draw` (boundary), `search_1`–`search_3`, `incumbent`, `kpi`. `lib.py`
differs from that of `vns` only where the instance and the neighborhood differ: `segment_moves`,
`change`, `exchange`, and `same_tour`, which here compares walks exactly, since a cycle read
backwards is another tour. Searcher ontology v1 (synchronous), v2 (asynchronous) and v3
(asymmetric neighborhood) are those of `vns`, v3 reading the history of the searchers through the
frozen binding `history`; there is no v4, and one criterion.

## 4. The forms and what they show

| Form | Ontology | Seed 2: incumbent | returns | moves | gap | Seeds 1–40: ends at 1,532 |
|---|---|---|---|---|---|---|
| synchronous (plan) | v1 | 1,562, 1,547 | 20 | 978 | 11 ‰ | 19 |
| asynchronous | v2 | 1,562, 1,555, 1,547, 1,532 | 23 | 1,000 | 1 ‰ | 22 |
| asymmetric | v3 | 1,562, 1,547, 1,544, 1,532 | 15 | 933 | 1 ‰ | 28 |

With seed 2 the synchronous form stops at 1,547, found by searcher 1 in round 2: in the 17 rounds
after it nothing shorter is certified, and 20 of the 60 certificates are of the tour their round
shook. The asymmetric form reaches 1,547 in round 2 as well, then certifies 1,544 in round 6 and
1,532 in round 8, both by searcher 2, 1.3 ‰ above the optimum, with 15 returns and fewer moves. The
asynchronous form also reaches 1,532 with this seed, in round 15.

Over seeds 1–40 no form reaches the optimum, and the end most often reached is 1,532. The
synchronous form ends there in 19 runs and at 1,547 in 16; the asymmetric form ends at 1,532 in 28
and at 1,547 in 8, shorter than the synchronous form in 13 seeds and longer in 2, with 17.8 returns
per run against 24.6. The asynchronous form ends at 1,532 in 22 runs, 23.4 returns per run; the
asymmetric form ends shorter than it in 11 seeds and longer in 4. The mean gap is 6.4 ‰ for the
synchronous form, 5.7 ‰ for the asynchronous, 4.1 ‰ for the asymmetric. The moves per run are
about the same (1,071, 1,079, 1,092): as on fri26, the gain comes from not going back.

Both synchronous forms read only finished rounds, so with workers every lineage has the history it
has under the agenda: the asymmetric form, run by workers under 4 random schedules and in 2 runs with
977 workers killed, gave that history in every run, and every record replayed. The results over seeds
1–40 are reproduced by `python scripts/sweeps.py ftv38`, and the runs by workers by `python
scripts/trials.py ftv38` (the number of workers killed varies from run to run; 958 in a later run).

## 5. Plan

As in `vns`: phases 1 and 2, phase 3 until terminal, one KPI step. The asynchronous form records
ontology v2 of the three searchers before phase 3; the asymmetric form records v2 and v3 (versions
without gaps; v2 is then active for no invocation).

## 6. Expected end

1,195 events. `draw` closed (budget of 60 draws); the three searchers and `incumbent` wait after
round R. The incumbent improves twice: 1,562 (searcher 2, round 0) and 1,547 (searcher 1, round 2),
11 ‰ above the optimum. `expect` has no `any_schedule` part, as in `vns`.

## 7. Files

```
system.json                      instance (D, N, OPT), S, R, KMAX, START, the source of draw, bindings, plan, expect
lib.py                           the segment-exchange neighborhood, the change of length of a move, first improvement,
                                 the shake, the step of a searcher, the asymmetric neighborhood, the criterion,
                                 the incumbent of a round, the indicators
abstractions/draw/               [ω] boundary   [τ] a well-formed draw within the budget
abstractions/search_1/ … _3/     abstraction.json (I); [ω] v1 synchronous, v2 asynchronous, v3 asymmetric   [τ] a step of VNS
abstractions/incumbent/          [ω] the best after a round, once all searchers finished it   [τ] equal to its definition
abstractions/kpi/                [ω] indicators   [τ] each equal to its definition
```

## 8. Execution indicators (KPI)

```
rounds 20, moves 978, returns 20, optima 60, shakes_by_k [21, 21, 15], better_by_k [0, 1, 0],
best 1547, found_by [1, 2], optimum 1530, gap_permille 11, search_invocations 1298, search_not_yet 200
```

The indicators are those of `vns` without `relative`, since there is no certificate relative to the
record here.

## References

- Mladenović, N.; Hansen, P. Variable neighborhood search. *Computers & Operations Research* 1997, 24, 1097–1100.
- Reinelt, G. TSPLIB: A traveling salesman problem library. *ORSA Journal on Computing* 1991, 3, 376–384.
