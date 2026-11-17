"""The KPI profiles of the lifted VNS forms (Table 2 of the paper).

Each form is run once under the agenda, with the seeds of its system.json, and its profile is read
from the record: the profile abstraction of ZTES gives, per abstraction, the invocations I, the
admitted A, the Pending U and the refused F, so N_c = A + F and N_p = U. Two observables are
computed here over the record, after the run and without changing it:

  G    the possibilities of every descent step: the criterion admits any move that lowers the value
       (D2), so a move or a repair has as many possibilities as its tour has improving moves, and a
       certificate has one. The neighborhoods are enumerated in full (299 moves on fri26, 9,139 on
       ftv38); for the time windows the value of a move is lib.lowers, which the tests of vns-tw
       check against a full evaluation.
  N_u  the shakes after the first round: each starts from a certified local optimum in the record.

    OC = 1 - (descent steps) / G      AC = F / (A + F)      HRR = N_u / N_c
    DRR = U / I, for the three searchers together and for the incumbent

    python scripts/profiles.py                 # every form, about two minutes
    python scripts/profiles.py vns vns-atsp    # some systems only
"""
import json
import sys
from pathlib import Path

from ztes.substrate.store import MemoryStore, read
from ztes.system.system import System

ROOT = Path(__file__).resolve().parent.parent / "examples"
quiet = lambda *_: None


def form(*keys):
    govern = [f"search_{i}/{key}" for key in keys for i in (1, 2, 3)]
    return [{"phase": 1}, {"phase": 2}, {"govern": govern}, {"phase": 3}, {"kpi": True}]


FORMS = {
    "vns": [("v1 synchronous", None), ("v2 asynchronous", form("ontology.v2")),
            ("v3 asymmetric", form("ontology.v2", "ontology.v3")),
            ("v4 relative certificate", form("ontology.v2", "ontology.v3", "criterion.v2", "ontology.v4"))],
    "vns-atsp": [("v1", None), ("v3", form("ontology.v2", "ontology.v3"))],
    "vns-tw": [("v1", None), ("v3", form("ontology.v2", "ontology.v3"))],
}
NAMES = {"vns": "fri26", "vns-atsp": "ftv38", "vns-tw": "ftv38, windows and precedence"}


def constants(system):
    return json.loads((ROOT / system / "system.json").read_text(encoding="utf8"))["constants"]


def improving_2opt(c):
    """fri26: the number of 2-opt moves that shorten a tour."""
    n, low = c["N"], c["LOWER"]
    d = [[low[a][b] if b <= a else low[b][a] for b in range(n)] for a in range(n)]

    def count(w):
        out = 0
        for i in range(n - 1):
            for j in range(i + 2, n):
                if i == 0 and j == n - 1:
                    continue
                a, b, e, f = w[i], w[i + 1], w[j], w[(j + 1) % n]
                out += d[a][e] + d[b][f] < d[a][b] + d[e][f]
        return out
    return count


def improving_exchange(c):
    """ftv38: the number of exchanges of two adjacent segments that shorten a tour."""
    n, d = c["N"], c["D"]
    moves = [(i, j, k) for i in range(n) for j in range(i + 1, n) for k in range(j + 1, n)]

    def count(w):
        out = 0
        for i, j, k in moves:
            after = w[(k + 1) % n]
            out += (d[w[i]][w[j + 1]] + d[w[k]][w[i + 1]] + d[w[j]][after]
                    < d[w[i]][w[i + 1]] + d[w[j]][w[j + 1]] + d[w[k]][after])
        return out
    return count


def lowering_tw(c, C):
    """vns-tw: the number of moves that lower the lexicographic value, on the recorded scenarios."""
    lib = {}
    exec((ROOT / "vns-tw" / "lib.py").read_text(encoding="utf8"), lib)
    worlds = [e["payload"] for e in C if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == "world"]
    scen = lib["scenarios"](c["D"], worlds, c["N"], c["RHO"])
    moves = lib["segment_moves"](c["N"])

    def count(w):
        st = lib["state"](c["D"], c["A"], c["B"], c["PAIRS"], scen, w)
        v = lib["value"](st, c["ALLOW"])
        return sum(lib["lowers"](c["D"], c["A"], c["B"], c["PAIRS"], scen, c["ALLOW"], moves, w, st, m, v)
                   for m in range(len(moves)))
    return count


def profile(system, plan):
    s, store = System(ROOT / system), MemoryStore()
    s.run(store, log=quiet, plan=plan)
    C = list(read(store))
    ex = [e for e in C if e["coord"]["kind"] == "exec"]
    rows = {p["abstraction"]: p for p in [e["payload"] for e in ex if e["coord"]["abstraction"] == "profile"][0]}
    srch = [rows[f"search_{i}"] for i in (1, 2, 3)]
    I, A, U, F = (sum(p[k] for p in srch) for k in "IAUF")
    inc = rows["incumbent"]
    c = constants(system)
    count = {"vns": lambda: improving_2opt(c), "vns-atsp": lambda: improving_exchange(c),
             "vns-tw": lambda: lowering_tw(c, C)}[system]()
    G = steps = reuse = 0
    for i in (1, 2, 3):
        xs = [e["payload"] for e in ex if e["coord"]["abstraction"] == f"search_{i}"]
        for prev, x in zip(xs, xs[1:]):
            if x["kind"] == "opt":
                G, steps = G + 1, steps + 1
            elif x["kind"] in ("move", "repair"):
                G, steps = G + count(prev["walk"]), steps + 1
        reuse += sum(1 for x in xs if x["kind"] == "shake" and x["r"] > 0)
    return {"N_c": A + F, "N_p": U, "AC": F / (A + F), "OC": 1 - steps / G, "HRR": reuse / (A + F),
            "DRR": U / I, "DRR_incumbent": inc["U"] / inc["I"]}


def main(systems):
    print("| System | Form | N_c | N_p | AC | OC | HRR | DRR searchers | DRR incumbent |")
    print("|---|---|---|---|---|---|---|---|---|")
    for system in systems:
        for name, plan in FORMS[system]:
            p = profile(system, plan)
            print(f"| {NAMES[system]} | {name} | {p['N_c']:,} | {p['N_p']} | {p['AC']:g} | {p['OC']:.3f} "
                  f"| {100 * p['HRR']:.1f} % | {100 * p['DRR']:.1f} % | {100 * p['DRR_incumbent']:.1f} % |",
                  flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or list(FORMS))
