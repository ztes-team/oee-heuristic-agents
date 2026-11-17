"""Tests of examples/vns: variable neighborhood search by three cooperating searchers on fri26.

The example is executed by ZTES (https://github.com/ztes-team/ztes-minimal), installed as a package.
The first tests are those ZTES applies to each of its own examples: the system is well formed,
meets its expected end, replays (R2) in process and over HTTP, continues after an interruption,
and phase 3 run by workers holds on every store, under random schedules and with workers killed.
The rest check what DESIGN.md claims: every step is a step of VNS and every local optimum is
certified, the criterion does not know the strategy (D2), and the two forms of cooperation.
"""
import copy
import random
import threading
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

VNS = Path(__file__).parent.parent / "examples" / "vns"


def form(*keys):
    """The plan of the example with a governed change of the three searchers before phase 3."""
    govern = [f"search_{i}/{key}" for key in keys for i in (1, 2, 3)]
    return [{"phase": 1}, {"phase": 2}, {"govern": govern}, {"phase": 3}, {"kpi": True}]


ASYNC = form("ontology.v2")                                           # asynchronous cooperation
ASYM = form("ontology.v2", "ontology.v3")                             # the asymmetric neighborhood
STRICT = form("ontology.v2", "ontology.v3", "criterion.v2", "ontology.v4")   # with the relative certificate
STORES = {"memory": lambda tmp: MemoryStore(), "disk": lambda tmp: DiskStore(tmp),
          "redis": lambda tmp: RedisStore(client=fakeredis.FakeRedis(), batch=5)}
quiet = lambda *_: None


def by_agenda(plan=None):
    system, store = System(VNS), MemoryStore()
    system.run(store, log=quiet, plan=plan)
    return system, list(read(store))


@pytest.fixture(scope="module")
def central():
    """The system and its record under the agenda: one Z₀, the order of the plan."""
    return by_agenda()


@pytest.fixture(scope="module")
def asym():
    return by_agenda(ASYM)


@pytest.fixture(scope="module")
def strict():
    return by_agenda(STRICT)


def values(C, a):
    return [e["payload"] for e in C if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == a]


def lineages(C):
    """The history of every lineage but profile and kpi, which count the invocations of a schedule."""
    out = {}
    for e in C:
        if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] not in ("profile", "kpi"):
            out.setdefault(e["coord"]["abstraction"], []).append(e["payload"])
    return out


def holds_under_any_schedule(system, C, central):
    assert verify(list(C)) == []                                    # R2
    assert check_expect(system, C, log=quiet, any_schedule=True) == []
    assert system.states(C) == central[0].states(central[1])        # every abstraction ends the same way
    for row in values(C, "profile")[-1]:                            # the recorded counts are consistent
        assert row["I"] == row["A"] + row["U"] + row["F"] and 0 <= row["H"] <= row["U"]


# ---- the checks ZTES applies to each of its examples ----

def test_is_well_formed():
    assert System(VNS).check(log=quiet) == []


def test_meets_its_expected_end(central):
    assert check_expect(*central, log=quiet) == []


def test_replays_in_process_and_over_http(central, tmp_path):
    """R2 in process, and the same record when every abstraction is an HTTP service (the candidate travels as JSON)."""
    from fastapi.testclient import TestClient
    from ztes.service import HttpService, make_app
    C = central[1]
    assert verify(C) == [] and len(C) == 390
    system, store = System(VNS), DiskStore(tmp_path)
    system.run(store, {a: HttpService(client=TestClient(make_app(store, a))) for a in system.abstractions}, log=quiet)
    assert [e["payload"] for e in read(store)] == [e["payload"] for e in C]


def test_an_interrupted_run_continues_to_the_same_record(central):
    """The process may die after any event: started again, the plan gives the record it would have given."""
    full = central[1]
    for cut in (1, 2, 5, len(full) // 2, len(full) - 3, len(full)):
        store = MemoryStore()
        for n in range(cut):
            store.put_if_absent(n, copy.deepcopy(full[n]))
        System(VNS).run(store, log=quiet)
        assert list(read(store)) == full, f"interrupted after {cut} events"


@pytest.mark.parametrize("backend", STORES)
def test_by_workers_on_every_store(backend, central, tmp_path):
    system, store = System(VNS), STORES[backend](tmp_path)
    workers.run(system, store, log=quiet)
    holds_under_any_schedule(system, read(store), central)


class Killed(BaseException):
    """The worker stops at once, as a killed process does: no report, no cleanup."""


class DiesAfterAppending:
    """A handle on the record whose owner may die right after one of its events has been appended."""

    def __init__(self, store, rnd, chance):
        self.store, self.rnd, self.chance = store, rnd, chance
        if hasattr(store, "get_many"):
            self.get_many, self.batch = store.get_many, store.batch
        self.get, self.get_note, self.put_note = store.get, store.get_note, store.put_note

    def put_if_absent(self, n, event):
        done = self.store.put_if_absent(n, event)
        if done and n > 0 and self.rnd.random() < self.chance:
            raise Killed()                                         # the event is in C; the worker never learns it
        return done


def run_with_failures(system, store, seed, chance=0.15):
    """Every worker may be killed before an invocation or right after an append; it is started again."""
    rnd, deaths = random.Random(seed), []

    def before_invocation():
        time.sleep(rnd.random() * 0.002)
        if rnd.random() < chance:
            raise Killed()

    def supervise(a):
        while True:
            worker = workers.Worker(system, a, DiesAfterAppending(store.again(), rnd, chance), hesitate=before_invocation)
            try:
                return worker.run()
            except Killed:
                deaths.append(a)
                time.sleep(rnd.random() * 0.005)                   # it stays down for a while

    threads = [threading.Thread(target=supervise, args=(a,), daemon=True) for a in system.abstractions]
    for t in threads:
        t.start()
    workers.run(system, store, local=False, log=quiet)
    for t in threads:
        t.join(timeout=5)
    return deaths


# ---- what the example claims (DESIGN.md) ----

def _fri26():
    """The distance matrix of fri26 from the lower triangle in system.json, and the constants."""
    c = System(VNS).definition["constants"]
    low, n = c["LOWER"], c["N"]
    return [[low[a][b] if b <= a else low[b][a] for b in range(n)] for a in range(n)], c


def _neighbors(walk):
    """Every tour one 2-opt move away, in the order of the moves (written here independently of lib.py)."""
    n = len(walk)
    return [walk[:a + 1] + walk[a + 1:b + 1][::-1] + walk[b + 1:]
            for a in range(n) for b in range(a + 2, n) if not (a == 0 and b == n - 1)]


def test_every_step_is_a_step_of_vns_and_every_local_optimum_is_certified(central):
    C = central[1]
    D, c = _fri26()
    length = lambda w: sum(D[w[i - 1]][w[i]] for i in range(len(w)))
    optima = []
    for i in (1, 2, 3):
        steps = values(C, f"search_{i}")
        kinds = [x["kind"] for x in steps]
        assert kinds.count("shake") == kinds.count("opt") == c["R"]          # a round: shake, moves, certificate
        for prev, x in zip(steps, steps[1:]):
            assert sorted(x["walk"]) == list(range(c["N"])) and x["length"] == length(x["walk"])
            if x["kind"] == "move":
                assert x["walk"] in _neighbors(prev["walk"]) and x["length"] < prev["length"]
            if x["kind"] == "opt":                                           # no 2-opt neighbor is shorter
                assert x["walk"] == prev["walk"] and min(map(length, _neighbors(x["walk"]))) >= x["length"]
        optima += [x for x in steps if x["kind"] == "opt"]
    incumbent = values(C, "incumbent")
    assert [b["r"] for b in incumbent] == list(range(c["R"]))
    for b in incumbent:                                  # the shortest local optimum certified up to round r
        assert b["length"] == min(o["length"] for o in optima if o["r"] <= b["r"])
    assert incumbent[-1]["length"] == c["OPT"] == 937                         # the optimum of fri26 (TSPLIB)


def test_criterion_admits_any_step_of_vns_and_refuses_the_rest(central):
    """D2: the criterion of a searcher knows nothing of the strategy that chose the step."""
    C = central[1]
    D, _ = _fri26()
    length = lambda w: sum(D[w[i - 1]][w[i]] for i in range(len(w)))
    n = next(k for k, e in enumerate(C) if e["coord"].get("abstraction") == "search_1"
             and e["coord"]["kind"] == "exec" and e["payload"]["kind"] == "move")
    P, good = C[:n], C[n]["payload"]
    prev = values(P, "search_1")[-1]
    tau = lookups.load(P, C[n]["coord"]["criterion"])
    judge = lambda **change: evaluation.judge(P, tau, dict(good, **change))
    assert judge()                                                           # the first improving move
    moves = _neighbors(prev["walk"])
    other = next(m for m, w in enumerate(moves) if length(w) < prev["length"] and m != good["m"])
    assert judge(m=other, walk=moves[other], length=length(moves[other]))   # any improving move is a step
    worse = next(m for m, w in enumerate(moves) if length(w) > prev["length"])
    assert not judge(m=worse, walk=moves[worse], length=length(moves[worse]))
    assert not judge(kind="opt", m=-1, walk=prev["walk"], length=prev["length"])   # not a local optimum
    assert not judge(kind="shake", m=-1)                                     # a round has not been certified
    s = next(k for k, e in enumerate(C) if e["coord"].get("abstraction") == "search_1"
             and e["coord"]["kind"] == "exec" and e["payload"]["kind"] == "shake" and e["payload"]["r"] > 0)
    P, shake = C[:s], C[s]["payload"]
    tau = lookups.load(P, C[s]["coord"]["criterion"])
    assert evaluation.judge(P, tau, shake)
    assert not evaluation.judge(P, tau, dict(shake, src=[2, 9]))           # a tour no searcher has certified
    assert not evaluation.judge(P, tau, dict(shake, k=4))                   # beyond the last neighborhood


def _bodies(C, role):
    """The body of the specification by which each searcher's events were judged (criterion) or proposed (ontology)."""
    return {e["coord"]["abstraction"]: str(lookups.load(C, e["coord"][role])["body"])
            for e in C if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"].startswith("search_")}


def _chain(C):
    return [(b["r"], b["src"], b["length"]) for b in values(C, "incumbent") if b["improved"]]


def test_asynchronous_cooperation_changes_three_ontologies_and_no_criterion(central):
    """The two classical forms of cooperation are one horizon apart: the criteria are the same."""
    sync = central[1]
    _, asyn = by_agenda(ASYNC)
    assert verify(asyn) == []
    assert _bodies(sync, "criterion") == _bodies(asyn, "criterion")
    assert all("source_sync" in b for b in _bodies(sync, "ontology").values())
    assert all("source_async" in b for b in _bodies(asyn, "ontology").values())
    assert _chain(sync) == [(0, [1, 0], 1004), (1, [1, 1], 985), (4, [3, 4], 937)]
    assert _chain(asyn) == [(0, [1, 0], 1004), (1, [3, 1], 953), (4, [3, 4], 937)]  # 953 already in round 1


def test_synchronous_cooperation_gives_the_same_histories_under_every_schedule(central):
    """Each searcher waits for the incumbent of the round it has finished: a complete horizon, so every
    lineage has the history it has under the agenda (Theorem K), with no lock and no message. Each
    worker pauses at random before every invocation, so the race is decided differently each time."""
    expected, orders = lineages(central[1]), set()
    for seed in range(4):
        rnd = random.Random(seed)
        system, store = System(VNS), MemoryStore()
        workers.run(system, store, log=quiet, hesitate=lambda: time.sleep(rnd.random() * 0.002))
        C = read(store)
        holds_under_any_schedule(system, C, central)
        assert lineages(C) == expected
        orders.add(tuple(e["coord"].get("abstraction") for e in C))
    agenda = tuple(e["coord"].get("abstraction") for e in central[1])
    assert agenda not in orders or len(orders) > 1                     # the record was ordered otherwise


def test_synchronous_cooperation_survives_killed_workers_with_the_same_histories(central):
    """A worker holds no state of its own: killed and started again, it costs time and nothing else."""
    expected, killed = lineages(central[1]), 0
    for seed in range(4):
        system, store = System(VNS), MemoryStore()
        killed += len(run_with_failures(system, store, seed))
        C = read(store)
        holds_under_any_schedule(system, C, central)
        assert lineages(C) == expected
    assert killed, "no worker was killed in any of the runs"


def test_asynchronous_cooperation_is_verifiable_under_every_schedule():
    """Each searcher shakes the best optimum certified so far, as it stands: no waiting, a course
    that depends on the schedule, and a record that replays in every case."""
    for seed in range(3):
        rnd = random.Random(seed)
        system, store = System(VNS), MemoryStore()
        workers.run(system, store, log=quiet, plan=ASYNC, hesitate=lambda: time.sleep(rnd.random() * 0.002))
        C = read(store)
        assert verify(list(C)) == []
        lengths = [b["length"] for b in values(C, "incumbent")]
        assert len(lengths) == 10 and lengths == sorted(lengths, reverse=True)


# ---- the asymmetric neighborhood (ontology v3) and the relative certificate (ontology v4, criterion v2) ----

def _cycle(walk):
    """A tour of the symmetric problem as one key: the walk or the walk read backwards, whichever is smaller."""
    return min(tuple(walk), (walk[0],) + tuple(walk[:0:-1]))


def _recorded_before(C, r):
    """The tours the searchers recorded in the rounds before r (written here independently of lib.py)."""
    return {_cycle(x["walk"]) for i in (1, 2, 3) for x in values(C, f"search_{i}") if x["r"] < r}


def _returns(C, start):
    """The certificates of the very tour their round shook, counted independently of lib.py."""
    opts = [x for i in (1, 2, 3) for x in values(C, f"search_{i}") if x["kind"] == "opt"]
    walk = {(x["i"], x["r"]): x["walk"] for x in opts}
    return sum(_cycle(x["walk"]) == _cycle(start if x["src"] == [0, -1] else walk[tuple(x["src"])]) for x in opts)


def test_the_symmetric_neighborhood_goes_back_and_the_asymmetric_one_less(central, asym):
    """The inverse of a shake is an improving move of the shaken tour. v1 often takes it and certifies
    the tour it shook; v3 takes it only when every improving move leads to a recorded tour."""
    start = _fri26()[1]["START"]
    assert _returns(central[1], start) == values(central[1], "kpi")[-1]["returns"] == 14
    assert _returns(asym[1], start) == values(asym[1], "kpi")[-1]["returns"] == 11


def test_the_asymmetric_descent_avoids_the_recorded_tours(asym):
    """Every step of the descent under ontology v3 is the first improving move to a tour the finished
    rounds have not recorded, the first improving move if there is none, or the certificate if no
    move improves (checked here independently of lib.py)."""
    C = asym[1]
    D, _ = _fri26()
    length = lambda w: sum(D[w[i - 1]][w[i]] for i in range(len(w)))
    known = {r: _recorded_before(C, r) for r in range(10)}
    for i in (1, 2, 3):
        steps = values(C, f"search_{i}")
        for prev, x in zip(steps, steps[1:]):
            if x["kind"] == "shake":
                continue
            better = [w for w in _neighbors(prev["walk"]) if length(w) < length(prev["walk"])]
            new = [w for w in better if _cycle(w) not in known[x["r"]]]
            assert x["walk"] == (new or better or [prev["walk"]])[0]
            assert (x["kind"] == "opt") == (not better)


def test_the_asymmetric_neighborhood_changes_three_ontologies_and_no_criterion(central, asym):
    """The neighborhood is resolved against the record by the ontology alone (D1, D2)."""
    assert verify(asym[1]) == []
    assert _bodies(central[1], "criterion") == _bodies(asym[1], "criterion")
    assert all("vns_step_asym" in b and "False" in b for b in _bodies(asym[1], "ontology").values())
    assert _chain(asym[1]) == [(0, [1, 0], 1004), (1, [1, 1], 985), (3, [2, 3], 974), (4, [3, 4], 937)]


def test_the_asymmetric_neighborhood_gives_the_same_histories_under_every_schedule(asym):
    """v3 reads only the rounds that are finished when its round begins, a complete horizon, so the
    synchronous form keeps one history of every lineage under every schedule (Theorem K)."""
    expected = lineages(asym[1])
    for seed in range(2):
        rnd = random.Random(seed)
        system, store = System(VNS), MemoryStore()
        workers.run(system, store, log=quiet, plan=ASYM, hesitate=lambda: time.sleep(rnd.random() * 0.002))
        C = read(store)
        assert verify(list(C)) == [] and lineages(C) == expected


def test_the_relative_certificate_is_admitted_by_criterion_v2_and_refused_by_v1(strict):
    """Under ontology v4 no round goes back. Every certificate is of a tour whose shorter neighbors
    are all recorded in the rounds before its own; criterion v2 admits it, v1 only if it has none."""
    C = strict[1]
    D, c = _fri26()
    length = lambda w: sum(D[w[i - 1]][w[i]] for i in range(len(w)))
    assert verify(C) == []
    kpi = values(C, "kpi")[-1]
    assert kpi["returns"] == _returns(C, c["START"]) == 0 and kpi["relative"] == 12
    relative = []
    for n, e in enumerate(C):
        x = e["payload"]
        if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"].startswith("search_") and x["kind"] == "opt":
            better = [w for w in _neighbors(x["walk"]) if length(w) < x["length"]]
            assert all(_cycle(w) in _recorded_before(C, x["r"]) for w in better)
            if better:
                relative.append(n)
    assert len(relative) == 12
    n = relative[0]
    P, w, a = C[:n], C[n]["payload"], C[n]["coord"]["abstraction"]
    v1 = next(e["coord"]["addr"] for e in C if e["coord"]["kind"] == "spec" and e["coord"]["abstraction"] == a
              and e["coord"]["role"] == "criterion" and e["coord"]["version"] == 1)
    assert evaluation.judge(P, lookups.load(P, C[n]["coord"]["criterion"]), w)       # criterion v2
    assert not evaluation.judge(P, lookups.load(P, v1), w)                            # criterion v1
    m = next(k for k, e in enumerate(C) if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == a
             and e["payload"]["kind"] == "move")                                      # in round 0 nothing is recorded
    P, prev = C[:m], values(C[:m], a)[-1]
    false = dict(C[m]["payload"], kind="opt", m=-1, walk=prev["walk"], length=prev["length"])
    assert not evaluation.judge(P, lookups.load(P, C[m]["coord"]["criterion"]), false)
