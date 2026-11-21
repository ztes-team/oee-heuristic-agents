"""Tests of examples/ksat: k-SAT as evolutive consensus, with clauses as abstractions.

Every check is made against definitions written here, independently of examples/ksat/lib.py: the
assignments of a formula, a DPLL procedure, and a checker of resolution proofs.

- The committed instances are exactly what scripts/ksat_system.py writes. They meet their
  expected end under the agenda and by workers, and replay in both modes.
- Verdicts agree with all assignments on small random k-CNF formulas (k = 2..5, below, at and
  above the threshold) and on edge cases, and with DPLL on larger ones. A SAT verdict is a model.
  An UNSAT verdict ends a refutation that the checker here accepts, and every learned clause
  holds in every model of the formula.
- The record is the native execution of the same relations: the frames, decisions, learned
  clauses and verdict of the helpers called in a plain loop.
- Evolutive consensus (FUEE paper, Section 8): the verdict admits a model exactly when every
  clause abstraction voted for it, and that model satisfies every clause.
- Governance (R1):
  - a learned clause brings in its abstraction and the next version of round, which are active
    from its event; τ_root and the criterion of learn refuse what is not exact;
  - adapt puts version 2 of decide in force at its event, and every later decision is made by it;
  - the criterion of decide judges both versions (D2), and the verdict is the same without the
    change.
- The checks applied to every example: an interrupted run continues to the same record, and
  workers give the lineages of the agenda under random schedules and when killed and started
  again, the workers of abstractions brought in during the run among them (Theorem K).
- The criteria as authorities: forged speeches, decisions, derivations, frames, switches and
  verdicts are refused; any correct decision and any valid derivation is admitted (D2).
"""
import copy
import importlib.util
import random
import threading
import time
from itertools import product
from pathlib import Path

import pytest

from ztes import model as evaluation
from ztes.substrate import governance, lookups
from ztes.substrate.replay import verify
from ztes.substrate.store import MemoryStore, read
from ztes.system import workers
from ztes.system.report import check_expect
from ztes.system.system import System

from test_vns import DiesAfterAppending, Killed, lineages

ROOT = Path(__file__).resolve().parents[1]
KSAT = ROOT / "examples" / "ksat"
SPEC = importlib.util.spec_from_file_location("ksat_system", ROOT / "scripts" / "ksat_system.py")
ks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ks)
lib = ks.helpers()
NEVER = 10 ** 9                                              # a threshold of adapt that is never reached
INSTANCES = {"php43": (ks.pigeonhole(4, 3), "PHP(4,3): 12 variables, 22 clauses as abstractions"),
             "random20": (ks.random_kcnf(20, 85, 3, 1), "random 3-CNF: 20 variables, 85 clauses as abstractions")}


def quiet(*_):
    pass


# ---- definitions written here ----

def satisfies(assignment, clause):
    return any(literal in assignment for literal in clause)


def assignments(variables):
    for values in product((False, True), repeat=len(variables)):
        yield {var if value else -var for var, value in zip(variables, values)}


def models(variables, formula):
    return [a for a in assignments(variables) if all(satisfies(a, clause) for clause in formula)]


def dpll(formula, partial=frozenset()):
    """Satisfiability by the Davis–Putnam–Logemann–Loveland procedure, written here."""
    rest = []
    for clause in formula:
        if any(literal in partial for literal in clause):
            continue
        left = [literal for literal in clause if -literal not in partial]
        if not left:
            return False
        rest.append(left)
    if not rest:
        return True
    for clause in rest:
        if len(clause) == 1:
            return dpll(rest, partial | {clause[0]})
    literal = rest[0][0]
    return dpll(rest, partial | {literal}) or dpll(rest, partial | {-literal})


def refutation(record, formula):
    """Check the learn events of a record as resolution derivations, by code written here: each
    learned clause is derived from its start along its chain, each parent being a clause of the
    formula or one learned earlier. Returns the learned clauses; raises AssertionError otherwise."""
    known = {f"c{i + 1}": frozenset(clause) for i, clause in enumerate(formula)}
    out = []
    for p in values(record, "learn"):
        assert p["name"] not in known
        derived = set(known[p["start"]])
        for step in p["chain"]:
            parent, literal = known[step["clause"]], step["literal"]
            assert literal in parent and -literal in derived, (p["name"], step)
            derived = (derived - {-literal}) | (parent - {literal})
            assert not any(-x in derived for x in derived), (p["name"], "tautology")
        assert derived == set(p["literals"]), (p["name"], derived, p["literals"])
        known[p["name"]] = frozenset(p["literals"])
        out.append(p["literals"])
    return out


# ---- runs and records ----

def run(d):
    system, store = System.from_dict(d), MemoryStore()
    system.run(store, log=quiet)
    return system, list(read(store))


def values(record, name):
    return [e["payload"] for e in record if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == name]


def positions(record, name):
    return [e["coord"]["n"] for e in record if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == name]


def judges(record, position, candidate, prefix=None):
    """The criterion of the event at position, on the prefix (by default the one it was judged on)."""
    P = record[:position if prefix is None else prefix]
    return evaluation.judge(P, lookups.load(P, record[position]["coord"]["criterion"]), candidate)


def run_killing(system, store, seed, chance=0.05):
    """Workers that may be killed before an invocation or right after an append, and started
    again; the workers of abstractions brought in during the run are started and supervised the
    same way. Returns the names of the killed workers."""
    rnd, deaths, threads = random.Random(seed), [], []

    def before():
        time.sleep(rnd.random() * 0.001)
        if rnd.random() < chance:
            raise Killed()

    def supervise(a):
        while True:
            worker = workers.Worker(system, a, DiesAfterAppending(store.again(), rnd, chance), hesitate=before)
            try:
                return worker.run()
            except Killed:
                deaths.append(a)
                time.sleep(rnd.random() * 0.003)

    def start(a):
        threads.append(threading.Thread(target=supervise, args=(a,), daemon=True))
        threads[-1].start()

    coordinator = workers.Coordinator(store, start=start, timeout=300.0)
    for a in system.abstractions:
        start(a)
    try:
        system.run(store, log=quiet, phase3=coordinator)
    finally:
        coordinator.stop()
        for t in threads:
            t.join(timeout=5)
    return deaths


@pytest.fixture(scope="module")
def committed():
    """The committed instances, each run under the agenda: name → (system, record)."""
    out = {}
    for name in INSTANCES:
        system, store = System(KSAT / name), MemoryStore()
        system.run(store, log=quiet)
        out[name] = system, list(read(store))
    return out


# ---- the committed instances ----

def test_the_committed_instances_are_what_the_script_writes(tmp_path):
    for name, (formula, title) in INSTANCES.items():
        assert ks.read_dimacs((KSAT / f"{name}.cnf").read_text(encoding="utf8")) == formula
        written = ks.save(KSAT / f"{name}.cnf", tmp_path / name, f"ksat-{name}", title)
        files = sorted(p.relative_to(written) for p in written.rglob("*") if p.is_file())
        assert files == sorted(p.relative_to(KSAT / name) for p in (KSAT / name).rglob("*") if p.is_file())
        for f in files:
            assert (written / f).read_bytes() == (KSAT / name / f).read_bytes(), f"{name}/{f}"
        assert (KSAT / name / "lib.py").read_bytes() == (KSAT / "lib.py").read_bytes()


def test_the_committed_instances_meet_their_expected_end_and_replay(committed):
    for name, (system, record) in committed.items():
        (variables, formula), _ = INSTANCES[name]
        assert System(KSAT / name).check(log=quiet) == []                     # a fresh system: one that ran has adopted more
        assert check_expect(system, record, log=quiet) == []
        assert verify(record) == [] and verify(record, judgments_only=True) == []
        verdict, = values(record, "verdict")
        assert verdict["sat"] == dpll(formula) == (name == "random20")
        learned = refutation(record, formula)
        assert (not verdict["sat"]) == ([] in learned)
        if verdict["sat"]:
            assert all(satisfies(set(verdict["model"]), clause) for clause in formula)


@pytest.mark.parametrize("name", list(INSTANCES))
def test_workers_meet_the_expected_end_of_the_committed_instances(committed, name):
    system, store = System(KSAT / name), MemoryStore()
    workers.run(system, store, log=quiet, timeout=300.0)
    record = list(read(store))
    assert check_expect(system, record, log=quiet, any_schedule=True) == []
    assert verify(record) == [] and lineages(record) == lineages(committed[name][1])


# ---- verdicts ----

SMALL = [(n, k, ratio, seed) for k, n in ((2, 6), (3, 8), (4, 8), (5, 7)) for ratio in (0.6, 1.0, 1.6)
         for seed in range(2) if (k, ratio) != (5, 1.6)]
THRESHOLD = {2: 1.0, 3: 4.26, 4: 9.93, 5: 21.1}             # ratios m/n near the threshold of random k-SAT


@pytest.mark.parametrize(("n", "k", "ratio", "seed"), SMALL)
def test_verdicts_agree_with_all_assignments(n, k, ratio, seed):
    variables, formula = ks.random_kcnf(n, max(1, round(ratio * THRESHOLD[k] * n)), k, seed)
    _, record = run(ks.definition(variables, formula))
    assert verify(record) == []
    all_models = models(variables, formula)
    verdict, = values(record, "verdict")
    assert verdict["sat"] == bool(all_models)
    if verdict["sat"]:
        assert set(verdict["model"]) in all_models
    learned = refutation(record, formula)
    assert (not verdict["sat"]) == ([] in learned)
    for clause in learned:                                   # every learned clause is implied by the formula
        assert all(satisfies(m, clause) for m in all_models)


EDGES = {
    "an empty clause": ([1, 2], [[1, 2], []]),
    "contradicting units": ([1], [[1], [-1]]),
    "a chain of units": ([1, 2, 3], [[1], [-1, 2], [-2, 3]]),
    "repeated literals": ([1, 2], [[1, 1, 2], [-1, -1]]),
    "a tautology": ([1, 2], [[1, -1], [2]]),
    "an unused variable": ([1, 2, 3], [[1, 2]]),
    "PHP(3,2)": ks.pigeonhole(3, 2),
}


@pytest.mark.parametrize("case", list(EDGES))
def test_edge_cases(case):
    variables, formula = EDGES[case]
    _, record = run(ks.definition(variables, formula))
    assert verify(record) == [] and verify(record, judgments_only=True) == []
    verdict, = values(record, "verdict")
    assert verdict["sat"] == bool(models(variables, formula))
    assert (not verdict["sat"]) == ([] in refutation(record, formula))


@pytest.mark.parametrize(("n", "seed"), [(20, 0), (25, 2), (30, 1), (30, 3)])
def test_verdicts_agree_with_dpll_on_larger_formulas(n, seed):
    variables, formula = ks.random_kcnf(n, round(4.26 * n), 3, seed)
    _, record = run(ks.definition(variables, formula))
    assert verify(record, judgments_only=True) == []
    verdict, = values(record, "verdict")
    assert verdict["sat"] == dpll(formula)
    if verdict["sat"]:
        assert all(satisfies(set(verdict["model"]), clause) for clause in formula)
    assert (not verdict["sat"]) == ([] in refutation(record, formula))


@pytest.mark.parametrize(("n", "m", "k", "seed", "after"), [
    (10, 43, 3, 0, 3), (12, 51, 3, 4, 3), (12, 51, 3, 4, NEVER), (12, 110, 4, 1, 2),
    (16, 68, 3, 1, 3), (16, 68, 3, 1, NEVER), (20, 85, 3, 2, 1), (30, 128, 3, 1, 3)])
def test_the_record_is_the_native_execution_of_the_same_relations(n, m, k, seed, after):
    variables, formula = ks.random_kcnf(n, m, k, seed)
    _, record = run(ks.definition(variables, formula, after=after))
    native = ks.native(variables, formula, after=after)
    assert values(record, "round") == native["frames"]
    assert values(record, "decide") == native["decisions"]
    assert [{f: v for f, v in p.items() if f != "specifications"} for p in values(record, "learn")] == native["learned"]
    assert values(record, "verdict") == [native["verdict"]]


# ---- evolutive consensus ----

def test_consensus_is_the_conjunction_of_the_clause_criteria():
    variables, formula = ks.random_kcnf(9, 38, 3, 17)
    _, record = run(ks.definition(variables, formula))
    names = [f"c{i + 1}" for i in range(len(formula))]
    learned = [p["name"] for p in values(record, "learn")]
    at, = positions(record, "verdict")
    verdict = record[at]["payload"]
    consensus = values(record, "round")[-1]
    assert verdict["sat"] and consensus["votes"] == names + learned and consensus["total"] and consensus["quiet"]
    votes = [e for e in record if e["coord"]["kind"] == "exec" and e["payload"].get("kind") == "vote"]
    assert sorted(e["coord"]["abstraction"] for e in votes) == sorted(names + learned)
    for e in votes:                                          # each vote is an admission under its own τᵢ
        assert judges(record, e["coord"]["n"], e["payload"])
        assert not judges(record, e["coord"]["n"], dict(e["payload"], literal=1))
    model = set(verdict["model"])
    assert all(satisfies(model, clause) for clause in formula)
    for candidate in assignments(variables):                 # one model: the one every clause voted for
        assert judges(record, at, {"sat": True, "model": sorted(candidate, key=abs)}) == (candidate == model)
    before = positions(record, "round")[-1]                  # before the consensus frame: no verdict
    assert not judges(record, at, verdict, prefix=before)
    assert not judges(record, at, {"sat": False, "model": []})
    missing = dict(consensus, votes=consensus["votes"][1:])  # a frame with one vote missing
    assert not lib.check_verdict(formula, variables, names, missing, {}, 0, verdict)
    # the verdict checks the model against the formula itself, not only the votes: on a forged
    # frame with every vote and a trail that falsifies a clause, it is refused
    clause = formula[0]
    falsifying = sorted({-x for x in clause} | {v for v in variables if v not in {abs(x) for x in clause}}, key=abs)
    forged = dict(consensus, trail=[{"literal": x, "level": 0, "reason": "decide"} for x in falsifying])
    assert not lib.check_verdict(formula, variables, names, forged, {}, 0, {"sat": True, "model": falsifying})


def test_a_clause_votes_only_for_a_total_frame_that_satisfies_it():
    frame = {"epoch": 0, "round": 4, "level": 1, "trail": [{"literal": -1, "level": 0, "reason": "c1"},
             {"literal": 2, "level": 1, "reason": "decide"}], "conflicts": [], "votes": [],
             "quiet": True, "total": True}
    vote = {"clause": "c9", "round": 5, "kind": "vote", "literal": 0}
    assert lib.check_speech("c9", [1, 2], frame, None, vote)
    assert not lib.check_speech("c9", [1, -2], frame, None, vote)               # false on the frame
    assert not lib.check_speech("c9", [1, 2], dict(frame, total=False), None, vote)
    assert not lib.check_speech("c9", [1, 2], frame, {"round": 5}, vote)        # a second speech in the round
    assert lib.speech("c9", [1, 2], dict(frame, total=False)) is None           # quiet, not total: nothing to say


def test_the_refutation_is_in_the_record_and_replay_finds_a_forged_step(committed):
    system, record = committed["php43"]
    (variables, formula), _ = INSTANCES["php43"]
    learned = refutation(record, formula)
    assert learned[-1] == [] and all(satisfies(m, c) for c in learned for m in models(variables, formula))
    at = positions(record, "learn")[1]
    forged = copy.deepcopy(record)
    step = forged[at]["payload"]["chain"][0]
    step["literal"] = -step["literal"]
    for judgments_only in (False, True):
        (where, why), *_ = verify(forged, judgments_only=judgments_only)
        assert where == at, why


# ---- governance ----

def test_a_learned_clause_brings_in_its_abstraction_and_the_next_round(committed):
    _, record = committed["php43"]
    rounds = positions(record, "round")
    version = 1
    for at in positions(record, "learn"):
        p, coord = record[at]["payload"], record[at]["coord"]
        if not p["literals"]:
            assert p["specifications"] == [] and "carries" not in coord
            continue
        version += 1
        carried = [(d["abstraction"], d["role"], d["version"]) for d in coord["carries"]["specs"]]
        assert carried == [(p["name"], "criterion", 1), (p["name"], "ontology", 1),
                           ("round", "criterion", version), ("round", "ontology", version)]
        for d in coord["carries"]["specs"]:
            assert lookups.active(record[:at], d["abstraction"], d["role"]) != d["addr"]
            assert lookups.active(record[:at + 1], d["abstraction"], d["role"]) == d["addr"]
        nxt = next(n for n in rounds if n > at)
        assert record[nxt]["coord"]["ontology"] == coord["carries"]["specs"][3]["addr"]
        said = lookups.load(record, coord["carries"]["specs"][2]["addr"])["inputs"]["context"]["said"]["from"]
        assert said[-1] == p["name"] and len(said) == 22 + version - 1
        first = next(e for e in record[at:] if e["coord"].get("abstraction") == p["name"])
        assert first["payload"]["kind"] == "unit" and first["coord"]["n"] > nxt   # it speaks on the new epoch


def test_tau_root_and_learn_refuse_what_is_not_exact(committed):
    _, record = committed["php43"]
    at = positions(record, "learn")[0]
    P, p = record[:at], record[at]["payload"]
    o = lookups.load(P, record[at]["coord"]["ontology"])
    assert governance.carry(P, o, p)[2] is None
    gap = copy.deepcopy(p)
    for s in gap["specifications"][2:]:
        s["version"] = 3
    assert governance.carry(P, o, gap)[2] is not None                     # τ_root: a version with a gap
    alone = dict(p, specifications=p["specifications"][1:2])
    assert governance.carry(P, o, alone)[2] is not None                   # an ontology without its criterion
    assert judges(record, at, p)
    altered = copy.deepcopy(p)
    altered["specifications"][1]["body"]["result"] = "None"
    assert not judges(record, at, altered)                                # the criterion of learn: exactly
    assert not judges(record, at, dict(p, specifications=p["specifications"][:2]))
    assert not judges(record, at, dict(p, specifications=[]))


def test_adapt_puts_the_second_policy_in_force_at_its_event(committed):
    _, record = committed["php43"]
    switch, = positions(record, "adapt")
    learns = positions(record, "learn")
    assert learns[2] < switch < learns[3]                                 # after the third learned clause
    carried, = record[switch]["coord"]["carries"]["specs"]
    assert (carried["abstraction"], carried["role"], carried["version"]) == ("decide", "ontology", 2)
    decisions = [e["coord"] for e in record if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == "decide"]
    assert all((c["n"] > switch) == (c["ontology"] == carried["addr"]) for c in decisions)
    assert len({c["criterion"] for c in decisions}) == 1                  # one criterion judges both (D2)
    v1 = lookups.load(record, decisions[0]["ontology"])
    for n in range(learns[2] + 1, switch + 1):                            # due and not decided: version 1 waits
        assert evaluation.realize(record[:n], v1) is None
    p = record[switch]["payload"]
    assert judges(record, switch, p)
    assert not judges(record, switch, dict(p, conflicts=2))               # the evidence stated falsely
    assert not judges(record, switch, p, prefix=learns[2])                # before the third conflict
    assert not judges(record, switch, dict(p, conflicts=2), prefix=learns[2])   # stated truly, but too few
    assert not judges(record, switch, p, prefix=switch + 1)               # a second change
    assert not judges(record, switch, dict(p, specifications=[]))
    other = copy.deepcopy(p)
    other["specifications"][0]["body"]["result"] = "None"
    assert not judges(record, switch, other)                              # not the designated version


@pytest.mark.parametrize(("n", "m", "seed"), [(12, 51, 4), (16, 68, 1), (20, 85, 1)])
def test_the_change_of_policy_changes_the_course_and_not_the_verdict(n, m, seed):
    variables, formula = ks.random_kcnf(n, m, 3, seed)
    _, changed = run(ks.definition(variables, formula, after=1))
    _, kept = run(ks.definition(variables, formula, after=NEVER))
    assert positions(changed, "adapt") and not positions(kept, "adapt")
    assert values(changed, "verdict")[0]["sat"] == values(kept, "verdict")[0]["sat"] == dpll(formula)
    assert values(changed, "decide") != values(kept, "decide")
    assert verify(changed, judgments_only=True) == []


# ---- the checks applied to every example ----

def test_an_interrupted_run_continues_to_the_same_record():
    """After every event of PHP(3,2), with the change of policy after the first conflict, and
    right before every carrying event of PHP(4,3)."""
    variables, formula = ks.pigeonhole(3, 2)
    small = ks.definition(variables, formula, after=1)
    php43 = ks.definition(*ks.pigeonhole(4, 3))
    for d, cuts in ((small, None), (php43, "carrying")):
        _, full = run(d)
        if cuts is None:
            cuts = range(1, len(full) + 1)
        else:
            carrying = [e["coord"]["n"] for e in full if "carries" in e["coord"]]
            cuts = sorted(set(carrying) | {1, len(full)})
        for cut in cuts:
            store = MemoryStore()
            for n in range(cut):
                store.put_if_absent(n, copy.deepcopy(full[n]))
            System.from_dict(d).run(store, log=quiet)
            assert list(read(store)) == full, f"interrupted after {cut} events"


def test_the_same_lineages_under_random_schedules_and_killed_workers(committed):
    killed_brought_in = 0
    for name in INSTANCES:
        expected = lineages(committed[name][1])
        rnd = random.Random(name)
        store = MemoryStore()
        workers.run(System(KSAT / name), store, log=quiet, timeout=300.0,
                    hesitate=lambda: time.sleep(rnd.random() * 0.001))
        record = list(read(store))
        assert verify(record) == [] and lineages(record) == expected
        store = MemoryStore()
        deaths = run_killing(System(KSAT / name), store, seed=len(name))
        record = list(read(store))
        assert deaths and verify(record) == [] and lineages(record) == expected
        killed_brought_in += sum(1 for a in deaths if a.startswith("l"))
    assert killed_brought_in, "no worker of a learned clause was killed"


# ---- the criteria as authorities ----

def test_the_clause_criteria_refuse_a_false_or_untimely_speech(committed):
    _, record = committed["random20"]
    units = [e for e in record if e["coord"]["kind"] == "exec" and e["payload"].get("kind") == "unit"]
    conflicts = [e for e in record if e["coord"]["kind"] == "exec" and e["payload"].get("kind") == "conflict"]
    assert units and conflicts
    for e in units[:10] + conflicts[:3]:
        at, p = e["coord"]["n"], e["payload"]
        assert judges(record, at, p)
        assert not judges(record, at, dict(p, clause="c999"))                    # for another clause
        assert not judges(record, at, dict(p, round=p["round"] + 1))             # out of turn
        assert not judges(record, at, p, prefix=at + 1)                          # a second time
        assert not judges(record, at, dict(p, kind="vote", literal=0))           # not a total frame
    for e in units[:10]:
        at, p = e["coord"]["n"], e["payload"]
        assert not judges(record, at, dict(p, literal=-p["literal"]))
        assert not judges(record, at, dict(p, kind="conflict", literal=0))
    for e in conflicts[:3]:
        at, p = e["coord"]["n"], e["payload"]
        assert not judges(record, at, dict(p, kind="unit", literal=1))


def test_the_criterion_of_decide_admits_any_correct_decision_and_nothing_else(committed):
    (variables, _), _ = INSTANCES["random20"]
    _, record = committed["random20"]
    rounds = values(record, "round")
    for at in positions(record, "decide")[:6]:
        p = record[at]["payload"]
        frame = next(f for f in reversed(rounds) if f["round"] == p["round"])
        values_ = {s["literal"] for s in frame["trail"]}
        free = [v for v in variables if v not in values_ and -v not in values_]
        assigned = frame["trail"][0]["literal"] if frame["trail"] else None
        assert judges(record, at, p)
        for literal in (free[-1], -free[-1]):                                     # another policy, still correct
            assert judges(record, at, dict(p, literals=[literal]))
        assert judges(record, at, dict(p, literals=free[:3]))
        assert not judges(record, at, dict(p, literals=[]))
        assert not judges(record, at, dict(p, literals=[free[0], -free[0]]))
        assert not judges(record, at, dict(p, literals=[max(variables) + 1]))
        assert not judges(record, at, dict(p, round=p["round"] + 1))
        if assigned is not None:
            assert not judges(record, at, dict(p, literals=[assigned]))
        assert not judges(record, at, p, prefix=at + 1)                           # decided already


def test_the_criterion_of_learn_admits_any_valid_derivation_and_nothing_else(committed):
    _, record = committed["php43"]
    alternatives = 0
    for at in positions(record, "learn"):
        p = record[at]["payload"]
        P = record[:at]
        spec = lookups.load(P, record[at]["coord"]["criterion"])
        names, clauses, templates = (spec["constants"][k] for k in ("NAMES", "CLAUSES", "TEMPLATES"))
        learned = {q["name"]: q["literals"] for q in values(P, "learn")}
        frame = values(P, "round")[-1]
        assert judges(record, at, p)
        assert not judges(record, at, dict(p, name="l99"))
        assert not judges(record, at, dict(p, level=frame["level"] + 1))
        assert not judges(record, at, dict(p, start="c999"))
        assert not judges(record, at, dict(p, literals=p["literals"] + [99]))
        if p["chain"]:
            assert not judges(record, at, dict(p, chain=p["chain"][:-1]))
        # one resolution step more than the first unique implication point: another valid
        # derivation, admitted with what it must carry (D2)
        table = lib.clause_table(clauses, learned)
        reason = {s["literal"]: s["reason"] for s in frame["trail"]}
        for literal in p["literals"]:
            parent = reason.get(-literal)
            if parent in (None, "decide"):
                continue
            resolvent = (set(p["literals"]) - {literal}) | {x for x in table[parent] if x != -literal}
            if any(-x in resolvent for x in resolvent):
                continue
            literals = sorted(resolvent)
            longer = dict(p, chain=p["chain"] + [{"clause": parent, "literal": -literal}], literals=literals,
                          specifications=lib.carried_for(names, learned, templates, p["name"], literals))
            assert judges(record, at, longer), (p["name"], literal)
            alternatives += 1
            break
    assert alternatives >= 2


def derive(table, start, chain):
    """What a chain gives from its start when every step is applied blindly: the clause so far
    without the complement of the step's literal, joined with the parent without the literal."""
    current = set(table[start])
    for step in chain:
        current = (current - {-step["literal"]}) | (set(table[step["clause"]]) - {step["literal"]})
    return current


def test_the_criterion_of_learn_refuses_what_is_not_a_resolution_from_a_conflict(committed):
    """Each forged derivation states exactly what its steps give and carries what that clause
    must carry, so that only the rule it breaks can refuse it: a start that is not a false clause
    of the frame, a parent without the step's literal, a step without a clash, a tautology."""
    _, record = committed["php43"]
    seen = {"start": 0, "parent": 0, "clash": 0, "tautology": 0}
    for at in positions(record, "learn"):
        p = record[at]["payload"]
        P = record[:at]
        spec = lookups.load(P, record[at]["coord"]["criterion"])
        names, clauses, templates = (spec["constants"][k] for k in ("NAMES", "CLAUSES", "TEMPLATES"))
        learned = {q["name"]: q["literals"] for q in values(P, "learn")}
        table = lib.clause_table(clauses, learned)
        frame = values(P, "round")[-1]

        def forged(start, chain):
            literals = sorted(derive(table, start, chain))
            return dict(p, start=start, chain=chain, literals=literals,
                        specifications=lib.carried_for(names, learned, templates, p["name"], literals))

        other = next(n for n in names if n not in frame["conflicts"])
        assert not judges(record, at, forged(other, []))
        seen["start"] += 1
        if p["chain"]:
            last = p["chain"][-1]
            wrong = next((n for n in table if last["literal"] not in table[n] and n != last["clause"]), None)
            if wrong is not None:
                assert not judges(record, at, forged(p["start"], p["chain"][:-1] + [dict(last, clause=wrong)]))
                seen["parent"] += 1
        current, tried = derive(table, p["start"], p["chain"]), set()
        for n in table:
            for literal in table[n]:
                result = (current - {-literal}) | (set(table[n]) - {literal})
                tautology = any(-x in result for x in result)
                kind = "clash" if -literal not in current and not tautology else \
                       "tautology" if -literal in current and tautology else None
                if kind and kind not in tried:                     # one of each kind per learned clause
                    step = {"clause": n, "literal": literal}
                    assert not judges(record, at, forged(p["start"], p["chain"] + [step])), (kind, step)
                    tried.add(kind)
                    seen[kind] += 1
    assert all(seen.values()), seen


def test_decide_waits_while_a_change_of_policy_is_due():
    """With the change due after the first learned clause and an adapt that never decides,
    version 1 of decide makes no decision after that clause: it waits for adapt."""
    variables, formula = ks.random_kcnf(16, 68, 3, 1)
    d = ks.definition(variables, formula, after=1)
    for key in ("adapt/ontology.v1", "adapt/criterion.v1"):
        d["specifications"][key]["constants"]["AFTER"] = NEVER
    system, record = run(d)
    first, = positions(record, "learn")
    assert positions(record, "decide") and max(positions(record, "decide")) < first
    assert values(record, "verdict") == [] and system.states(record)["decide"] == "wait"
    frame = values(record, "round")[-1]
    names, clauses = d["constants"]["NAMES"], d["constants"]["CLAUSES"]
    learned = {p["name"]: p["literals"] for p in values(record, "learn")}
    assert lib.decision_due(frame, values(record, "decide")[-1])                 # a decision is due
    assert lib.propose_decision(names, clauses, variables, frame, values(record, "decide")[-1], learned, True) is None


def test_the_criteria_of_round_and_verdict_refuse_a_forged_frame_or_verdict(committed):
    for name, (_, record) in committed.items():
        for at in positions(record, "round")[1:40:7]:
            frame = record[at]["payload"]
            assert judges(record, at, frame)
            assert not judges(record, at, dict(frame, quiet=not frame["quiet"]))
            assert not judges(record, at, dict(frame, round=frame["round"] + 1))
            assert not judges(record, at, dict(frame, votes=["c1"]))
            if frame["trail"]:
                trail = copy.deepcopy(frame["trail"])
                trail[-1]["literal"] = -trail[-1]["literal"]
                assert not judges(record, at, dict(frame, trail=trail))
        at, = positions(record, "verdict")
        verdict = record[at]["payload"]
        assert judges(record, at, verdict)
        assert not judges(record, at, verdict, prefix=at + 1)                    # once
        assert not judges(record, at, {"sat": not verdict["sat"], "model": [] if verdict["sat"] else [1]})
        if verdict["sat"]:
            model = list(verdict["model"])
            model[0] = -model[0]
            assert not judges(record, at, dict(verdict, model=model))
