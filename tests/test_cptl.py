from itertools import product

import pytest

from scripts.benchmark_cptl import EXAMPLE, case_system, domain, event_payloads, execute, guard_sequence, native_dp
from ztes import model as evaluation
from ztes.substrate import lookups
from ztes.substrate.replay import verify
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
