# Helper functions shared by the specifications of the vns system.
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


def source_async(START, D, prev, opts):
    """[ω] What a searcher shakes in its next round under asynchronous cooperation: the shortest
    local optimum certified so far by any searcher, as it stands now; before round 0 the starting tour."""
    best = [[0, -1], START, tour_length(D, START)]
    if prev["r"] < 0:
        return best
    for o in opts:
        if o["length"] < best[2]:
            best = [[o["i"], o["r"]], o["walk"], o["length"]]
    return best


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


def measure(KMAX, OPT, steps, bests, profile, profiles):
    """The indicators of the search (KPI abstraction), all read from the record.

    shakes_by_k and better_by_k count, for each neighborhood N_k, the shakes made in it and the
    local optima reached from them that are shorter than the tour shaken; round 0, which shakes
    the starting tour, is initialization and is not counted."""
    shakes_by_k = [0 for k in range(KMAX)]
    better_by_k = [0 for k in range(KMAX)]
    moves = 0
    optima = 0
    for x in steps:
        if x["kind"] == "move":
            moves += 1
        elif x["kind"] == "opt":
            optima += 1
        if x["r"] > 0 and x["kind"] == "shake":
            shakes_by_k[x["k"] - 1] += 1
        if x["r"] > 0 and x["kind"] == "opt" and x["length"] < x["src_length"]:
            better_by_k[x["k"] - 1] += 1
    last = bests[-1]
    searchers = [x for x in profile if x["abstraction"].startswith("search_")]
    return {"profile": profiles, "rounds": len(bests), "moves": moves, "optima": optima,
            "shakes_by_k": shakes_by_k, "better_by_k": better_by_k, "best": last["length"], "found_by": last["src"],
            "optimum": OPT, "gap_permille": (last["length"] - OPT) * 1000 // OPT,
            "search_invocations": sum(x["I"] for x in searchers), "search_not_yet": sum(x["U"] for x in searchers)}
