"""Tests of examples/vns-adaptive: an agent that puts the forms of the searchers of vns in force
during the run, by carrying their specifications.

The first tests are those applied to every example: the system is well formed, meets its expected
end, replays in both modes, continues after an interruption, and gives the same lineages by workers
on every store, under random schedules and with workers killed. The rest check what DESIGN.md
claims: each form is in force from the start of a round; every decision is the rule applied to the
record; the authority admits the next form only past the tolerance and nothing else; τ_root
judges what is carried; until the first change, and with a tolerance never exceeded, the search is
that of vns.
"""
import copy
import random
import time
from pathlib import Path

import pytest

from test_vns import STORES, VNS, lineages, quiet, run_with_failures, values
from ztes import model as evaluation
from ztes.substrate import events, governance, lookups
from ztes.substrate.replay import verify
from ztes.substrate.store import MemoryStore, read
from ztes.system import workers
from ztes.system.report import check_expect
from ztes.system.system import System

ADAPTIVE = Path(__file__).parent.parent / "examples" / "vns-adaptive"
SEARCHERS = ("search_1", "search_2", "search_3")


def by_agenda(system):
    store = MemoryStore()
    system.run(store, log=quiet)
    return list(read(store))


def with_tolerance(tolerance):
    d = copy.deepcopy(System(ADAPTIVE).definition)
    d["constants"]["TOLERANCE"] = tolerance
    d.pop("expect")
    return System.from_dict(d)


@pytest.fixture(scope="module")
def central():
    system = System(ADAPTIVE)
    return system, by_agenda(system)


def decisions(C):
    """(position, payload, coordinate) of every decision of the agent."""
    return [(e["coord"]["n"], e["payload"], e["coord"]) for e in C
            if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == "adapt"]


# ---- the checks applied to every example ----

def test_is_well_formed():
    assert System(ADAPTIVE).check(log=quiet) == []


def test_meets_its_expected_end_and_replays_in_both_modes(central):
    system, C = central
    assert check_expect(system, C, log=quiet) == []
    assert verify(C) == [] and verify(C, judgments_only=True) == []


def test_the_same_record_over_http(central, tmp_path):
    """Every abstraction an HTTP service: the decision travels as JSON, and Z₀ binds what it carries."""
    from fastapi.testclient import TestClient
    from ztes.service import HttpService, make_app
    from ztes.substrate.store import DiskStore
    system, store = System(ADAPTIVE), DiskStore(tmp_path)
    system.run(store, {a: HttpService(client=TestClient(make_app(store, a))) for a in system.abstractions}, log=quiet)
    assert list(read(store)) == central[1]


def test_an_interrupted_run_continues_to_the_same_record(central):
    """Cut before, at and after each decision that carries specifications, and elsewhere."""
    full = central[1]
    carrying = [n for n, _, c in decisions(full) if "carries" in c]
    for cut in sorted({1, 13, *carrying, *(n + 1 for n in carrying), len(full) // 2, len(full) - 3, len(full)}):
        store = MemoryStore()
        for n in range(cut):
            store.put_if_absent(n, copy.deepcopy(full[n]))
        System(ADAPTIVE).run(store, log=quiet)
        assert list(read(store)) == full, f"interrupted after {cut} events"


@pytest.mark.parametrize("backend", STORES)
def test_by_workers_on_every_store(backend, central, tmp_path):
    system, store = System(ADAPTIVE), STORES[backend](tmp_path)
    workers.run(system, store, log=quiet)
    C = list(read(store))
    assert verify(C) == [] and lineages(C) == lineages(central[1])
    assert check_expect(system, C, log=quiet, any_schedule=True) == []


def test_the_same_histories_under_random_schedules_and_killed_workers(central):
    """The agent decides at every round and the searchers wait for its decision: the change is at the
    same position of every lineage under every schedule, and after any worker is killed (Theorem K)."""
    expected, killed = lineages(central[1]), 0
    for seed in range(3):
        rnd = random.Random(seed)
        system, store = System(ADAPTIVE), MemoryStore()
        workers.run(system, store, log=quiet, hesitate=lambda: time.sleep(rnd.random() * 0.002))
        C = list(read(store))
        assert verify(C) == [] and lineages(C) == expected
    for seed in range(2):
        system, store = System(ADAPTIVE), MemoryStore()
        killed += len(run_with_failures(system, store, seed))
        C = list(read(store))
        assert verify(C) == [] and lineages(C) == expected
    assert killed, "no worker was killed in any of the runs"


# ---- what the example claims (DESIGN.md) ----

def test_each_form_is_in_force_from_the_start_of_a_round(central):
    """Every step is proposed and judged by the versions active at its position, and the versions
    change only between rounds: v1 in rounds 0–2, v2 in 3–6, v3 under criterion v2 in 7–9."""
    C = central[1]
    rounds = {}
    for e in C:
        c = e["coord"]
        if c["kind"] == "exec" and c["abstraction"] in SEARCHERS:
            assert c["ontology"] == lookups.active(C[:c["n"]], c["abstraction"], "ontology")
            assert c["criterion"] == lookups.active(C[:c["n"]], c["abstraction"], "criterion")
            v = (lookups.load(C, c["ontology"])["version"], lookups.load(C, c["criterion"])["version"])
            rounds.setdefault(v, set()).add(e["payload"]["r"])
    assert rounds == {(1, 1): {0, 1, 2}, (2, 1): {3, 4, 5, 6}, (3, 2): {7, 8, 9}}
    assert [e["coord"]["kind"] for e in C].count("spec") == 2 * 6 + 4      # the plan records version 1 only


def _returns_by_round(C, start):
    """The certificates of each round that certify the tour their round shook, written here
    independently of lib.py: the same tour, read either way from the first city."""
    steps = values(C, "search_1") + values(C, "search_2") + values(C, "search_3")
    certified = {(x["i"], x["r"]): x["walk"] for x in steps if x["kind"] == "opt"}
    out = {}
    for x in steps:
        if x["kind"] == "opt":
            shaken = start if x["src"] == [0, -1] else certified[tuple(x["src"])]
            same = x["walk"] == shaken or x["walk"] == [shaken[0]] + shaken[1:][::-1]
            out[x["r"]] = out.get(x["r"], 0) + same
    return out


def test_every_decision_is_the_rule_applied_to_the_record(central):
    system, C = central
    c = system.definition["constants"]
    per_round = _returns_by_round(C, c["START"])
    form, since, expected = 0, 0, []
    for r in range(c["R"] - 1):
        n = sum(per_round[q] for q in range(since, r + 1))
        if n > c["TOLERANCE"] and form < 2:
            form, since = form + 1, r + 1
        expected.append({"r": r, "returns": n, "form": form, "since": since})
    made = decisions(C)
    assert [{f: p[f] for f in ("r", "returns", "form", "since")} for _, p, _ in made] == expected
    assert [p["returns"] for _, p, _ in made] == [0, 1, 3, 0, 0, 2, 4, 0, 0]
    carrying = [(n, p, coord) for n, p, coord in made if p["specifications"]]
    assert [p["r"] for _, p, _ in carrying] == [2, 6]
    files = system.specs                                                   # what is carried is what the files say
    first, second = carrying[0][1]["specifications"], carrying[1][1]["specifications"]
    assert [governance._bound(C[:carrying[0][0]], [files[f"{a}/ontology.v2"] for a in SEARCHERS])] == [first]
    assert [dict(s, criterion=None) if s["role"] == "ontology" else s for s in second] == \
        [dict(files[f"{a}/{k}"], criterion=None) if k.startswith("ontology") else files[f"{a}/{k}"]
         for a in SEARCHERS for k in ("criterion.v2", "ontology.v3")]
    for k in range(0, 6, 2):                                               # each ontology bound to the criterion before it
        assert second[k + 1]["criterion"] == events.addr(second[k])
    assert [(d["abstraction"], d["role"], d["version"]) for d in carrying[1][2]["carries"]["specs"]] == \
        [(a, role, v) for a in SEARCHERS for role, v in (("criterion", 2), ("ontology", 3))]


def test_the_authority_admits_the_next_form_only_past_the_tolerance(central):
    """D2 for the agent: its criterion admits keeping the form at any time, and the next form, carried
    exactly, only when the returns since the current form exceed the tolerance; nothing else."""
    C = central[1]
    made = {p["r"]: (n, p, coord) for n, p, coord in decisions(C)}

    def judge(at, **change):
        n, p, coord = made[at]
        P = C[:n]
        return evaluation.judge(P, lookups.load(P, coord["criterion"]), dict(p, **change))

    n, _, coord = made[2]
    stages = lookups.load(C[:n], coord["ontology"])["constants"]["STAGES"]
    assert judge(2) and judge(3) and judge(6)
    assert judge(2, form=0, since=0, specifications=[])                  # it may wait: the strategy is the ontology's
    assert not judge(3, form=2, since=4, specifications=stages[1])        # 0 returns: no change is allowed
    assert not judge(2, form=2, since=3, specifications=stages[1])        # not the next form
    assert not judge(2, specifications=stages[0][:2])                     # not exactly the form
    incumbent = dict(lookups.load(C, lookups.active(C, "incumbent", "ontology")), version=2)
    assert not judge(2, specifications=stages[0] + [incumbent])           # another abstraction
    adapt = dict(lookups.load(C, coord["ontology"]), version=2)
    assert not judge(2, specifications=stages[0] + [adapt])               # itself
    assert not judge(2, returns=5) and not judge(3, returns=1)            # evidence the record does not hold
    assert not judge(2, r=3) and not judge(2, since=4)


def test_tau_root_judges_what_the_agent_carries(central):
    """τ_root, not the agent's criterion, keeps the lineages without gaps: the strict form carried
    while ontology v1 is active would skip version 2."""
    C = central[1]
    n, p, coord = next(d for d in decisions(C) if d[1]["r"] == 2)
    P = C[:n]
    stages = lookups.load(P, coord["ontology"])["constants"]["STAGES"]
    o = lookups.load(P, coord["ontology"])
    assert governance.carry(P, o, p)[2] is None
    why = governance.carry(P, o, dict(p, specifications=stages[1]))[2]
    assert why == "carried specification 1: version 3: the next version of search_1/ontology is 2"


def test_until_the_first_change_the_searchers_take_the_steps_of_vns(central):
    vns = by_agenda(System(VNS))
    for a in SEARCHERS:
        assert [x for x in values(central[1], a) if x["r"] < 3] == [x for x in values(vns, a) if x["r"] < 3]


def test_an_agent_whose_tolerance_is_never_exceeded_leaves_the_search_of_vns():
    C = by_agenda(with_tolerance(100))
    assert verify(C) == [] and not any("carries" in c for _, _, c in decisions(C))
    assert [p["form"] for _, p, _ in decisions(C)] == [0] * 9
    vns = by_agenda(System(VNS))
    for a in SEARCHERS + ("incumbent",):
        assert values(C, a) == values(vns, a)
