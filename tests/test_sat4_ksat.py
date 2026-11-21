"""Tests of examples/sat4 beyond its instance: k-SAT and evolutive consensus.

The criteria of sat4 are written for any CNF formula. Its ontologies execute one trace: the
conflict of (x ∨ A) and (¬x ∨ A), the resolvent A, and the retry in which A is unit. Four groups
of tests check this against all assignments, by definitions written here independently of lib.py.

1. The trace for every k from 2 to 8, with random variable numbers, signs, literal and probe order
   and unused variables. The system of examples/sat4, with only its constants changed, meets the
   expected end written here for its instance and replays in both modes. It continues to the same
   record after an interruption at every event. Workers give the lineages of the agenda under
   random schedules and with workers killed.
2. Evolutive consensus (Radenković et al., Facta Universitatis, Ser. Electronics and Energetics
   39(4), 2026, Section 8; DOI 10.2298/FUEE2604723R,
   https://casopisi.junis.ni.ac.rs/index.php/FUElectEnerg/article/view/14966): the composite criterion
   τ = τ₁ ∧ … ∧ τₘ, one τᵢ per clause, evaluated over the shared record. The witness criterion is
   that conjunction on the completions of the propagated retry, and consensus is constituted when
   a witness is admitted. With clauses on other variables added, a run either reaches consensus
   or ends with the witness closed (τ false). The record and its terminal states show which, and
   the failure is not silent. If a model extends the retry, the criterion admits it, so the gap is
   in the ontology's choice. If none does, the criterion admits nothing, and this path is
   exhausted.
3. Different strategies, different fixed points (ibid., Section 8.4): every choice of the last
   literal of the probe is admitted by the same criterion of branch (D2). Each choice leads to its
   own witness, and each witness is a model.
4. The criteria as authorities on random k-CNF formulas (k = 2..6):
   - every admitted unit is forced in every model of the branch;
   - every admitted conflict leaves the branch without a model;
   - every resolvent of an admitted conflict holds in every model and is false on the branch;
   - for any two clauses that clash, the resolvent is refused if it would be a tautology and
     otherwise holds in every model;
   - the branch, unit, conflict and witness criteria admit exactly what the definitions here
     admit, and a witness of the right length that repeats a variable or names another is refused;
   - the ontologies propose whenever their criteria admit something.
"""
import copy
import random
import time
from importlib.util import module_from_spec, spec_from_file_location
from itertools import product
from pathlib import Path

import pytest

from ztes import model as evaluation
from ztes.substrate import lookups
from ztes.substrate.replay import verify
from ztes.substrate.store import MemoryStore, read
from ztes.system import workers
from ztes.system.report import check_expect
from ztes.system.system import System

from test_vns import lineages, run_with_failures

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sat4"
LIB_SPEC = spec_from_file_location("sat4_lib_ksat", EXAMPLE / "lib.py")
lib = module_from_spec(LIB_SPEC)
LIB_SPEC.loader.exec_module(lib)
NAMES = ("branch", "propagate", "conflict", "learn", "adapt", "witness")


def quiet(*_):
    pass


# ---- definitions written here, independently of lib.py ----

def satisfies(assignment, clause):
    """τᵢ for one clause: some literal of the clause is in the assignment."""
    return any(literal in assignment for literal in clause)


def assignments(variables):
    """All 2ⁿ total assignments of the variables."""
    for values in product((False, True), repeat=len(variables)):
        yield [var if value else -var for var, value in zip(variables, values)]


def models(formula, variables):
    return [a for a in assignments(variables) if all(satisfies(a, clause) for clause in formula)]


def extends(assignment, partial):
    return set(partial) <= set(assignment)


def consistent(variables, literals):
    """Each variable once, and only variables of the formula."""
    named = [abs(literal) for literal in literals]
    return len(set(named)) == len(named) and all(var in variables for var in named)


def forced(clause, partial):
    """The literal a clause forces under a partial assignment: no literal of it is true, and
    exactly one is not false."""
    if satisfies(partial, clause):
        return None
    left = [literal for literal in clause if -literal not in partial]
    return left[0] if len(left) == 1 else None


def values(record, name):
    return [e["payload"] for e in record if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == name]


# ---- instances and runs ----

def trace(k, unused, seed):
    """(variables, formula, probe, x, A) for the trace of width k: (x ∨ A) and (¬x ∨ A) with
    |A| = k − 1, random variable numbers and signs, and the literals of each clause and of the
    probe ¬A in random order."""
    rnd = random.Random(f"trace/{k}/{unused}/{seed}")
    variables = sorted(rnd.sample(range(1, 4 * (k + unused) + 1), k + unused))
    x, *others = rnd.sample(variables, k)
    A = [var if rnd.random() < 0.5 else -var for var in others]
    d1, d2 = [x] + A, [-x] + A
    rnd.shuffle(d1)
    rnd.shuffle(d2)
    probe = [-literal for literal in A]
    rnd.shuffle(probe)
    return variables, [d1, d2], probe, x, A


def definition(variables, formula, probe, expect=None):
    d = copy.deepcopy(System(EXAMPLE).definition)
    d["constants"].update(VARIABLES=variables, FORMULA=formula, PROBE=probe)
    d.pop("expect")
    if expect is not None:
        d["expect"] = expect
    return d


def run(d):
    system, store = System.from_dict(d), MemoryStore()
    system.run(store, log=quiet)
    return system, list(read(store))


def expected_end(variables, formula, probe, x):
    """The expected end of the trace, as in system.json, for this instance: the witness is the
    propagated retry with every other variable false."""
    retry = probe[:-1]
    unit = -probe[-1]
    return {
        "events": 21,
        "states": {name: "wait" for name in NAMES},
        "values": {
            "branch": [{"id": 0, "assumptions": probe}, {"id": 1, "assumptions": retry}],
            "propagate": [{"branch": 0, "reason": 0, "literal": x},
                          {"branch": 1, "reason": len(formula), "literal": unit}],
            "conflict": [{"branch": 0, "clause": 1}],
            "learn": [{"left": 0, "right": 1, "pivot": abs(x), "literals": sorted(-literal for literal in probe)}],
            "witness": [[var if var in retry + [unit] else -var for var in variables]],
        },
    }


TRACES = [(k, unused, seed) for k in range(2, 9) for unused in (0, 2) for seed in range(4)]


# ---- 1. the trace for every k ----

@pytest.mark.parametrize(("k", "unused", "seed"), TRACES)
def test_the_trace_runs_and_replays_for_every_k(k, unused, seed):
    variables, formula, probe, x, A = trace(k, unused, seed)
    system, record = run(definition(variables, formula, probe, expected_end(variables, formula, probe, x)))
    assert check_expect(system, record, log=quiet) == []
    assert verify(record) == [] and verify(record, judgments_only=True) == []
    all_models = models(formula, variables)
    learned, = values(record, "learn")
    first, retry = values(record, "branch")
    witness, = values(record, "witness")
    assert all(satisfies(m, learned["literals"]) for m in all_models)                 # F ⊨ L
    assert not any(extends(m, first["assumptions"]) for m in all_models)             # the first branch is closed
    assert any(extends(m, first["assumptions"][:-1]) for m in all_models)            # the retry is not
    assert witness in all_models and extends(witness, retry["assumptions"])
    assert -probe[-1] in A and -probe[-1] in witness                                 # the literal the resolvent forces


@pytest.mark.parametrize("k", (3, 7))
def test_an_interrupted_run_continues_to_the_same_record_for_every_k(k):
    variables, formula, probe, x, _ = trace(k, 2, 0)
    d = definition(variables, formula, probe)
    _, full = run(d)
    for cut in range(1, len(full) + 1):
        store = MemoryStore()
        for n in range(cut):
            store.put_if_absent(n, copy.deepcopy(full[n]))
        System.from_dict(d).run(store, log=quiet)
        assert list(read(store)) == full, f"k = {k}, interrupted after {cut} events"


@pytest.mark.parametrize("k", (2, 5, 8))
def test_workers_give_the_lineages_of_the_agenda_for_every_k(k):
    variables, formula, probe, x, _ = trace(k, 2, 1)
    d = definition(variables, formula, probe, expected_end(variables, formula, probe, x))
    expected, killed = lineages(run(d)[1]), 0
    for seed in range(2):
        rnd = random.Random(seed)
        system, store = System.from_dict(d), MemoryStore()
        workers.run(system, store, log=quiet, hesitate=lambda: time.sleep(rnd.random() * 0.003))
        record = list(read(store))
        assert verify(record) == [] and lineages(record) == expected
        assert check_expect(system, record, log=quiet, any_schedule=True) == []
    for seed in range(3):
        system, store = System.from_dict(d), MemoryStore()
        killed += len(run_with_failures(system, store, seed))
        record = list(read(store))
        assert verify(record) == [] and lineages(record) == expected
    assert killed, "no worker was killed in any of the runs"


# ---- 2. evolutive consensus ----

def with_other_clauses(seed):
    """The trace of a random width with clauses on four other variables. Some instances get all
    four clauses of width 2 over two of them, so that no assignment satisfies them."""
    rnd = random.Random(f"consensus/{seed}")
    k = rnd.randint(2, 6)
    variables, formula, probe, x, A = trace(k, 0, seed)
    others = [max(variables) + i for i in range(1, 5)]
    extra = []
    for _ in range(rnd.randint(1, 5)):
        chosen = rnd.sample(others, rnd.randint(2, 4))
        extra.append([var if rnd.random() < 0.5 else -var for var in chosen])
    if rnd.random() < 0.3:
        a, b = rnd.sample(others, 2)
        extra += [[a, b], [a, -b], [-a, b], [-a, -b]]
    return variables + others, formula + extra, probe, x


def test_consensus_is_constituted_when_all_clause_criteria_hold_at_once():
    outcomes = {"consensus": 0, "the ontology's choice": 0, "exhausted": 0}
    for seed in range(120):
        variables, formula, probe, x = with_other_clauses(seed)
        system, record = run(definition(variables, formula, probe))
        assert verify(record) == [] and verify(record, judgments_only=True) == []
        retry, = [b["assumptions"] for b in values(record, "branch") if b["id"] == 1]
        unit = values(record, "propagate")[-1]
        assert unit["branch"] == 1 and unit["reason"] == len(formula)                  # the resolvent, not another clause
        prefix = retry + [unit["literal"]]
        reached = values(record, "witness")
        decided = record[:-1] if reached else record                                   # the context of the witness's turn
        assert not reached or record[-1]["coord"]["abstraction"] == "witness"
        criterion = lookups.load(decided, lookups.active(decided, "witness", "criterion"))
        completions = []
        for candidate in assignments(variables):
            composite = extends(candidate, prefix) and all(satisfies(candidate, clause) for clause in formula)
            assert evaluation.judge(decided, criterion, candidate) == composite, (seed, candidate)
            assert not (reached and evaluation.judge(record, criterion, candidate))   # constituted once
            completions += [candidate] if composite else []
        proposed = [var if var in prefix else -var for var in variables]           # the ontology's rule, written here
        states = system.states(record)
        if all(satisfies(proposed, clause) for clause in formula):
            assert reached == [proposed] and states == {name: "wait" for name in NAMES}
            outcomes["consensus"] += 1
        else:
            assert reached == [] and states["witness"] == "closed"                     # observable, not silent
            assert all(states[name] == "wait" for name in NAMES if name != "witness")
            assert len(record) == 20
            outcomes["the ontology's choice" if completions else "exhausted"] += 1
    assert min(outcomes.values()) >= 10, outcomes


# ---- 3. different strategies, different fixed points ----

@pytest.mark.parametrize("k", (3, 5, 8))
def test_each_order_of_the_probe_reaches_its_own_model_under_one_criterion(k):
    variables, formula, probe, x, A = trace(k, 1, 2)
    witnesses, criteria, ontologies = [], set(), set()
    all_models = models(formula, variables)
    for last in range(len(probe)):
        order = probe[:last] + probe[last + 1:] + [probe[last]]
        system, record = run(definition(variables, formula, order, expected_end(variables, formula, order, x)))
        assert check_expect(system, record, log=quiet) == [] and verify(record) == []
        trial = next(e for e in record if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == "branch")
        criteria.add(trial["coord"]["criterion"])
        ontologies.add(trial["coord"]["ontology"])
        witness, = values(record, "witness")
        assert witness in all_models
        witnesses.append(tuple(witness))
    assert len(criteria) == 1                                                          # one authority
    assert len(ontologies) == len(set(witnesses)) == k - 1                             # k − 1 strategies, k − 1 fixed points


# ---- 4. the criteria as authorities on random k-CNF formulas ----

def random_formula(rnd):
    n = rnd.randint(3, 8)
    k = rnd.randint(2, min(6, n))
    variables = list(range(1, n + 1))
    formula = [[var if rnd.random() < 0.5 else -var for var in rnd.sample(variables, k)]
               for _ in range(rnd.randint(1, 4 * n))]
    return variables, formula


def test_the_criteria_are_sound_and_exact_on_random_kcnf():
    seen = {"widths": set(), "unsatisfiable": 0, "units": 0, "conflicts": 0, "resolvents": 0, "tautologies": 0,
            "witnesses admitted": 0, "witnesses refused": 0}
    for seed in range(300):
        rnd = random.Random(f"kcnf/{seed}")
        variables, formula = random_formula(rnd)
        seen["widths"].add(len(formula[0]))
        all_models = models(formula, variables)
        seen["unsatisfiable"] += not all_models
        A = [var if rnd.random() < 0.5 else -var for var in rnd.sample(variables, rnd.randint(0, len(variables)))]
        of_branch = [m for m in all_models if extends(m, A)]
        literals = sorted({literal for clause in formula for literal in clause} | {-l for clause in formula for l in clause})

        # branch: exactly a consistent next branch
        for candidate in (A, A + A[:1], A + [max(variables) + 1], A + [-literal for literal in A[:1]], []):
            assert lib.check_branch(variables, [], {"id": 0, "assumptions": candidate}) == consistent(variables, candidate)
            assert not lib.check_branch(variables, [], {"id": 1, "assumptions": candidate})

        # propagate: exactly the forced literals of the clauses; each forced in every model of the branch
        branches = [{"id": 0, "assumptions": A}]
        admitted = []
        for index in range(len(formula)):
            for literal in literals:
                candidate = {"branch": 0, "reason": index, "literal": literal}
                ok = lib.check_unit(formula, branches, [], [], candidate)
                assert ok == (forced(formula[index], A) == literal), (seed, candidate)
                if ok:
                    admitted.append(candidate)
                    assert all(literal in m for m in of_branch), (seed, candidate)
        assert not lib.check_unit(formula, branches, [], [], {"branch": 1, "reason": 0, "literal": literals[0]})
        proposal = lib.propose_unit(formula, branches, [], [])
        assert (proposal is None) == (not admitted) and (proposal is None or proposal in admitted)
        seen["units"] += len(admitted)

        # conflict and resolution: an admitted conflict closes the branch, and the resolvent holds in
        # every model and is false on the branch, so it closes the branch in every later context
        for unit in admitted:
            trial = A + [unit["literal"]]
            falsifiable = [j for j, clause in enumerate(formula) if all(-literal in trial for literal in clause)]
            conflict = lib.propose_conflict(formula, branches, [unit], [])
            assert (conflict is None) == (not falsifiable)
            for j in range(len(formula)):
                candidate = {"branch": 0, "clause": j}
                assert lib.check_conflict(formula, branches, [unit], [], candidate) == (j in falsifiable)
                if j in falsifiable:
                    seen["conflicts"] += 1
                    assert of_branch == [], (seed, unit, j)
                    proof = lib.resolution_certificate(formula, [unit], [candidate])
                    if proof is not None:
                        seen["resolvents"] += 1
                        assert all(satisfies(m, proof["literals"]) for m in all_models), (seed, proof)
                        assert all(-literal in A for literal in proof["literals"]), (seed, proof)
                        assert unit["literal"] in formula[proof["left"]] and -unit["literal"] in formula[proof["right"]]

        # resolution in general: for every two clauses that clash on a literal, the resolvent is
        # refused if it would be a tautology, and otherwise holds in every model of the formula
        for left, reason in enumerate(formula):
            for right, other in enumerate(formula):
                for literal in reason:
                    if -literal not in other:
                        continue
                    proof = lib.resolution_certificate(formula, [{"branch": 0, "reason": left, "literal": literal}],
                                                       [{"branch": 0, "clause": right}])
                    resolvent = {l for l in reason + other if abs(l) != abs(literal)}
                    if any(-l in resolvent for l in resolvent):
                        assert proof is None, (seed, left, right)
                        seen["tautologies"] += 1
                    else:
                        assert proof == {"left": left, "right": right, "pivot": abs(literal),
                                         "literals": sorted(resolvent)}, (seed, left, right)
                        assert all(satisfies(m, proof["literals"]) for m in all_models), (seed, proof)

        # witness: exactly a total model that extends the propagated retry
        if admitted and A:
            retry = {"id": 1, "assumptions": A[:-1]}
            second = lib.propose_unit(formula, [branches[0], retry], [admitted[0]], [])
            if second is not None:
                both, propagated = [branches[0], retry], [admitted[0], second]
                prefix = A[:-1] + [second["literal"]]
                for candidate in assignments(variables):
                    rnd.shuffle(candidate)
                    expected = extends(candidate, prefix) and all(satisfies(candidate, c) for c in formula)
                    assert lib.check_witness(formula, variables, both, propagated, candidate) == expected
                    seen["witnesses admitted" if expected else "witnesses refused"] += 1
                    if expected:                                                       # total in length only
                        for malformed in (candidate[:-1] + [candidate[0]], candidate[:-1] + [-candidate[0]],
                                          candidate[:-1] + [max(variables) + 1]):
                            assert not lib.check_witness(formula, variables, both, propagated, malformed)
                if all_models:
                    assert not lib.check_witness(formula, variables, both, propagated, all_models[0][:-1])
    assert seen["widths"] == {2, 3, 4, 5, 6}
    assert min(v for name, v in seen.items() if name != "widths") >= 20, seen
