"""Tests of examples/sat4: a 4-CNF conflict, a reusable resolvent and a governed retry.

The learned clause is checked against all 16 assignments, the record against its expected end in
both replay modes and by workers, and the governing event against the ontology active on each side
of it. The checks applied to every example follow: an interrupted run continues to the same record,
and workers give the lineages of the agenda under random schedules and with workers killed. The
criteria are then checked as authorities (D2): on the record, a candidate out of turn or malformed
is refused, and any correct branch is admitted, while which branch is tried is the choice of the
active ontology, put in force by the governing event (R1); on small inputs written here, the
helpers refuse what this one instance cannot show (a satisfied clause as a reason, a tautology or a
resolvent without a clash, a witness that falsifies a clause).
"""
import copy
import random
import time
from importlib.util import module_from_spec, spec_from_file_location
from copy import deepcopy
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


def quiet(*_):
    pass


def positions(record, name):
    return [i for i, event in enumerate(record)
            if event["coord"]["kind"] == "exec" and event["coord"]["abstraction"] == name]


def judges(record, position, candidate, prefix_length=None):
    prefix = record[:position if prefix_length is None else prefix_length]
    criterion = lookups.load(prefix, record[position]["coord"]["criterion"])
    return evaluation.judge(prefix, criterion, candidate)


@pytest.fixture(scope="module")
def agenda():
    system, store = System(EXAMPLE), MemoryStore()
    system.run(store, log=quiet)
    return system, list(read(store))


def test_example_meets_its_expected_end_and_replays(agenda):
    system, record = agenda
    assert system.check(log=quiet) == []
    assert check_expect(system, record, log=quiet) == []
    assert verify(record) == []
    assert verify(record, judgments_only=True) == []


def test_workers_meet_the_same_expectations_and_replay():
    system, store = System(EXAMPLE), MemoryStore()
    workers.run(system, store, log=quiet)
    record = list(read(store))
    assert check_expect(system, record, log=quiet, any_schedule=True) == []
    assert verify(record) == []
    assert verify(record, judgments_only=True) == []


def test_resolvent_conflict_and_witness_match_all_assignments(agenda):
    system, record = agenda
    variables = system.definition["constants"]["VARIABLES"]
    formula = system.definition["constants"]["FORMULA"]
    assert all(len(clause) == len({abs(literal) for literal in clause}) == 4 for clause in formula)
    proof = record[positions(record, "learn")[0]]["payload"]
    first = record[positions(record, "branch")[0]]["payload"]["assumptions"]
    witness = record[positions(record, "witness")[0]]["payload"]

    models = []
    for values in product((False, True), repeat=len(variables)):
        assignment = [var if value else -var for var, value in zip(variables, values)]
        satisfies_formula = all(any(literal in assignment for literal in clause) for clause in formula)
        satisfies_resolvent = any(literal in assignment for literal in proof["literals"])
        assert satisfies_formula == satisfies_resolvent
        if satisfies_formula:
            models.append(assignment)
    assert len(models) == 14
    assert all(not set(first).issubset(assignment) for assignment in models)
    assert witness in models


def test_policy_change_requires_evidence_and_takes_effect_at_the_event(agenda):
    _, record = agenda
    switch, = positions(record, "adapt")
    learn, = positions(record, "learn")
    trial, retry = positions(record, "branch")
    candidate = record[switch]["payload"]
    version, = record[switch]["coord"]["carries"]["specs"]
    assert trial < learn < switch < retry
    assert (version["abstraction"], version["version"]) == ("branch", 2)
    assert lookups.active(record[:switch], "branch", "ontology") == record[trial]["coord"]["ontology"]
    assert lookups.active(record[:switch + 1], "branch", "ontology") == version["addr"]
    assert record[retry]["coord"]["ontology"] == version["addr"]
    assert record[retry]["coord"]["criterion"] == record[trial]["coord"]["criterion"]
    assert judges(record, switch, candidate)
    assert not judges(record, switch, candidate, prefix_length=learn)
    assert not judges(record, switch, dict(candidate, conflicts=0))
    wrong_policy = deepcopy(candidate)
    wrong_policy["specifications"][0]["body"]["result"] = "None"
    assert not judges(record, switch, wrong_policy)


@pytest.mark.parametrize(("abstraction", "occurrence", "change"), [
    ("propagate", 0, {"reason": 1}),
    ("conflict", 0, {"clause": 0}),
    ("conflict", 0, {"branch": 1}),
    ("learn", 0, {"pivot": 2}),
    ("learn", 0, {"literals": [4]}),
    ("propagate", 1, {"reason": 0}),
])
def test_admission_checks_reject_incorrect_evidence(agenda, abstraction, occurrence, change):
    _, record = agenda
    position = positions(record, abstraction)[occurrence]
    candidate = record[position]["payload"]
    assert judges(record, position, candidate)
    assert not judges(record, position, dict(candidate, **change))


def test_witness_judgment_checks_the_assignment_instead_of_the_ontology_choice(agenda):
    _, record = agenda
    position, = positions(record, "witness")
    assert judges(record, position, [1, -2, -3, 4])
    assert not judges(record, position, [-1, -2, -3, -4])
    assert not judges(record, position, [-1, -2, 2, 4])


# ---- the checks applied to every example ----

def test_an_interrupted_run_continues_to_the_same_record(agenda):
    _, full = agenda
    for cut in range(1, len(full) + 1):
        store = MemoryStore()
        for n in range(cut):
            store.put_if_absent(n, copy.deepcopy(full[n]))
        System(EXAMPLE).run(store, log=quiet)
        assert list(read(store)) == full, f"interrupted after {cut} events"


def test_the_same_lineages_under_random_schedules_and_killed_workers(agenda):
    expected, killed = lineages(agenda[1]), 0
    for seed in range(3):
        rnd = random.Random(seed)
        store = MemoryStore()
        workers.run(System(EXAMPLE), store, log=quiet, hesitate=lambda: time.sleep(rnd.random() * 0.003))
        record = list(read(store))
        assert verify(record) == [] and lineages(record) == expected
    for seed in range(3):
        store = MemoryStore()
        killed += len(run_with_failures(System(EXAMPLE), store, seed))
        record = list(read(store))
        assert verify(record) == [] and lineages(record) == expected
    assert killed, "no worker was killed in any of the runs"


# ---- the criteria as authorities (D2) ----

def test_the_criteria_refuse_a_candidate_out_of_turn_or_malformed(agenda):
    _, record = agenda
    trial, retry = positions(record, "branch")
    switch, = positions(record, "adapt")
    second, = positions(record, "propagate")[1:]
    witness, = positions(record, "witness")
    assert not judges(record, trial, {"id": 0, "assumptions": [-2, -2, -4]})       # a variable twice
    assert not judges(record, trial, {"id": 0, "assumptions": [-2, 2, -4]})        # a variable with both signs
    assert not judges(record, trial, {"id": 0, "assumptions": [-2, -3, 5]})        # not a variable of the formula
    assert not judges(record, trial, {"id": 1, "assumptions": [-2, -3, -4]})       # out of turn
    assert not judges(record, retry, dict(record[retry]["payload"], id=0))          # out of turn
    assert not judges(record, second, dict(record[second]["payload"], branch=0))    # the propagation of another branch
    assert not judges(record, switch, record[switch]["payload"], prefix_length=switch + 1)   # a second decision
    assert not judges(record, witness, [1, 2, -3, -4])                              # a model that does not extend the retry
    assert not judges(record, witness, [4, -2, -3, 4])                              # four literals, one variable twice


def test_which_branch_is_the_ontologys_choice_put_in_force_by_the_governing_event(agenda):
    """D2: the criterion of branch admits any next branch that is a consistent assignment, the probe,
    another first branch, the retry or another one, at any position. R1: which branch is tried is
    chosen by the active ontology, and the retry rule is in force only from the governing event.
    Version 1 proposes nothing after the probe, on every prefix up to the retry; version 2,
    carried by adapt, proposes the retry, only once the resolvent is admitted and where it is unit.
    Another correct second branch passes the replay of judgments and fails the full replay (R2)."""
    _, record = agenda
    trial, retry = positions(record, "branch")
    switch, = positions(record, "adapt")
    learn, = positions(record, "learn")
    retried = record[retry]["payload"]
    for first in ([-1, -2, -3], [1], [], [4, -3, 2, -1]):
        assert judges(record, trial, {"id": 0, "assumptions": first})             # another strategy, still correct
    assert judges(record, retry, retried, prefix_length=switch)                     # correct before the event too
    assert judges(record, retry, dict(retried, assumptions=[-2, -4]))               # another second branch
    probe = lookups.load(record, record[trial]["coord"]["ontology"])
    upgraded = lookups.load(record, record[retry]["coord"]["ontology"])
    assert (probe["version"], upgraded["version"]) == (1, 2)
    assert evaluation.realize(record[:trial], probe) == record[trial]["payload"]
    assert all(evaluation.realize(record[:n], probe) is None for n in range(trial + 1, retry + 1))
    assert evaluation.realize(record[:retry], upgraded) == retried
    assert evaluation.realize(record[:learn], upgraded) is None                     # no resolvent yet
    satisfied = [dict(e, payload=dict(e["payload"], assumptions=[-2, 4, -3])) if n == trial else e
                 for n, e in enumerate(record[:retry])]
    assert evaluation.realize(satisfied, upgraded) is None                          # the resolvent is satisfied at [-2, 4]
    assert all(lookups.active(record[:n], "branch", "ontology") == record[trial]["coord"]["ontology"]
               for n in range(trial + 1, switch + 1))
    assert all(lookups.active(record[:n], "branch", "ontology") == record[retry]["coord"]["ontology"]
               for n in range(switch + 1, retry + 1))
    other = record[:retry] + [dict(record[retry], payload=dict(retried, assumptions=[-2, -4]))]
    assert verify(other, judgments_only=True) == []                                 # a correct step
    (at, why), = verify(other)                                                      # not the one the ontology proposed
    assert at == retry and why.startswith("S1.2/S1.4 realization gives")


LIB_SPEC = spec_from_file_location("sat4_lib", EXAMPLE / "lib.py")
lib = module_from_spec(LIB_SPEC)
LIB_SPEC.loader.exec_module(lib)


def test_the_helpers_refuse_what_this_instance_cannot_show():
    """Every completion of the retry here satisfies the formula, no clause is ever satisfied before it
    is used as a reason, and the parents clash on the pivot: small inputs show the remaining refusals."""
    assert lib.unit_literal([1, 2], [1, -2]) is None                                # satisfied, one literal left
    assert lib.unit_literal([1, 2], [-2]) == 1
    unit, conflict = [{"branch": 0, "reason": 0, "literal": 1}], [{"branch": 0, "clause": 1}]
    assert lib.resolution_certificate([[1, 2], [-1, -2]], unit, conflict) is None   # the resolvent would be a tautology
    assert lib.resolution_certificate([[1, 2], [1, 3]], unit, conflict) is None     # no clash on the pivot
    assert lib.resolution_certificate([[1, 2], [-1, 3]], unit, conflict) == {"left": 0, "right": 1, "pivot": 1, "literals": [2, 3]}
    branches = [{"id": 0, "assumptions": [-3]}, {"id": 1, "assumptions": []}]
    propagations = [{"branch": 0, "reason": 0, "literal": 4}, {"branch": 1, "reason": 0, "literal": 1}]
    formula = [[1, 2], [3, 4]]
    assert lib.check_witness(formula, [1, 2, 3, 4], branches, propagations, [1, -2, 3, -4])
    assert not lib.check_witness(formula, [1, 2, 3, 4], branches, propagations, [1, 2, -3, -4])   # falsifies [3, 4]
