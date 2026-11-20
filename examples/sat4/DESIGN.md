# A 4-SAT conflict and a reusable clause

This example executes the two-clause construction in Section 8.3 of the heuristic-search manuscript. It records a local conflict, derives a clause that can be used across branches, and uses that evidence to govern a retry. The input formula has four variables and two clauses of four literals each.

## Formula and evidence

The variable numbers 1 through 4 denote $x,a,b,c$. A negative number denotes a negated literal. The original formula is the conjunction of two clauses.

$$
D_1=(x\lor a\lor b\lor c), \qquad D_2=(\neg x\lor a\lor b\lor c).
$$

The first branch sets $a=b=c=0$. This makes $D_1$ unit and forces $x=1$. Under that branch and its admitted unit, $D_2$ is false, so the branch has no completion. The conflict names the branch and the falsified clause. The corresponding propagation records the reason clause.

The resolution proof uses $D_1$ and $D_2$ as parents and $x$ as the pivot. Its result is $L=(a\lor b\lor c)$. Because both parents are original clauses, the derivation is valid for the entire formula. The retry sets $a=b=0$. At that prefix the two original clauses still have two unassigned literals each. The learned clause is unit and forces $c=1$. The final assignment is $x=a=b=0,\ c=1$ and satisfies both original clauses.

## Abstractions and checks

| Abstraction | Proposal | Admission check |
|---|---|---|
| `branch` | Version 1 proposes the fixed negative-first trial. Version 2 retries the prefix before its last assumption if the learned clause is unit there. | Check consistent assignments and branch order. A retry uses the shorter prefix after a governing event and a checked resolvent. |
| `propagate` | Select the first unit in the visible clauses. | Read the stated reason at the current branch and check that its unique unassigned literal has the proposed sign. |
| `conflict` | Locate a false original clause after propagating the trial. | Check every literal of that clause under the recorded trial and its unit. |
| `learn` | Resolve the original reason and conflict clauses. | Check the original parent indices, complementary pivot and resulting clause. |
| `adapt` | Carry `branch/ontology.v2` after the conflict and resolvent are admitted. | Check the conflict count and the designated version. The substrate binds the carried ontology to the active branch criterion. |
| `witness` | Give a value to the remaining variable and propose a complete assignment. | Check the retry and its unit, consistency and completeness of the assignment, and satisfaction of every original clause. |

Clause indices 0 and 1 refer to the input clauses. The admitted resolvent has index 2 in the visible clause list. Branch indices distinguish the conflict under the first assumptions from the later propagation. The governing event activates the retry rule under R1. R2 checks the proposals and judgments under their original prefixes and specification versions.

## Reproduction

From the repository root, use the ZTES revision in `requirements.txt`.

```sh
python -m ztes check examples/sat4
python -m ztes run examples/sat4 --record sat4-record
python -m ztes verify sat4-record
python -m ztes verify sat4-record --judgments
python -m ztes run examples/sat4 --workers
python -m pytest -q tests/test_sat4.py
```

The expected record has 21 events including setup. During execution it records two branches, two propagations, one conflict, one resolution proof, one change of policy and one satisfying assignment. The tests enumerate all 16 assignments independently. Exactly 14 satisfy the formula, every such assignment satisfies the resolvent, and neither completion of the first branch satisfies the formula.

This worked trace uses one fixed probe and one clause-guided retry. The comparison of occurrence-based and conflict-activity branching proposed in Section 8.3 uses families of formulas and matched search budgets.
