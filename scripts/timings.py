"""Time the run and both replays of every example, on one host, with the record in memory.

    python scripts/timings.py              # median of three runs of each example
    python scripts/timings.py --repeat 5

For each example it reports the events of the record, the run under the agenda, the full replay
(every candidate derived again and judged again) and the replay of judgments (the recorded
candidates judged again), each the median over the repetitions. Every run must meet the expected
end of its system and every replay must pass. The native comparisons of CPTL and ksat are in
scripts/benchmark_cptl.py and scripts/benchmark_ksat.py.
"""
import argparse
import platform
import statistics
import sys
import time
from pathlib import Path

from ztes.substrate.replay import verify
from ztes.substrate.store import MemoryStore, read
from ztes.system.report import check_expect
from ztes.system.system import System

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ["vns", "vns-atsp", "vns-tw", "vns-hk", "vns-adaptive", "cptl", "sat4", "ksat/php43", "ksat/random20"]


def quiet(*_):
    pass


def once(path):
    """One run under the agenda and both replays; (events, run, full replay, replay of judgments)."""
    system, store = System(path), MemoryStore()
    t = time.perf_counter()
    system.run(store, log=quiet)
    run = time.perf_counter() - t
    C = list(read(store))
    assert check_expect(system, C, log=quiet) == [], path
    t = time.perf_counter()
    assert verify(C) == [], path
    full = time.perf_counter() - t
    t = time.perf_counter()
    assert verify(C, judgments_only=True) == [], path
    judged = time.perf_counter() - t
    return len(C), run, full, judged


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repeat", type=int, default=3)
    p.add_argument("examples", nargs="*", default=EXAMPLES)
    a = p.parse_args(argv)
    print(f"{platform.system()} {platform.machine()}, Python {platform.python_version()}, "
          f"median of {a.repeat} runs, record in memory\n")
    print("| Example | Events | Run | Full replay | Replay of judgments |")
    print("|---|---|---|---|---|")
    for name in a.examples:
        runs = [once(ROOT / "examples" / name) for _ in range(a.repeat)]
        events = runs[0][0]
        med = [statistics.median(r[k] for r in runs) for k in (1, 2, 3)]
        print(f"| {name} | {events} | {med[0]:.3f} s | {med[1]:.3f} s | {med[2]:.3f} s |")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
