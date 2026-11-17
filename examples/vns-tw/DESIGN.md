# VNS with time windows and precedence under a recorded environment: design (step 0)

*Not in the paper on the calculus of execution (a candidate for the paper on heuristic agents). The companion of [`vns-atsp`](../vns-atsp/DESIGN.md) and [`vns`](../vns/DESIGN.md), whose design this one follows. Tags: [C] epistemic, [ω] ontological, [τ] eschatological.*

**What this example adds.** Three things. First, constraints whose violation has the statuses of the calculus: a city reached after its window closes is late, and since its arrival is fixed by the prefix before it, no change after it can repair it (False, an upper set of the prefix order); a city visited before a city it must follow is premature, admissible once that city is visited (Not Yet). The prefix order gives the repair rule: only a move that cuts before the first position that is not admissible can repair it. Second, an environment in the record: the travel times vary by scenario, the scenarios are boundary events, the tour must be on time in all but a few of them, and the probability of being on time is the measure of a Borel event of the space of records, estimated on recorded draws. Third, three sources of chance in one record: the algorithm's (the draws of the shakes, read by ω), the schedule's (the order of C under workers), and the environment's (the scenarios, which decide what τ admits); their shares of the variability of the result are measured.

## 1. Problem and instance

The asymmetric TSP with time windows and precedence constraints. A tour leaves the depot (city 0)
at time 0; the service at a city starts on arrival or, if the tour arrives early, when the window
opens; a city reached after its window closes is late, and so is a return to the depot after its
window closes. A precedence pair [p, q] requires p before q. The tours are compared by a
lexicographic value: the precedence pairs violated, the total lateness, the scenarios failed beyond
those allowed (below), and the length.

The travel times are those of ftv38 (TSPLIB, 39 cities), as in `vns-atsp`. The windows and the
pairs are generated as `generate.py` documents and `tests/test_vns_tw.py` checks: windows as in
Dumas et al. (1995), around the arrival times on a random reference tour, half-widths uniform in
[0, 750]; 10 precedence pairs consistent with the reference tour whose windows overlap, so that the
windows alone do not imply them. The optimum is 3,415 (HiGHS, `optima.json`); without the
precedence pairs it would be 3,229, and that tour violates 3 of them, so the pairs bind. Finding a
feasible tour of such a problem is itself NP-hard (Savelsbergh 1985); the starting tour, the
cities in the order in which their windows close, violates 2 pairs and is 23 late.

**The environment.** In a scenario the travel time of arc (a, b) is D[a][b]·(100 + δ)/100, with δ
an integer percent uniform in [−10, 10], a pure function of the scenario's seed and the arc (the
SplitMix64 mixer). The boundary abstraction `world` records M = 20 seeds; a tour must be on time in
all but ALLOW = 2 of their scenarios (a chance constraint at 90 %, as a sample average). The
boundary abstraction `audit` records one more seed, from which 1,000 further scenarios are derived
that the search never reads. With the recorded world the sample-average optimum is 3,492 (HiGHS).

| Tour | Length | On time, world (20) | On time, audit (1,000) |
|---|---|---|---|
| deterministic optimum | 3,415 | 6 | 457 |
| sample-average optimum | 3,492 | 20 | 898 |

The deterministic optimum is on time in fewer than half of the scenarios. The sample-average
optimum is on time in all 20 scenarios it was optimized on, but in 898 of the 1,000 it never saw,
below the 90 % the constraint aims at: the sample overstates the probability it estimates, and the
audit, recorded like the rest, shows by how much.

## 2. The statuses of a tour and the repair

Every step records, with its tour, the first position that is not admissible and why:

| Status | At the first position that is not admissible | Prefix order |
|---|---|---|
| `true` | none: the tour is feasible in the nominal times | — |
| `false` | the city is late | its arrival is fixed by the prefix before it: every extension and every change after it leaves it late |
| `not_yet` | a city it must follow comes later | premature: admissible once that city is visited before it |

A move (i, j, k) changes only the positions after i. So a move that cuts at or after the first
position that is not admissible leaves that position as it is, late or premature; the repair takes
the best move among those that cut before it. If only scenarios fail, the same holds per scenario:
a scenario late before the cut stays late, so the repair cuts before the latest first lateness of a
failing scenario. The rule also makes the evaluation of a move incremental, for the nominal times
and for every scenario. In the prototype (20 rounds) the repair restricted this way reached the deterministic optimum
in 8–9 of 40 seeds, against 2–6 for the best move over the whole neighborhood.

## 3. Lifting

| Abstraction | Role | [ω] | [τ] |
|---|---|---|---|
| `draw` | boundary, the algorithm's chance | KMAX move indices | a well-formed draw within S·R |
| `world` | boundary, the environment's chance | the seed of one scenario | M seeds |
| `scenario` | the travel times of each scenario | the scenario of the next recorded seed | equal to its definition |
| `audit` | boundary, the environment's chance | the seed of the audit scenarios | one seed |
| `search_1`–`search_3` | the searchers | the next step: shake, repair, move, or certificate (requires the M recorded scenarios) | the step states its tour truly and is a step of VNS (below) |
| `incumbent` | the best after each round | lexicographic best of the round's certificates and the previous incumbent | equal to its definition |
| `kpi` | indicators | read from the record | equal to their definition |

A step is a **shake** of the incumbent in N_k by the recorded draw (it may leave the feasible
region), a **repair** of an infeasible tour, a **move** that shortens a feasible one, or the
**certificate** that no move lowers the value. The criterion (D2) admits a step if what it states
about its tour (value, first position that is not admissible, status, scenarios failed) is true and
it is a legitimate step of VNS: a shake by the recorded draw, any move that lowers the value (not
only the one the strategy chose), or a certificate checked over all 9,139 moves and all scenarios.

Ontology v1 cooperates synchronously, v2 asynchronously, as in `vns-atsp`. v3 is the asymmetric
neighborhood: the descent, its repair and its shortening alike, does not take a move to a tour
recorded in the finished rounds while another move would do. Here the returns come mostly from the
repair, which tends to undo the shake, so v3 applies to both.

## 4. Three sources of chance

| Source | Enters through | Measure |
|---|---|---|
| the algorithm: the draws of the shakes | ω: what is proposed | given (SplitMix64, recorded) |
| the schedule of the workers: the order of C | C: what is known when | none needed for the synchronous forms (the history of every lineage is the same under every schedule, Theorem K); posited for the asynchronous form (random pauses) |
| the environment: the scenarios | τ: what is admitted | given (SplitMix64, recorded) |

All three are in the record, so every indicator is a function of the record and each source can be
varied while the others are held.

Measured in ZTES with the chance constraint:

- **Algorithm × environment** (6 draw seeds × 6 world seeds, v3 under the agenda). Of the variance
  of the final length, 55 % comes from the algorithm, 15 % from the environment and 30 % from their
  interaction; of the number of audit scenarios in which the final tour is on time, 45 %, 24 % and
  31 %. Every run ends feasible, on time in 18 to 20 of the scenarios of its own world.
- **The schedule, synchronous forms.** v1 and v3, each run by workers under 3 schedules (random
  pauses with seeds 1–3), gave in every run the history of every lineage they give under the
  agenda, and every record replayed: the share of the schedule is exactly 0, by Theorem K, and no
  measure over schedules is needed to say so.
- **The schedule, asynchronous form.** v2, run by workers over 3 draw seeds × 3 world seeds × 3
  schedules (27 runs, every record replayed): the schedule changed the final tour in 5 of the 9
  combinations of draw and world. Of the variance of the final length, the algorithm explains
  25 %, the environment 6 %, the schedule 9 %, and their interactions 60 % (a 3 × 3 × 3 design:
  indicative only). Here the measure over schedules is the one posited by the random pauses.

## 5. The forms and what they show

Over draw seeds 1–20 (world seed 11, audit seed 999), each form under the agenda:

| Problem | Form | Optimum reached | Mean gap | On time, world (20) | On time, audit (1,000): mean (min–max) | Returns (of 30) |
|---|---|---|---|---|---|---|
| with the chance constraint (ALLOW 2) | v1 | 1 | 7.1 ‰ | 20 in every run | 966 (898–1,000) | 24.9 |
| | v3 | 8 | 1.6 ‰ | 20 in every run | 932 (898–994) | 16.2 |
| deterministic (ALLOW = M) | v1 | 0 | 21.2 ‰ | 11.7 | 546 (357–724) | 23.9 |
| | v3 | 3 | 16.6 ‰ | 10.2 | 519 (357–724) | 16.1 |

The optimum is the sample-average one (3,492) with the chance constraint and the deterministic one
(3,415) without it. Every run ends feasible.

- **The asymmetric neighborhood.** v3 reaches the sample-average optimum in 8 seeds against 1, ends
  shorter than v1 in 13 seeds and longer in 1, and goes back to the tour it shook in 16 rounds of
  30 instead of 25. Without the chance constraint it ends shorter in 6 seeds and longer in 1.
- **The environment.** Without the chance constraint the best tours are on time in about half of
  the audit scenarios, and tours of the same length differ widely: with seed 1, v1 and v3 both end
  at 3,482, on time in 672 and in 430 of the 1,000. With it, at 2–3 % more length, they are on
  time in 93–97 % on average.
- **The sample.** Every run with the chance constraint is on time in all 20 scenarios of the world
  (ALLOW is never used), yet the audit gives as little as 89.8 %, the value of the sample-average
  optimum itself.

**The scenarios are recorded once.** A scenario is a pure function of its seed, and the
searchers and their criteria need all M of them at every invocation. Computing them there each
time took most of the run (10,840 times in one run). The abstraction `scenario` computes each once,
from the seed the world recorded, and records its travel times; the searchers read them through a
map binding. What is computed once and reused is thus in the record, on the epistemic axis, with a
criterion that checks it, and not in a cache outside it. The histories of the searchers and the
indicators are those of the earlier version; a run takes about 6 s instead of 16.

## 6. Plan and expected end

Phases 1 and 2; phase 3 until terminal; one KPI step. The world records its 20 seeds first, and
`scenario` the travel times of each (the searchers require them); then R = 10 rounds of S = 3
searchers. The asynchronous form records
ontology v2 before phase 3, the asymmetric form v2 and v3 (versions without gaps). The deterministic
problem is the same system with ALLOW = M: every scenario may fail.

With draw seed 1, world seed 11 and audit seed 999: 349 events. The incumbent goes 3,612 (searcher
1, round 0), 3,504 (searcher 2, round 6), 3 ‰ above the sample-average optimum; it is on time in all
20 scenarios of the world and in 994 of the 1,000 of the audit. Of the 93 repairs, 73 were of a late
city and 20 of a premature one; 26 of the 30 rounds certified the tour they shook.

## 7. Files

```
system.json                      instance (D, A, B, PAIRS), S, R, KMAX, M, ALLOW, RHO, AUDIT, the optima, the three sources, plan, expect
lib.py                           the neighborhood, the scenarios from a seed, the state and value of a tour, the incremental evaluation,
                                 the repair and the descent, the step of a searcher, the criterion, the incumbent, the indicators
generate.py                      how the windows and the precedence pairs were made (not executed by ZTES)
optima.json                      the deterministic and the sample-average optimum (HiGHS, not executed by ZTES)
abstractions/draw/, world/, audit/   [ω] boundary   [τ] well-formed within the budget
abstractions/scenario/           [ω] the travel times of the next recorded seed   [τ] equal to its definition
abstractions/search_1/ … _3/     abstraction.json (I); [ω] v1 synchronous, v2 asynchronous, v3 asymmetric   [τ] a true step of VNS
abstractions/incumbent/          [ω] the best after a round   [τ] equal to its definition
abstractions/kpi/                [ω] indicators   [τ] each equal to its definition
```

## 8. Execution indicators (KPI)

```
rounds 10, moves 92, repairs 93, repairs_false 73, repairs_not_yet 20, returns 26, optima 30,
best [0, 0, 0, 3504], found_by [2, 6], feasible true, on_time 20, audit_on_time 994,
optimum 3492, gap_permille 3, search_invocations 336, search_not_yet 91
```

`repairs_false` and `repairs_not_yet` count the repairs by the status of the tour they repaired;
`on_time` and `audit_on_time` the scenarios of the world and of the audit in which the best tour is
on time; `optimum` is the deterministic optimum when ALLOW = M and the sample-average optimum otherwise.

## References

- Dumas, Y.; Desrosiers, J.; Gelinas, E.; Solomon, M.M. An optimal algorithm for the traveling salesman problem with time windows. *Operations Research* 1995, 43, 367–371.
- Mingozzi, A.; Bianco, L.; Ricciardelli, S. Dynamic programming strategies for the traveling salesman problem with time window and precedence constraints. *Operations Research* 1997, 45, 365–377.
- Savelsbergh, M.W.P. Local search in routing problems with time windows. *Annals of Operations Research* 1985, 4, 285–305.
- Da Silva, R.F.; Urrutia, S. A general VNS heuristic for the traveling salesman problem with time windows. *Discrete Optimization* 2010, 7, 203–211.
- Mladenović, N.; Todosijević, R.; Urošević, D. An efficient general variable neighborhood search for large travelling salesman problem with time windows. *Yugoslav Journal of Operations Research* 2013, 23, 19–30.
- Steele, G.L.; Lea, D.; Flood, C.H. Fast splittable pseudorandom number generators. *OOPSLA* 2014.
- Reinelt, G. TSPLIB: A traveling salesman problem library. *ORSA Journal on Computing* 1991, 3, 376–384.
