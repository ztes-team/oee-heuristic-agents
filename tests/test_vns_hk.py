"""Tests of examples/vns-hk: three VNS searchers and 26 city abstractions on fri26. The cities
compute a Held–Karp lower bound by their potentials, a tree abstraction records the minimum
1-tree of each round, and a proof abstraction records when the bound proves the incumbent optimal.

The first tests are those ZTES applies to each of its examples. The rest check what DESIGN.md
claims; the 1-tree, its weight and the direction of every potential are computed here again,
independently of lib.py (Kruskal instead of Prim).
"""
import copy
import importlib.util
import json
import random
import time
from pathlib import Path

import fakeredis
import pytest

from ztes import model as evaluation
from ztes.substrate import lookups
from ztes.substrate.replay import verify
from ztes.substrate.store import DiskStore, MemoryStore, RedisStore, read
from ztes.system import workers
from ztes.system.report import check_expect
from ztes.system.system import System

from test_vns import run_with_failures

HK = Path(__file__).parent.parent / "examples" / "vns-hk"
STORES = {"memory": lambda tmp: MemoryStore(), "disk": lambda tmp: DiskStore(tmp),
          "redis": lambda tmp: RedisStore(client=fakeredis.FakeRedis(), batch=5)}
AIM_AT_START = [{"phase": 1}, {"phase": 2}, {"govern": [f"city_{i}/ontology.v2" for i in range(26)]},
                {"phase": 3}, {"kpi": True}]
quiet = lambda *_: None


def by_agenda(plan=None):
    system, store = System(HK), MemoryStore()
    system.run(store, log=quiet, plan=plan)
    return system, list(read(store))


@pytest.fixture(scope="module")
def central():
    return by_agenda()


def values(C, a):
    return [e["payload"] for e in C if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == a]


def lineages(C):
    out = {}
    for e in C:
        if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] not in ("profile", "kpi"):
            out.setdefault(e["coord"]["abstraction"], []).append(e["payload"])
    return out


def kpi(C):
    return values(C, "kpi")[-1]


def holds_under_any_schedule(system, C, central):
    assert verify(list(C)) == []
    assert check_expect(system, C, log=quiet, any_schedule=True) == []
    assert system.states(C) == central[0].states(central[1])
    for row in values(C, "profile")[-1]:
        assert row["I"] == row["A"] + row["U"] + row["F"] and 0 <= row["H"] <= row["U"]


# ---- the instance and the 1-tree, written here independently of lib.py ----

C0 = System(HK).definition["constants"]
N, SC, R = C0["N"], C0["SC"], C0["R"]
D = [[C0["LOWER"][a][b] if b <= a else C0["LOWER"][b][a] for b in range(N)] for a in range(N)]


def _potentials(C, t):
    """The potentials of round t, from the events of the cities (0 in round 0)."""
    if t == 0:
        return [0] * N
    pi = {x["i"]: x["pi"] for c in range(N) for x in values(C, f"city_{c}") if x["t"] == t}
    return [pi[c] for c in range(N)]


def _minimum_one_tree(pi):
    """The weight of a minimum 1-tree by Kruskal on the cities 1..N−1 and the two cheapest edges at 0."""
    w = lambda a, b: SC * D[a][b] + pi[a] + pi[b]
    part = list(range(N))

    def root(c):
        while part[c] != c:
            c = part[c]
        return c
    total = 0
    for weight, a, b in sorted((w(a, b), a, b) for a in range(1, N) for b in range(a + 1, N)):
        if root(a) != root(b):
            part[root(a)] = root(b)
            total += weight
    return total + sum(sorted(w(0, c) for c in range(1, N))[:2])


def _is_one_tree(edges):
    rest = [e for e in edges if 0 not in e]
    part = list(range(N))

    def root(c):
        while part[c] != c:
            c = part[c]
        return c
    for a, b in rest:
        if root(a) == root(b):
            return False
        part[root(a)] = root(b)
    return len(edges) == N and len(rest) == N - 2 and sum(0 in e for e in edges) == 2


def _degree(edges, c):
    return sum(c in e for e in edges)


# ---- the checks ZTES applies to each of its examples ----

def test_is_well_formed():
    assert System(HK).check(log=quiet) == []


def test_the_generator_reproduces_the_cities():
    spec = importlib.util.spec_from_file_location("generate", HK / "generate.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    for path, text in gen.cities().items():
        assert (HK / path).read_text(encoding="utf8") == text, path
    assert (HK / "system.json").read_text(encoding="utf8") == gen.system()


def test_meets_its_expected_end_and_replays(central):
    assert check_expect(*central, log=quiet) == []
    assert verify(central[1]) == []


def test_an_interrupted_run_continues_to_the_same_record(central):
    full = central[1]
    for cut in (1, 5, len(full) // 3, len(full) - 3, len(full)):
        store = MemoryStore()
        for n in range(cut):
            store.put_if_absent(n, copy.deepcopy(full[n]))
        System(HK).run(store, log=quiet)
        assert list(read(store)) == full, f"interrupted after {cut} events"


@pytest.mark.parametrize("backend", STORES)
def test_by_workers_on_every_store(backend, central, tmp_path):
    system, store = System(HK), STORES[backend](tmp_path)
    workers.run(system, store, log=quiet)
    holds_under_any_schedule(system, read(store), central)


def test_the_same_histories_under_random_schedules_and_killed_workers(central):
    """33 workers, one per abstraction: every lineage has the history it has under the agenda, also
    when workers are killed at random and started again."""
    expected, orders, killed = lineages(central[1]), set(), 0
    for seed in range(3):
        rnd = random.Random(seed)
        system, store = System(HK), MemoryStore()
        workers.run(system, store, log=quiet, hesitate=lambda: time.sleep(rnd.random() * 0.002))
        C = read(store)
        holds_under_any_schedule(system, C, central)
        assert lineages(C) == expected
        orders.add(tuple(e["coord"].get("abstraction") for e in C))
    for seed in range(2):
        system, store = System(HK), MemoryStore()
        killed += len(run_with_failures(system, store, seed))
        C = read(store)
        holds_under_any_schedule(system, C, central)
        assert lineages(C) == expected
    assert len(orders) > 1 and killed > 0


# ---- what the example claims (DESIGN.md) ----

def test_every_tree_is_a_minimum_one_tree_and_states_its_bound_truly(central):
    C = central[1]
    trees = values(C, "tree")
    assert [x["t"] for x in trees] == list(range(len(trees)))
    for x in trees:
        pi = _potentials(C, x["t"])
        weight = sum(SC * D[a][b] + pi[a] + pi[b] for a, b in x["edges"])
        assert _is_one_tree(x["edges"]) and weight == _minimum_one_tree(pi)
        assert x["bound"] == weight - 2 * sum(pi)


def test_every_bound_is_below_every_recorded_tour_and_the_proof_is_true(central):
    """Weak duality, checked on the record: under the potentials of every round, every tour the
    searchers recorded weighs at least the minimum 1-tree, so the bound is at most SC times its
    length. The best bound, 936.10, proves 937 optimal; the proof cites it."""
    C = central[1]
    tours = {tuple(x["walk"]) for i in (1, 2, 3) for x in values(C, f"search_{i}")}
    for x in values(C, "tree"):
        pi = _potentials(C, x["t"])
        for w in tours:
            weight = sum(SC * D[w[k - 1]][w[k]] + pi[w[k - 1]] + pi[w[k]] for k in range(N))
            assert x["bound"] <= weight - 2 * sum(pi) == SC * sum(D[w[k - 1]][w[k]] for k in range(N))
    bounds = [x["bound"] for x in values(C, "tree")]
    [proof] = values(C, "proof")
    assert proof == {"t": 18, "r": 9, "bound": 93610, "length": 937}
    assert max(bounds[:19]) == 93610 and -(-93610 // SC) == 937 == values(C, "incumbent")[-1]["length"]
    assert all(-(-max(bounds[:t + 1]) // SC) < 937 for t in range(18))         # no earlier round proves it


def test_every_potential_moves_in_the_direction_of_the_subgradient(central):
    C = central[1]
    trees = {x["t"]: x for x in values(C, "tree")}
    for c in range(N):
        before = 0
        for x in values(C, f"city_{c}"):
            d = _degree(trees[x["t"] - 1]["edges"], c) - 2
            move = x["pi"] - before
            assert (d > 0 and move > 0) or (d < 0 and move < 0) or (d == 0 and move == 0)
            before = x["pi"]


def test_the_criteria_know_nothing_of_the_strategy(central):
    """D2. A city's criterion admits any potential that moves in its direction, not only the step
    the ontology chose, and refuses one that moves against it; the tree's criterion refuses a
    1-tree that is not minimum and a bound that is not true; the proof's criterion refuses a
    length the bound does not reach."""
    C = central[1]
    judge_at = lambda n, w: evaluation.judge(C[:n], lookups.load(C[:n], C[n]["coord"]["criterion"]), w)
    n = next(k for k, e in enumerate(C) if e["coord"].get("abstraction") == "city_1" and e["coord"]["kind"] == "exec"
             and e["payload"]["pi"] != 0)
    good = C[n]["payload"]
    sign = 1 if good["pi"] > 0 else -1
    assert judge_at(n, good)
    assert judge_at(n, dict(good, pi=good["pi"] + sign * 1000))                # a longer step in the same direction
    assert not judge_at(n, dict(good, pi=-good["pi"]))                          # against the subgradient
    t = next(k for k, e in enumerate(C) if e["coord"].get("abstraction") == "tree" and e["coord"]["kind"] == "exec"
             and e["payload"]["t"] == 5)
    tree = C[t]["payload"]
    assert judge_at(t, tree)
    assert not judge_at(t, dict(tree, bound=tree["bound"] + 1))
    edges = [list(e) for e in tree["edges"]]
    a, b = next(e for e in edges if 0 not in e)
    other = next(c for c in range(1, N) if c not in (a, b) and [min(a, c), max(a, c)] not in edges)
    worse = sorted([e for e in edges if e != [a, b]] + [sorted([a, other])])
    assert not judge_at(t, dict(tree, edges=worse))                            # not a minimum 1-tree (or not a 1-tree)
    p = next(k for k, e in enumerate(C) if e["coord"].get("abstraction") == "proof" and e["coord"]["kind"] == "exec")
    proof = C[p]["payload"]
    assert judge_at(p, proof)
    assert not judge_at(p, dict(proof, length=938))
    assert not judge_at(p, dict(proof, t=17, bound=max(x["bound"] for x in values(C[:p], "tree")[:18])))


def test_aiming_at_the_starting_tour_takes_eighteen_times_as_many_rounds(central):
    """Ontology v2 of the cities aims each step at the starting tour (1,140) instead of the
    incumbent; the criteria are the same. The bound proves 937 only in round 330, not 18."""
    _, C = by_agenda(AIM_AT_START)
    assert verify(C) == []
    def bodies(C, role):
        used = {(e["coord"]["abstraction"], e["coord"][role]) for e in C
                if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"].startswith("city_")}
        return {a: str(lookups.load(C, address)["body"]) for a, address in sorted(used)}
    assert bodies(C, "criterion") == bodies(central[1], "criterion")
    assert all("TLEN" in b for b in bodies(C, "ontology").values())
    one, two = kpi(central[1]), kpi(C)
    assert (one["proved_at"], two["proved_at"]) == (18, 330)
    assert (len(central[1]), len(C)) == (934, 9384)
    assert lineages(C)["incumbent"] == lineages(central[1])["incumbent"]       # the searchers are not affected
