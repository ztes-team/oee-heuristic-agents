# OEE-heuristic-agents
Heuristic agents lifted into the OEE calculus of execution on the ZTES substrate: metaheuristics as interacting abstractions over one record, starting with cooperative parallel variable neighborhood search. Executable supplement to the paper.

A heuristic is lifted here as a system of abstractions: each step of the method is a candidate
proposed by an ontology [ω], admitted by a criterion [τ] and appended to one record C. The loops
of the method become interaction through the record, a claim about a whole neighborhood becomes an
admitted certificate, and every run replays (R2). The systems are executed by
[ZTES](https://github.com/ztes-team/ztes-minimal), the minimal zero-tier execution substrate of the
paper *A Calculus of Execution for Systems of Interacting Binary Relations*, installed as a
package. ZTES is not changed for these examples: everything specific to a heuristic is in its
directory, as JSON specifications and one `lib.py` of bounded functions.

| Example | Heuristic | Abstractions | Events | What it shows |
|---|---|---|---|---|
| [`vns`](examples/vns/DESIGN.md) | variable neighborhood search by three cooperating searchers on fri26 (TSPLIB, symmetric, optimum 937) | 5 | 390 | every loop of VNS is interaction; each local optimum is a certificate; the criterion admits any step of VNS (D2); synchronous cooperation gives the same record under every schedule, with no lock, no message and no master process; the asymmetric neighborhood and the certificate relative to the record |
| [`vns-atsp`](examples/vns-atsp/DESIGN.md) | the same on ftv38 (TSPLIB, asymmetric, optimum 1,530) | 5 | 1,195 | a neighborhood that keeps the direction of every arc it does not cut; nothing in the lifting changes; the asymmetric neighborhood reaches a shorter tour |
| [`vns-tw`](examples/vns-tw/DESIGN.md) | the same on ftv38 with time windows and precedence constraints, under a recorded environment | 7 | 327 | a late city is False and a premature one Not Yet, and the prefix order gives the repair rule; a chance constraint on recorded scenarios and an audit of the probability of being on time; three sources of chance (algorithm, schedule, environment) in one record |

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
the boundary `world` records 20 seeds, a tour must be on time in all but 2 of their scenarios, and
the boundary `audit` records one more seed for 1,000 scenarios the search never sees. The
deterministic optimum (3,415) is on time in 457 of these; the sample-average optimum (3,492) in all
20 scenarios of the world but only 898 of the audit, so the sample overstates the probability it
estimates. Over 20 seeds the asymmetric neighborhood (v3) reaches the sample-average optimum in 8
runs, v1 in 1. The algorithm, the schedule of the workers and the environment are three sources of
chance in one record: for the synchronous forms the share of the schedule is exactly 0, for the
asynchronous form it is measured. See [`examples/vns-tw/DESIGN.md`](examples/vns-tw/DESIGN.md).

## Running

Python 3.12 or later.

```
pip install -r requirements.txt               # ZTES from GitHub, at the commit the examples were checked with
python -m ztes run examples/vns               # under the agenda: the report, R2 and the expected end
python -m ztes run examples/vns --workers     # phase 3 by one worker per abstraction
python -m ztes run examples/vns --record DIR  # keep the record; then: python -m ztes explain DIR 220
python -m ztes run examples/vns-atsp
python -m ztes run examples/vns-tw         # about 15 s, and as long for R2
python -m pytest
```

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

`tests/test_vns.py`, `tests/test_vns_atsp.py` and `tests/test_vns_tw.py` apply to the examples the checks ZTES applies to
each of its own, and check what the `DESIGN.md` files claim.

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
| `test_the_exact_optima_and_the_bias_of_the_sample` (vns-tw) | the HiGHS optima: 3,415 fails 14 of the 20 scenarios and is on time in 457 of 1,000 audit scenarios; 3,492 fails none of the 20 but is on time in only 898 |
| `test_the_incremental_evaluation_equals_the_full_one` (vns-tw) | the evaluation of a move from the state of the tour before it agrees with a full evaluation written in the test |
| `test_every_step_states_its_tour_truly_and_is_a_step_of_vns` (vns-tw) | every step's value and status are true; every repair and move lowers the value; the final certificate holds by brute force over 9,139 moves and 20 scenarios |
| `test_a_late_city_is_false_and_a_premature_one_not_yet` (vns-tw) | a move that cuts at or after the first position that is not admissible leaves it late or premature, for every recorded tour that has one |
| `test_the_asymmetric_neighborhood_returns_less` (vns-tw) | v3 has the criteria of v1, 17 returns instead of 26, and reaches 3,504 in round 3 instead of 6 |
| `test_without_the_chance_constraint_the_search_is_blind_to_the_environment` (vns-tw) | ALLOW = M: v1 and v3 both end at 3,482, on time in 672 and in 430 of the audit scenarios |
| `test_the_synchronous_form_gives_the_same_histories_by_workers`, `test_the_asynchronous_form_is_verifiable_by_workers` (vns-tw) | by workers: the synchronous form gives the histories of the agenda; the asynchronous one replays and its incumbent never gets worse |

## License

MIT, see [LICENSE](LICENSE).
