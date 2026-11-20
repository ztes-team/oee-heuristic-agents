"""Tests of examples/cptl: parity and a strict budget along a path with recorded precedence.

The local projection and the exact path solution are checked against exhaustive enumeration, the
record against its expected end in both replay modes, and the governing event against the ontology
active on each side of it. The checks applied to every example follow: an interrupted run continues
to the same record, and workers give the lineages of the agenda under random schedules and with
workers killed. The last tests check the two criteria as authorities (D2): the criterion of route
admits only valid stage witnesses that continue the route and attain the recorded optimum, and the
criterion of adapt admits only the designated version, and only when the trial is obstructed.
"""
import copy
import random
import time
from itertools import product

import pytest

from scripts.benchmark_cptl import EXAMPLE, case_system, domain, event_payloads, execute, guard_sequence, native_dp
from test_vns import lineages, run_with_failures
from ztes import model as evaluation
from ztes.substrate import lookups
from ztes.substrate.replay import verify
from ztes.substrate.store import MemoryStore, read
from ztes.system import workers
from ztes.system.authoring import read_directory
from ztes.system.report import check_expect
from ztes.system.system import System


def direct_module(bits, guard_first):
    x1, x2, x3, x4 = bits
    return ((x1 ^ x2 ^ x3 ^ x4) == 1 and 4 * x1 + 3 * x2 + 4 * x3 + 3 * x4 < 8
            and (guard_first or x1 == 0 or (x2 ^ x4) == 1))


def test_the_two_state_recurrence_uses_the_exact_projection():
    for guard_first, incoming, outgoing in product((0, 1), repeat=3):
        allowed = any(direct_module((incoming, x2, x3, outgoing), guard_first)
                      for x2, x3 in product((0, 1), repeat=2))
        assert allowed == domain.transition_allowed(guard_first, incoming, outgoing)


def test_the_same_assignment_has_a_different_judgment_under_a_different_precedence():
    bits = [1, 0, 0, 0]
    assert domain.module_valid(bits, True, [3, 1, 2, 4])
    assert not domain.module_valid(bits, False, [1, 3, 2, 4])
    assert not domain.module_valid(bits, True, [1, 3, 2, 4])


def test_default_example_replays_with_the_recorded_governance_boundary():
    system = System(EXAMPLE)
    assert system.check(log=lambda *_: None) == []
    assert system.definition["constants"]["GUARDS"] == guard_sequence(6)
    record = execute(system)
    assert check_expect(system, record, log=lambda *_: None) == []
    assert verify(record) == [] and verify(record, judgments_only=True) == []
    trial = next(i for i, e in enumerate(record) if e["coord"].get("abstraction") == "route"
                 and e["coord"]["kind"] == "exec")
    change = next(i for i, e in enumerate(record) if "carries" in e["coord"])
    version = record[change]["coord"]["carries"]["specs"][0]
    assert trial < change and record[trial]["payload"]["trial"]
    assert version["abstraction"] == "route" and version["version"] == 2
    assert lookups.active(record[:change], "route", "ontology") != version["addr"]
    assert lookups.active(record[:change + 1], "route", "ontology") == version["addr"]
    assert all(e["coord"]["ontology"] == version["addr"] for e in record[change + 1:]
               if e["coord"].get("abstraction") == "route" and e["coord"]["kind"] == "exec")

    accepted = next(i for i, e in enumerate(record) if e["coord"].get("abstraction") == "route"
                    and e["coord"]["kind"] == "exec" and not e["payload"]["trial"] and e["payload"]["incoming"])
    prefix, event = record[:accepted], record[accepted]
    criterion = lookups.load(prefix, event["coord"]["criterion"])
    assert evaluation.judge(prefix, criterion, event["payload"])
    assert not evaluation.judge(prefix, criterion, dict(event["payload"], order=[1, 3, 2, 4]))


@pytest.mark.parametrize("guards", [
    [True, False],
    [False, False, True, False, True],
    [True, False, True, True, False, True, True, True],
])
def test_path_dp_and_ztes_match_exhaustive_link_search(guards):
    scores = []
    for word in product((0, 1), repeat=len(guards)):
        if word[-1] != 1:
            continue
        if all(any(direct_module((incoming, x2, x3, outgoing), guard_first)
                   for x2, x3 in product((0, 1), repeat=2))
               for guard_first, incoming, outgoing in zip(guards, (0, *word), word)):
            scores.append(sum(word))
    native_rows, native_route = native_dp(guards)
    root = native_rows[0]
    assert (root["count"][0], root["best"][0]) == (len(scores), max(scores))
    record = execute(case_system(guards))
    assert event_payloads(record, "suffix")[-1] == root
    assert [step for step in event_payloads(record, "route") if not step["trial"]] == native_route
    assert verify(record) == []


# ---- the checks applied to every example ----

def test_an_interrupted_run_continues_to_the_same_record():
    full = execute(System(EXAMPLE))
    change = next(i for i, e in enumerate(full) if "carries" in e["coord"])
    for cut in sorted({1, 7, change, change + 1, len(full) - 3, len(full)}):
        store = MemoryStore()
        for n in range(cut):
            store.put_if_absent(n, copy.deepcopy(full[n]))
        System(EXAMPLE).run(store, log=lambda *_: None)
        assert list(read(store)) == full, f"interrupted after {cut} events"


@pytest.mark.parametrize("size", [6, 20])
def test_the_same_lineages_by_workers_under_random_schedules_and_killed_workers(size):
    expected, killed = lineages(execute(case_system(guard_sequence(size)))), 0
    for seed in range(3):
        rnd = random.Random(seed)
        store = MemoryStore()
        workers.run(case_system(guard_sequence(size)), store, log=lambda *_: None,
                    hesitate=lambda: time.sleep(rnd.random() * 0.002))
        C = list(read(store))
        assert verify(C) == [] and lineages(C) == expected
    for seed in range(2):
        store = MemoryStore()
        killed += len(run_with_failures(case_system(guard_sequence(size)), store, seed))
        C = list(read(store))
        assert verify(C) == [] and lineages(C) == expected
    assert killed, "no worker was killed in any of the runs"


# ---- the criteria as authorities (D2) ----

def _route_events(record):
    return [(i, e) for i, e in enumerate(record)
            if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == "route" and not e["payload"]["trial"]]


def _judge(record, at, candidate):
    prefix = record[:at]
    return evaluation.judge(prefix, lookups.load(prefix, record[at]["coord"]["criterion"]), candidate)


@pytest.mark.parametrize("guards", [guard_sequence(6), [True, False, True, True], [True, False, True, True, False, True, True, True]])
def test_the_route_criterion_admits_a_committed_link_only_at_the_recorded_optimum(guards):
    """The other link of every committed step is judged on the same prefix: it is admitted exactly
    when it is a feasible transition with a feasible remainder that attains the optimum of the row."""
    record = execute(case_system(guards))
    rows = {r["stage"]: r for r in event_payloads(record, "suffix")}
    refused_feasible = 0
    for at, e in _route_events(record):
        w = e["payload"]
        assert _judge(record, at, w)
        other = domain.step(w["stage"], w["incoming"], 1 - w["link"], guards[w["stage"]], False)
        tail = rows.get(w["stage"] + 1) or domain.terminal_row(len(guards))
        feasible = domain.transition_allowed(guards[w["stage"]], w["incoming"], other["link"]) and tail["count"][other["link"]] > 0
        optimal = feasible and rows[w["stage"]]["best"][w["incoming"]] == other["link"] + tail["best"][other["link"]]
        assert _judge(record, at, other) == optimal
        refused_feasible += feasible and not optimal
    if guards == [True, False, True, True]:                              # at stage 1 the link 0 is feasible but not optimal
        assert refused_feasible > 0, "no feasible but suboptimal link was tried"


def test_the_route_criterion_refuses_an_invalid_witness_or_a_broken_route():
    record = execute(System(EXAMPLE))
    steps = _route_events(record)
    at, w = next((i, e["payload"]) for i, e in steps if e["payload"]["incoming"] == 1)       # stage 2: [1, 0, 0, 0]
    assert _judge(record, at, w)
    assert not _judge(record, at, dict(w, bits=[1, 1, 1, 0]))      # odd parity, but weight 11: over the budget
    assert not _judge(record, at, dict(w, bits=[1, 1, 0, 0]))      # within the budget, but even parity
    at, w = next((i, e["payload"]) for i, e in steps if e["payload"]["stage"] == 3)          # incoming 0, link 0
    assert _judge(record, at, w)
    assert not _judge(record, at, dict(w, stage=4, order=domain.decision_order(False)))     # skips a stage
    assert not _judge(record, at, domain.step(3, 1, 0, True, False))                         # does not continue the link
    assert not _judge(record, at, dict(w, trial=True))                                       # a second trial


def test_the_governing_criterion_admits_only_the_designated_version_on_an_obstructed_trial():
    record = execute(System(EXAMPLE))
    at = next(i for i, e in enumerate(record) if "carries" in e["coord"])
    w = record[at]["payload"]
    assert _judge(record, at, w)
    v2 = w["specifications"][0]
    other = dict(v2, body={"result": "None"})
    assert not _judge(record, at, dict(w, specifications=[other]))       # another body
    assert not _judge(record, at, dict(w, specifications=[v2, v2]))      # more than the designated version
    assert not _judge(record, at, dict(w, specifications=[]))            # nothing carried
    assert not _judge(record, at, dict(w, blocked_stage=2))              # the obstruction stated falsely
    later = record[:at + 1]                                              # a second decision
    assert not evaluation.judge(later, lookups.load(later, lookups.active(later, "adapt", "criterion")), w)
    definition = read_directory(EXAMPLE)                                 # a guard-first second stage: no obstruction
    definition["constants"]["GUARDS"] = [True, True, False, True]
    definition.pop("expect")
    open_trial = execute(System.from_dict(definition))
    assert not any("carries" in e["coord"] for e in open_trial)
    adapt = lookups.load(open_trial, lookups.active(open_trial, "adapt", "criterion"))
    forged = dict(w, specifications=adapt["constants"]["UPGRADE"])        # its own designated version: only
    assert not evaluation.judge(open_trial, adapt, forged)               # the obstruction is missing
