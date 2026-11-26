"""The worker trials of the companion paper (in preparation): phase 3 run by one worker per abstraction, under random schedules
and with workers killed and started again.

A synchronous form reads only complete horizons, so under the conditions of Theorem K every lineage
must have the history it has under the agenda, whatever the schedule and however often a worker
dies. Each trial checks exactly that, and that the record replays (R2). A schedule is made by a
random pause of every worker before every invocation (the pauses have a seed; the interleaving
the operating system makes of them does not). A worker may be killed before an invocation or right
after one of its events has been appended, and is started again after a while; the number of
workers killed depends on the run and is reported.

    python scripts/trials.py vns      # v1 on fri26, 40 schedules, 20 runs with workers killed
    python scripts/trials.py forms    # v3 and v4 on fri26, 20 schedules and 10 runs with kills each
    python scripts/trials.py ftv38    # v3 on ftv38, 4 schedules and 2 runs with kills
    python scripts/trials.py tw       # v1 and v3 with time windows under 3 schedules,
                                      #   and v2 (asynchronous) over 3 draws x 3 worlds x 3 schedules
    python scripts/trials.py          # all of them, about half an hour
    python scripts/trials.py --quick  # two runs of each kind, for a check in a few minutes

The forms are those of scripts/sweeps.py.
"""
import copy
import random
import statistics
import sys
import threading
import time
from pathlib import Path

from ztes.substrate.replay import verify
from ztes.substrate.store import MemoryStore, read
from ztes.system import workers
from ztes.system.system import System

ROOT = Path(__file__).resolve().parent.parent / "examples"
quiet = lambda *_: None
QUICK = "--quick" in sys.argv


def form(*keys):
    """The plan of an example with a governed change of the three searchers before phase 3."""
    govern = [f"search_{i}/{key}" for key in keys for i in (1, 2, 3)]
    return [{"phase": 1}, {"phase": 2}, {"govern": govern}, {"phase": 3}, {"kpi": True}]


FORMS = {"v1": None,
         "v2": form("ontology.v2"),
         "v3": form("ontology.v2", "ontology.v3"),
         "v4": form("ontology.v2", "ontology.v3", "criterion.v2", "ontology.v4")}


def system_of(example, draw=None, world=None):
    """The system of an example, with other seeds of its boundary abstractions if given."""
    definition = copy.deepcopy(System(ROOT / example).definition)
    definition.pop("expect", None)
    system = System.from_dict(definition)
    if draw is not None:
        system.declared_sources["draw"]["random"]["seed"] = draw
    if world is not None:
        system.declared_sources["world"]["random"]["seed"] = world
    return system


def lineages(C):
    """The history of every lineage but profile and kpi, which count the invocations of a schedule."""
    out = {}
    for e in C:
        if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] not in ("profile", "kpi"):
            out.setdefault(e["coord"]["abstraction"], []).append(e["payload"])
    return out


def kpi(C):
    return [e["payload"] for e in C if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == "kpi"][-1]


def by_agenda(example, plan, **seeds):
    store = MemoryStore()
    system_of(example, **seeds).run(store, log=quiet, plan=plan)
    return list(read(store))


def by_workers(example, plan, schedule, **seeds):
    """Phase 3 by one worker per abstraction, each pausing at random before every invocation."""
    rnd, store = random.Random(schedule), MemoryStore()
    workers.run(system_of(example, **seeds), store, log=quiet, plan=plan,
                hesitate=lambda: time.sleep(rnd.random() * 0.002))
    return list(read(store))


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
            raise Killed()                                   # the event is in C; the worker never learns it
        return done


def with_kills(example, plan, seed, chance=0.15):
    """Every worker may be killed before an invocation or right after an append, and is started again.
    Returns the record and the number of workers killed."""
    system, store = system_of(example), MemoryStore()
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
                time.sleep(rnd.random() * 0.005)             # it stays down for a while

    threads = [threading.Thread(target=supervise, args=(a,), daemon=True) for a in system.abstractions]
    for t in threads:
        t.start()
    workers.run(system, store, local=False, log=quiet, plan=plan)
    for t in threads:
        t.join(timeout=5)
    return list(read(store)), len(deaths)


def trial(example, name, schedules, kill_runs):
    """A synchronous form under random schedules and with workers killed: the histories of the agenda?"""
    plan = FORMS[name]
    expected = lineages(by_agenda(example, plan))
    if QUICK:
        schedules, kill_runs = min(schedules, 2), min(kill_runs, 2)
    same = replayed = 0
    for s in range(1, schedules + 1):
        C = by_workers(example, plan, s)
        same += lineages(C) == expected
        replayed += verify(C) == []
    print(f"{example} {name}: {same} of {schedules} random schedules gave the histories of the agenda; "
          f"{replayed} of {schedules} records replayed")
    if kill_runs:
        same = replayed = killed = 0
        for s in range(1, kill_runs + 1):
            C, k = with_kills(example, plan, s)
            killed += k
            same += lineages(C) == expected
            replayed += verify(C) == []
        print(f"{example} {name}: {same} of {kill_runs} runs with workers killed gave the histories of the "
              f"agenda ({killed} workers killed in all); {replayed} of {kill_runs} records replayed")
    sys.stdout.flush()


def vns():
    trial("vns", "v1", 40, 20)


def forms():
    trial("vns", "v3", 20, 10)
    trial("vns", "v4", 20, 10)


def ftv38():
    trial("vns-atsp", "v3", 4, 2)


def shares3(table):
    """Three-way decomposition of the variance of table[(a, b, c)]: the three main effects and the
    interactions together, in % of the total to one decimal."""
    grand = statistics.mean(table.values())
    total = sum((x - grand) ** 2 for x in table.values())
    out = []
    for axis in range(3):
        means = {}
        for key, x in table.items():
            means.setdefault(key[axis], []).append(x)
        out.append(sum(len(v) * (statistics.mean(v) - grand) ** 2 for v in means.values()))
    out.append(total - sum(out))
    return tuple(round(100 * x / total, 1) for x in out) if total else (0, 0, 0, 0)


def tw():
    trial("vns-tw", "v1", 3, 0)
    trial("vns-tw", "v3", 3, 0)
    draws, worlds, schedules = (1, 2, 3), (11, 12, 13), (1, 2, 3)
    if QUICK:
        draws, worlds, schedules = (1,), (11,), (1, 2)
    length, replayed, changed = {}, 0, 0
    for d in draws:
        for w in worlds:
            ends = set()
            for s in schedules:
                C = by_workers("vns-tw", FORMS["v2"], s, draw=d, world=w)
                replayed += verify(C) == []
                best = kpi(C)["best"]
                length[(d, w, s)] = best[3]
                ends.add(tuple(best))
            changed += len(ends) > 1
    runs = len(draws) * len(worlds) * len(schedules)
    print(f"vns-tw v2 (asynchronous): {runs} runs by workers, {replayed} records replayed; the schedule changed "
          f"the final tour in {changed} of the {len(draws) * len(worlds)} combinations of draw and world")
    if not QUICK:
        print("shares of the variance of the final length (algorithm, environment, schedule, interactions): "
              "%.1f %%, %.1f %%, %.1f %%, %.1f %%" % shares3(length))
    sys.stdout.flush()


if __name__ == "__main__":
    for what in [a for a in sys.argv[1:] if not a.startswith("--")] or ["vns", "forms", "ftv38", "tw"]:
        globals()[what]()
