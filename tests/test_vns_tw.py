"""Tests of examples/vns-tw: VNS by three cooperating searchers on ftv38 with time windows and
precedence constraints, under a recorded environment.

The evaluation of a tour (schedule, lateness, precedence, the scenarios it fails) is written here
again, independently of lib.py; only the definition of a scenario from its recorded seed and of the
audit scenarios is taken from lib.py, since it is part of the instance. A run takes about six
seconds, so each form is run once.
"""
import importlib.util
import json
import random
import time
from pathlib import Path

import pytest

from ztes.substrate import lookups
from ztes.substrate.replay import verify
from ztes.substrate.store import MemoryStore, read
from ztes.system import authoring, workers
from ztes.system.report import check_expect
from ztes.system.system import System

TW = Path(__file__).parent.parent / "examples" / "vns-tw"
LIB = {}
exec((TW / "lib.py").read_text(encoding="utf8"), LIB)
quiet = lambda *_: None


def form(*versions):
    govern = [f"search_{i}/ontology.v{v}" for v in versions for i in (1, 2, 3)]
    return [{"phase": 1}, {"phase": 2}] + ([{"govern": govern}] if govern else []) + [{"phase": 3}, {"kpi": True}]


ASYNC, ASYM = form(2), form(2, 3)


def system(**constants):
    d = authoring.read_directory(TW)
    d["constants"].update(constants)
    return System(definition=d)


def by_agenda(plan=None, **constants):
    s, store = system(**constants), MemoryStore()
    s.run(store, log=quiet, plan=plan)
    return s, list(read(store))


@pytest.fixture(scope="module")
def central():
    """The plan: synchronous cooperation (v1) with the chance constraint."""
    return by_agenda()


@pytest.fixture(scope="module")
def asym():
    return by_agenda(ASYM)


def values(C, a):
    return [e["payload"] for e in C if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == a]


def lineages(C):
    out = {}
    for e in C:
        if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] not in ("profile", "kpi"):
            out.setdefault(e["coord"]["abstraction"], []).append(e["payload"])
    return out


def kpi(C):
    return {k: v for k, v in values(C, "kpi")[-1].items() if k != "profile"}


def _bodies(C, role):
    return {e["coord"]["abstraction"]: str(lookups.load(C, e["coord"][role])["body"])
            for e in C if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"].startswith("search_")}


# ---- the evaluation of a tour, written here independently of lib.py ----

C0 = json.loads((TW / "system.json").read_text(encoding="utf8"))["constants"]
N, D, A, B, PAIRS = C0["N"], C0["D"], C0["A"], C0["B"], C0["PAIRS"]


def _times(T, walk, scale):
    t, out = 0, [0]
    for x in range(1, len(walk)):
        t = max(t + T[walk[x - 1]][walk[x]], scale * A[walk[x]])
        out.append(t)
    return out, t + T[walk[-1]][walk[0]]


def _late_anywhere(T, walk, scale):
    t, back = _times(T, walk, scale)
    return any(t[x] > scale * B[walk[x]] for x in range(1, len(walk))) or back > scale * B[0]


def _evaluate(scen, allow, walk):
    """[precedence pairs violated, lateness, scenarios failed beyond allow, length]."""
    t, back = _times(D, walk, 1)
    late = sum(max(0, t[x] - B[walk[x]]) for x in range(1, N)) + max(0, back - B[0])
    pos = {c: x for x, c in enumerate(walk)}
    fails = sum(_late_anywhere(T, walk, 100) for T in scen)
    return [sum(pos[p] > pos[q] for p, q in PAIRS), late, max(0, fails - allow),
            sum(D[walk[x - 1]][walk[x]] for x in range(N))]


def _first(walk):
    """The first position that is not admissible and why: ("false", x) late, ("not_yet", x) a city
    it must follow comes later; ("true", -1) none."""
    t, back = _times(D, walk, 1)
    pos = {c: x for x, c in enumerate(walk)}
    for x in range(1, N):
        if t[x] > B[walk[x]]:
            return "false", x
        if any(q == walk[x] and pos[p] > x for p, q in PAIRS):
            return "not_yet", x
    return ("false", N) if back > B[0] else ("true", -1)


def _scenarios(C):
    return [LIB["scenario"](D, w[0], N, C0["RHO"]) for w in values(C, "world")]


def _exchange(walk, i, j, k):
    return walk[:i + 1] + walk[j + 1:k + 1] + walk[i + 1:j + 1] + walk[k + 1:]


MOVES = [(i, j, k) for i in range(N) for j in range(i + 1, N) for k in range(j + 1, N)]


# ---- the checks ----

def test_is_well_formed():
    assert System(TW).check(log=quiet) == []


def test_the_generator_reproduces_the_instance():
    spec = importlib.util.spec_from_file_location("generate", TW / "generate.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    a, b, pairs, ref = gen.generate(D)
    assert (a, b, pairs) == (A, B, PAIRS)
    assert _evaluate([], 0, ref)[:2] == [0, 0]                      # the reference tour is feasible


def test_meets_its_expected_end_and_replays(central):
    s, C = central
    assert check_expect(s, C, log=quiet) == []
    assert verify(C) == []


def test_the_scenarios_are_recorded_once_and_read_by_the_searchers(central):
    """Each scenario of the world is computed once, by the abstraction scenario, and recorded: one
    event per recorded seed, equal to its definition. The searchers and their criteria read the
    scenarios from the record: their horizon holds scenario, and not world."""
    C = central[1]
    rec = values(C, "scenario")
    assert [x["s"] for x in rec] == list(range(C0["M"]))
    assert [x["seed"] for x in rec] == [w[0] for w in values(C, "world")]
    assert [x["T"] for x in rec] == _scenarios(C)
    for i in (1, 2, 3):
        horizon = lookups.horizon(C, f"search_{i}")
        assert "scenario" in horizon and "world" not in horizon


def test_the_exact_optima_and_the_bias_of_the_sample(central):
    """The deterministic optimum (3,415) fails in 14 of the 20 scenarios of the world and is on
    time in 457 of the 1,000 audit scenarios. The sample-average optimum (3,492) is on time in all
    20 scenarios it was optimized on, but only in 898 of the 1,000 audit scenarios, below the 90 %
    the constraint aims at: the sample overstates the probability of the event it estimates."""
    C = central[1]
    scen, seed = _scenarios(C), values(C, "audit")[0][0]
    audit = lambda w: sum(LIB["on_time"](D, A, B, w, LIB["audit_seed"](seed, s), N, C0["RHO"]) for s in range(C0["AUDIT"]))
    opt = json.loads((TW / "optima.json").read_text(encoding="utf8"))
    det, saa = opt["deterministic"]["walk"], opt["chance"]["walk"]
    assert _evaluate([], 0, det) == [0, 0, 0, 3415] and sum(_late_anywhere(T, det, 100) for T in scen) == 14
    assert _evaluate(scen, C0["ALLOW"], saa) == [0, 0, 0, 3492] and sum(_late_anywhere(T, saa, 100) for T in scen) == 0
    assert (audit(det), audit(saa)) == (457, 898)
    assert kpi(C)["audit_on_time"] == audit(values(C, "incumbent")[-1]["walk"]) == 994


def test_the_incremental_evaluation_equals_the_full_one(central):
    """lib.value_after and lib.lowers, used by the searchers and their criterion, agree with the
    evaluation written here, on random tours and on tours near the optimum."""
    scen = _scenarios(central[1])
    opt = json.loads((TW / "optima.json").read_text(encoding="utf8"))["deterministic"]["walk"]
    rnd, moves = random.Random(5), LIB["segment_moves"](N)
    for trial in range(150):
        w = [0] + rnd.sample(range(1, N), N - 1) if trial % 3 == 0 else list(opt)
        for _ in range(rnd.randint(0, 3) if trial % 3 else 0):
            w = _exchange(w, *MOVES[rnd.randrange(len(MOVES))])
        st = LIB["state"](D, A, B, PAIRS, scen, w)
        v = LIB["value"](st, C0["ALLOW"])
        assert v == _evaluate(scen, C0["ALLOW"], w)
        for m in rnd.sample(range(len(MOVES)), 10):
            full = _evaluate(scen, C0["ALLOW"], _exchange(w, *MOVES[m]))
            assert LIB["value_after"](D, A, B, PAIRS, scen, C0["ALLOW"], moves, w, st, m) == full
            assert LIB["lowers"](D, A, B, PAIRS, scen, C0["ALLOW"], moves, w, st, m, v) == (full < v)


def test_every_step_states_its_tour_truly_and_is_a_step_of_vns(central):
    """Every step states the value and the first position that is not admissible of its tour; every
    repair and move lowers the value (a repair if the tour was infeasible); the final incumbent's
    certificate holds by brute force over the 9,139 moves and the 20 scenarios."""
    C = central[1]
    scen, allow = _scenarios(C), C0["ALLOW"]
    for a in ("search_1", "search_2", "search_3"):
        steps = values(C, a)
        for prev, x in zip([None] + steps, steps):
            assert x["value"] == _evaluate(scen, allow, x["walk"])
            assert [x["status"], x["first"]] == list(_first(x["walk"]))
            if x["kind"] in ("repair", "move"):
                assert x["walk"] == _exchange(prev["walk"], *MOVES[x["m"]]) and x["value"] < prev["value"]
                assert (x["kind"] == "repair") == (sum(prev["value"][:3]) > 0)
    best = values(C, "incumbent")[-1]["walk"]
    v = _evaluate(scen, allow, best)
    assert all(_evaluate(scen, allow, _exchange(best, *m)) >= v for m in MOVES)


def test_a_late_city_is_false_and_a_premature_one_not_yet(central):
    """Both are decided by the prefix: a move that cuts at or after the first position that is not
    admissible leaves that position as it is (late stays late, premature stays premature), so a
    repair must cut before it. Checked on every recorded tour that has such a position."""
    C, rnd = central[1], random.Random(3)
    seen = {"false": 0, "not_yet": 0}
    for a in ("search_1", "search_2", "search_3"):
        for x in values(C, a):
            if x["status"] != "true" and x["first"] < N:
                f = x["first"]
                seen[x["status"]] += 1
                after = [m for m in MOVES if m[0] >= f]
                for m in rnd.sample(after, min(10, len(after))):
                    y = _exchange(x["walk"], *m)
                    assert y[:f + 1] == x["walk"][:f + 1] and _first(y) == (x["status"], f)
    assert seen["false"] > 0 and seen["not_yet"] > 0


def test_the_asymmetric_neighborhood_returns_less(central, asym):
    """v3: the repair and the shortening avoid the tours of the finished rounds; same criteria."""
    assert verify(asym[1]) == []
    assert _bodies(central[1], "criterion") == _bodies(asym[1], "criterion")
    one, three = kpi(central[1]), kpi(asym[1])
    assert (one["returns"], three["returns"]) == (26, 17)
    assert one["best"] == three["best"] == [0, 0, 0, 3504]
    first = lambda C: [b["r"] for b in values(C, "incumbent") if b["value"] == [0, 0, 0, 3504]][0]
    assert (first(central[1]), first(asym[1])) == (6, 3)


@pytest.mark.parametrize("plan, best, on_time, audit", [(None, 3482, 17, 672), (ASYM, 3482, 7, 430)], ids=["v1", "v3"])
def test_without_the_chance_constraint_the_search_is_blind_to_the_environment(plan, best, on_time, audit):
    """ALLOW = M: every scenario may fail, the deterministic problem. v1 and v3 end at the same
    length, 2 % above the deterministic optimum, with tours that the environment treats very differently."""
    s, C = by_agenda(plan, ALLOW=C0["M"])
    k = kpi(C)
    assert (k["best"][3], k["on_time"], k["audit_on_time"], k["optimum"]) == (best, on_time, audit, 3415)


def test_the_synchronous_form_gives_the_same_histories_by_workers(central):
    rnd = random.Random(1)
    s, store = system(), MemoryStore()
    workers.run(s, store, log=quiet, hesitate=lambda: time.sleep(rnd.random() * 0.002))
    C = list(read(store))
    assert verify(C) == [] and lineages(C) == lineages(central[1])


def test_the_asynchronous_form_is_verifiable_by_workers():
    rnd = random.Random(1)
    s, store = system(), MemoryStore()
    workers.run(s, store, log=quiet, plan=ASYNC, hesitate=lambda: time.sleep(rnd.random() * 0.002))
    C = list(read(store))
    assert verify(C) == []
    v = [b["value"] for b in values(C, "incumbent")]
    assert len(v) == C0["R"] and v == sorted(v, reverse=True)
