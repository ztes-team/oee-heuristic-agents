"""Compare flat sampling, native path DP, and a checked ZTES run on the same CPTL instances."""

import argparse
import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from random import Random
from time import perf_counter_ns
from tracemalloc import get_traced_memory, start, stop

from ztes.substrate.replay import verify
from ztes.substrate.store import MemoryStore, read
from ztes.system.authoring import read_directory
from ztes.system.system import System

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "cptl"
domain_spec = spec_from_file_location("cptl_domain", EXAMPLE / "lib.py")
domain = module_from_spec(domain_spec)
domain_spec.loader.exec_module(domain)


def guard_sequence(size):
    if size < 2:
        raise ValueError("CPTL requires at least two stages")
    return [stage % 3 != 1 for stage in range(size)]


def case_system(guards):
    if len(guards) < 2 or guards[1]:
        raise ValueError("the case study requires an input-first second stage")
    definition = read_directory(EXAMPLE)
    definition["constants"]["GUARDS"] = guards
    definition.pop("expect")
    return System.from_dict(definition)


def event_payloads(record, name):
    return [
        event["payload"] for event in record
        if event["coord"]["kind"] == "exec" and event["coord"]["abstraction"] == name
    ]


def native_dp(guards):
    rows = {}
    tail = domain.terminal_row(len(guards))
    for stage in reversed(range(len(guards))):
        tail = domain.suffix_row(stage, guards[stage], tail)
        rows[stage] = tail
    route = []
    previous = {"stage": -1, "link": 0}
    for _ in guards:
        previous = domain.planned_step(guards, rows, previous)
        route.append(previous)
    return rows, route


def verify_native(guards, rows, route):
    previous = {"stage": -1, "link": 0}
    tail = domain.terminal_row(len(guards))
    for stage in reversed(range(len(guards))):
        if rows[stage] != domain.suffix_row(stage, guards[stage], tail):
            return False
        tail = rows[stage]
    for step in route:
        if step["trial"] or not domain.check_step(guards, rows, {"stage": -1}, previous, step):
            return False
        previous = step
    return previous["stage"] == len(guards) - 1 and previous["link"] == 1


def feasible_word(guards, word):
    if not (word >> (len(guards) - 1)) & 1:
        return False
    incoming = 0
    for stage, guard_first in enumerate(guards):
        link = (word >> stage) & 1
        if not domain.transition_allowed(guard_first, incoming, link):
            return False
        incoming = link
    return True


def execute(system):
    store = MemoryStore()
    system.run(store, log=lambda *_: None)
    return list(read(store))


def compare(guards, samples, seed, peak_memory=False):
    begin = perf_counter_ns()
    rows, route = native_dp(guards)
    native_time = perf_counter_ns() - begin
    begin = perf_counter_ns()
    if not verify_native(guards, rows, route):
        raise RuntimeError("native certificate failed")
    native_verification_time = perf_counter_ns() - begin

    system = case_system(guards)
    begin = perf_counter_ns()
    record = execute(system)
    execution_time = perf_counter_ns() - begin
    begin = perf_counter_ns()
    errors = verify(record)
    replay_time = perf_counter_ns() - begin
    if errors:
        raise RuntimeError(f"replay failed: {errors}")

    recorded_rows = {row["stage"]: row for row in event_payloads(record, "suffix")}
    recorded_route = [step for step in event_payloads(record, "route") if not step["trial"]]
    if recorded_rows != rows or recorded_route != route:
        raise RuntimeError("native and checked ZTES results differ")

    size = len(guards)
    rng = Random(seed)
    hits = sum(feasible_word(guards, rng.getrandbits(size)) for _ in range(samples))
    result = {
        "modules": size,
        "optimal_link_sum": rows[0]["best"][0],
        "feasible_link_words": rows[0]["count"][0],
        "possible_link_words": 2**size,
        "uniform_samples": samples,
        "uniform_feasible_hits": hits,
        "native_dp_ns": native_time,
        "native_certificate_check_ns": native_verification_time,
        "oee_execution_ns": execution_time,
        "oee_replay_ns": replay_time,
        "events": len(record),
        "record_json_bytes": len(json.dumps(record, separators=(",", ":")).encode("utf-8")),
    }
    if peak_memory:
        memory_system = case_system(guards)
        start()
        try:
            execute(memory_system)
            result["oee_peak_traced_python_bytes"] = get_traced_memory()[1]
        finally:
            stop()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sizes", type=int, nargs="*", default=[6, 20, 100])
    parser.add_argument("--samples", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--peak-memory", action="store_true", help="trace allocations in a separate run")
    args = parser.parse_args()
    if any(size < 2 for size in args.sizes) or args.samples < 0:
        parser.error("sizes must be at least two and samples must be nonnegative")
    for size in args.sizes:
        print(json.dumps(compare(guard_sequence(size), args.samples, args.seed, args.peak_memory)), flush=True)


if __name__ == "__main__":
    main()
