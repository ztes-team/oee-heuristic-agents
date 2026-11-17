"""Writes the 26 city abstractions of vns-hk and the lists of system.json that name them.

The cities differ only in their number I, so their specifications are written from one template:
ontology v1 (the step aims at the incumbent), ontology v2 (the step aims at the length of the
starting tour), and one criterion. Run it again after changing a template; the test
test_the_generator_reproduces_the_cities checks that the files in the directory are its output.

    python examples/vns-hk/generate.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
N = 26

ONTOLOGY_V1 = {
    "note": "[ω] the city's potential for the next round: a step of subgradient ascent of the Held–Karp bound, "
            "aimed at the incumbent of the coupled round; ⊥ while its 1-tree or that incumbent is missing, "
            "and once the bound proves the incumbent optimal",
    "inputs": {"context": ["me", "tree", "bounds", "incs"]},
    "returns": "City",
    "body": {"result": "city_step(I, N, R, SC, PATIENCE, HMAX, TMAX, me, tree, bounds, incs, None)"},
}
ONTOLOGY_V2 = {
    "note": "[ω] v2: the same step, aimed at the length of the starting tour instead of the incumbent; "
            "the incumbent still decides when the bound has proved it optimal",
    "inputs": {"context": ["me", "tree", "bounds", "incs"]},
    "returns": "City",
    "body": {"result": "city_step(I, N, R, SC, PATIENCE, HMAX, TMAX, me, tree, bounds, incs, TLEN)"},
}
CRITERION_V1 = {
    "note": "[τ] a potential for the round after the city's 1-tree that moves in the direction of the city's "
            "coordinate of the subgradient (up above degree 2, down at degree 1, unchanged at 2); how far is "
            "strategy, since every potential gives a valid bound (D2)",
    "inputs": {"context": ["me", "tree"], "candidate": {"name": "w", "type": "City"}},
    "body": {"result": "city_admissible(I, me, tree, w)"},
}


def spec_text(spec):
    lines = ["{"]
    items = list(spec.items())
    for k, (key, value) in enumerate(items):
        lines.append(f"  {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)}" + ("," if k < len(items) - 1 else ""))
    return "\n".join(lines) + "\n}\n"


def cities():
    """{relative path: text} of every file of the city abstractions."""
    out = {}
    for i in range(N):
        d = f"abstractions/city_{i}"
        out[f"{d}/abstraction.json"] = json.dumps({"constants": {"I": i}}) + "\n"
        out[f"{d}/ontology.v1.json"] = spec_text(ONTOLOGY_V1)
        out[f"{d}/ontology.v2.json"] = spec_text(ONTOLOGY_V2)
        out[f"{d}/criterion.v1.json"] = spec_text(CRITERION_V1)
    return out


def system_text(d):
    """system.json in a compact layout: one line per constant row, type, binding and plan step."""
    out = ["{"]
    keys = list(d)
    for n, key in enumerate(keys):
        v = d[key]
        end = "," if n < len(keys) - 1 else ""
        if isinstance(v, dict) and key in ("types", "constants", "bindings", "derived", "sources"):
            out.append(f"  {json.dumps(key)}: {{")
            inner = list(v.items())
            for m, (k2, v2) in enumerate(inner):
                e2 = "," if m < len(inner) - 1 else ""
                if key == "constants" and isinstance(v2, list) and v2 and isinstance(v2[0], list):
                    out.append(f"    {json.dumps(k2)}: [")
                    for r, row in enumerate(v2):
                        out.append("      " + json.dumps(row) + ("," if r < len(v2) - 1 else ""))
                    out.append("    ]" + e2)
                else:
                    out.append(f"    {json.dumps(k2)}: {json.dumps(v2, ensure_ascii=False)}{e2}")
            out.append("  }" + end)
        elif key == "plan":
            out.append(f"  {json.dumps(key)}: [")
            for m, step in enumerate(v):
                out.append("    " + json.dumps(step, ensure_ascii=False) + ("," if m < len(v) - 1 else ""))
            out.append("  ]" + end)
        else:
            out.append(f"  {json.dumps(key)}: {json.dumps(v, ensure_ascii=False)}{end}")
    return "\n".join(out) + "\n}\n"


def system():
    """system.json with the cities in the list of abstractions and in the binding pis."""
    d = json.loads((HERE / "system.json").read_text(encoding="utf8"))
    names = [f"city_{i}" for i in range(N)]
    others = [a for a in d["abstractions"] if not a.startswith("city_") and a not in ("tree", "proof")]
    d["abstractions"] = others + names + ["tree", "proof"]
    d["bindings"]["pis"]["from"] = names
    return system_text(d)


if __name__ == "__main__":
    for path, text in cities().items():
        (HERE / path).parent.mkdir(parents=True, exist_ok=True)
        (HERE / path).write_text(text, encoding="utf8")
    (HERE / "system.json").write_text(system(), encoding="utf8")
    print(f"wrote {N} cities and system.json")
