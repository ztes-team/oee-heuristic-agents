"""The ksat system of a CNF formula, in the standard form of a ZTES system.

Every clause of the formula is an abstraction (c1, c2, ...), with the same specifications and its
own constants CLAUSE and NAME. Beside them are round, decide, learn, adapt and verdict
(examples/ksat/DESIGN.md). The helpers are those of examples/ksat/lib.py.

    python scripts/ksat_system.py FORMULA.cnf DIRECTORY [--after K] [--name NAME] [--title TITLE]

writes the system as DIRECTORY, with the expected end of the run under the agenda ("expect"), so
that `python -m ztes run DIRECTORY` checks it. The committed instances were written so:

    python scripts/ksat_system.py examples/ksat/php43.cnf examples/ksat/php43 --name ksat-php43
    python scripts/ksat_system.py examples/ksat/random20.cnf examples/ksat/random20 --name ksat-random20

The module also gives the formulas of the committed instances (pigeonhole, random_kcnf), DIMACS
reading and writing, and native(): the same helpers called in a plain loop, round by round,
without ZTES, which gives the frames, decisions and learned clauses that a record must contain.
"""
import argparse
import importlib.util
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "examples" / "ksat" / "lib.py"
AFTER = 3                                      # adapt changes the policy once this many clauses are learned

TYPES = {
    "Step": {"record": {"literal": "integer", "level": "integer", "reason": "text"}},
    "Frame": {"record": {"epoch": "integer", "round": "integer", "level": "integer",
                         "trail": {"list": "Step"}, "conflicts": {"list": "text"},
                         "votes": {"list": "text"}, "quiet": "boolean", "total": "boolean"}},
    "Speech": {"record": {"clause": "text", "round": "integer", "kind": "text", "literal": "integer"}},
    "Decision": {"record": {"round": "integer", "literals": {"list": "integer"}}},
    "Resolution": {"record": {"clause": "text", "literal": "integer"}},
    "Learned": {"record": {"round": "integer", "name": "text", "start": "text",
                           "chain": {"list": "Resolution"}, "literals": {"list": "integer"},
                           "level": "integer", "specifications": {"list": "specification"}}},
    "Adaptation": {"record": {"conflicts": "integer", "specifications": {"list": "specification"}}},
    "Verdict": {"record": {"sat": "boolean", "model": {"list": "integer"}}},
}


# ---- formulas ----

def read_dimacs(text):
    """(variables, formula) of a DIMACS CNF text: the variables 1..n of the header "p cnf n m", and
    the clauses, each the literals before its terminating 0. Comment lines start with c."""
    n, numbers = None, []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("c") or line.startswith("%"):
            continue
        if line.startswith("p"):
            _, kind, n, _ = line.split()
            assert kind == "cnf", "only CNF formulas"
            n = int(n)
            continue
        numbers += [int(x) for x in line.split()]
    assert n is not None, "no header p cnf n m"
    formula, clause = [], []
    for x in numbers:
        if x == 0:
            formula.append(clause)
            clause = []
        else:
            assert abs(x) <= n, f"literal {x} beyond the {n} variables of the header"
            clause.append(x)
    assert not clause, "the last clause is not terminated by 0"
    return list(range(1, n + 1)), formula


def write_dimacs(variables, formula, comment=None):
    """The DIMACS CNF text of a formula over the variables 1..n."""
    assert variables == list(range(1, len(variables) + 1)), "DIMACS numbers the variables 1..n"
    head = [f"c {line}" for line in (comment or "").splitlines()]
    body = [" ".join(str(literal) for literal in clause + [0]) for clause in formula]
    return "\n".join(head + [f"p cnf {len(variables)} {len(formula)}"] + body) + "\n"


def pigeonhole(pigeons, holes):
    """PHP(pigeons, holes): every pigeon sits in a hole, no two pigeons share one. Variable
    i·holes + j + 1 says that pigeon i sits in hole j. Unsatisfiable when pigeons > holes."""
    var = lambda i, j: i * holes + j + 1
    formula = [[var(i, j) for j in range(holes)] for i in range(pigeons)]
    formula += [[-var(i, j), -var(k, j)] for j in range(holes) for i in range(pigeons) for k in range(i + 1, pigeons)]
    return list(range(1, pigeons * holes + 1)), formula


def random_kcnf(n, m, k, seed):
    """A uniform random k-CNF formula: m clauses, each of k distinct variables of 1..n, each literal
    negative with probability 1/2, drawn by random.Random(seed)."""
    rnd = random.Random(seed)
    variables = list(range(1, n + 1))
    return variables, [[var if rnd.random() < 0.5 else -var for var in rnd.sample(variables, k)] for _ in range(m)]


# ---- the system ----

def definition(variables, formula, name="ksat", title=None, after=AFTER):
    """The definition of the ksat system of a formula, in the form authoring.read_directory gives
    it: System.from_dict runs it, System.save stores it as a directory."""
    names = [f"c{i + 1}" for i in range(len(formula))]
    clauses = dict(zip(names, formula))
    bindings = {
        "frame": {"from": "round", "select": "all", "window": 1, "type": "Frame",
                  "note": "the latest frame, as a list of at most one (latest() reads it)"},
        "mine": {"from": "$self", "select": "all", "window": 1, "type": "Speech",
                 "note": "the last speech of this clause"},
        "said": {"from": names, "select": "map", "type": "Speech", "key": "[x['round'], x['clause']]",
                 "note": "every speech by (round, clause); a learned clause extends the lineages read"},
        "decision": {"from": "decide", "select": "all", "window": 1, "type": "Decision"},
        "last_learned": {"from": "learn", "select": "all", "window": 1, "type": "Learned"},
        "learned": {"from": "learn", "select": "map", "type": "Learned", "key": "x['name']", "value": "x['literals']",
                    "note": "name → literals of every learned clause, in the order of learning"},
        "learn_count": {"from": "learn", "select": "count"},
        "switches": {"from": "adapt", "select": "count"},
        "verdicts": {"from": "verdict", "select": "count"},
    }
    specs = {}
    for n in names:
        specs[f"{n}/criterion.v1"] = {
            "note": "τᵢ: what the clause says about the frame is true of the clause",
            "inputs": {"context": ["frame", "mine"], "candidate": {"name": "w", "type": "Speech"}},
            "body": {"result": "check_speech(NAME, CLAUSE, latest(frame), latest(mine), w)"}}
        specs[f"{n}/ontology.v1"] = {
            "note": "the unit, conflict or vote of the clause on the latest frame",
            "inputs": {"context": ["frame", "mine"]}, "returns": "Speech",
            "body": {"result": "propose_speech(NAME, CLAUSE, latest(frame), latest(mine))"}}
    round_context = ["frame", "said", "decision", "last_learned", "learned"]
    next_frame = "next_frame(NAMES, CLAUSES, VARIABLES, latest(frame), said, latest(decision), latest(last_learned), learned)"
    specs["round/criterion.v1"] = {
        "note": "the frame is the function of the record that defines it: round chooses nothing",
        "inputs": {"context": round_context, "candidate": {"name": "w", "type": "Frame"}},
        "body": {"result": f"w == {next_frame}"}}
    specs["round/ontology.v1"] = {
        "note": "the next frame once every expected speech, decision or learned clause is recorded",
        "inputs": {"context": round_context}, "returns": "Frame",
        "body": {"result": next_frame}}
    specs["decide/criterion.v1"] = {
        "note": "any consistent decision on unassigned variables when one is due (D2)",
        "inputs": {"context": ["frame", "decision"], "candidate": {"name": "w", "type": "Decision"}},
        "body": {"result": "check_decision(VARIABLES, latest(frame), latest(decision), w)"}}
    specs["decide/ontology.v1"] = {
        "note": "policy v1 by occurrence; waits while a change of policy is due and not decided",
        "inputs": {"context": ["frame", "decision", "learned", "learn_count", "switches"]}, "returns": "Decision",
        "body": {"result": "propose_decision(NAMES, CLAUSES, VARIABLES, latest(frame), latest(decision), learned,"
                           " learn_count >= AFTER and not switches)"}}
    specs["decide/ontology.v2"] = {
        "note": "policy v2 by conflict activity, carried by adapt",
        "inputs": {"context": ["frame", "decision", "learned"]}, "returns": "Decision",
        "body": {"result": "propose_decision_by_activity(NAMES, CLAUSES, VARIABLES, latest(frame), latest(decision), learned)"}}
    templates = {"$specifications": ["c1/criterion.v1", "c1/ontology.v1", "round/criterion.v1", "round/ontology.v1"]}
    learn_context = ["frame", "last_learned", "learned", "learn_count"]
    specs["learn/criterion.v1"] = {
        "note": "a resolution derivation from known clauses, carrying exactly its abstraction and round",
        "constants": {"TEMPLATES": templates},
        "inputs": {"context": learn_context, "candidate": {"name": "w", "type": "Learned"}},
        "body": {"result": "check_learned(NAMES, CLAUSES, latest(frame), latest(last_learned), learned, learn_count, TEMPLATES, w)"}}
    specs["learn/ontology.v1"] = {
        "note": "1-UIP analysis; a non-empty clause brings in its abstraction and the next version of round",
        "constants": {"TEMPLATES": templates},
        "inputs": {"context": learn_context}, "returns": "Learned",
        "body": {"result": "propose_learned(NAMES, CLAUSES, latest(frame), latest(last_learned), learned, learn_count, TEMPLATES)"}}
    upgrade = {"$specifications": ["decide/ontology.v2"]}
    specs["adapt/criterion.v1"] = {
        "note": "the authority over the policy: once, on the evidence of AFTER admitted conflicts",
        "constants": {"UPGRADE": upgrade},
        "inputs": {"context": ["learn_count", "switches"], "candidate": {"name": "w", "type": "Adaptation"}},
        "body": {"result": "check_switch(AFTER, learn_count, switches, UPGRADE, w)"}}
    specs["adapt/ontology.v1"] = {
        "note": "carry decide/ontology.v2 once AFTER clauses are learned",
        "constants": {"UPGRADE": upgrade},
        "inputs": {"context": ["learn_count", "switches"]}, "returns": "Adaptation",
        "body": {"result": "propose_switch(AFTER, learn_count, switches, UPGRADE)"}}
    specs["verdict/criterion.v1"] = {
        "note": "SAT: every clause of the formula voted for a model; UNSAT: the empty clause was learned",
        "inputs": {"context": ["frame", "learned", "verdicts"], "candidate": {"name": "w", "type": "Verdict"}},
        "body": {"result": "check_verdict(FORMULA, VARIABLES, NAMES, latest(frame), learned, verdicts, w)"}}
    specs["verdict/ontology.v1"] = {
        "note": "the consensus or the refutation, once",
        "inputs": {"context": ["frame", "learned", "verdicts"]}, "returns": "Verdict",
        "body": {"result": "propose_verdict(latest(frame), learned, verdicts)"}}
    return {
        "system": name,
        "title": title or f"{len(variables)} variables, {len(formula)} clauses as abstractions",
        "abstractions": ["round", "decide", "learn", "adapt", "verdict"] + names,
        "constants": {"VARIABLES": variables, "FORMULA": formula, "NAMES": names, "CLAUSES": clauses,
                      "AFTER": after},
        "types": TYPES,
        "bindings": bindings,
        "library": LIB.read_text(encoding="utf8"),
        "declarations": {n: {"constants": {"CLAUSE": c, "NAME": n}} for n, c in clauses.items()},
        "specifications": specs,
        "admission_limit": 1_000_000,
    }


def expected_end(definition_):
    """The expected end of the run of a definition under the agenda: its number of events, the
    state of every abstraction and the verdict. By Theorem K it holds under every schedule."""
    from ztes.substrate.store import MemoryStore, read
    from ztes.system.system import System
    system, store = System.from_dict(definition_), MemoryStore()
    system.run(store, log=lambda *_: None)
    C = list(read(store))
    verdict = [e["payload"] for e in C if e["coord"]["kind"] == "exec" and e["coord"]["abstraction"] == "verdict"]
    return {"events": len(C), "states": system.states(C), "values": {"verdict": verdict}}


DESIGN = """# {name}

Generated by `scripts/ksat_system.py` from [`../{cnf}`](../{cnf}): {title}.
The design of every ksat system is in [`../DESIGN.md`](../DESIGN.md).
"""


def save(cnf, directory, name, title=None, after=AFTER):
    """Write the system of a DIMACS file as a directory, with its expected end; returns the path."""
    from ztes.system.system import System
    variables, formula = read_dimacs(Path(cnf).read_text(encoding="utf8"))
    d = definition(variables, formula, name, title, after)
    d["expect"] = expected_end(d)
    design = DESIGN.format(name=name, cnf=Path(cnf).name, title=d["title"])
    System.from_dict(d).save(directory, design=design)
    return Path(directory)


# ---- the same relations, executed natively ----

def helpers():
    """The helpers of examples/ksat/lib.py as a module."""
    spec = importlib.util.spec_from_file_location("ksat_lib", LIB)
    lib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lib)
    return lib


def native(variables, formula, after=AFTER, limit=10**7):
    """Execute the relations of the ksat system natively: the helpers of lib.py called in a plain
    loop, one round at a time, in the order in which the abstractions of the system wait for each
    other (every speech about a frame, the decision or the learned clause, then the next frame).
    The change of policy is made as soon as `after` clauses are learned, as decide waits for adapt.
    Returns the frames, the decisions, the learned clauses (without what they carry) and the
    verdict."""
    lib = helpers()
    names = [f"c{i + 1}" for i in range(len(formula))]
    clauses = dict(zip(names, formula))
    learned, said, frames, decisions, learns = {}, {}, [], [], []
    stub = [{"inputs": {"context": {}}, "constants": {}}] * 4           # carried specifications are not computed
    frame = lib.next_frame(names, clauses, variables, None, said, None, None, learned)
    for _ in range(limit):
        frames.append(frame)
        verdict = lib.propose_verdict(frame, learned, 0)
        if verdict is not None:
            return {"frames": frames, "decisions": decisions, "learned": learns, "verdict": verdict}
        table = lib.clause_table(clauses, learned)
        for n in lib.clause_names(names, learned):
            told = lib.speech(n, table[n], frame)
            if told is not None:
                said[(told["round"], n)] = told
        last = decisions[-1] if decisions else None
        if len(learns) >= after:
            decision = lib.propose_decision_by_activity(names, clauses, variables, frame, last, learned)
        else:
            decision = lib.propose_decision(names, clauses, variables, frame, last, learned, False)
        if decision is not None:
            decisions.append(decision)
        new = lib.propose_learned(names, clauses, frame, learns[-1] if learns else None, learned, len(learns), stub)
        if new is not None:
            learns.append({k: v for k, v in new.items() if k != "specifications"})
            learned[new["name"]] = new["literals"]
            verdict = lib.propose_verdict(frame, learned, 0)
            if verdict is not None:
                return {"frames": frames, "decisions": decisions, "learned": learns, "verdict": verdict}
        frame = lib.next_frame(names, clauses, variables, frame, said, decisions[-1] if decisions else None,
                               learns[-1] if learns else None, learned)
        assert frame is not None, "no next frame and no verdict"
    raise RuntimeError(f"no verdict within {limit} rounds")


def main(argv=None):
    p = argparse.ArgumentParser(description="Write the ksat system of a DIMACS CNF formula as a directory.")
    p.add_argument("cnf")
    p.add_argument("directory")
    p.add_argument("--name", default="ksat")
    p.add_argument("--title")
    p.add_argument("--after", type=int, default=AFTER, help="learned clauses before the change of policy")
    a = p.parse_args(argv)
    print(save(a.cnf, a.directory, a.name, a.title, a.after))


if __name__ == "__main__":
    sys.exit(main())
