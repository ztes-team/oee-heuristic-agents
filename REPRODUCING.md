# Reproducing the results of the papers

This repository is the executable supplement of two papers.

* **The base paper**: *A Calculus of Execution for Interacting Binary Relations* (Škarić, Ivanović,
  M. Radenković, Prokhorov, Labus, B. Radenković), Preprints 2026, 2026081545, version 4,
  https://doi.org/10.20944/preprints202608.1545.v4. It describes these examples in §8.9 and Table 8,
  and relies on them in Table 10. Section, table and theorem numbers below refer to version 4.
* **The companion paper**: *Observable, Governable, Cooperative: Execution Analytics and Adaptive
  Heuristic Agents in the OEE Calculus* (M. Radenković, Prokhorov, Labus, B. Radenković), in
  preparation. Its measurements come from the scripts listed in the second part of this page. It is
  cited by its title only, because its numbering is not final.

The examples of the base paper that run without heuristics (√2, the Dedekind cut, prime witnesses,
factorization, the payment, exact TSP, the ant colony and the eight defects) are reproduced in
[ztes-minimal](https://github.com/ztes-team/ztes-minimal/blob/v0.1.1/REPRODUCING.md).

```bash
pip install -r requirements.txt          # Python 3.12 or later; ZTES v0.1.1, the release the examples were checked with
python -m pytest -q                      # every check below, in about seven minutes
```

Every `run` ends with `R2  replay of N events: OK` (the whole record replayed from the empty prefix)
and `Expect  OK` (the end stated in `system.json` holds). The terms of the output are those of
ZTES; [its glossary](https://github.com/ztes-team/ztes-minimal/blob/v0.1.1/docs/glossary.md) gives
them next to the terms of the papers. In particular, the output prints Not Yet for an invocation
that gave no candidate, which the base paper calls Pending.

The executions confirm, on these instances, that the construction is realizable, that every
judgment replays, and that results determined by their inputs do not depend on the schedule. They
make no claim of speed.

## The base paper: §8.9 and Table 8

| Table 8 | Command | What it shows | Events | Tests |
|---|---|---|---|---|
| `vns` | `python -m ztes run examples/vns` | three searchers cooperate through the record on fri26 (optimum 937); the incumbent reaches 937 with seed 7 | 390 | `tests/test_vns.py` |
| `vns-atsp` | `python -m ztes run examples/vns-atsp` | the same on the asymmetric ftv38; the asymmetric neighborhood resolved against the record | 1,195 | `tests/test_vns_atsp.py` |
| `vns-tw` | `python -m ztes run examples/vns-tw` | time windows, precedence and recorded travel times; a late city is False, a premature one Not Yet (in the sense of a goal, Definition 6) | 349 | `test_a_late_city_is_false_and_a_premature_one_not_yet` |
| `vns-hk` | `python -m ztes run examples/vns-hk` | 26 city abstractions compute a Held–Karp bound; the optimality of the incumbent is one admitted event | 934 | `tests/test_vns_hk.py` |
| `vns-adaptive` | `python -m ztes run examples/vns-adaptive` | an agent changes first the ontology, then the criterion of the searchers, on recorded evidence (R1) | 393 | `tests/test_vns_adaptive.py` |
| `cptl` | `python -m ztes run examples/cptl` | a certified obstruction justifies a governed change of the route ontology | 21 | `tests/test_cptl.py` |
| `sat4` | `python -m ztes run examples/sat4` | the two-clause example of §7.1: a checked resolvent is reused after a governed change | 21 | `tests/test_sat4.py` |
| `ksat`, PHP(4,3) | `python -m ztes run examples/ksat/php43` | the record ends in a resolution refutation, checked at every step and again by replay | 174 | `test_the_refutation_is_in_the_record_and_replay_finds_a_forged_step` |
| `ksat`, random 3-CNF, 20 variables, 85 clauses | `python -m ztes run examples/ksat/random20 --workers --config examples/ksat/ztes.yaml` | consensus: a model voted for by every clause, each vote an admission under its own criterion | 460 | `test_consensus_is_the_conjunction_of_the_clause_criteria`, `test_workers_meet_the_expected_end_of_the_committed_instances` |

`--record DIR` keeps a record; `python -m ztes explain DIR N` shows the ground of event N, and
`python -m ztes verify DIR` (or `verify DIR --judgments`) replays it.

**PHP(4,3).** Six clauses are learned. One of them is the empty clause, which ends the refutation,
so five are brought in as new abstractions.

### The rows of Table 10 that rest on this repository

| Contribution | Confirmed here by |
|---|---|
| C1 Two interacting relations | `ksat`: a learned clause changes the logic, the clauses being the criteria; `adapt` changes the control, the decision policy (`test_a_learned_clause_brings_in_its_abstraction_and_the_next_round`, `test_the_change_of_policy_changes_the_course_and_not_the_verdict`) |
| C2 Inseparable substrate | governed changes replayed in `vns-adaptive` and `ksat`; R2 for every example |
| C3 Taxonomy of non-termination | the refutation of PHP(4,3): non-convergence certified, not only observed |
| C4 Nondeterminism in the record | under every schedule of independent workers, and with workers killed and started again, each lineage has the history it has under the agenda (`test_the_same_lineages_under_random_schedules_and_killed_workers`; `scripts/trials.py`) |
| C5 Agnosticism | the same Z₀, with no code specific to these examples, executes VNS and CDCL |

## The companion paper

*Observable, Governable, Cooperative: Execution Analytics and Adaptive Heuristic Agents in the OEE
Calculus*, in preparation. Its measurements are read from records, so under the agenda every
number is the same on every host.

| Measurement | Command | Time, as the script states it |
|---|---|---|
| the KPI profile of every form of the searchers | `python scripts/profiles.py` | about two minutes |
| the forms over seeds 1–40, on fri26 and ftv38, with and without the chance constraint, the adaptive agent against the fixed forms, the shares of variance of algorithm and environment | `python scripts/sweeps.py` | about twenty minutes |
| runs by workers under random schedules and with workers killed | `python scripts/trials.py` (`--quick`: minutes) | about half an hour |
| execution and both replays of every example, medians of three | `python scripts/timings.py` | |
| CPTL: the native dynamic program, flat samples and checked runs | `python scripts/benchmark_cptl.py` | |
| ksat: native and checked runs, replay, record size | `python scripts/benchmark_ksat.py` | |
| the ksat system of any DIMACS formula | `python scripts/ksat_system.py formula.cnf DIR` | |
