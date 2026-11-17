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
| [`vns`](examples/vns/DESIGN.md) | variable neighborhood search by three cooperating searchers on fri26 (TSPLIB, optimum 937) | 5 | 390 | every loop of VNS is interaction; each local optimum is a certificate; the criterion admits any step of VNS (D2); synchronous cooperation gives the same record under every schedule, with no lock, no message and no master process |

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
forty seeds each form reaches the optimum in 22. The design, the derivation of the result and the
measurements are in [`examples/vns/DESIGN.md`](examples/vns/DESIGN.md).

## Running

Python 3.12 or later.

```
pip install -r requirements.txt               # ZTES from GitHub, at the commit the examples were checked with
python -m ztes run examples/vns               # under the agenda: the report, R2 and the expected end
python -m ztes run examples/vns --workers     # phase 3 by one worker per abstraction
python -m ztes run examples/vns --record DIR  # keep the record; then: python -m ztes explain DIR 220
python -m pytest
```

The asynchronous form is the same plan with a governed change of the three searcher ontologies:

```python
from ztes.substrate.store import MemoryStore
from ztes.system import workers
from ztes.system.system import System

plan = [{"phase": 1}, {"phase": 2},
        {"govern": ["search_1/ontology.v2", "search_2/ontology.v2", "search_3/ontology.v2"]},
        {"phase": 3}, {"kpi": True}]
System("examples/vns").run(MemoryStore(), plan=plan)                   # under the agenda
workers.run(System("examples/vns"), MemoryStore(), plan=plan)          # by workers: the course depends on the schedule
```

## Tests

`tests/test_vns.py` applies to the example the checks ZTES applies to each of its own, and checks
what `DESIGN.md` claims.

| Test | What it checks |
|---|---|
| `test_is_well_formed`, `test_meets_its_expected_end` | the static check of the system; the end stated in `expect` (390 events, the states, the incumbent 937, the indicators) |
| `test_replays_in_process_and_over_http` | R2; the same record when every abstraction is an HTTP service |
| `test_an_interrupted_run_continues_to_the_same_record` | the run, cut after any of six events and started again, gives the same record |
| `test_by_workers_on_every_store` | phase 3 by workers on memory, diskcache and Redis (fakeredis): R2, the end states, `expect` |
| `test_every_step_is_a_step_of_vns_and_every_local_optimum_is_certified` | every move shortens the tour; no 2-opt neighbor of a certified optimum is shorter (checked independently of `lib.py`); the incumbent of round r is the shortest optimum up to r; the end is 937 |
| `test_criterion_admits_any_step_of_vns_and_refuses_the_rest` | D2: another improving move is admitted; a longer move, a false certificate, a shake of an uncertified tour or beyond N₃ is refused |
| `test_asynchronous_cooperation_changes_three_ontologies_and_no_criterion` | the two forms have the same criteria; the asynchronous one reaches 953 in round 1, the synchronous one 985 |
| `test_synchronous_cooperation_gives_the_same_histories_under_every_schedule` | under random schedules of the workers every lineage has the history it has under the agenda, while the order of the record differs |
| `test_synchronous_cooperation_survives_killed_workers_with_the_same_histories` | workers killed at random and started again: the same histories; only time is lost |
| `test_asynchronous_cooperation_is_verifiable_under_every_schedule` | under random schedules every record replays and the incumbent never gets longer |

## License

MIT, see [LICENSE](LICENSE).
