# Helper functions shared by the specifications of the vns-atsp system.
# A specification receives a copy of the helpers it uses, so its recorded form stays self-contained.
# No helper contains an unbounded loop: every loop runs over a fixed finite set (the cities, the
# moves of the neighborhood, the k moves of a shake). The loops of the method itself are not here;
# they are the interaction of the abstractions through the record.
#
# The instance is asymmetric: the distance from a to b need not be that from b to a, so a tour and
# the same cycle traversed backwards have different lengths. 2-opt reverses a segment and with it
# every arc inside it; the neighborhood here exchanges two adjacent segments instead, which keeps
# the direction of every arc it does not cut (3-opt without reversal).

def tour_length(D, walk):
    """The length of the closed tour that visits the cities in the order of the walk."""
    return sum(D[walk[i - 1]][walk[i]] for i in range(len(walk)))


def valid(walk, N):
    """Every city exactly once."""
    return sorted(walk) == [c for c in range(N)]


def segment_moves(N):
    """The neighborhood N1 in a fixed order: each move (i, j, k) cuts the tour after positions i, j
    and k and exchanges the two segments between them, A B C D → A C B D. The first city never
    moves, and every arc that is not cut keeps its direction."""
    return [[i, j, k] for i in range(N) for j in range(i + 1, N) for k in range(j + 1, N)]


def change(D, MOVES, walk, m):
    """How much move m changes the length of the tour (negative: shorter), in O(1): three arcs
    removed, three added, each in its own direction."""
    i = MOVES[m][0]
    j = MOVES[m][1]
    k = MOVES[m][2]
    after = walk[(k + 1) % len(walk)]
    return (D[walk[i]][walk[j + 1]] + D[walk[k]][walk[i + 1]] + D[walk[j]][after]
            - D[walk[i]][walk[i + 1]] - D[walk[j]][walk[j + 1]] - D[walk[k]][after])


def exchange(MOVES, walk, m):
    """The tour after move m."""
    i = MOVES[m][0]
    j = MOVES[m][1]
    k = MOVES[m][2]
    return ([walk[c] for c in range(i + 1)] + [walk[c] for c in range(j + 1, k + 1)]
            + [walk[c] for c in range(i + 1, j + 1)] + [walk[c] for c in range(k + 1, len(walk))])


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
        x = exchange(MOVES, x, roll[j])
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
    it descends: the first improving move, or, if there is none, the certificate."""
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
    walk = prev["walk"] if m < 0 else exchange(MOVES, prev["walk"], m)
    return {"i": I, "r": prev["r"], "k": prev["k"], "kind": "opt" if m < 0 else "move", "src": prev["src"],
            "src_length": prev["src_length"], "m": m, "walk": walk, "length": tour_length(D, walk)}


# ---- the asymmetric neighborhood: the neighbors of a tour are resolved against the record ----

def same_tour(a, b):
    """Two walks are one tour of the asymmetric problem only if they are equal: read backwards,
    a cycle is another tour, of another length."""
    n = len(a)
    return len(b) == n and all(a[c] == b[c] for c in range(n))


def among(walks, walk):
    """Whether the tour is one of the given walks."""
    for w in walks:
        if same_tour(w, walk):
            return True
    return False


def recorded(steps, r):
    """[C] The tours the searchers recorded in the rounds before r, grouped by length. When round r
    begins those rounds are finished, so this is the same under every schedule (a complete horizon)."""
    out = {}
    for x in steps:
        if x["r"] < r:
            if x["length"] in out:
                out[x["length"]].append(x["walk"])
            else:
                out[x["length"]] = [x["walk"]]
    return out


def first_improving_new(D, MOVES, walk, known):
    """The first move, in the fixed order, that shortens the tour to a tour not among the recorded
    ones (`known`); -1 if there is none. The neighborhood of a tour is thus resolved against the
    record: as the record grows it can only shrink (C ≼ C′ ⇒ N(x | C′) ⊆ N(x | C)), and the way
    back to a recorded tour, which the inverse of the shake always offers, is not taken."""
    length = tour_length(D, walk)
    for m in range(len(MOVES)):
        d = change(D, MOVES, walk, m)
        if d < 0 and (length + d not in known or not among(known[length + d], exchange(MOVES, walk, m))):
            return m
    return -1


def vns_step_asym(I, S, R, KMAX, D, MOVES, prev, rolls, source, steps):
    """[ω] The next step of searcher I in the asymmetric neighborhood (v3). The shake is that of
    vns_step. The descent takes the first improving move to a tour not recorded in the finished
    rounds; if every improving move leads to a recorded tour, the first of them, since the
    criterion certifies only a tour that no move shortens."""
    if prev["kind"] == "opt":
        return vns_step(I, S, R, KMAX, D, MOVES, prev, rolls, source)
    m = first_improving_new(D, MOVES, prev["walk"], recorded(steps, prev["r"]))
    if m < 0:
        m = first_improving(D, MOVES, prev["walk"])
    walk = prev["walk"] if m < 0 else exchange(MOVES, prev["walk"], m)
    return {"i": I, "r": prev["r"], "k": prev["k"], "kind": "opt" if m < 0 else "move", "src": prev["src"],
            "src_length": prev["src_length"], "m": m, "walk": walk, "length": tour_length(D, walk)}


def admissible(I, S, R, KMAX, N, START, D, MOVES, prev, rolls, opts, w):
    """[τ] A step of searcher I is admitted if it is a legitimate step of VNS from the previous one,
    whatever strategy chose it: a shake of the starting tour or of a certified local optimum,
    within N_k for some k ≤ KMAX, by the searcher's recorded draw of that round; an improving
    move of the neighborhood; or a certificate that no move shortens the tour."""
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
        return 0 <= w["m"] < len(MOVES) and w["walk"] == exchange(MOVES, prev["walk"], w["m"]) and w["length"] < prev["length"]
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


def measure(KMAX, OPT, START, steps, bests, profile, profiles):
    """The indicators of the search (KPI abstraction), all read from the record.

    shakes_by_k and better_by_k count, for each neighborhood N_k, the shakes made in it and the
    local optima reached from them that are shorter than the tour shaken; round 0, which shakes
    the starting tour, is initialization and is not counted. returns counts the certificates of
    the very tour their round shook: the descent went back."""
    shakes_by_k = [0 for k in range(KMAX)]
    better_by_k = [0 for k in range(KMAX)]
    moves = 0
    optima = 0
    certified = {}
    for x in steps:
        if x["kind"] == "move":
            moves += 1
        elif x["kind"] == "opt":
            optima += 1
            certified[(x["i"], x["r"])] = x["walk"]
        if x["r"] > 0 and x["kind"] == "shake":
            shakes_by_k[x["k"] - 1] += 1
        if x["r"] > 0 and x["kind"] == "opt" and x["length"] < x["src_length"]:
            better_by_k[x["k"] - 1] += 1
    returns = 0
    for x in steps:
        if x["kind"] == "opt":
            source = START if x["src"] == [0, -1] else certified[(x["src"][0], x["src"][1])]
            if same_tour(x["walk"], source):
                returns += 1
    last = bests[-1]
    searchers = [x for x in profile if x["abstraction"].startswith("search_")]
    return {"profile": profiles, "rounds": len(bests), "moves": moves, "optima": optima, "returns": returns,
            "shakes_by_k": shakes_by_k, "better_by_k": better_by_k, "best": last["length"], "found_by": last["src"],
            "optimum": OPT, "gap_permille": (last["length"] - OPT) * 1000 // OPT,
            "search_invocations": sum(x["I"] for x in searchers), "search_not_yet": sum(x["U"] for x in searchers)}
