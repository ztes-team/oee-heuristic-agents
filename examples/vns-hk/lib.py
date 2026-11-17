# Helper functions shared by the specifications of the vns-hk system.
# A specification receives a copy of the helpers it uses, so its recorded form stays self-contained.
# No helper contains an unbounded loop: every loop runs over a fixed finite set (the cities, the
# 2-opt moves, the k moves of a shake). The loops of the method itself are not here; they are
# the interaction of the abstractions through the record.

def full(LOWER, N):
    """The symmetric distance matrix from its lower triangle, row by row (TSPLIB LOWER_DIAG_ROW)."""
    return [[LOWER[a][b] if b <= a else LOWER[b][a] for b in range(N)] for a in range(N)]


def tour_length(D, walk):
    """The length of the closed tour that visits the cities in the order of the walk."""
    return sum(D[walk[i - 1]][walk[i]] for i in range(len(walk)))


def valid(walk, N):
    """Every city exactly once."""
    return sorted(walk) == [c for c in range(N)]


def two_opt_moves(N):
    """The 2-opt neighborhood N1 in a fixed order: each move (a, b) removes the edges after
    positions a and b, which are not adjacent, and reverses the cities between them."""
    return [[a, b] for a in range(N) for b in range(a + 2, N) if not (a == 0 and b == N - 1)]


def change(D, MOVES, walk, m):
    """How much move m changes the length of the tour (negative: shorter), in O(1)."""
    a = MOVES[m][0]
    b = MOVES[m][1]
    n = len(walk)
    return (D[walk[a]][walk[b]] + D[walk[a + 1]][walk[(b + 1) % n]]
            - D[walk[a]][walk[a + 1]] - D[walk[b]][walk[(b + 1) % n]])


def reverse(MOVES, walk, m):
    """The tour after move m."""
    a = MOVES[m][0]
    b = MOVES[m][1]
    return [walk[c] for c in range(a + 1)] + [walk[c] for c in range(b, a, -1)] + [walk[c] for c in range(b + 1, len(walk))]


def first_improving(D, MOVES, walk):
    """[ω] The first move, in the fixed order, that shortens the tour; -1 if none does.

    The improving neighbors of a tour form a multivalued relation; taking the first in a fixed
    order resolves it to one candidate (D1) without a choice function."""
    for m in range(len(MOVES)):
        if change(D, MOVES, walk, m) < 0:
            return m
    return -1


def shaken(MOVES, walk, roll, k):
    """A tour in N_k of the given one: the first k moves of the recorded draw, applied in order."""
    x = [c for c in walk]
    for j in range(k):
        x = reverse(MOVES, x, roll[j])
    return x


def source_sync(START, D, prev, inc):
    """[ω] What a searcher shakes in its next round under synchronous cooperation: the incumbent of
    the round it has just finished, once every searcher has finished that round; before round 0
    the starting tour. None (wait) while the incumbent of that round is not yet recorded."""
    if prev["r"] < 0:
        return [[0, -1], START, tour_length(D, START)]
    if inc["r"] != prev["r"]:
        return None
    return [inc["src"], inc["walk"], inc["length"]]


def vns_step(I, S, R, KMAX, D, MOVES, prev, rolls, source):
    """[ω] The next step of searcher I: a shake, an improving move, or the certificate of a local
    optimum; None (⊥) while it must wait, and after the last round.

    After a certificate (or before round 0) the searcher shakes the tour that `source` names in
    the neighborhood N_k, with k by the rule of basic VNS: back to 1 when the tour to shake has
    improved since the previous round, otherwise the next neighborhood. After a shake or a move
    it descends: the first improving 2-opt move, or, if there is none, the certificate."""
    if prev["kind"] == "opt":
        r = prev["r"] + 1
        if r >= R or source is None or len(rolls) <= r * S + I - 1:
            return None
        if prev["r"] < 0:
            k = KMAX
        elif source[2] < prev["src_length"]:
            k = 1
        else:
            k = prev["k"] % KMAX + 1
        walk = shaken(MOVES, source[1], rolls[r * S + I - 1], k)
        return {"i": I, "r": r, "k": k, "kind": "shake", "src": [v for v in source[0]], "src_length": source[2],
                "m": -1, "walk": walk, "length": tour_length(D, walk)}
    m = first_improving(D, MOVES, prev["walk"])
    walk = prev["walk"] if m < 0 else reverse(MOVES, prev["walk"], m)
    return {"i": I, "r": prev["r"], "k": prev["k"], "kind": "opt" if m < 0 else "move", "src": prev["src"],
            "src_length": prev["src_length"], "m": m, "walk": walk, "length": tour_length(D, walk)}


def admissible(I, S, R, KMAX, N, START, D, MOVES, prev, rolls, opts, w):
    """[τ] A step of searcher I is admitted if it is a legitimate step of VNS from the previous one,
    whatever strategy chose it: a shake of the starting tour or of a certified local optimum,
    within N_k for some k ≤ KMAX, by the searcher's recorded draw of that round; an improving
    2-opt move; or a certificate that no 2-opt move shortens the tour."""
    if w["i"] != I or not valid(w["walk"], N) or tour_length(D, w["walk"]) != w["length"]:
        return False
    if w["kind"] == "shake":
        r = w["r"]
        if prev["kind"] != "opt" or r != prev["r"] + 1 or r >= R or w["k"] < 1 or w["k"] > KMAX or w["m"] != -1:
            return False
        if len(rolls) <= r * S + I - 1:
            return False
        source = START if w["src"] == [0, -1] else None
        for o in opts:
            if [o["i"], o["r"]] == w["src"]:
                source = o["walk"]
        if source is None or tour_length(D, source) != w["src_length"]:
            return False
        return w["walk"] == shaken(MOVES, source, rolls[r * S + I - 1], w["k"])
    if prev["kind"] == "opt" or [w["r"], w["k"], w["src"], w["src_length"]] != [prev["r"], prev["k"], prev["src"], prev["src_length"]]:
        return False
    if w["kind"] == "move":
        return 0 <= w["m"] < len(MOVES) and w["walk"] == reverse(MOVES, prev["walk"], w["m"]) and w["length"] < prev["length"]
    return (w["kind"] == "opt" and w["m"] == -1 and w["walk"] == prev["walk"]
            and all(change(D, MOVES, w["walk"], m) >= 0 for m in range(len(MOVES))))


def round_best(S, START, D, r, before, opts):
    """The incumbent after round r: the shortest of the previous incumbent and the S local optima of
    round r (among equals the earlier, then the searcher with the smaller number); None until
    every searcher has certified its local optimum of round r."""
    found = [o for o in opts if o["r"] == r]
    if len(found) < S:
        return None
    out = {"r": r, "src": [0, -1], "walk": START, "length": tour_length(D, START), "improved": False}
    if before["r"] >= 0:
        out = {"r": r, "src": before["src"], "walk": before["walk"], "length": before["length"], "improved": False}
    for i in range(1, S + 1):
        for o in found:
            if o["i"] == i and o["length"] < out["length"]:
                out = {"r": r, "src": [i, r], "walk": o["walk"], "length": o["length"], "improved": True}
    return out




# ---- the cities: a Held–Karp lower bound, computed by the potentials of the cities ----
#
# Lengths are scaled by SC so that every potential and every bound is an integer: ZTES has no
# floating point, and the bound is exact. With potentials π, every tour is a 1-tree in which every
# city has degree 2, so the weight of a minimum 1-tree under the weights SC·d(a, b) + π_a + π_b,
# minus 2·Σπ, is at most SC times the length of any tour: L(π) is a lower bound for every π
# [Held and Karp 1970]. Which π the cities choose is strategy; that the bound holds is not.

def weight(D, SC, pi, a, b):
    """The weight of the edge {a, b} under the potentials."""
    return SC * D[a][b] + pi[a] + pi[b]


def one_tree(D, N, SC, pi):
    """[ω] A minimum 1-tree under the potentials: a minimum spanning tree of the cities 1..N−1
    (Prim from city 1; among equal weights the smaller city, then the smaller endpoint) and the two
    cheapest edges at city 0 (among equal weights the smaller cities). Returns [edges, weight]."""
    inside = [c == 1 for c in range(N)]
    near = [[weight(D, SC, pi, 1, c), 1] for c in range(N)]
    edges = []
    total = 0
    for step in range(N - 2):
        v = -1
        for c in range(2, N):
            if not inside[c] and (v < 0 or near[c][0] < near[v][0]):
                v = c
        inside[v] = True
        total += near[v][0]
        edges.append(sorted([near[v][1], v]))
        for c in range(2, N):
            if not inside[c] and weight(D, SC, pi, v, c) < near[c][0]:
                near[c] = [weight(D, SC, pi, v, c), v]
    zero = sorted([[weight(D, SC, pi, 0, c), c] for c in range(1, N)])
    for e in range(2):
        total += zero[e][0]
        edges.append([0, zero[e][1]])
    return [sorted(edges), total]


def potentials(N, t, pis):
    """[C] The potentials of round t: 0 in round 0; in round t ≥ 1 those the cities recorded for t.
    None while a city has not recorded its potential of round t."""
    if t == 0:
        return [0 for c in range(N)]
    out = []
    for c in range(N):
        if (c, t) not in pis:
            return None
        out.append(pis[(c, t)])
    return out


def tree_step(D, N, SC, before, pis):
    """[ω] The minimum 1-tree of the next round, once every city has recorded its potential for it,
    with the bound it gives."""
    t = before["t"] + 1
    pi = potentials(N, t, pis)
    if pi is None:
        return None
    found = one_tree(D, N, SC, pi)
    return {"t": t, "edges": found[0], "bound": found[1] - 2 * sum(pi)}


def degree(edges, c):
    """The degree of city c in the edges."""
    return sum(1 for e in edges if e[0] == c or e[1] == c)


def spans(N, edges):
    """Whether the edges are a 1-tree on N cities: N edges, two of them at city 0, and the others a
    spanning tree of the cities 1..N−1 (N − 2 edges that join them all)."""
    if len(edges) != N or degree(edges, 0) != 2:
        return False
    part = [c for c in range(N)]
    joined = 0
    for e in edges:
        if e[0] != 0:
            a = part[e[0]]
            b = part[e[1]]
            if a == b:
                return False
            for c in range(N):
                if part[c] == b:
                    part[c] = a
            joined += 1
    return joined == N - 2


def tree_admissible(D, N, SC, before, pis, w):
    """[τ] A 1-tree of the next round is admitted if it spans the cities, if no 1-tree is lighter
    under the potentials the cities recorded for that round, and if its bound is its weight
    minus 2·Σπ. Any minimum 1-tree is admitted, not only the one Prim finds (D2)."""
    pi = potentials(N, w["t"], pis)
    if w["t"] != before["t"] + 1 or pi is None or not spans(N, w["edges"]):
        return False
    total = sum(weight(D, SC, pi, e[0], e[1]) for e in w["edges"])
    return total == one_tree(D, N, SC, pi)[1] and w["bound"] == total - 2 * sum(pi)


def ceil_div(a, b):
    """⌈a / b⌉ for integers, b > 0."""
    return -((-a) // b)


def strategy(bounds, t, PATIENCE):
    """[C] The state of the ascent after round t, read from the recorded bounds: the number h of
    halvings of the step (one whenever PATIENCE rounds in a row have not raised the best bound),
    and the best bound."""
    h = 0
    stall = 0
    best = bounds[0]
    for s in range(1, t + 1):
        if bounds[s] > best:
            best = bounds[s]
            stall = 0
        else:
            stall += 1
            if stall >= PATIENCE:
                h += 1
                stall = 0
    return [h, best]


def proves(SC, best, length):
    """The bound proves a tour of this length optimal: no tour is shorter than ⌈best / SC⌉."""
    return ceil_div(best, SC) >= length


def city_step(I, N, R, SC, PATIENCE, HMAX, TMAX, me, tree, bounds, incs, aim):
    """[ω] City I's potential for the next round, after the 1-tree of its round: a step of
    subgradient ascent of the bound. Its own coordinate of the subgradient is deg_I − 2: a city of
    degree above two raises its potential, a leaf lowers it. The size of the step is the same for
    every city, (2 / 2^h)·(SC·U − L) / Σ(deg − 2)² [Held, Wolfe and Crowder 1974], where U is the
    length the step aims at: the incumbent of the coupled round under v1 (aim None), the fixed
    length aim under v2. Round t is coupled to the incumbent of round min(t, R − 1) of the
    searchers. None while the 1-tree or that incumbent is missing; after the bound has proved that
    incumbent optimal; when the 1-tree is a tour; and when the step is exhausted."""
    t = me["t"]
    if tree["t"] != t or min(t, R - 1) not in incs:
        return None
    length = incs[min(t, R - 1)]
    state = strategy(bounds, t, PATIENCE)
    if proves(SC, state[1], length) or t + 1 >= TMAX or state[0] > HMAX:
        return None
    gg = sum((degree(tree["edges"], c) - 2) ** 2 for c in range(N))
    if gg == 0:
        return None
    target = length if aim is None else aim
    step = max(1, (2 * (SC * target - tree["bound"])) // (2 ** state[0] * gg))
    return {"i": I, "t": t + 1, "pi": me["pi"] + step * (degree(tree["edges"], I) - 2)}


def city_admissible(I, me, tree, w):
    """[τ] A potential of city I for the next round is admitted if it follows the 1-tree of the
    city's round and moves in the direction of its own coordinate of the subgradient: up if its
    degree was above 2, down if it was 1, unchanged if it was 2. How far is strategy (D2): every
    potential gives a valid bound."""
    if w["i"] != I or w["t"] != me["t"] + 1 or tree["t"] != me["t"]:
        return False
    d = degree(tree["edges"], I) - 2
    move = w["pi"] - me["pi"]
    return (d > 0 and move > 0) or (d < 0 and move < 0) or (d == 0 and move == 0)


def proof_step(R, SC, bounds, incs, proofs):
    """[ω] The first round t whose best bound so far proves the incumbent of the coupled round
    min(t, R − 1) optimal. None while a round cannot be decided (its incumbent is missing) and while
    no round proves it; once recorded, the proof is not repeated."""
    if proofs > 0:
        return None
    best = None
    for t in range(len(bounds)):
        if min(t, R - 1) not in incs:
            return None
        if best is None or bounds[t] > best:
            best = bounds[t]
        if proves(SC, best, incs[min(t, R - 1)]):
            return {"t": t, "r": min(t, R - 1), "bound": best, "length": incs[min(t, R - 1)]}
    return None


def proof_admissible(R, SC, bounds, incs, proofs, w):
    """[τ] A proof is admitted once: the bound it cites is the best recorded up to its round, the
    length is that of the incumbent of the coupled round, and the bound proves it. Since every
    recorded bound is the weight of an admitted minimum 1-tree, no tour is shorter: the incumbent
    is optimal, and the proof holds in every extension of the record (an upper set)."""
    t = w["t"]
    if proofs > 0 or t < 0 or t >= len(bounds) or w["r"] != min(t, R - 1) or w["r"] not in incs:
        return False
    best = max(bounds[s] for s in range(t + 1))
    return w["bound"] == best and w["length"] == incs[w["r"]] and proves(SC, best, w["length"])


def measure(SC, OPT, bests, bounds, proof, profile, profiles):
    """The indicators of the system (KPI abstraction), all read from the record."""
    last = bests[-1]
    found = {"bound_rounds": len(bounds), "bound": max(bounds[t] for t in range(len(bounds))),
             "proved_at": -1, "proved_in_round": -1}
    if proof:
        found["proved_at"] = proof[0]["t"]
        found["proved_in_round"] = proof[0]["r"]
    groups = {"search": "search_", "city": "city_", "tree": "tree", "incumbent": "incumbent"}
    counts = {}
    for g in groups:
        rows = [x for x in profile if x["abstraction"].startswith(groups[g])]
        counts[g] = [sum(x["I"] for x in rows), sum(x["A"] for x in rows), sum(x["U"] for x in rows)]
    return {"profile": profiles, "rounds": len(bests), "best": last["length"], "found_by": last["src"],
            "optimum": OPT, "bound_rounds": found["bound_rounds"], "bound": found["bound"],
            "bound_ceiling": ceil_div(found["bound"], SC), "proved_at": found["proved_at"],
            "proved_in_round": found["proved_in_round"], "invocations": [counts[g][0] for g in groups],
            "admitted": [counts[g][1] for g in groups], "pending": [counts[g][2] for g in groups]}
