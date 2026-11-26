# OEE-heuristic-agents

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24416246.svg)](https://doi.org/10.5281/zenodo.24416246)

Heuristic agents lifted into the OEE calculus of execution on the ZTES substrate: metaheuristics as interacting abstractions over one record, starting with cooperative parallel variable neighborhood search. Executable supplement to two papers; see [the two papers](#the-two-papers).

A heuristic is lifted here as a system of abstractions: each step of the method is a candidate
proposed by an ontology [ω], admitted by a criterion [τ] and appended to one record C. The loops
of the method become interaction through the record, a claim about a whole neighborhood becomes an
admitted certificate, and every run replays (R2). The systems are executed by
[ZTES](https://github.com/ztes-team/ztes-minimal), the minimal zero-tier execution substrate of the
base paper *A Calculus of Execution for Interacting Binary Relations*, installed as a
package. ZTES contains nothing specific to these examples: everything specific to a heuristic is
in its directory, as JSON specifications and one `lib.py` of bounded functions.

| Example | Method | Abstractions | Events | What it shows |
|---|---|---|---|---|
| [`vns`](examples/vns/DESIGN.md) | variable neighborhood search by three cooperating searchers on fri26 (TSPLIB, symmetric, optimum 937) | 5 | 390 | every loop of VNS is interaction; each local optimum is a certificate; the criterion admits any step of VNS (D2); synchronous cooperation gives the same history of every lineage under every schedule, with no lock, no message and no master process; the asymmetric neighborhood and the certificate relative to the record |
| [`vns-atsp`](examples/vns-atsp/DESIGN.md) | the same on ftv38 (TSPLIB, asymmetric, optimum 1,530) | 5 | 1,195 | a neighborhood that keeps the direction of every arc it does not cut; nothing in the lifting changes; the asymmetric neighborhood reaches a shorter tour |
| [`vns-tw`](examples/vns-tw/DESIGN.md) | the same on ftv38 with time windows and precedence constraints, under a recorded environment | 8 | 349 | a late city is False and a premature one Not Yet, and the prefix order gives the repair rule; a chance constraint on recorded scenarios and an audit of the probability of being on time; three sources of chance (algorithm, schedule, environment) in one record |
| [`vns-hk`](examples/vns-hk/DESIGN.md) | the searchers of `vns` beside 26 city abstractions that compute a Held–Karp lower bound on fri26 | 33 | 934 | heterogeneous agents in one record: the cities are the dual, each moves its own potential, and a minimum 1-tree is admitted in each round; the bound proves the incumbent optimal, a claim about every tour made one admitted event; aimed at the incumbent the cities need 18 rounds, aimed at the starting tour 330 |
| [`vns-adaptive`](examples/vns-adaptive/DESIGN.md) | the searchers of `vns` and an agent that changes their form during the run | 6 | 393 | an adaptive heuristic agent: after every round it reads the returns in the record and, past a tolerance, carries the next form of the searchers, first a change of ontology, then of criterion; its criterion is the authority over what may change and on what evidence; every change is in force from the start of a round under every schedule, and replays |
| [`cptl`](examples/cptl/DESIGN.md) | parity and a strict budget along a path with declared precedence | 3 | 21 | a locally valid trial has a certified obstruction in the next stage. A governed change uses the recorded two-state suffix certificates to build an optimum. A native dynamic program and flat sampling supply comparisons. |
| [`sat4`](examples/sat4/DESIGN.md) | propagation and resolution on two 4-CNF clauses | 6 | 21 | a conflict closes one branch. A checked resolvent is reused after a governed change and forces a literal in the retry. |
| [`ksat`](examples/ksat/DESIGN.md) | conflict-driven clause learning on any CNF formula, every clause an abstraction: PHP(4,3) and a random 3-CNF with 20 variables | 5 and one per clause (32 and 96 at the end) | 174 and 460 | evolutive consensus: the clauses vote for a model by their own admissions, or the record ends in a checked resolution refutation; every learned clause is brought in as a new abstraction under governance, and an agent changes the decision policy on the evidence of the conflicts; the same history of every lineage under every schedule |

## The two papers

This repository is the executable supplement of two papers.

* **The base paper**: *A Calculus of Execution for Interacting Binary Relations* (Škarić, Ivanović,
  M. Radenković, Prokhorov, Labus, B. Radenković), Preprints 2026, 2026081545, version 4,
  https://doi.org/10.20944/preprints202608.1545.v4 [1]. It defines the calculus that ZTES executes,
  describes these examples in §8.9 and Table 8, and relies on them in Table 10 (its contributions
  and their executable confirmation). Section, table, theorem and corollary numbers in this
  repository, wherever a paper is not named otherwise, refer to version 4 of this paper.
* **The companion paper**: *Observable, Governable, Cooperative: Execution Analytics and Adaptive
  Heuristic Agents in the OEE Calculus* (M. Radenković, Prokhorov, Labus, B. Radenković), in
  preparation [2]. It studies the heuristics of this repository as observable, governable and
  cooperative agents. The KPI profiles, the results over many seeds and the worker trials of the
  scripts are its measurements. It is cited here by its title only, because its numbering is not
  final.

[`REPRODUCING.md`](REPRODUCING.md) gives, for both papers, every result that comes from this
repository, the command that produces it and the test that checks it.

## Before you start

The examples are systems for [ZTES](https://github.com/ztes-team/ztes-minimal), and their output is
that of ZTES. If the calculus is new to you, read first, in ztes-minimal:

* [`docs/tour.md`](https://github.com/ztes-team/ztes-minimal/blob/main/docs/tour.md): one invocation
  from start to finish, the base paper mapped to the code;
* [`docs/glossary.md`](https://github.com/ztes-team/ztes-minimal/blob/main/docs/glossary.md): the
  terms of the papers next to those of the output;
* [`docs/writing-a-system.md`](https://github.com/ztes-team/ztes-minimal/blob/main/docs/writing-a-system.md):
  the files of an abstraction, which every example here follows.

Eight terms are enough to read this page:

| Term | Meaning |
|---|---|
| record, C | the one append-only sequence of admitted events; everything a step reads is in it |
| abstraction | one lifted relation: an ontology that proposes and a criterion that admits |
| ontology [ω] | proposes the next candidate from the record, or gives ⊥ (no candidate) |
| criterion [τ] | a Boolean predicate on the preceding prefix and the candidate: admitted or refused |
| Not Yet | the output's name for an invocation that gave no candidate (Pending in the base paper); vns-tw also uses Not Yet for a premature city, in the sense of a goal |
| governed change | a new version of a specification, admitted as an event; in force from that event (R1) |
| R2 | replay: every event re-derived and re-judged on its own prefix |
| workers | one process per abstraction instead of the agenda; for results determined by their inputs, every lineage has the same history under every schedule (Theorem K) |

## Repository layout

```
examples/<name>/          one system per example: system.json, abstractions/, lib.py, DESIGN.md
examples/ksat/php43/      the ksat system of PHP(4,3), written by scripts/ksat_system.py
examples/ksat/random20/   the ksat system of a random 3-CNF formula, 20 variables, 85 clauses
scripts/                  the measurements: profiles, sweeps, trials, timings, benchmarks, ksat_system
tests/                    the checks of every example and of the scripts (docs/tests.md)
REPRODUCING.md            every result of both papers: command, output, test
CHANGELOG.md              what changed between versions
docs/tests.md             what each test shows
requirements.txt          ZTES at the commit the examples were checked with
```

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

The companion paper uses CPTL to connect structural inference, policy change and measured
execution cost; the base paper lists it in §8.9 and Table 8. A local proof rules out the greedy trial and supplies the evidence for
activating a new route ontology. The same two-state recurrence gives the optimum in the native and
ZTES runs. The [case study](examples/cptl/DESIGN.md) gives the proof, replay commands and benchmark.

## sat4

The two-clause example of §7.1 of the base paper records a branch conflict,
checks a resolution proof from the original clauses, and reuses the derived clause during a governed
retry. The [design](examples/sat4/DESIGN.md) gives the evidence for each decision, the expected SAT
witness and the replay commands.

## ksat: k-SAT as evolutive consensus

Every clause of a CNF formula is an abstraction, and its criterion is the authority over that
clause alone. The formula is then the composite criterion τ = τ₁ ∧ … ∧ τₘ of evolutive consensus in
the sense of the FUEE paper (Section 8; DOI 10.2298/FUEE2604723R,
[the article on the journal's site](https://casopisi.junis.ni.ac.rs/index.php/FUElectEnerg/article/view/14966)).

The search runs in rounds over the shared record:
- each clause reports the literal it forces or its conflict;
- `decide` branches;
- `learn` derives a clause by resolution and brings it in as a new abstraction, together with a
  new version of `round` that reads it;
- `adapt` changes the decision policy once, on the evidence of the conflicts.

A model is admitted only when every clause has voted for it, each vote an admission under its own
criterion. Otherwise the record ends in a resolution refutation, checked at every step and again by
replay. `scripts/ksat_system.py` writes the system of any DIMACS formula, and the
[design](examples/ksat/DESIGN.md) gives the abstractions, the criteria and the measurements.

## Running

Python 3.12 or later.

```
pip install -r requirements.txt               # ZTES from GitHub, at the commit the examples were checked with
python -m ztes run examples/vns               # under the agenda: the report, R2 and the expected end
python -m ztes run examples/vns --workers     # phase 3 by one worker per abstraction
python -m ztes run examples/vns --record DIR  # keep the record; then: python -m ztes explain DIR 220
python -m ztes run examples/vns-atsp
python -m ztes run examples/vns-tw         # about 7 s, and as long for R2
python -m ztes run examples/vns-tw --record DIR && python -m ztes verify DIR --judgments
                                              # R2 by re-judging the recorded steps only: 0.65 s
python -m ztes run examples/vns-hk
python -m ztes run examples/vns-adaptive
python -m ztes run examples/cptl
python -m ztes run examples/sat4
python scripts/benchmark_cptl.py               # native DP, flat samples and checked OEE runs
python -m ztes run examples/ksat/php43         # UNSAT: a refutation; six clauses learned, the empty one ends it,
                                              # so five are brought in as abstractions
python -m ztes run examples/ksat/random20 --workers --config examples/ksat/ztes.yaml
                                              # about ninety workers; the record in memory
python scripts/ksat_system.py formula.cnf DIR  # the ksat system of any DIMACS formula
python scripts/benchmark_ksat.py               # native and checked runs, replay, record size
python scripts/timings.py                      # run and both replays of every example, medians of three
python -m pytest
python scripts/profiles.py                    # the KPI profiles of every form, about two minutes
python scripts/sweeps.py                      # the forms over many seeds (companion paper), about twenty minutes
python scripts/trials.py                      # schedules and killed workers, about half an hour (--quick: minutes)
```

`scripts/sweeps.py` runs every form once per seed under the agenda and reads its indicators from the
record: the forms on fri26 and ftv38 over seeds 1–40, time windows with and without the chance
constraint, the adaptive agent against the fixed forms, and the shares of the variance of algorithm
and environment, all measurements of the companion paper. Under the agenda every
number is the same on every host. `scripts/trials.py` runs phase 3 by workers under random schedules
and with workers killed and started again, and checks that every lineage has the history it has
under the agenda and that every record replays; the number of workers killed varies from run to run.

`scripts/profiles.py` runs each form once and reads its KPI profile from the record (for the
companion paper): the completed and the Pending invocations of the searchers, admission compression,
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

```
python -m pytest
```

runs the checks of every example and of the scripts. What each test shows is listed in
[`docs/tests.md`](docs/tests.md); [`REPRODUCING.md`](REPRODUCING.md) names the test behind each
result of the papers.

## References

1. Škarić, M.; Ivanović, A.; Radenković, M.; Prokhorov, S.; Labus, A.; Radenković, B. *A Calculus of
   Execution for Interacting Binary Relations*. Preprints **2026**, 2026081545 (version 4).
   https://doi.org/10.20944/preprints202608.1545.v4
2. Radenković, M.; Prokhorov, S.; Labus, A.; Radenković, B. *Observable, Governable, Cooperative:
   Execution Analytics and Adaptive Heuristic Agents in the OEE Calculus*. In preparation.
3. Radenković, M.; Prokhorov, S.; Labus, A.; Radenković, B. *ZTES: a minimal Zero Tier Execution
   Substrate for the OEE calculus*, software, Zenodo, 2026. https://doi.org/10.5281/zenodo.24416120
4. Ivanović, A.; Radenković, M.; Prokhorov, S.; Labus, A.; Radenković, B. Zero Tier Execution
   Substrate for Evolutionary Software Systems. *Systems* **2026**, 14, 547.
   https://doi.org/10.3390/systems14050547
5. Radenković, M.; Radosavljević, N.; Labus, A.; Prokhorov, S.; Radenković, B. Evolutive consensus
   for agentic AI: OEE incompleteness of external guardrails and the execution calculus for safe
   evolutive agents. *Facta Universitatis, Series: Electronics and Energetics* **2026**, 39(4),
   723–765. https://doi.org/10.2298/FUEE2604723R
6. Mladenović, N.; Hansen, P. Variable neighborhood search. *Computers & Operations Research*
   **1997**, 24(11), 1097–1100.
7. Reinelt, G. TSPLIB—A traveling salesman problem library. *ORSA Journal on Computing* **1991**,
   3(4), 376–384.
8. Held, M.; Karp, R. M. The traveling-salesman problem and minimum spanning trees. *Operations
   Research* **1970**, 18(6), 1138–1162.
9. Marques-Silva, J. P.; Sakallah, K. A. GRASP: a search algorithm for propositional
   satisfiability. *IEEE Transactions on Computers* **1999**, 48(5), 506–521.

## License

MIT, see [LICENSE](LICENSE).

## Notice

The examples in this repository are a supplement to two scientific papers and are provided as is (see
the license); the authors accept no liability for their use.

"Zero-tier execution substrate" (ZTES), in the sense of tierless execution, is the name of a concept of
program execution defined in the base paper. It is not a commercial product, and it is not connected with
ZeroTier, Inc. or its VPN and SDN networking products; the authors have no relation to that company.
