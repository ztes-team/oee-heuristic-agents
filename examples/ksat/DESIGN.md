# ksat: k-SAT as evolutive consensus

## What the example shows

A CNF formula $F = D_1 \land \dots \land D_m$ is lifted so that every clause is its own abstraction. The criterion $\tau_i$ of clause $D_i$ is the authority over that clause and nothing else. The composite criterion is the formula itself, $\tau = \tau_1 \land \dots \land \tau_m$, evaluated over the shared record. This is evolutive consensus in the sense of the FUEE paper (Section 8; DOI 10.2298/FUEE2604723R, [the article on the journal's site](https://casopisi.junis.ni.ac.rs/index.php/FUElectEnerg/article/view/14966)). The record ends in one of two ways:

- **Consensus (SAT).** Every clause abstraction admits a vote for the same total assignment. Voting is execution: each vote is an admission under $\tau_i$, and the consensus is the record itself.
- **Refutation (UNSAT).** The empty clause is learned. Every learned clause carries a resolution derivation that its criterion checked, so the record contains a resolution refutation of $F$. The replay checks it again in both modes. Non-convergence is then not only observable: it is certified.

Learned clauses are not kept in a data structure. Each non-empty learned clause becomes a new abstraction, which the learn event brings in by carrying its specifications. The same event carries a new version of `round` whose horizon includes the new clause. The composite criterion grows under governance (R1) by clauses that $F$ implies, which is the τ-evolution of FUEE (ii). The search procedure is conflict-driven clause learning (CDCL). Its parts are distributed over abstractions that wait for each other only through the record.

`sat4` remains the worked trace of Section 4.3 of the paper. ksat is the general method.

## The abstractions

| Abstraction | Proposal (ontology, strategy) | Admission check (criterion) |
|---|---|---|
| `c1 … cm` | One per clause of $F$. On the latest frame: the literal the clause forces, a conflict if it is false, a vote if the frame is quiet and total and the clause is satisfied. | $\tau_i$: once per round, for itself, and true of its own clause on the frame. A unit is the only unassigned literal of a clause that is not satisfied, a conflict is a clause with every literal false, and a vote is a clause satisfied on a total frame. |
| `l1, l2, …` | Learned clauses, brought in by `learn`, with the same specifications as `c1` and their own literals. | The same $\tau_i$ for the learned clause. |
| `round` | The next frame, a function of the record (see below). | The frame is that function. The round chooses nothing, so its criterion is its definition. |
| `decide` | Policy v1, by occurrence: the literal that occurs most often in clauses not yet satisfied. When every clause is satisfied, the remaining variables are set false in one decision. Version 2, carried by `adapt`, chooses by conflict activity: the literal that occurs most often in the learned clauses. While a change is due and not yet decided, version 1 waits for `adapt`. | On a quiet frame that is not total, once per round: a non-empty, consistent set of literals of unassigned variables of $F$. Which ones is the policy's choice (D2). |
| `learn` | On a frame with a conflict: analysis by resolution to the first unique implication point, the backjump level, and the carried specifications. | Once per conflict: the chain derives the stated clause by resolution from clauses already known, starting from a false clause of the frame (D2: any derivation is admitted, not only the 1-UIP one). The level is a level of the trail, the name is the next one, and the carried specifications are exactly the new clause abstraction and the next version of `round`. |
| `adapt` | Once the K-th clause is learned, carry version 2 of the ontology of `decide`. | Once, on the evidence of at least K admitted conflicts, stated truly, carrying exactly the designated version. The criterion of `decide` does not change: both policies are judged by version 1 (D2). |
| `verdict` | SAT when all clauses voted on a frame, UNSAT when the empty clause is learned. | Once. SAT: every clause abstraction of $F$ voted on the frame, and the model is its trail, a consistent total assignment that satisfies every clause of $F$. UNSAT: the empty clause was admitted under the criterion of learn. |

## A round

A frame is the shared state of one round. It holds:

- the trail: the assigned literals in order, each with its decision level and its reason, which is the clause that forced it or a decision;
- the clauses found false;
- whether the frame is quiet (no clause is unit or false on it) and whether it is total;
- after a vote, the names of the voters.

The next frame is computed as follows:

1. The first frame is empty.
2. After a conflict, the round waits for the learned clause. The new epoch starts on the trail cut back to the learned clause's level, where the new clause abstraction forces its literal.
3. Otherwise the round waits until every clause that has something to say about the frame has spoken.
   - If they all voted, the frame is the consensus.
   - If none has anything to say, the round waits for the decision of this round and adds its literals at the next level.
   - Otherwise it adds the forced literals in the order of the clauses. A unit whose literal is already false counts as a conflict.

Each clause speaks about a frame that is already closed, and the round closes only when every expected speaker is in. Every realization is therefore a function of complete horizons, and the record is the same under every schedule (Theorem K). Workers run without any synchronization other than the record.

## Two forms of adaptation

Every new specification enters the record the same way: an abstraction proposes it with a reason, and the criterion of that abstraction admits the change only on that reason, under R1. Z₀ treats all abstractions alike and knows no kind called governing. ksat uses the mechanism twice, on different objects.

- **`learn` changes what is checked.** The reason is a resolution derivation. The change adds a criterion $\tau_i$ that $F$ implies and extends the horizon of `round`. The models are unchanged, so the composite criterion grows monotonically, as Corollary 1 of the FUEE paper assumes.
- **`adapt` changes what is tried.** The reason is the number of admitted conflicts. The change is a new ontology of `decide`, and no criterion changes.

The second form is included as a demonstration with one fixed trigger. The comparison proposed in Section 10.3 of the paper is left for further work. That comparison uses a window of W decisions, families of formulas and matched budgets. It needs no new mechanism, only the trigger and a measurement.

## Strategy and correctness

The criteria decide what is correct. The ontologies decide what is tried:

- the decision policy;
- the 1-UIP analysis;
- the backjump level;
- setting the remaining variables at once.

A different policy changes the course of the search but not what any criterion admits. Termination is a property of the strategy. With asserting learned clauses, CDCL does not repeat a trail, so it terminates. The criteria do not check termination. If a strategy failed to converge, the record would show it as Not Yet or stop at the admission limit, never with a wrong verdict. The example has no restarts, no clause deletion and no watched literals. Every clause abstraction is evaluated on every frame, which is the cost of cooperation without a central propagator. NP-hardness is a property of the reduct. The lifting is measured by events, learned clauses and replay, not by the asymptotics of the reduct.

## Measurements

`scripts/benchmark_ksat.py` runs each formula natively, in ZTES under the agenda with the record in memory, and in both replays. It checks that the record contains exactly the frames, decisions, learned clauses and verdict of the native run. It was measured with Python 3.13 in a Linux container, on random 3-CNF at the ratio $m/n \approx 4.26$ (seeds 0–2) and on PHP(4,3).

| Formula | Events | Learned | Abstractions | Native | Run | Full replay | Replay of judgments | Record | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| PHP(4,3) | 174 | 6 | 32 | 0.010 s | 0.28 s | 0.28 s | 0.19 s | 0.44 MB | UNSAT (policy changed) |
| random 3-CNF n=20 m=85 seed=0 | 450 | 7 | 97 | 0.019 s | 0.89 s | 0.67 s | 0.42 s | 1.02 MB | SAT (policy changed) |
| random 3-CNF n=20 m=85 seed=1 | 460 | 6 | 96 | 0.021 s | 0.76 s | 0.59 s | 0.45 s | 1.00 MB | SAT (policy changed) |
| random 3-CNF n=20 m=85 seed=2 | 308 | 0 | 90 | 0.010 s | 0.38 s | 0.32 s | 0.28 s | 0.75 MB | SAT |
| random 3-CNF n=30 m=128 seed=0 | 449 | 0 | 133 | 0.016 s | 0.60 s | 0.44 s | 0.56 s | 1.09 MB | SAT |
| random 3-CNF n=30 m=128 seed=1 | 800 | 14 | 147 | 0.053 s | 2.13 s | 1.52 s | 1.07 s | 1.70 MB | SAT (policy changed) |
| random 3-CNF n=30 m=128 seed=2 | 449 | 0 | 133 | 0.014 s | 0.71 s | 0.58 s | 0.50 s | 1.08 MB | SAT |
| random 3-CNF n=40 m=170 seed=0 | 952 | 23 | 197 | 0.108 s | 3.68 s | 2.12 s | 1.24 s | 2.38 MB | UNSAT (policy changed) |
| random 3-CNF n=40 m=170 seed=1 | 1486 | 39 | 213 | 0.195 s | 6.00 s | 2.85 s | 1.82 s | 3.21 MB | UNSAT (policy changed) |
| random 3-CNF n=40 m=170 seed=2 | 1630 | 38 | 212 | 0.208 s | 6.79 s | 3.14 s | 1.88 s | 3.23 MB | UNSAT (policy changed) |
| random 3-CNF n=50 m=213 seed=0 | 737 | 0 | 218 | 0.036 s | 1.37 s | 0.84 s | 0.97 s | 1.76 MB | SAT |
| random 3-CNF n=50 m=213 seed=1 | 2900 | 68 | 285 | 0.662 s | 17.07 s | 5.84 s | 3.91 s | 5.45 MB | UNSAT (policy changed) |
| random 3-CNF n=50 m=213 seed=2 | 988 | 8 | 226 | 0.086 s | 2.56 s | 1.27 s | 0.97 s | 2.20 MB | SAT (policy changed) |

*Learned* counts the learned clauses; each non-empty one is an abstraction brought in during the run, and *Abstractions* counts all that executed. *Native* calls the helpers of `lib.py` in a plain loop. *Run* is the checked execution with its record, under the agenda. *Full replay* re-derives every candidate and judges it again. *Replay of judgments* only re-judges the recorded candidates. *Record* is the record's size in canonical JSON, most of it the specifications. Each clause abstraction has two specifications, and every learned clause carries four. In "policy changed", `adapt` acted, after the third learned clause.

- **Checked run against native.** The checked run takes 26–51 times as long as the native one.
- **Full replay against run.** The full replay takes from a third of the time of the run to all of it, the smaller share in the runs with many conflicts.
- **Growth.** Time grows with the number of conflicts more than with the size of the formula. Every frame is offered to every clause abstraction, and every learned clause rebuilds the map of speeches for the new version of `round`.

The disk store with ninety workers is another matter. Every worker polls the shared record, and the run of random20 does not finish within the default timeout of the coordinator (60 s). With `examples/ksat/ztes.yaml` the record is kept in memory, and the same run takes about 7 s.

## Tests

`tests/test_ksat.py` makes every check against definitions written in the test, independently of `lib.py`: the assignments of a formula, a DPLL procedure and a checker of resolution proofs.

1. **The committed instances.** `php43` and `random20` are exactly what `scripts/ksat_system.py` writes, and their `lib.py` is this one. They meet their expected end under the agenda and by workers, and replay in both modes.
2. **Verdicts.**
   - Against all assignments on random k-CNF with k = 2–5, below, at and above the threshold.
   - Against DPLL on random 3-CNF with n = 20–30.
   - Edge cases: an empty clause, contradicting units, a chain of units, repeated literals, a tautology, an unused variable, PHP(3,2).
   - A SAT verdict is a model. An UNSAT verdict ends a refutation that the checker accepts, and every learned clause holds in every model of the formula.
3. **The native execution.** On eight formulas, with and without the change of policy, the record contains exactly the frames, decisions, learned clauses and verdict of `native()`.
4. **Consensus.** Every clause abstraction, the learned ones included, voted on the final frame, each vote admitted under its own $\tau_i$. On all 512 assignments of a formula with 9 variables, the verdict admits exactly the one model that every clause voted for. The verdict refuses a frame with a vote missing, and a vote is refused on a frame that is not total or on which the clause is false.
5. **The refutation.** The checker accepts the record of PHP(4,3). A forged step of a chain fails replay at that event in both modes.
6. **Governance.**
   - Every non-empty learned clause carries exactly its two specifications and the next version of `round`. They are active from its event and not before. The next frame is made by the new version of `round`, whose horizon includes the new clause, and the new clause speaks first on the new epoch.
   - $\tau_{root}$ refuses a version with a gap and an ontology without its criterion. The criterion of learn refuses carried specifications that are not exact.
   - `adapt` acts after the third learned clause. Every decision before it is made by version 1 of `decide` and every one after it by version 2, all judged by the same criterion (D2). Between the third conflict and the change, version 1 proposes nothing. The criterion of `adapt` refuses false evidence, a change before the threshold, a second change and another version.
   - With and without the change, the course of the search differs and the verdict does not.
7. **The checks applied to every example.**
   - An interrupted run continues to the same record, after every event of PHP(3,2) with the change of policy after the first conflict, and before every carrying event of PHP(4,3).
   - On both committed instances, workers under random schedules give the lineages of the agenda. So do workers that are killed and started again, including the workers of learned clauses.
8. **What only one rule refuses.** Each forged derivation states exactly what its steps give and carries what that clause must carry. Only the broken rule can then refuse it: a start that is not a false clause, a parent without the step's literal, a step without a clash, a tautology. With the change of policy due and an `adapt` that never decides, `decide` makes no decision after the first learned clause.
9. **The criteria as authorities.**
   - Speeches for another clause, out of turn, a second time, with another literal or of another kind are refused.
   - Any correct decision is admitted, also of several literals. An empty, inconsistent, unknown, assigned or untimely decision is refused.
   - A derivation one resolution step longer than the 1-UIP one is admitted, with what it must carry (D2). Another name, level, start, result or a shortened chain is refused.
   - Forged frames and verdicts are refused.

**Mutation tests.** 36 mutants of `lib.py` each weaken or alter one rule:
- every criterion;
- the round;
- the analysis;
- what a learned clause carries;
- the waiting of `decide`;
- the policies;
- the verdict.

Every mutant fails at least one test of `tests/test_ksat.py`. Seven survived the first version of the tests:
- a resolution that yields a tautology;
- a step whose literal is not in its parent;
- a step without a clash;
- a derivation that does not start from a false clause of the frame;
- `decide` that does not wait for `adapt`;
- a change of policy before the threshold, with the evidence stated truly;
- a verdict that does not check the model against the formula.

A forged candidate in which only the broken rule differs now refuses each of them. So does a run in which `adapt` never decides.

## Layout and reproduction

- `examples/ksat/lib.py`: the helpers.
- `examples/ksat/php43.cnf`, `random20.cnf`: the committed formulas in DIMACS. They are `pigeonhole(4, 3)` and `random_kcnf(20, 85, 3, 1)` of the script.
- `examples/ksat/php43/`, `random20/`: their systems in the standard form, one directory per clause abstraction, written by the script with their expected end.
- `examples/ksat/ztes.yaml`: the configuration for workers. About ninety workers poll the record, so it is kept in memory.
- `scripts/ksat_system.py`: the system of any DIMACS formula, and `native()`.
- `scripts/benchmark_ksat.py`: the measurements above.

```
python -m ztes run examples/ksat/php43
python -m ztes run examples/ksat/random20
python -m ztes run examples/ksat/random20 --workers --config examples/ksat/ztes.yaml
python scripts/ksat_system.py formula.cnf my-system --name mine
python scripts/benchmark_ksat.py
python -m pytest -q tests/test_ksat.py
```
