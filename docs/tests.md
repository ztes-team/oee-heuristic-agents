# Tests

`python -m pytest` runs every test. This page lists what the tests of each example and of the
scripts show. [`REPRODUCING.md`](../REPRODUCING.md) names the test behind each result of the papers.
Section, theorem and table numbers refer to version 4 of the base paper, *A Calculus of Execution for
Interacting Binary Relations*.

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
evolutive consensus in the sense of the FUEE paper (Section 8; DOI 10.2298/FUEE2604723R,
[the article on the journal's site](https://casopisi.junis.ni.ac.rs/index.php/FUElectEnerg/article/view/14966)): the composite criterion is the
conjunction of the clause criteria over the shared record.

`tests/test_ksat.py` checks ksat against definitions written in the test: all assignments, a DPLL
procedure and a checker of resolution proofs. It also checks that the record is the native
execution of the same relations.

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
| `test_the_committed_instances_are_what_the_script_writes`, `…_meet_their_expected_end_and_replay`, `test_workers_meet_the_expected_end_of_the_committed_instances` (ksat) | php43 and random20 as `scripts/ksat_system.py` writes them; their expected end under the agenda and by workers; both replay modes |
| `test_verdicts_agree_with_all_assignments`, `test_edge_cases`, `test_verdicts_agree_with_dpll_on_larger_formulas` (ksat) | random k-CNF, k = 2..5, below, at and above the threshold, against all assignments; edge cases; n = 20..30 against DPLL. A SAT verdict is a model; an UNSAT verdict ends a refutation the checker accepts; every learned clause holds in every model |
| `test_the_record_is_the_native_execution_of_the_same_relations` (ksat) | the frames, decisions, learned clauses and verdict of the helpers called in a plain loop, with and without the change of policy |
| `test_consensus_is_the_conjunction_of_the_clause_criteria`, `test_a_clause_votes_only_for_a_total_frame_that_satisfies_it` (ksat) | every clause abstraction voted under its own τᵢ; on all assignments, the verdict admits exactly the model every clause voted for; a missing vote, or a vote of a false clause or on a frame that is not total, is refused |
| `test_the_refutation_is_in_the_record_and_replay_finds_a_forged_step` (ksat) | the refutation of PHP(4,3) passes the checker; a forged step fails replay at that event in both modes |
| `test_a_learned_clause_brings_in_its_abstraction_and_the_next_round`, `test_tau_root_and_learn_refuse_what_is_not_exact` (ksat) | each learned clause carries its abstraction and the next version of round, active from its event; the next frame is made by that version and the clause speaks first on the new epoch; a version with a gap, an ontology without its criterion and inexact specifications are refused |
| `test_adapt_puts_the_second_policy_in_force_at_its_event`, `test_the_change_of_policy_changes_the_course_and_not_the_verdict` (ksat) | every decision after the change is by version 2, all judged by one criterion; version 1 waits while the change is due; false evidence, an early or second change and another version are refused; the course changes, the verdict does not |
| `test_an_interrupted_run_continues_to_the_same_record`, `test_the_same_lineages_under_random_schedules_and_killed_workers` (ksat) | the checks applied to every example, with the workers of learned clauses killed too |
| `test_the_criterion_of_learn_refuses_what_is_not_a_resolution_from_a_conflict`, `test_decide_waits_while_a_change_of_policy_is_due` (ksat) | forged derivations that differ from a valid one only in the broken rule (start, parent, clash, tautology) are refused; with the change of policy due and an adapt that never decides, decide makes no decision |
| `test_the_clause_criteria_refuse_a_false_or_untimely_speech`, `test_the_criterion_of_decide_admits_any_correct_decision_and_nothing_else`, `test_the_criterion_of_learn_admits_any_valid_derivation_and_nothing_else`, `test_the_criteria_of_round_and_verdict_refuse_a_forged_frame_or_verdict` (ksat) | the criteria as authorities (D2): any correct decision and any valid derivation is admitted; forged speeches, decisions, derivations, frames and verdicts are refused |
