"""Tests of examples/vns-atsp: variable neighborhood search by three cooperating searchers on ftv38.

The lifting is that of examples/vns. What changes is the instance, which is asymmetric, and the
neighborhood, which exchanges two adjacent segments so that every arc it does not cut keeps its
direction. A run takes several seconds, so each form is run once under the agenda and once by
workers; the asymmetric neighborhood itself is checked step by step in tests/test_vns.py.
"""
import random
import time
from pathlib import Path

import pytest

from ztes.substrate import lookups
from ztes.substrate.replay import verify
from ztes.substrate.store import MemoryStore, read
from ztes.system import workers
from ztes.system.report import check_expect
from ztes.system.system import System

ATSP = Path(__file__).parent.parent / "examples" / "vns-atsp"
ASYM = [{"phase": 1}, {"phase": 2},
        {"govern": [f"search_{i}/ontology.v{v}" for v in (2, 3) for i in (1, 2, 3)]},
        {"phase": 3}, {"kpi": True}]
quiet = lambda *_: None


def by_agenda(plan=None):
    system, store = System(ATSP), MemoryStore()
    system.run(store, log=quiet, plan=plan)
    return system, list(read(store))


@pytest.fixture(scope="module")
def central():
    """The plan of the example (synchronous cooperation, ontology v1) under the agenda."""
    return by_agenda()


@pytest.fixture(scope="module")
def asym():
    """The asymmetric neighborhood (ontology v3) under the agenda."""
    return by_agenda(ASYM)


def values(C, a):
    return [e["payload"] for e in C if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == a]


def lineages(C):
    """The history of every lineage but profile and kpi, which count the invocations of a schedule."""
    out = {}
    for e in C:
        if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] not in ("profile", "kpi"):
            out.setdefault(e["coord"]["abstraction"], []).append(e["payload"])
    return out


def _chain(C):
    return [(b["r"], b["src"], b["length"]) for b in values(C, "incumbent") if b["improved"]]


def _bodies(C, role):
    return {e["coord"]["abstraction"]: str(lookups.load(C, e["coord"][role])["body"])
            for e in C if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"].startswith("search_")}


def _instance():
    c = System(ATSP).definition["constants"]
    return c["D"], c


def _exchange(walk, i, j, k):
    """A B C D → A C B D, written here independently of lib.py."""
    return walk[:i + 1] + walk[j + 1:k + 1] + walk[i + 1:j + 1] + walk[k + 1:]


def _arcs(walk):
    return {(walk[i - 1], walk[i]) for i in range(len(walk))}


def test_is_well_formed():
    assert System(ATSP).check(log=quiet) == []


def test_meets_its_expected_end_and_replays(central):
    system, C = central
    assert check_expect(system, C, log=quiet) == []
    assert verify(C) == [] and len(C) == 1195


def test_every_step_keeps_the_direction_of_the_arcs_it_does_not_cut(central):
    """The instance is asymmetric: a cycle read backwards is another tour, of another length. Every
    move exchanges two adjacent segments, shortens the tour, cuts three arcs and keeps the direction
    of all the others; a certificate is of a tour no exchange shortens (checked by brute force)."""
    C = central[1]
    D, c = _instance()
    n = c["N"]
    length = lambda w: sum(D[w[i - 1]][w[i]] for i in range(len(w)))
    assert sum(D[a][b] != D[b][a] for a in range(n) for b in range(a)) == 694
    best = values(C, "incumbent")[-1]["walk"]
    assert length(best) == 1547 and length([best[0]] + best[:0:-1]) != 1547
    moves = [(i, j, k) for i in range(n) for j in range(i + 1, n) for k in range(j + 1, n)]
    last = []
    for a in ("search_1", "search_2", "search_3"):
        steps = values(C, a)
        for prev, x in zip(steps, steps[1:]):
            if x["kind"] == "move":
                assert x["walk"] == _exchange(prev["walk"], *moves[x["m"]])
                assert length(x["walk"]) == x["length"] < prev["length"]
                assert len(_arcs(prev["walk"]) - _arcs(x["walk"])) == 3
            if x["kind"] == "opt" and x["r"] == c["R"] - 1:
                last.append(x["walk"])
    for walk in last:                                                  # the certificates of the last round
        assert min(length(_exchange(walk, *m)) for m in moves) >= length(walk)


def test_the_asymmetric_neighborhood_reaches_a_shorter_tour_with_fewer_returns(central, asym):
    """Ontology v3, as in examples/vns: the criteria are those of v1; the descent does not go back."""
    assert verify(asym[1]) == []
    assert _bodies(central[1], "criterion") == _bodies(asym[1], "criterion")
    one, three = values(central[1], "kpi")[-1], values(asym[1], "kpi")[-1]
    assert (one["best"], one["returns"], one["gap_permille"]) == (1547, 20, 11)
    assert (three["best"], three["returns"], three["gap_permille"]) == (1532, 15, 1)
    assert _chain(central[1]) == [(0, [2, 0], 1562), (2, [1, 2], 1547)]
    assert _chain(asym[1]) == [(0, [2, 0], 1562), (2, [1, 2], 1547), (6, [2, 6], 1544), (8, [2, 8], 1532)]


@pytest.mark.parametrize("plan", [None, ASYM], ids=["v1", "v3"])
def test_both_synchronous_forms_give_the_same_histories_by_workers(plan, central, asym):
    """Each searcher waits for the incumbent of its round, and v3 reads only finished rounds: under a
    random schedule of the workers every lineage has the history it has under the agenda."""
    expected = lineages((central if plan is None else asym)[1])
    rnd = random.Random(1)
    system, store = System(ATSP), MemoryStore()
    workers.run(system, store, log=quiet, plan=plan, hesitate=lambda: time.sleep(rnd.random() * 0.002))
    C = read(store)
    assert verify(list(C)) == [] and lineages(C) == expected
