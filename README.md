# OEE-heuristic-agents
Heuristic agents lifted into the OEE calculus of execution on the ZTES substrate: metaheuristics as interacting abstractions over one record, starting with cooperative parallel variable neighborhood search. Executable supplement to the paper.

A heuristic is lifted here as a system of abstractions: each step of the method is a candidate
proposed by an ontology [ω], admitted by a criterion [τ] and appended to one record C. The loops
of the method become interaction through the record, a claim about a whole neighborhood becomes an
admitted certificate, and every run replays (R2). The systems are executed by
[ZTES](https://github.com/ztes-team/ztes-minimal), the minimal zero-tier execution substrate of the
paper *A Calculus of Execution for Systems of Interacting Binary Relations*, installed as a
package. ZTES contains nothing specific to these examples: everything specific to a heuristic is
in its directory, as JSON specifications and one `lib.py` of bounded functions.

| Example | Method | Abstractions | Events | What it shows |
|---|---|---|---|---|
| [`vns`](examples/vns/DESIGN.md) | variable neighborhood search by three cooperating searchers on fri26 (TSPLIB, symmetric, optimum 937) | 5 | 390 | every loop of VNS is interaction; each local optimum is a certificate; the criterion admits any step of VNS (D2); synchronous cooperation gives the same record under every schedule, with no lock, no message and no master process; the asymmetric neighborhood and the certificate relative to the record |
| [`vns-atsp`](examples/vns-atsp/DESIGN.md) | the same on ftv38 (TSPLIB, asymmetric, optimum 1,530) | 5 | 1,195 | a neighborhood that keeps the direction of every arc it does not cut; nothing in the lifting changes; the asymmetric neighborhood reaches a shorter tour |
| [`vns-tw`](examples/vns-tw/DESIGN.md) | the same on ftv38 with time windows and precedence constraints, under a recorded environment | 8 | 349 | a late city is False and a premature one Not Yet, and the prefix order gives the repair rule; a chance constraint on recorded scenarios and an audit of the probability of being on time; three sources of chance (algorithm, schedule, environment) in one record |
| [`vns-hk`](examples/vns-hk/DESIGN.md) | the searchers of `vns` beside 26 city abstractions that compute a Held–Karp lower bound on fri26 | 33 | 934 | heterogeneous agents in one record: the cities are the dual, each moves its own potential, and a minimum 1-tree is admitted in each round; the bound proves the incumbent optimal, a claim about every tour made one admitted event; aimed at the incumbent the cities need 18 rounds, aimed at the starting tour 330 |
| [`vns-adaptive`](examples/vns-adaptive/DESIGN.md) | the searchers of `vns` and an agent that changes their form during the run | 6 | 393 | an adaptive heuristic agent: after every round it reads the returns in the record and, past a tolerance, carries the next form of the searchers, first a change of ontology, then of criterion; its criterion is the authority over what may change and on what evidence; every change is in force from the start of a round under every schedule, and replays |
| [`cptl`](examples/cptl/DESIGN.md) | parity and a strict budget along a path with declared precedence | 3 | 21 | a locally valid trial has a certified obstruction in the next stage. A governed change uses the recorded two-state suffix certificates to build an optimum. A native dynamic program and flat sampling supply comparisons. |
| [`sat4`](examples/sat4/DESIGN.md) | propagation and resolution on two 4-CNF clauses | 6 | 21 | a conflict closes one branch. A checked resolvent is reused after a governed change and forces a literal in the retry. |

## vns: variable neighborhood search by cooperating searchers

Three searchers run VNS on fri26 (26 cities). A step is a shake in the k-th neighborhood, an
improving 2-opt move, or the certificate of a local optimum, and each is an admitted event: the
descent, the change of neighborhood and the rounds are not loops in a body, and k is read from the
record. The criterion admits any step of VNS, not only the one the strategy chose (D2).

In the plan the searchers cooperate synchronously: each shakes the incumbent of the round it has
finished and waits for it, so every lineage has the same history under every schedule of the
workers. Version 2 of the three searcher ontologies makes the cooperation asynchronous (the best
optimum certified so far, as it stands): the same criteria, and another valid course under each
schedule. These are the two classical forms of cooperative parallel VNS (replicated shaking, and
cooperation through a central memory); here the master process is replaced by a horizon. With seed
7 the incumbent goes 1,004, 985, 937, the last found by searcher 3 from a tour of searcher 1; over
forty seeds each form reaches the optimum in 22.

The 2-opt neighborhood is symmetric: the inverse of a shake is an improving move of the shaken tour,
and in about half of the rounds the descent takes it and certifies the very tour it shook (the
indicator `returns`: 14 of 30 with seed 7). Version 3 adapts VNS to the asymmetric space of
execution: the neighborhood of a tour is resolved against the record, and the descent does not take
a move to a tour the finished rounds have recorded while another improving move exists. The
criterion is unchanged, the record is still the same under every schedule, and over forty seeds the
optimum is reached in 28 instead of 22. Version 4 with criterion v2 adds a certificate relative to
the record (every shorter neighbor is already recorded), an upper set of the prefix order: over
forty seeds the returns fall from about 15 per run to 2 in all, both shakes that cancelled, at
the same quality. The design, the derivation of the result and the
measurements are in [`examples/vns/DESIGN.md`](examples/vns/DESIGN.md).

## vns-atsp: the same on an asymmetric instance

On ftv38 (39 cities) a tour and the same cycle read backwards have different lengths, so 2-opt,
which reverses a segment, does not fit. The neighborhood exchanges two adjacent segments, which
keeps the direction of every arc it does not cut; the abstractions, bindings, plan and criteria are
those of `vns`. With seed 2 the synchronous form stops at 1,547 (11 ‰ above the optimum) and the
asymmetric neighborhood reaches 1,532 (1 ‰), with 15 returns instead of 20. See
[`examples/vns-atsp/DESIGN.md`](examples/vns-atsp/DESIGN.md).

## vns-tw: time windows, precedence and a recorded environment

On ftv38 every city gets a time window and ten pairs of cities a precedence. A city reached after
its window closes is late, and no change after it can repair that (False, an upper set of the
prefix order); a city visited before one it must follow is premature (Not Yet). Every step records
which of the two stops its tour, and the repair cuts before it. The travel times vary by scenario:
the boundary `world` records 20 seeds, `scenario` the travel times of each, once (the searchers read
them from the record), a tour must be on time in all but 2 of the scenarios, and
the boundary `audit` records one more seed for 1,000 scenarios the search never sees. The
deterministic optimum (3,415) is on time in 457 of these; the sample-average optimum (3,492) in all
20 scenarios of the world but only 898 of the audit, so the sample overstates the probability it
estimates. Over 20 seeds the asymmetric neighborhood (v3) reaches the sample-average optimum in 8
runs, v1 in 1. The algorithm, the schedule of the workers and the environment are three sources of
chance in one record: for the synchronous forms the share of the schedule is exactly 0, for the
asynchronous form it is measured. See [`examples/vns-tw/DESIGN.md`](examples/vns-tw/DESIGN.md).

## vns-hk: the cities prove the incumbent optimal

The searchers of `vns` keep their tours; beside them, every city of fri26 is an abstraction with a
potential. In each round an abstraction `tree` records the minimum 1-tree under the potentials,
and its weight minus twice their sum is a lower bound on every tour. Each city then moves its own
potential, up if its degree in the tree was above 2, down if it was a leaf, by a step aimed at the
incumbent of the searchers. The criterion of a city admits any move in that direction, since every
potential gives a valid bound; that of the tree admits any minimum 1-tree. In round 18 the bound is
936.10, and the abstraction `proof` records that no tour is shorter than the incumbent, 937. Every
horizon is complete before it is read, so the 33 workers give the same history of every lineage
under every schedule. Aimed at the starting tour instead (ontology v2 of the cities, the same
criteria), the bound needs 330 rounds. See [`examples/vns-hk/DESIGN.md`](examples/vns-hk/DESIGN.md).

## vns-adaptive: an agent changes the form of the search

In the other examples a form of the searchers is put in force by the experimenter, before the
searchers start. Here one more abstraction, `adapt`, decides after every round whether to change
it, from the returns the record holds since the current form came into force. Past a tolerance of
two its candidate carries the next form: first ontology v2 of the three searchers (the asymmetric
neighborhood, criteria unchanged), then criterion v2 and the ontology v3 bound to it (the
certificate relative to the record). Its criterion is the authority. It admits keeping the form at
any time, and the next form, carried exactly, only past the tolerance and on the returns the record
gives; it admits nothing else. With seed 7 the forms change from rounds 3 and 7, and the incumbent
reaches 937 in round 4. Over seeds 1–40 the agent ends shorter than its starting form in 7 seeds and
longer in 2, but not shorter than the best fixed form chosen in hindsight. The searchers wait for the
decision of each round, so a change is at the same position of every lineage under every schedule.
See [`examples/vns-adaptive/DESIGN.md`](examples/vns-adaptive/DESIGN.md).

## CPTL as the exact reference case

Section 3 of the heuristic-search manuscript uses CPTL to connect structural inference, policy change
and measured execution cost. A local proof rules out the greedy trial and supplies the evidence for
activating a new route ontology. The same two-state recurrence gives the optimum in the native and
ZTES runs. The [case study](examples/cptl/DESIGN.md) gives the proof, replay commands and benchmark.

## sat4

The two-clause example from Section 8.3 of the heuristic-search manuscript records a branch conflict,
checks a resolution proof from the original clauses, and reuses the derived clause during a governed
retry. The [design](examples/sat4/DESIGN.md) gives the evidence for each decision, the expected SAT
witness and the replay commands.

## Running

Python 3.12 or later.

```
pip install -r requirements.txt               # ZTES from GitHub, at the commit the examples were checked with
python -m ztes run examples/vns               # under the agenda: the report, R2 and the expected end
python -m ztes run examples/vns --workers     # phase 3 by one worker per abstraction
python -m ztes run examples/vns --record DIR  # keep the record; then: python -m ztes explain DIR 220
python -m ztes run examples/vns-atsp
python -m ztes run examples/vns-tw         # about 6 s, and as long for R2
python -m ztes run examples/vns-tw --record DIR && python -m ztes verify DIR --judgments
                                              # R2 by re-judging the recorded steps only: 0.6 s
python -m ztes run examples/vns-hk
python -m ztes run examples/vns-adaptive
python -m ztes run examples/cptl
python -m ztes run examples/sat4
python scripts/benchmark_cptl.py               # native DP, flat samples and checked OEE runs
python -m pytest
python scripts/profiles.py                    # the KPI profiles of every form, about two minutes
```

`scripts/profiles.py` runs each form once and reads its KPI profile from the record (Table 2 of
the paper): the completed and the Pending invocations of the searchers, admission compression,
ontological compression (the improving moves of every recorded descent step, enumerated after
the run), the reuse of certified optima by the shakes, and the deferred resolution ratio of the
searchers and of the incumbent.

The other forms are the same plan with a governed change of the three searchers before phase 3.
τ_root records the versions of a specification without gaps, so a form records the versions
before its own in the same change:

```python
from ztes.substrate.store import MemoryStore
from ztes.system import workers
from ztes.system.system import System

def form(*keys):
    govern = [f"search_{i}/{key}" for key in keys for i in (1, 2, 3)]
    return [{"phase": 1}, {"phase": 2}, {"govern": govern}, {"phase": 3}, {"kpi": True}]

asynchronous = form("ontology.v2")
asymmetric = form("ontology.v2", "ontology.v3")
relative = form("ontology.v2", "ontology.v3", "criterion.v2", "ontology.v4")     # vns only

System("examples/vns").run(MemoryStore(), plan=asymmetric)                     # under the agenda
workers.run(System("examples/vns"), MemoryStore(), plan=asynchronous)         # by workers: the course depends on the schedule
```

## Tests

`tests/test_vns.py`, `tests/test_vns_atsp.py`, `tests/test_vns_tw.py`, `tests/test_vns_hk.py` and `tests/test_vns_adaptive.py` apply to the examples the checks ZTES applies to
each of its own, and check what the `DESIGN.md` files claim.

`tests/test_cptl.py` checks the local projection and exact path solution against exhaustive
enumeration. It also verifies both replay modes and checks which ontology is active at each
side of the governing event.

`tests/test_sat4.py` checks the learned clause on all 16 assignments and replays the executed trace.
It also checks the version boundary and verifies that the criteria refuse incorrect evidence and
admit any correct branch, the choice of branch being the active ontology's.

`tests/test_sat4_ksat.py` checks sat4 beyond its instance, against all assignments. It runs the same
trace for every k from 2 to 8 and checks the criteria on random k-CNF formulas. It also checks
evolutive consensus in the sense of the FUEE paper (Section 8,
[doi:10.2298/FUEE2604723R](https://doi.org/10.2298/FUEE2604723R)): the composite criterion is the
conjunction of the clause criteria over the shared record.

| Test | What it checks |
|---|---|
| `test_is_well_formed`, `test_meets_its_expected_end` | the static check of the system; the end stated in `expect` (events, states, the incumbent, the indicators) |
| `test_replays_in_process_and_over_http` | R2; the same record when every abstraction is an HTTP service |
| `test_an_interrupted_run_continues_to_the_same_record` | the run, cut after any of six events and started again, gives the same record |
| `test_by_workers_on_every_store` | phase 3 by workers on memory, diskcache and Redis (fakeredis): R2, the end states, `expect` |
| `test_every_step_is_a_step_of_vns_and_every_local_optimum_is_certified` | every move shortens the tour; no 2-opt neighbor of a certified optimum is shorter (checked independently of `lib.py`); the incumbent of round r is the shortest optimum up to r; the end is 937 |
| `test_criterion_admits_any_step_of_vns_and_refuses_the_rest` | D2: another improving move is admitted; a longer move, a false certificate, a shake of an uncertified tour or beyond N₃ is refused |
| `test_asynchronous_cooperation_changes_three_ontologies_and_no_criterion` | the two forms have the same criteria; the asynchronous one reaches 953 in round 1, the synchronous one 985 |
| `test_synchronous_cooperation_gives_the_same_histories_under_every_schedule` | under random schedules of the workers every lineage has the history it has under the agenda, while the order of the record differs |
| `test_synchronous_cooperation_survives_killed_workers_with_the_same_histories` | workers killed at random and started again: the same histories; only time is lost |
| `test_asynchronous_cooperation_is_verifiable_under_every_schedule` | under random schedules every record replays and the incumbent never gets longer |
| `test_the_symmetric_neighborhood_goes_back_and_the_asymmetric_one_less` | `returns`, counted independently of `lib.py`: 14 under v1, 11 under v3 |
| `test_the_asymmetric_descent_avoids_the_recorded_tours` | every step of the descent under v3 is the first improving move to a tour the finished rounds have not recorded, or the first improving move if there is none (checked independently of `lib.py`) |
| `test_the_asymmetric_neighborhood_changes_three_ontologies_and_no_criterion` | v3 has the criteria of v1; the incumbent goes 1,004, 985, 974, 937 |
| `test_the_asymmetric_neighborhood_gives_the_same_histories_under_every_schedule` | v3 reads only finished rounds: the same histories under random schedules of the workers |
| `test_the_relative_certificate_is_admitted_by_criterion_v2_and_refused_by_v1` | under v4 no round goes back; every certificate is of a tour whose shorter neighbors are all recorded; criterion v2 admits a relative certificate that v1 refuses, and refuses a false one |
| `test_meets_its_expected_end_and_replays` (vns-atsp) | `expect` and R2 for the asymmetric instance |
| `test_every_step_keeps_the_direction_of_the_arcs_it_does_not_cut` (vns-atsp) | the instance is asymmetric; every move is an exchange of two adjacent segments that shortens the tour and cuts three arcs; the certificates of the last round hold by brute force |
| `test_the_asymmetric_neighborhood_reaches_a_shorter_tour_with_fewer_returns` (vns-atsp) | v1 ends at 1,547 with 20 returns, v3 at 1,532 with 15, with the same criteria |
| `test_both_synchronous_forms_give_the_same_histories_by_workers` (vns-atsp) | v1 and v3 by workers under a random schedule: the histories of the agenda |
| `test_the_generator_reproduces_the_instance` (vns-tw) | `generate.py` gives the windows and pairs of `system.json`; its reference tour is feasible |
| `test_meets_its_expected_end_and_replays` (vns-tw) | `expect` and R2 |
| `test_the_scenarios_are_recorded_once_and_read_by_the_searchers` (vns-tw) | one event of `scenario` per recorded seed, equal to its definition; the searchers read the scenarios from the record (their horizon holds `scenario`, not `world`) |
| `test_the_exact_optima_and_the_bias_of_the_sample` (vns-tw) | the HiGHS optima: 3,415 fails 14 of the 20 scenarios and is on time in 457 of 1,000 audit scenarios; 3,492 fails none of the 20 but is on time in only 898 |
| `test_the_incremental_evaluation_equals_the_full_one` (vns-tw) | the evaluation of a move from the state of the tour before it agrees with a full evaluation written in the test |
| `test_every_step_states_its_tour_truly_and_is_a_step_of_vns` (vns-tw) | every step's value and status are true; every repair and move lowers the value; the final certificate holds by brute force over 9,139 moves and 20 scenarios |
| `test_a_late_city_is_false_and_a_premature_one_not_yet` (vns-tw) | a move that cuts at or after the first position that is not admissible leaves it late or premature, for every recorded tour that has one |
| `test_the_asymmetric_neighborhood_returns_less` (vns-tw) | v3 has the criteria of v1, 17 returns instead of 26, and reaches 3,504 in round 3 instead of 6 |
| `test_without_the_chance_constraint_the_search_is_blind_to_the_environment` (vns-tw) | ALLOW = M: v1 and v3 both end at 3,482, on time in 672 and in 430 of the audit scenarios |
| `test_the_synchronous_form_gives_the_same_histories_by_workers`, `test_the_asynchronous_form_is_verifiable_by_workers` (vns-tw) | by workers: the synchronous form gives the histories of the agenda; the asynchronous one replays and its incumbent never gets worse |
| `test_the_generator_reproduces_the_cities` (vns-hk) | `generate.py` gives the 26 city abstractions and `system.json` |
| `test_the_same_histories_under_random_schedules_and_killed_workers` (vns-hk) | 33 workers, under random schedules and with workers killed: the histories of the agenda |
| `test_every_tree_is_a_minimum_one_tree_and_states_its_bound_truly` (vns-hk) | every recorded 1-tree is minimum under the recorded potentials (Kruskal, in the test) and its bound is its weight minus 2·Σπ |
| `test_every_bound_is_below_every_recorded_tour_and_the_proof_is_true` (vns-hk) | weak duality on every recorded tour; the proof (round 18, 936.10, 937) is true and no earlier round proves it |
| `test_every_potential_moves_in_the_direction_of_the_subgradient` (vns-hk) | up above degree 2, down at degree 1, unchanged at 2 |
| `test_the_criteria_know_nothing_of_the_strategy` (vns-hk) | D2: a longer step in the same direction is admitted, one against it refused; a 1-tree that is not minimum, a false bound, a proof of 938 or from round 17 are refused |
| `test_aiming_at_the_starting_tour_takes_eighteen_times_as_many_rounds` (vns-hk) | ontology v2 of the cities, the same criteria: the proof in round 330 instead of 18 |
| `test_the_same_histories_under_random_schedules_and_killed_workers` (vns-adaptive) | the change of form at the same position of every lineage, under random schedules and with workers killed |
| `test_each_form_is_in_force_from_the_start_of_a_round` (vns-adaptive) | every step is proposed and judged by the versions active at its position: v1 in rounds 0–2, v2 in 3–6, v3 under criterion v2 in 7–9 |
| `test_every_decision_is_the_rule_applied_to_the_record` (vns-adaptive) | the returns counted in the test, the rule applied to them; what is carried is what the files say, each ontology bound to the criterion carried before it |
| `test_the_authority_admits_the_next_form_only_past_the_tolerance` (vns-adaptive) | D2 for the agent: waiting is admitted; a change without the evidence, a form out of order or incomplete, a change of another abstraction or of the agent itself, evidence the record does not hold are refused |
| `test_the_same_record_over_http` (vns-adaptive) | every abstraction an HTTP service: the same record, the carried specifications included |
| `test_tau_root_judges_what_the_agent_carries` (vns-adaptive) | a version carried out of line is refused by τ_root, not by the agent's criterion |
| `test_the_route_criterion_admits_a_committed_link_only_at_the_recorded_optimum` (cptl) | the other link of every committed step is admitted exactly when it is feasible and attains the recorded optimum |
| `test_the_route_criterion_refuses_an_invalid_witness_or_a_broken_route` (cptl) | a witness over the budget or of even parity, a skipped stage, a broken link and a second trial are refused |
| `test_the_governing_criterion_admits_only_the_designated_version_on_an_obstructed_trial` (cptl) | another body, more than the designated version, nothing carried, a false obstruction, a second decision, and a decision without an obstruction are refused |
| `test_an_interrupted_run_continues_to_the_same_record`, `test_the_same_lineages_by_workers_under_random_schedules_and_killed_workers` (cptl) | the checks applied to every example, at 6 and 20 stages |
| `test_the_criteria_refuse_a_candidate_out_of_turn_or_malformed` (sat4) | on the record: a branch with a variable twice or with both signs, outside the formula or out of turn, the propagation of another branch, a second decision, and a witness that does not extend the retry or repeats a variable are refused |
| `test_which_branch_is_the_ontologys_choice_put_in_force_by_the_governing_event` (sat4) | D2 and R1: the criterion admits any consistent next branch, also the retry before the governing event; ontology version 1 proposes nothing after the probe, and version 2, active only from the governing event, proposes the retry once the resolvent is admitted and only where it is unit; another correct second branch passes the replay of judgments and fails the full replay |
| `test_the_trace_runs_and_replays_for_every_k` (sat4 k-SAT) | 56 instances, k = 2..8, random variable numbers, signs, literal and probe order, unused variables: the expected end written for each instance, both replay modes, a resolvent implied by the formula, a closed first branch and a witness that is a model |
| `test_an_interrupted_run_continues_to_the_same_record_for_every_k`, `test_workers_give_the_lineages_of_the_agenda_for_every_k` (sat4 k-SAT) | the checks applied to every example, at k = 3, 7 and k = 2, 5, 8 |
| `test_consensus_is_constituted_when_all_clause_criteria_hold_at_once` (sat4 k-SAT) | 120 instances with clauses on other variables: the witness criterion equals the conjunction of the clause criteria on all assignments; a run reaches consensus exactly when the ontology's assignment satisfies every clause, and otherwise ends with the witness closed, either with a model the criterion admits or with none; the consensus is constituted once |
| `test_each_order_of_the_probe_reaches_its_own_model_under_one_criterion` (sat4 k-SAT) | k − 1 probe orders, one criterion of branch, k − 1 different witnesses, each a model |
| `test_the_criteria_are_sound_and_exact_on_random_kcnf` (sat4 k-SAT) | 300 random k-CNF formulas, k = 2..6, against all assignments: units forced in every model of the branch, conflicts that leave no model, resolvents implied by the formula and tautologies refused, and the branch, unit, conflict and witness criteria exact |
| `test_the_helpers_refuse_what_this_instance_cannot_show` (sat4) | on small inputs: a satisfied clause forces nothing, a tautology or parents without a clash give no resolvent, a witness that falsifies a clause is refused |
| `test_an_interrupted_run_continues_to_the_same_record`, `test_the_same_lineages_under_random_schedules_and_killed_workers` (sat4) | the checks applied to every example, with an interruption after every event |
| `test_until_the_first_change_the_searchers_take_the_steps_of_vns`, `test_an_agent_whose_tolerance_is_never_exceeded_leaves_the_search_of_vns` (vns-adaptive) | the agent changes nothing it does not carry |

## License

MIT, see [LICENSE](LICENSE).
