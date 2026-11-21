"""Measure the ksat systems: the native execution of the same relations, the checked execution in
ZTES with its record, and the replay of the record.

    python scripts/benchmark_ksat.py                 # the table of examples/ksat/DESIGN.md
    python scripts/benchmark_ksat.py --sizes 20 30   # random 3-CNF of these sizes only

For each formula it reports the events of the record, the learned clauses (each non-empty one an
abstraction brought in during the run), the abstractions that executed, the times of the native
run, of the run under the agenda (memory store) and of both replays, the size of the record in
canonical JSON, and the verdict. It also checks that the record contains exactly the frames,
decisions, learned clauses and verdict of the native run, and that every replay passes.
"""
import argparse
import importlib.util
import time
from pathlib import Path

from ztes.substrate.replay import verify
from ztes.substrate.store import MemoryStore, read
from ztes.system.report import record_size
from ztes.system.system import System

SPEC = importlib.util.spec_from_file_location("ksat_system", Path(__file__).with_name("ksat_system.py"))
ks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ks)


def values(record, name):
    return [e["payload"] for e in record if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == name]


def measure(label, variables, formula):
    """One row: run natively, run in ZTES, replay twice, and compare."""
    t = time.perf_counter()
    native = ks.native(variables, formula)
    t_native = time.perf_counter() - t
    system, store = System.from_dict(ks.definition(variables, formula)), MemoryStore()
    t = time.perf_counter()
    system.run(store, log=lambda *_: None)
    t_run = time.perf_counter() - t
    C = list(read(store))
    t = time.perf_counter()
    full = verify(C)
    t_full = time.perf_counter() - t
    t = time.perf_counter()
    judged = verify(C, judgments_only=True)
    t_judged = time.perf_counter() - t
    same = (values(C, "round") == native["frames"] and values(C, "decide") == native["decisions"]
            and [{k: v for k, v in p.items() if k != "specifications"} for p in values(C, "learn")] == native["learned"]
            and values(C, "verdict") == [native["verdict"]])
    assert full == [] and judged == [] and same, (label, full[:1], judged[:1], same)
    learned = values(C, "learn")
    return {"formula": label, "events": len(C), "learned": len(learned),
            "abstractions": len(system.abstractions), "native": t_native, "run": t_run,
            "replay": t_full, "judgments": t_judged,
            "bytes": sum(b for _, b in record_size(C).values()),
            "verdict": "SAT" if native["verdict"]["sat"] else "UNSAT",
            "adapt": bool(values(C, "adapt"))}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--sizes", type=int, nargs="*", default=[20, 30, 40, 50])
    p.add_argument("--seeds", type=int, default=3)
    a = p.parse_args(argv)
    rows = [measure("PHP(4,3)", *ks.pigeonhole(4, 3))]
    for n in a.sizes:
        m = round(4.26 * n)
        for seed in range(a.seeds):
            rows.append(measure(f"random 3-CNF n={n} m={m} seed={seed}", *ks.random_kcnf(n, m, 3, seed)))
    print("| Formula | Events | Learned | Abstractions | Native | Run | Full replay | Replay of judgments "
          "| Record | Verdict |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['formula']} | {r['events']} | {r['learned']} | {r['abstractions']} | {r['native']:.3f} s "
              f"| {r['run']:.2f} s | {r['replay']:.2f} s | {r['judgments']:.2f} s | {r['bytes'] / 1e6:.2f} MB "
              f"| {r['verdict']}{' (policy changed)' if r['adapt'] else ''} |")


if __name__ == "__main__":
    main()
