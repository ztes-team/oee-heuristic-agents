"""The results of the paper over many seeds: one run per seed and form under the agenda.

Every number is an indicator read from the record of a run, by the kpi abstraction of the example
or, for the round of the first return, by the function below; nothing is measured during a run.
The runs are under the agenda, so every number is the same on every host.

    python scripts/sweeps.py fri26      # Table 7: the forms on fri26, seeds 1-40, and the paired counts
    python scripts/sweeps.py agent      # Table 10: the adaptive agent against the fixed forms on fri26
    python scripts/sweeps.py ftv38      # Table 8: the forms on ftv38, seeds 1-40
    python scripts/sweeps.py tw         # Table 9: time windows with and without the chance constraint
    python scripts/sweeps.py variance   # Section 7.2: algorithm x environment, shares of the variance
    python scripts/sweeps.py            # all of them, about twenty minutes

The forms are those of Section 4.2 of the paper: v1 the plan (synchronous), v2 asynchronous, v3 the
asymmetric neighborhood, v4 the strict descent with criterion v2 (the certificate relative to the
record). Each is a governed change of the three searchers before phase 3, as in the tests.
"""
import copy
import statistics
import sys
from pathlib import Path

from ztes.substrate.store import MemoryStore, read
from ztes.system.system import System

ROOT = Path(__file__).resolve().parent.parent / "examples"
quiet = lambda *_: None


def form(*keys):
    """The plan of an example with a governed change of the three searchers before phase 3."""
    govern = [f"search_{i}/{key}" for key in keys for i in (1, 2, 3)]
    return [{"phase": 1}, {"phase": 2}, {"govern": govern}, {"phase": 3}, {"kpi": True}]


FORMS = {"v1": None,
         "v2": form("ontology.v2"),
         "v3": form("ontology.v2", "ontology.v3"),
         "v4": form("ontology.v2", "ontology.v3", "criterion.v2", "ontology.v4")}


def run(example, draw, plan=None, constants=None, world=None):
    """One run under the agenda with the given draw seed (and world seed); (record, last kpi payload)."""
    definition = copy.deepcopy(System(ROOT / example).definition)
    definition.pop("expect", None)                    # the expected end holds for the seeds of system.json only
    if constants:
        definition["constants"].update(constants)
    system = System.from_dict(definition)
    system.declared_sources["draw"]["random"]["seed"] = draw
    if world is not None:
        system.declared_sources["world"]["random"]["seed"] = world
    store = MemoryStore()
    system.run(store, log=quiet, plan=plan)
    C = list(read(store))
    kpi = [e["payload"] for e in C if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == "kpi"][-1]
    return C, kpi


def values(C, a):
    return [e["payload"] for e in C if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == a]


def chain(C):
    """The lengths the incumbent takes, in order, each once."""
    out = []
    for x in values(C, "incumbent"):
        if not out or x["length"] != out[-1]:
            out.append(x["length"])
    return out


def first_return(C, start):
    """The first round in which a searcher certifies the very tour its shake started from (a return)."""
    def cycle(w):
        return min(tuple(w), (w[0],) + tuple(w[:0:-1]))
    certs = [x for i in (1, 2, 3) for x in values(C, f"search_{i}") if x["kind"] == "opt"]
    tour = {(x["i"], x["r"]): x["walk"] for x in certs}
    rounds = [x["r"] for x in certs
              if cycle(x["walk"]) == cycle(start if x["src"] == [0, -1] else tour[tuple(x["src"])])]
    return min(rounds) if rounds else None


def paired(a, b):
    """(shorter, longer, the same): how often the end of a is below, above or equal to that of b."""
    return (sum(x < y for x, y in zip(a, b)), sum(x > y for x, y in zip(a, b)),
            sum(x == y for x, y in zip(a, b)))


def mean(xs, digits=2):
    return round(statistics.mean(xs), digits)


SEEDS = range(1, 41)


def fri26():
    print("## Table 7: the forms of the searchers on fri26 (optimum 937)\n")
    print("| Form | Seed 7: incumbent | Seed 7: returns | Seed 7: moves | Seeds 1-40: optimum reached | "
          "Seeds 1-40: returns per run | moves per run | relative certificates per run |")
    print("|---|---|---|---|---|---|---|---|")
    ends = {}
    for name, plan in FORMS.items():
        C7, k7 = run("vns", 7, plan)
        rows = [run("vns", s, plan)[1] for s in SEEDS]
        ends[name] = [r["best"] for r in rows]
        returns = "—" if name == "v2" else mean([r["returns"] for r in rows], 3)
        print(f"| {name} | {', '.join(map(str, chain(C7)))} | {k7['returns']} | {k7['moves']} | "
              f"{sum(b == 937 for b in ends[name])} | {returns} | {mean([r['moves'] for r in rows])} | "
              f"{mean([r['relative'] for r in rows])} |")
        sys.stdout.flush()
    print(f"\nv3 against v1 (shorter, longer, the same): {paired(ends['v3'], ends['v1'])}")
    print(f"v4 against v3: {paired(ends['v4'], ends['v3'])}\n")


def agent():
    print("## Table 10: the agent against the fixed forms on fri26, seeds 1-40\n")
    print("| Form | Reaches 937 | Mean final length | Returns per run | Relative certificates per run |")
    print("|---|---|---|---|---|")
    start = System(ROOT / "vns").definition["constants"]["START"]
    ends, firsts, total = {}, [], 0
    for name in ("v1", "v3", "v4"):
        rows = []
        for s in SEEDS:
            C, k = run("vns", s, FORMS[name])
            rows.append(k)
            if name == "v1":
                firsts.append(first_return(C, start))
                total += k["returns"]
        ends[name] = [r["best"] for r in rows]
        print(f"| {name} (fixed) | {sum(b == 937 for b in ends[name])} | {mean(ends[name])} | "
              f"{mean([r['returns'] for r in rows], 3)} | {mean([r['relative'] for r in rows])} |")
        sys.stdout.flush()
    for tolerance in (0, 2, 4):
        rows = [run("vns-adaptive", s, None, {"TOLERANCE": tolerance})[1] for s in SEEDS]
        ends[f"agent {tolerance}"] = [r["best"] for r in rows]
        print(f"| agent, tolerance {tolerance} | {sum(b == 937 for b in ends[f'agent {tolerance}'])} | "
              f"{mean(ends[f'agent {tolerance}'])} | {mean([r['returns'] for r in rows], 3)} | "
              f"{mean([r['relative'] for r in rows])} |")
        sys.stdout.flush()
    print(f"\nagent with tolerance 2 against fixed v1 (shorter, longer, the same): {paired(ends['agent 2'], ends['v1'])}")
    print(f"against fixed v3: {paired(ends['agent 2'], ends['v3'])}")
    print(f"fixed v1: {total} returns over seeds 1-40; the first return by round 1 in "
          f"{sum(f is not None and f <= 1 for f in firsts)} of {len(firsts)} runs\n")


def ftv38():
    print("## Table 8: the forms on ftv38 (optimum 1,530), R = 20\n")
    print("| Form | Seed 2: end | Seed 2: returns | Seeds 1-40: runs ending at 1,532 | mean gap | "
          "returns per run | moves per run | runs reaching 1,530 |")
    print("|---|---|---|---|---|---|---|---|")
    ends = {}
    for name in ("v1", "v2", "v3"):
        k2 = run("vns-atsp", 2, FORMS[name])[1]
        rows = [run("vns-atsp", s, FORMS[name])[1] for s in SEEDS]
        ends[name] = [r["best"] for r in rows]
        gap = lambda x: 1000 * (x - 1530) / 1530
        print(f"| {name} | {k2['best']} ({gap(k2['best']):.1f} ‰) | {k2['returns']} | "
              f"{sum(b == 1532 for b in ends[name])} | {mean([gap(b) for b in ends[name]], 1)} ‰ | "
              f"{mean([r['returns'] for r in rows], 1)} | {mean([r['moves'] for r in rows], 1)} | "
              f"{sum(b == 1530 for b in ends[name])} |")
        sys.stdout.flush()
    print(f"\nv3 against v1 (shorter, longer, the same): {paired(ends['v3'], ends['v1'])}")
    print(f"v3 against v2: {paired(ends['v3'], ends['v2'])}\n")


def tw():
    print("## Table 9: time windows and precedence on ftv38, draw seeds 1-20 (world seed 11), R = 10\n")
    print("| Problem | Form | Optimum reached | Mean gap | On time, world (of 20): mean (min) | "
          "On time, audit: mean (min-max) | Returns (of 30) | all feasible |")
    print("|---|---|---|---|---|---|---|---|")
    M = System(ROOT / "vns-tw").definition["constants"]["M"]
    for label, constants, optimum in (("with the chance constraint", None, 3492),
                                      ("deterministic (ALLOW = M)", {"ALLOW": M}, 3415)):
        ends, seed1, lengths = {}, {}, {}
        for name in ("v1", "v3"):
            rows = [run("vns-tw", s, FORMS[name], constants)[1] for s in range(1, 21)]
            ends[name] = [tuple(r["best"]) for r in rows]
            length = lengths[name] = [r["best"][3] for r in rows]
            audit = [r["audit_on_time"] for r in rows]
            world = [r["on_time"] for r in rows]
            seed1[name] = f"length {length[0]}, on time in {audit[0]} of the audit scenarios"
            print(f"| {label} | {name} | {sum(x == optimum for x in length)} | "
                  f"{mean([1000 * (x - optimum) / optimum for x in length], 1)} ‰ | {mean(world)} ({min(world)}) | "
                  f"{mean(audit, 1)} ({min(audit)}-{max(audit)}) | {mean([r['returns'] for r in rows])} | "
                  f"{all(r['feasible'] for r in rows)} |")
            sys.stdout.flush()
        print(f"\n{label}: v3 against v1 (shorter, longer, the same): {paired(ends['v3'], ends['v1'])}")
        print(f"mean length: v1 {mean(lengths['v1'], 1)}, v3 {mean(lengths['v3'], 1)}")
        print(f"seed 1: v1 {seed1['v1']}; v3 {seed1['v3']}\n")


def shares(table, rows, cols):
    """Two-way decomposition of the variance of table[(r, c)]: shares of rows, columns and interaction, in %
    to one decimal."""
    grand = statistics.mean(table.values())
    by_row = {r: statistics.mean(table[(r, c)] for c in cols) for r in rows}
    by_col = {c: statistics.mean(table[(r, c)] for r in rows) for c in cols}
    ss_row = len(cols) * sum((by_row[r] - grand) ** 2 for r in rows)
    ss_col = len(rows) * sum((by_col[c] - grand) ** 2 for c in cols)
    ss_int = sum((table[(r, c)] - by_row[r] - by_col[c] + grand) ** 2 for r in rows for c in cols)
    total = ss_row + ss_col + ss_int
    return tuple(round(100 * x / total, 1) for x in (ss_row, ss_col, ss_int))


DRAWS, WORLDS = range(1, 7), range(11, 17)          # the design of Section 7.2; world seed 11 is that of the instance


def variance():
    print("## Section 7.2: algorithm x environment, v3 with the chance constraint under the agenda\n")
    length, audit = {}, {}
    for d in DRAWS:
        for w in WORLDS:
            k = run("vns-tw", d, FORMS["v3"], world=w)[1]
            length[(d, w)], audit[(d, w)] = k["best"][3], k["audit_on_time"]
    print(f"draw seeds {list(DRAWS)} x world seeds {list(WORLDS)}")
    print("final length, shares of the variance (algorithm, environment, interaction): %.1f %%, %.1f %%, %.1f %%"
          % shares(length, DRAWS, WORLDS))
    print("audit scenarios on time, shares (algorithm, environment, interaction): %.1f %%, %.1f %%, %.1f %%"
          % shares(audit, DRAWS, WORLDS))
    print("The design is small, and the shares depend on the seeds chosen.\n")


if __name__ == "__main__":
    for what in sys.argv[1:] or ["fri26", "agent", "ftv38", "tw", "variance"]:
        globals()[what]()
