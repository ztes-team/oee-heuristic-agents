# Parity and budget on a path with recorded precedence

The causal parity–threshold lock (CPTL) is the exact reference case in Section 3 of the heuristic-search manuscript.
A local check rules out every extension of a greedy trial, and a one-bit separator supports an exact solution (RQ1).
The governing criterion uses the obstruction to admit a policy change whose activation and subsequent steps can be replayed (RQ2).
A native implementation of the same recurrence gives a baseline for the cost of checked execution and replay (RQ3).

## 1. Problem

Every stage has four bits $x_1,x_2,x_3,x_4$. The weight vector is $(4,3,4,3)$ in tenths of a unit, the weight must be strictly below 8 in these units, and $x_1\oplus x_2\oplus x_3\oplus x_4=1$. Three active bits weigh at least 10. Every feasible stage therefore activates exactly one bit.

Each stage specifies one of two local precedence chains. In **input-first** order, the decision on $x_3$ depends on the earlier decision on $x_1$. In **guard-first** order, the dependency runs the other way. The two remaining decisions follow these two. The rule is that $x_1=1$ followed by the dependent decision on $x_3$ requires $x_2\oplus x_4=1$. Hence the same assignment $(1,0,0,0)$ is admissible with guard-first precedence and fails with input-first precedence. The order in a stage witness represents these declared dependencies. Its validity is checked against the instance's recorded gate mode.

Adjacent stages share the bit $b_i=x_4^{(i)}=x_1^{(i+1)}$. The boundary conditions are $b_0=0$ and $b_k=1$.
The objective is to maximize $\sum_{i=1}^k b_i$. The worked instances have at least two stages and an input-first
second stage so that the greedy trial has a certified obstruction.

## 2. Decomposition

The projected local relation pairs an incoming bit and a gate mode with feasible outgoing bits. Input 0 allows output 0 or 1. Input 1 allows output 0 under guard-first precedence and has no transition under input-first precedence. This follows from the one-active-bit property and the order rule. The tests independently enumerate all 16 assignments for each gate mode to check this projection.

Let $T_i(a)$ be the feasible outputs of stage $i$ at incoming bit $a$. The suffix row holds $V_i(a)$,
the best remaining link sum, and $N_i(a)$, the number of feasible remaining link words. The terminal row
has value 0 and count 1 for input 1. An infeasible suffix has value $-\infty$ and count 0. The implementation
stores a best value of -1 when the count is zero and omits those continuations when taking the maximum.

$$
V_i(a)=\max_{b\in T_i(a)}\{b+V_{i+1}(b)\}, \qquad
N_i(a)=\sum_{b\in T_i(a)}N_{i+1}(b).
$$

The first output partitions the feasible words. A stage witness and the corresponding suffix can be joined
when their boundary bits agree. This gives at most four transition checks per stage, with arbitrary-precision
integers for the counts. Record handling and replay have their own measured costs.

## 3. Lifting

| Abstraction | Ontology | Admission criterion | Horizon |
|---|---|---|---|
| `route` | Version 1 proposes one locally admissible trial with $b_1=1$. Version 2 proposes an actual next stage using the suffix certificate. | Check the stage witness for parity, budget and precedence. For a committed step, check the incoming link and the claimed optimum against its suffix rows. | Trial and committed route, plus suffix evidence. |
| `adapt` | After the trial, propose the designated ontology version 2. | Verify that neither output extends the trial through stage 2 and that the exact allowed version is carried. ZTES also checks lineage and binds the carried ontology to the active route criterion. | Recorded trial and prior governance decisions. |
| `suffix` | Propose the next row working from the terminal boundary. | Check both entries against the next recorded row. | The last suffix row. |

## 4. Design decisions

The trial is a checked claim about one module. At stage 2 its link would force $x_1=1$ with input-first precedence, so the remaining budget and parity cannot satisfy the order rule. `adapt` checks the empty set of continuations for this prefix and admits a change of the proposal rule under R1. The certified route begins at the original boundary. R2 replays the trial, the decision carrying the version, and every later admission against the historical prefix and authority.

An ordinary dynamic program with the same two states uses the same structural inference. Each flat sample selects an entire word of $k$ link bits uniformly and independently, and receives the terminal feasibility verdict. If $A_k$ is the number of feasible words, its success probability per draw is exactly $A_k/2^k$. With the benchmark's gate pattern and $k=3m$, the input-first gates force $b_1,b_4,\ldots,b_{k-2}$ to zero. Of the two bits following each forced zero, at most one can be active. Each nonterminal pair has three choices, and the terminal pair is fixed by $b_k=1$. Each pair can contribute one to the objective, giving optimum $m$. Hence $A_{3m}=3^{m-1}$ and the per-draw success probability is $(3/8)^m/3$. The matched dynamic program controls for the advantage of exposing the separator.

## 5. Plan and expected end

The standard plan admits version 1 of each criterion and ontology, then executes them. In the six-stage instance, the locally admissible trial fails to extend, a single governing event carries `route/ontology.v2`, six suffix rows are admitted, and the route commits links $0,1,0,0,0,1$. There are three feasible link words and the optimum is two. The expected record has 21 events including setup. Replay must reproduce every admission.

## 6. Reproduction and measurements

```bash
python -m ztes check examples/cptl
python -m ztes run examples/cptl --record cptl-record
python -m ztes verify cptl-record
python -m ztes verify cptl-record --judgments
python scripts/benchmark_cptl.py 6 20 100 500 --samples 4096 --seed 7
python -m pytest -q tests/test_cptl.py
```

The benchmark uses input-first order at stages 2, 5, 8 and so on. It reports the exact feasible count, flat sample hits, the native dynamic program and certificate-check times, OEE execution and full replay times, event count and serialized record size. Use `--peak-memory` to record peak traced Python allocations in a separate OEE execution. Runtime comparisons depend on the host and the record backend. This study compares a specified greedy step, a specified flat sampler, and a native path algorithm using the same structure.

One pilot run on Windows used the pinned ZTES and its in-memory store, with 4,096 samples at each size and seed 7. The two exact implementations produced the same suffix rows and committed route at every tested size. Times are observations from this run.

| Modules | Optimum | Feasible flat samples | Native solve and check (ms) | OEE execution (s) | Full replay (s) | Events |
|---:|---:|---:|---:|---:|---:|---:|
| 6 | 2 | 170 | 0.10 | 0.029 | 0.020 | 21 |
| 20 | 7 | 3 | 0.19 | 0.025 | 0.025 | 49 |
| 100 | 34 | 0 | 1.63 | 0.098 | 0.077 | 209 |
| 500 | 167 | 0 | 7.79 | 0.943 | 0.955 | 1009 |

At 500 modules the record encoded as JSON occupied 439,034 bytes. A separate traced run measured 1,831,199 bytes of peak Python allocations. The timed native baseline pays for computing and checking the path certificates. The OEE run also admits and stores each event, including the authorization of the policy change.

For context on bounded-width constraint solving, see [Freuder, *Complexity of K-Tree Structured Constraint Satisfaction Problems*](https://cdn.aaai.org/AAAI/1990/AAAI90-001.pdf).
