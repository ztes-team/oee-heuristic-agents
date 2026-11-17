# Helper functions shared by the specifications of the vns-tw system.
# A specification receives a copy of the helpers it uses, so its recorded form stays self-contained.
# No helper contains an unbounded loop: every loop runs over a fixed finite set (the cities, the
# moves of the neighborhood, the scenarios, the k moves of a shake).
#
# The problem: the asymmetric TSP with time windows and precedence constraints. A tour leaves the
# depot (city 0) at time 0; at each city the service starts at the arrival or, if it arrives early,
# when the window opens; a city reached after its window closes is late, and so is a return to the
# depot after its window closes. A precedence pair [p, q] requires p before q.
#
# Times in a scenario of the environment are kept in hundredths: arc (a, b) takes
# D[a][b] * (100 + delta) / 100, with delta an integer percent in [-RHO, RHO].

def tour_length(D, walk):
    """The length of the closed tour that visits the cities in the order of the walk."""
    return sum(D[walk[i - 1]][walk[i]] for i in range(len(walk)))


def valid(walk, N):
    """Every city exactly once, from the depot."""
    return len(walk) == N and walk[0] == 0 and sorted(walk) == [c for c in range(N)]


def segment_moves(N):
    """The neighborhood N1 in a fixed order: each move (i, j, k) cuts the tour after positions i, j
    and k and exchanges the two segments between them, A B C D → A C B D. The depot never moves,
    and every arc that is not cut keeps its direction."""
    return [[i, j, k] for i in range(N) for j in range(i + 1, N) for k in range(j + 1, N)]


def change(D, MOVES, walk, m):
    """How much move m changes the length of the tour, in O(1)."""
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


def by_closing(B, N):
    """The starting tour: the depot, then the cities in the order in which their windows close."""
    return [0] + [p[1] for p in sorted([[B[c], c] for c in range(1, N)])]


# ---- the environment: scenarios as a pure function of recorded seeds ----

def mix(z):
    """The output function of SplitMix64 (Steele, Lea, Flood 2014) on a 64-bit integer."""
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return z ^ (z >> 31)


def deviation(seed, a, b, N, RHO):
    """The deviation of arc (a, b), in percent, in the scenario of the given seed."""
    return mix((seed + (a * N + b + 1) * 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF) % (2 * RHO + 1) - RHO


def scenario(D, seed, N, RHO):
    """[C] The travel times, in hundredths, of the scenario whose seed the world recorded."""
    return [[D[a][b] * (100 + deviation(seed, a, b, N, RHO)) if a != b else 0 for b in range(N)] for a in range(N)]


def scenarios(D, worlds, N, RHO):
    """The scenarios of all recorded seeds of the world."""
    return [scenario(D, w[0], N, RHO) for w in worlds]


def scenario_event(D, N, RHO, worlds, done):
    """[ω] The next scenario of the world: its number, the seed the world recorded for it, and its
    travel times. A scenario is a pure function of its seed, but it is computed here once and
    recorded, so that every searcher and every criterion reads it from the record instead of
    computing it again at each invocation. None when every recorded seed has its scenario."""
    if done >= len(worlds):
        return None
    seed = worlds[done][0]
    return {"s": done, "seed": seed, "T": scenario(D, seed, N, RHO)}


def recorded_scenarios(scens, M):
    """[C] The travel times of the M scenarios as the abstraction scenario recorded them (read
    through a map: scenario s → its travel times); None while one of them is not recorded."""
    out = []
    for s in range(M):
        if s not in scens:
            return None
        out.append(scens[s])
    return out


# ---- the state of a tour: its schedule, where it stops being admissible, and its value ----

def state(D, A, B, PAIRS, SCEN, walk):
    """[C] What can be read from a tour: the schedule (t), the lateness up to each position (lp),
    the precedence pairs violated, the first position whose city is not admissible and why, and,
    per scenario, the times, the first and the last late position (-1: on time; N: the return).

    The status of the first position that is not admissible: "false" if the city is late (its
    arrival is fixed by the prefix before it, so no change after it can repair it), "not_yet" if
    a city it must follow comes later (it is premature: admissible once that city is visited);
    "true" if there is none."""
    n = len(walk)
    pos = [0 for c in range(n)]
    for x in range(n):
        pos[walk[x]] = x
    t = [0 for x in range(n)]
    lp = [0 for x in range(n)]
    late = 0
    first = -1
    status = "true"
    for x in range(1, n):
        c = walk[x]
        t[x] = max(t[x - 1] + D[walk[x - 1]][c], A[c])
        late += max(0, t[x] - B[c])
        lp[x] = late
        if first < 0 and t[x] > B[c]:
            first = x
            status = "false"
        if first < 0 and any(p[1] == c and pos[p[0]] > x for p in PAIRS):
            first = x
            status = "not_yet"
    back = t[n - 1] + D[walk[n - 1]][walk[0]]
    late += max(0, back - B[0])
    if first < 0 and back > B[0]:
        first = n
        status = "false"
    ts = []
    fs = []
    ls = []
    for DS in SCEN:
        u = [0 for x in range(n)]
        f = -1
        last = -1
        for x in range(1, n):
            u[x] = max(u[x - 1] + DS[walk[x - 1]][walk[x]], 100 * A[walk[x]])
            if u[x] > 100 * B[walk[x]]:
                last = x
                if f < 0:
                    f = x
        if u[n - 1] + DS[walk[n - 1]][walk[0]] > 100 * B[0]:
            last = n
            if f < 0:
                f = n
        ts.append(u)
        fs.append(f)
        ls.append(last)
    return {"t": t, "lp": lp, "late": late, "pos": pos, "prec": sum(1 for p in PAIRS if pos[p[0]] > pos[p[1]]),
            "first": first, "status": status, "ts": ts, "fs": fs, "ls": ls,
            "fails": sum(1 for f in fs if f >= 0), "length": tour_length(D, walk)}


def value(st, ALLOW):
    """The value of a tour, compared lexicographically: precedence pairs violated, lateness, the
    scenarios it fails beyond the ALLOW permitted, length. A tour is feasible if the first three are 0."""
    return [st["prec"], st["late"], max(0, st["fails"] - ALLOW), st["length"]]


def late_after(DS, A, B, walk, u, f, last, order, i, k):
    """Whether the tour after the move (i, j, k) is late in one scenario, from the schedule u of the
    tour before it. A tour late before the cut stays late; after the exchanged segments the old
    schedule is taken up again as soon as an arrival time coincides with the old one."""
    if 0 <= f <= i:
        return 1
    n = len(walk)
    t = u[i]
    prev = walk[i]
    for x in order:
        c = walk[x]
        t = max(t + DS[prev][c], 100 * A[c])
        prev = c
        if t > 100 * B[c]:
            return 1
    for x in range(k + 1, n):
        c = walk[x]
        t = max(t + DS[prev][c], 100 * A[c])
        prev = c
        if t > 100 * B[c]:
            return 1
        if t == u[x]:
            return 1 if last >= x else 0
    return 1 if t + DS[prev][walk[0]] > 100 * B[0] else 0


def nominal_after(D, A, B, PAIRS, MOVES, walk, st, m):
    """The precedence pairs violated and the lateness of the tour after move m, computed from the
    state of the tour before it: the positions before the cut keep their times, so only the rest is
    computed again, and after the exchanged segments the old schedule is taken up again as soon as
    an arrival time coincides with the old one."""
    n = len(walk)
    i = MOVES[m][0]
    j = MOVES[m][1]
    k = MOVES[m][2]
    prec = st["prec"]
    for p in PAIRS:
        a = st["pos"][p[0]]
        b = st["pos"][p[1]]
        if i < a <= j < b <= k:
            prec += 1
        elif i < b <= j < a <= k:
            prec -= 1
    order = [x for x in range(j + 1, k + 1)] + [x for x in range(i + 1, j + 1)]
    t = st["t"][i]
    late = st["lp"][i]
    prev = walk[i]
    for x in order:
        c = walk[x]
        t = max(t + D[prev][c], A[c])
        late += max(0, t - B[c])
        prev = c
    joined = False
    for x in range(k + 1, n):
        c = walk[x]
        t = max(t + D[prev][c], A[c])
        if t == st["t"][x]:
            late += st["late"] - st["lp"][x - 1]
            joined = True
            break
        late += max(0, t - B[c])
        prev = c
    if not joined:
        late += max(0, t + D[prev][walk[0]] - B[0])
    return [prec, late]


def fails_after(A, B, SCEN, MOVES, walk, st, m):
    """The scenarios in which the tour after move m is late."""
    i = MOVES[m][0]
    j = MOVES[m][1]
    k = MOVES[m][2]
    order = [x for x in range(j + 1, k + 1)] + [x for x in range(i + 1, j + 1)]
    return sum(late_after(SCEN[s], A, B, walk, st["ts"][s], st["fs"][s], st["ls"][s], order, i, k) for s in range(len(SCEN)))


def value_after(D, A, B, PAIRS, SCEN, ALLOW, MOVES, walk, st, m):
    """The value of the tour after move m."""
    return (nominal_after(D, A, B, PAIRS, MOVES, walk, st, m)
            + [max(0, fails_after(A, B, SCEN, MOVES, walk, st, m) - ALLOW), st["length"] + change(D, MOVES, walk, m)])


def lowers(D, A, B, PAIRS, SCEN, ALLOW, MOVES, walk, st, m, v):
    """Whether move m lowers the value v of the tour. The value is compared lexicographically, so
    its parts are computed only as far as the comparison needs them: a move that lengthens a
    feasible tour is refused in O(1), and the scenarios are read only if the nominal part ties."""
    d = change(D, MOVES, walk, m)
    if v[0] + v[1] + v[2] == 0 and d >= 0:
        return False
    nom = nominal_after(D, A, B, PAIRS, MOVES, walk, st, m)
    if nom != v[:2]:
        return nom < v[:2]
    return [max(0, fails_after(A, B, SCEN, MOVES, walk, st, m) - ALLOW), st["length"] + d] < v[2:]


# ---- the descent ----

def same_tour(a, b):
    """Two walks are one tour only if they are equal."""
    return len(a) == len(b) and all(a[c] == b[c] for c in range(len(a)))


def among(walks, walk):
    for w in walks:
        if same_tour(w, walk):
            return True
    return False


def recorded(steps, r):
    """[C] The tours the searchers recorded in the rounds before r, grouped by length."""
    out = {}
    for x in steps:
        if x["r"] < r:
            if x["value"][3] in out:
                out[x["value"][3]].append(x["walk"])
            else:
                out[x["value"][3]] = [x["walk"]]
    return out


def best_repair(D, A, B, PAIRS, SCEN, ALLOW, MOVES, walk, st, v, cut, known):
    """The move that lowers the value v most among those that cut before position `cut` (with
    `known`, among those that lead to a tour not recorded); -1 if none lowers it. The nominal part
    decides first; the scenarios are read only when it ties."""
    best = -1
    bnom = v[:2]
    bval = v
    for m in range(len(MOVES)):
        if MOVES[m][0] < cut:
            nom = nominal_after(D, A, B, PAIRS, MOVES, walk, st, m)
            if nom > bnom:
                continue
            w = None
            if nom == bnom:
                if bval is None:
                    bval = value_after(D, A, B, PAIRS, SCEN, ALLOW, MOVES, walk, st, best)
                w = value_after(D, A, B, PAIRS, SCEN, ALLOW, MOVES, walk, st, m)
                if not w < bval:
                    continue
            if known is not None:
                length = st["length"] + change(D, MOVES, walk, m)
                if length in known and among(known[length], exchange(MOVES, walk, m)):
                    continue
            best = m
            bnom = nom
            bval = w
    return best


def next_move(D, A, B, PAIRS, SCEN, ALLOW, MOVES, walk, known):
    """[ω] The move of the descent from a tour, or -1 if no move lowers its value (the certificate).

    An infeasible tour is repaired by the move that lowers the value most among those that cut
    before the first position that is not admissible (or, if only scenarios fail, before the
    latest first lateness of a failing scenario): a move that cuts after it leaves that position
    as it is. If none lowers the value, the first move that does. A feasible tour is shortened by
    the first move that lowers the value (v1). With `known` (v3) both the repair and the
    shortening prefer a tour not recorded in the finished rounds, and take a recorded one only if
    there is no other."""
    st = state(D, A, B, PAIRS, SCEN, walk)
    v = value(st, ALLOW)
    if v[0] + v[1] + v[2] > 0:
        cut = st["first"] if v[0] + v[1] > 0 else max(st["fs"])
        best = best_repair(D, A, B, PAIRS, SCEN, ALLOW, MOVES, walk, st, v, cut, known)
        if best < 0 and known is not None:
            best = best_repair(D, A, B, PAIRS, SCEN, ALLOW, MOVES, walk, st, v, cut, None)
        if best >= 0:
            return best
        for m in range(len(MOVES)):
            if lowers(D, A, B, PAIRS, SCEN, ALLOW, MOVES, walk, st, m, v):
                return m
        return -1
    first = -1
    for m in range(len(MOVES)):
        if lowers(D, A, B, PAIRS, SCEN, ALLOW, MOVES, walk, st, m, v):
            d = change(D, MOVES, walk, m)
            if known is None:
                return m
            if v[3] + d not in known or not among(known[v[3] + d], exchange(MOVES, walk, m)):
                return m
            if first < 0:
                first = m
    return first


def shaken(MOVES, walk, roll, k):
    """A tour in N_k of the given one: the first k moves of the recorded draw, applied in order.
    The shake may leave the feasible region; the descent repairs before it shortens."""
    x = [c for c in walk]
    for j in range(k):
        x = exchange(MOVES, x, roll[j])
    return x


def step(D, A, B, PAIRS, SCEN, ALLOW, I, r, k, kind, src, src_value, m, walk):
    """A step of searcher I, with what the record states about its tour."""
    st = state(D, A, B, PAIRS, SCEN, walk)
    return {"i": I, "r": r, "k": k, "kind": kind, "src": src, "src_value": src_value, "m": m, "walk": walk,
            "value": value(st, ALLOW), "first": st["first"], "status": st["status"], "fails": st["fails"]}


def source_sync(START, D, A, B, PAIRS, SCEN, ALLOW, prev, inc):
    """[ω] Synchronous cooperation: the incumbent of the round the searcher has finished, once every
    searcher has finished it; before round 0 the starting tour. None (wait) until then."""
    if prev["r"] < 0:
        return [[0, -1], START, value(state(D, A, B, PAIRS, SCEN, START), ALLOW)]
    if inc["r"] != prev["r"]:
        return None
    return [inc["src"], inc["walk"], inc["value"]]


def source_async(START, D, A, B, PAIRS, SCEN, ALLOW, prev, opts):
    """[ω] Asynchronous cooperation: the best local optimum certified so far, as it stands now."""
    best = [[0, -1], START, value(state(D, A, B, PAIRS, SCEN, START), ALLOW)]
    if prev["r"] < 0:
        return best
    for o in opts:
        if o["value"] < best[2]:
            best = [[o["i"], o["r"]], o["walk"], o["value"]]
    return best


def vns_step(I, S, R, KMAX, D, A, B, PAIRS, SCEN, ALLOW, MOVES, prev, rolls, source, known):
    """[ω] The next step of searcher I: a shake, a repair, a move that shortens, or the certificate
    that no move lowers the value; None (⊥) while it must wait, and after the last round. `known`
    is None for v1 and v2, and the tours of the finished rounds for v3."""
    if prev["kind"] == "opt":
        r = prev["r"] + 1
        if r >= R or source is None or len(rolls) <= r * S + I - 1:
            return None
        if prev["r"] < 0:
            k = KMAX
        elif source[2] < prev["src_value"]:
            k = 1
        else:
            k = prev["k"] % KMAX + 1
        walk = shaken(MOVES, source[1], rolls[r * S + I - 1], k)
        return step(D, A, B, PAIRS, SCEN, ALLOW, I, r, k, "shake", [v for v in source[0]], [v for v in source[2]], -1, walk)
    m = next_move(D, A, B, PAIRS, SCEN, ALLOW, MOVES, prev["walk"], known)
    if m < 0:
        return step(D, A, B, PAIRS, SCEN, ALLOW, I, prev["r"], prev["k"], "opt", prev["src"], prev["src_value"], -1, prev["walk"])
    feasible = prev["value"][0] + prev["value"][1] + prev["value"][2] == 0
    return step(D, A, B, PAIRS, SCEN, ALLOW, I, prev["r"], prev["k"], "move" if feasible else "repair",
                prev["src"], prev["src_value"], m, exchange(MOVES, prev["walk"], m))


def vns_step_asym(I, S, R, KMAX, D, A, B, PAIRS, SCEN, ALLOW, MOVES, prev, rolls, source, steps):
    """[ω] v3: the descent (the repair and the shortening) does not take a move to a tour recorded
    in the finished rounds while another move would do."""
    known = None if prev["kind"] == "opt" else recorded(steps, prev["r"])
    return vns_step(I, S, R, KMAX, D, A, B, PAIRS, SCEN, ALLOW, MOVES, prev, rolls, source, known)


def searcher_v1(I, S, R, KMAX, N, M, D, A, B, PAIRS, ALLOW, MOVES, START, prev, rolls, inc, scens):
    """[ω] v1: synchronous cooperation, on the recorded scenarios of the world."""
    SCEN = recorded_scenarios(scens, M)
    if SCEN is None:
        return None
    source = source_sync(START, D, A, B, PAIRS, SCEN, ALLOW, prev, inc)
    return vns_step(I, S, R, KMAX, D, A, B, PAIRS, SCEN, ALLOW, MOVES, prev, rolls, source, None)


def searcher_v2(I, S, R, KMAX, N, M, D, A, B, PAIRS, ALLOW, MOVES, START, prev, rolls, opts, scens):
    """[ω] v2: asynchronous cooperation."""
    SCEN = recorded_scenarios(scens, M)
    if SCEN is None:
        return None
    source = source_async(START, D, A, B, PAIRS, SCEN, ALLOW, prev, opts)
    return vns_step(I, S, R, KMAX, D, A, B, PAIRS, SCEN, ALLOW, MOVES, prev, rolls, source, None)


def searcher_v3(I, S, R, KMAX, N, M, D, A, B, PAIRS, ALLOW, MOVES, START, prev, rolls, inc, steps, scens):
    """[ω] v3: synchronous cooperation, the asymmetric neighborhood."""
    SCEN = recorded_scenarios(scens, M)
    if SCEN is None:
        return None
    source = source_sync(START, D, A, B, PAIRS, SCEN, ALLOW, prev, inc)
    return vns_step_asym(I, S, R, KMAX, D, A, B, PAIRS, SCEN, ALLOW, MOVES, prev, rolls, source, steps)


# ---- the criterion ----

def admissible(I, S, R, KMAX, N, START, D, A, B, PAIRS, SCEN, ALLOW, MOVES, prev, rolls, opts, w):
    """[τ] A step of searcher I is admitted if what it states about its tour is true and it is a
    legitimate step of VNS from the previous one, whatever strategy chose it: a shake of the
    starting tour or of a certified local optimum within N_k by the recorded draw; a repair or a
    move: any move that lowers the value (a repair if the tour was infeasible, a move if it was
    feasible); or a certificate that no move lowers the value of the tour."""
    if w["i"] != I or not valid(w["walk"], N):
        return False
    st = state(D, A, B, PAIRS, SCEN, w["walk"])
    if [w["value"], w["first"], w["status"], w["fails"]] != [value(st, ALLOW), st["first"], st["status"], st["fails"]]:
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
        if source is None or value(state(D, A, B, PAIRS, SCEN, source), ALLOW) != w["src_value"]:
            return False
        return w["walk"] == shaken(MOVES, source, rolls[r * S + I - 1], w["k"])
    same = ["r", "k", "src", "src_value"]
    if prev["kind"] == "opt" or any(w[f] != prev[f] for f in same):
        return False
    feasible = prev["value"][0] + prev["value"][1] + prev["value"][2] == 0
    if w["kind"] == "move" or w["kind"] == "repair":
        return (w["kind"] == ("move" if feasible else "repair") and 0 <= w["m"] < len(MOVES)
                and w["walk"] == exchange(MOVES, prev["walk"], w["m"]) and w["value"] < prev["value"])
    if w["kind"] != "opt" or w["m"] != -1 or w["walk"] != prev["walk"]:
        return False
    sp = state(D, A, B, PAIRS, SCEN, prev["walk"])
    v = value(sp, ALLOW)
    return not any(lowers(D, A, B, PAIRS, SCEN, ALLOW, MOVES, prev["walk"], sp, m, v) for m in range(len(MOVES)))


def searcher_criterion(I, S, R, KMAX, N, M, START, D, A, B, PAIRS, ALLOW, MOVES, prev, rolls, opts, scens, w):
    """[τ] The criterion of a searcher, on the recorded scenarios of the world; false while one of
    them is not recorded."""
    SCEN = recorded_scenarios(scens, M)
    return SCEN is not None and admissible(I, S, R, KMAX, N, START, D, A, B, PAIRS, SCEN, ALLOW, MOVES, prev, rolls, opts, w)


# ---- the incumbent and the indicators ----

def round_best(S, r, before, opts):
    """The incumbent after round r: the best value among the previous incumbent and the S local
    optima of round r (among equals the earlier, then the searcher with the smaller number); None
    until every searcher has certified its local optimum of round r."""
    found = [o for o in opts if o["r"] == r]
    if len(found) < S:
        return None
    out = None
    if before["r"] >= 0:
        out = {"r": r, "src": before["src"], "walk": before["walk"], "value": before["value"], "improved": False}
    for i in range(1, S + 1):
        for o in found:
            if o["i"] == i and (out is None or o["value"] < out["value"]):
                out = {"r": r, "src": [i, r], "walk": o["walk"], "value": o["value"], "improved": True}
    return out


def on_time(D, A, B, walk, seed, N, RHO):
    """Whether the tour is on time everywhere in the scenario of the given seed (arc times computed
    only along the tour)."""
    t = 0
    for x in range(1, N):
        t = max(t + D[walk[x - 1]][walk[x]] * (100 + deviation(seed, walk[x - 1], walk[x], N, RHO)), 100 * A[walk[x]])
        if t > 100 * B[walk[x]]:
            return False
    return t + D[walk[N - 1]][walk[0]] * (100 + deviation(seed, walk[N - 1], walk[0], N, RHO)) <= 100 * B[0]


def audit_seed(seed, s):
    """The seed of audit scenario s, derived from the one seed the audit recorded."""
    return mix((seed + (s + 1) * 0xD1B54A32D192ED03) & 0xFFFFFFFFFFFFFFFF)


def measure(N, M, ALLOW, KMAX, OPT, OPT_CHANCE, AUDIT, RHO, D, A, B, START, steps, bests, audits, profile, profiles):
    """The indicators of the search (KPI abstraction), all read from the record.

    returns: certificates of the very tour their round shook. repairs_false and repairs_not_yet:
    repair steps whose tour had a late city (False) or a premature city (Not Yet) as the first
    position that is not admissible. on_time: the scenarios of the world in which the best tour is
    on time everywhere; audit_on_time: the same over AUDIT further scenarios derived from the
    recorded seed of the audit, which the search never saw: an estimate of the probability of the
    event "on time everywhere", a Borel set of the space of records of the environment."""
    before = {}
    moves = 0
    repairs = 0
    rf = 0
    rn = 0
    certified = {}
    for x in steps:
        if x["kind"] == "move":
            moves += 1
        if x["kind"] == "repair":
            repairs += 1
            if before[x["i"]]["status"] == "false":
                rf += 1
            if before[x["i"]]["status"] == "not_yet":
                rn += 1
        if x["kind"] == "opt":
            certified[(x["i"], x["r"])] = x["walk"]
        before[x["i"]] = x
    returns = 0
    optima = 0
    for x in steps:
        if x["kind"] == "opt":
            optima += 1
            source = START if x["src"] == [0, -1] else certified[(x["src"][0], x["src"][1])]
            if same_tour(x["walk"], source):
                returns += 1
    last = bests[-1]
    seed = audits[0][0]
    audit = sum(1 for s in range(AUDIT) if on_time(D, A, B, last["walk"], audit_seed(seed, s), N, RHO))
    optimum = OPT if ALLOW >= M else OPT_CHANCE                # ALLOW = M: no chance constraint
    searchers = [x for x in profile if x["abstraction"].startswith("search_")]
    return {"profile": profiles, "rounds": len(bests), "moves": moves, "repairs": repairs, "repairs_false": rf,
            "repairs_not_yet": rn, "returns": returns, "optima": optima, "best": last["value"], "found_by": last["src"],
            "feasible": last["value"][0] + last["value"][1] + last["value"][2] == 0,
            "on_time": M - [x for x in steps if same_tour(x["walk"], last["walk"])][0]["fails"],
            "audit_on_time": audit, "optimum": optimum, "gap_permille": (last["value"][3] - optimum) * 1000 // optimum,
            "search_invocations": sum(x["I"] for x in searchers), "search_not_yet": sum(x["U"] for x in searchers)}
