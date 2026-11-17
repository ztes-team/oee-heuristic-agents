"""How the instance of vns-tw was made (not executed by ZTES; tests/test_vns_tw.py checks that it
reproduces the constants of system.json).

The travel times are those of ftv38 (TSPLIB), the matrix D of system.json. The windows follow
Dumas, Desrosiers, Gelinas and Solomon (1995): a random reference tour from the depot 0, and for
each city a window around its arrival time on that tour, the two half-widths uniform in [0, W/2];
the depot's window closes at most W/2 after the return. Precedence: P random pairs [p, q] with p
before q on the reference tour whose windows overlap, so that the windows alone do not imply them.
The reference tour is feasible by construction; it is not the starting tour of the search."""
import json
import random
from pathlib import Path


def generate(D, W=1500, P=10, seed=1):
    n = len(D)
    rnd = random.Random(seed)
    ref = [0] + rnd.sample(range(1, n), n - 1)
    t, at = 0, {0: 0}
    for k in range(1, n):
        t += D[ref[k - 1]][ref[k]]
        at[ref[k]] = t
    back = t + D[ref[-1]][0]
    A, B = [0] * n, [0] * n
    for c in range(1, n):
        A[c] = max(0, at[c] - rnd.randint(0, W // 2))
        B[c] = at[c] + rnd.randint(0, W // 2)
    A[0], B[0] = 0, back + rnd.randint(0, W // 2)
    pos = {c: k for k, c in enumerate(ref)}
    cand = [(p, q) for p in range(1, n) for q in range(1, n) if pos[p] < pos[q] and A[q] < B[p]]
    rnd.shuffle(cand)
    return A, B, sorted([list(pq) for pq in cand[:P]]), ref


if __name__ == "__main__":
    D = json.loads((Path(__file__).parent.parent / "vns-atsp" / "system.json").read_text())["constants"]["D"]
    A, B, PAIRS, ref = generate(D)
    print(json.dumps({"A": A, "B": B, "PAIRS": PAIRS}))
