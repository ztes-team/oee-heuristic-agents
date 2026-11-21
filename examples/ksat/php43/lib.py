# Helper functions shared by the specifications of the ksat systems.
# A specification receives a copy of the helpers it uses, so its recorded form stays self-contained.
#
# A literal is a signed variable number (-3 is "not x3"); a clause is a list of literals. Every
# clause of the formula is an abstraction (c1, c2, ...), and so is every non-empty learned clause
# (l1, l2, ...) that learn brings in. A frame is the shared state of one round:
#   trail      the assigned literals in the order of assignment, as steps {"literal", "level",
#              "reason"}, where reason is the name of the clause that forced the literal, or
#              "decide";
#   conflicts  the names of the clauses found false;
#   quiet      no conflict, and no clause is unit or false on the frame;
#   total      every variable is assigned;
#   votes      once every clause has voted on a quiet total frame, the names of the voters;
#   epoch      the number of backjumps so far; round, the number of the frame; level, the
#              current decision level.
# No helper contains an unbounded loop: every loop runs over a clause, the clauses, the learned
# clauses, the trail or the variables.

def latest(window):
    """The last value of a binding that reads only the last event of a lineage ("window": 1), or
    None while the lineage has none."""
    return window[-1] if window else None


def assigned(trail):
    """The literals of a trail, as a set."""
    return {step["literal"] for step in trail}


def satisfied(clause, values):
    """Whether some literal of the clause is assigned true."""
    return any(literal in values for literal in clause)


def falsified(clause, values):
    """Whether every literal of the clause is assigned false (the empty clause always is)."""
    return all(-literal in values for literal in clause)


def unit_literal(clause, values):
    """The literal a clause forces: None if the clause is satisfied, or if it does not have exactly
    one literal left unassigned."""
    if satisfied(clause, values):
        return None
    left = [literal for literal in clause if -literal not in values]
    return left[0] if len(left) == 1 else None


def clause_names(names, learned):
    """The names of the clause abstractions in their order: those of the formula, then the learned
    clauses that brought in an abstraction (every one but the empty clause)."""
    return [*names] + [name for name in learned if len(learned[name]) > 0]


def clause_table(clauses, learned):
    """Every known clause by name: those of the formula and the learned ones (learned is the map
    name → literals of the learn lineage, in the order of learning)."""
    table = {**clauses}
    for name in learned:
        table[name] = [*learned[name]]
    return table


def learned_name(count):
    """The name of the next learned clause, after count clauses were learned."""
    return "l" + "%d" % (count + 1)


def round_version(names, learned):
    """The version of the specifications of round that the next non-empty learned clause brings
    in: version 1 comes from the files, and each learned clause abstraction adds one."""
    return len(clause_names(names, learned)) - len(names) + 2


# ---- a clause: what it says about a frame, and its criterion τᵢ ----

def speech(name, clause, frame):
    """[ω] What a clause says about a frame, for the next round; None if it has nothing to say.
    On a frame that is quiet and total, a satisfied clause votes for it. Otherwise a false clause
    reports a conflict and a unit clause the literal it forces. A frame with a conflict or with
    votes is not spoken about: learn, or verdict, acts on it."""
    if frame is None or frame["conflicts"] or frame["votes"]:
        return None
    values = assigned(frame["trail"])
    told = {"clause": name, "round": frame["round"] + 1, "kind": "", "literal": 0}
    if frame["quiet"]:
        if frame["total"] and satisfied(clause, values):
            return {**told, "kind": "vote"}
        return None
    if falsified(clause, values):
        return {**told, "kind": "conflict"}
    literal = unit_literal(clause, values)
    return None if literal is None else {**told, "kind": "unit", "literal": literal}


def propose_speech(name, clause, frame, mine):
    """[ω] The ontology of a clause: its speech about the latest frame, once per round (mine is
    its own last speech)."""
    told = speech(name, clause, frame)
    if told is None or (mine is not None and mine["round"] >= told["round"]):
        return None
    return told


def check_speech(name, clause, frame, mine, candidate):
    """[τ] τᵢ, the criterion of a clause: it speaks once in the next round, for itself, about a
    frame that is spoken about, and what it says is true of its own clause on the frame. A unit
    names the one literal left unassigned in a clause that is not satisfied; a conflict, a clause
    every literal of which is false; a vote, a total frame on which the clause is satisfied."""
    if frame is None or frame["conflicts"] or frame["votes"]:
        return False
    if candidate["clause"] != name or candidate["round"] != frame["round"] + 1:
        return False
    if mine is not None and mine["round"] >= candidate["round"]:
        return False
    values = assigned(frame["trail"])
    kind = candidate["kind"]
    if kind == "unit":
        return candidate["literal"] != 0 and unit_literal(clause, values) == candidate["literal"]
    if kind == "conflict":
        return candidate["literal"] == 0 and falsified(clause, values)
    if kind == "vote":
        return candidate["literal"] == 0 and frame["total"] and satisfied(clause, values)
    return False


# ---- round: the next frame ----

def close(frame, names, table, variables):
    """A frame completed with whether it is quiet (no conflict, and no clause unit or false on it)
    and whether it is total (every variable assigned)."""
    values = assigned(frame["trail"])
    quiet = not frame["conflicts"]
    if quiet:
        for name in names:
            clause = table[name]
            if falsified(clause, values) or unit_literal(clause, values) is not None:
                quiet = False
                break
    return {**frame, "quiet": quiet, "total": len(values) == len(variables)}


def next_frame(names, clauses, variables, frame, said, decision, last_learned, learned):
    """[ω] The next frame, a function of the record; None while what it needs is not recorded.

    The first frame is empty. After a conflict the next frame waits for the learned clause; it
    starts a new epoch on the trail cut back to the level the clause names, where the clause is
    unit. Otherwise it waits for every clause that has something to say about the frame (said is
    the map (round, clause) → speech). When all of them voted, the frame is the consensus. When
    none has anything to say, it waits for the decision of this round and adds its literals at the
    next level. Otherwise it adds the forced literals in the order of the clauses, a unit whose
    literal is already false being a conflict, and records the conflicts. A refutation (the empty
    clause) and a consensus end the rounds."""
    order = clause_names(names, learned)
    table = clause_table(clauses, learned)
    empty = {"epoch": 0, "round": 0, "level": 0, "trail": [], "conflicts": [], "votes": []}
    if frame is None:
        return close(empty, order, table, variables)
    if frame["votes"]:
        return None
    r = frame["round"]
    if frame["conflicts"]:
        if last_learned is None or last_learned["round"] != r or not last_learned["literals"]:
            return None
        level = last_learned["level"]
        trail = [step for step in frame["trail"] if step["level"] <= level]
        return close({**empty, "epoch": frame["epoch"] + 1, "round": r + 1, "level": level, "trail": trail},
                     order, table, variables)
    speakers = [name for name in order if speech(name, table[name], frame) is not None]
    for name in speakers:
        if (r + 1, name) not in said:
            return None
    if not speakers:
        if decision is None or decision["round"] != r:
            return None
        level = frame["level"] + 1
        trail = [*frame["trail"]] + [{"literal": literal, "level": level, "reason": "decide"}
                                     for literal in decision["literals"]]
        return close({**empty, "epoch": frame["epoch"], "round": r + 1, "level": level, "trail": trail},
                     order, table, variables)
    told = [said[(r + 1, name)] for name in speakers]
    if all(t["kind"] == "vote" for t in told):
        return {**frame, "round": r + 1, "votes": speakers}
    trail, values, conflicts = [*frame["trail"]], assigned(frame["trail"]), []
    for t in told:
        if t["kind"] == "conflict":
            conflicts.append(t["clause"])
        elif t["kind"] == "unit" and -t["literal"] in values:
            conflicts.append(t["clause"])
        elif t["kind"] == "unit" and t["literal"] not in values:
            trail.append({"literal": t["literal"], "level": frame["level"], "reason": t["clause"]})
            values.add(t["literal"])
    return close({**empty, "epoch": frame["epoch"], "round": r + 1, "level": frame["level"], "trail": trail,
                  "conflicts": conflicts}, order, table, variables)


# ---- decide: the decision policies ----

def decision_due(frame, decision):
    """Whether the frame waits for a decision: it is quiet, not total, not a consensus, and this
    round has no decision yet (decision is the last one recorded)."""
    if frame is None or not frame["quiet"] or frame["total"] or frame["votes"] or frame["conflicts"]:
        return False
    return decision is None or decision["round"] < frame["round"]


def open_counts(names, clauses, frame, learned):
    """The free variables in order, the clauses not yet satisfied, and how often each unassigned
    literal occurs in those clauses."""
    order = clause_names(names, learned)
    table = clause_table(clauses, learned)
    values = assigned(frame["trail"])
    open_clauses = [table[name] for name in order if not satisfied(table[name], values)]
    count = {}
    for clause in open_clauses:
        for literal in clause:
            if literal not in values and -literal not in values:
                count[literal] = count.get(literal, 0) + 1
    return values, open_clauses, count


def choose(names, clauses, variables, frame, learned):
    """[ω] Policy v1, by occurrence: the literal that occurs most often in the clauses not yet
    satisfied, among the unassigned variables (ties: the variable that comes first, the negative
    literal first). When every clause is satisfied, the remaining variables are all set false at
    once."""
    values, open_clauses, count = open_counts(names, clauses, frame, learned)
    free = [var for var in variables if var not in values and -var not in values]
    if not open_clauses:
        return [-var for var in free]
    best, most = None, -1
    for var in free:
        for literal in (-var, var):
            if count.get(literal, 0) > most:
                best, most = literal, count.get(literal, 0)
    return [best]


def choose_by_activity(names, clauses, variables, frame, learned):
    """[ω] Policy v2, by conflict activity: the literal that occurs most often in the learned
    clauses, among the unassigned variables; ties are broken by the count of policy v1, then by the
    variable that comes first, the negative literal first. When every clause is satisfied, the
    remaining variables are all set false at once."""
    values, open_clauses, count = open_counts(names, clauses, frame, learned)
    free = [var for var in variables if var not in values and -var not in values]
    if not open_clauses:
        return [-var for var in free]
    activity = {}
    for name in learned:
        for literal in learned[name]:
            activity[literal] = activity.get(literal, 0) + 1
    best, most = None, (-1, -1)
    for var in free:
        for literal in (-var, var):
            score = (activity.get(literal, 0), count.get(literal, 0))
            if score > most:
                best, most = literal, score
    return [best]


def propose_decision(names, clauses, variables, frame, decision, learned, waiting):
    """[ω] Version 1 of the ontology of decide: a decision by policy v1 when one is due. While a
    change of policy is due and adapt has not yet decided (waiting), it proposes nothing, so that
    every decision after the change is made by version 2 under every schedule."""
    if waiting or not decision_due(frame, decision):
        return None
    return {"round": frame["round"], "literals": choose(names, clauses, variables, frame, learned)}


def propose_decision_by_activity(names, clauses, variables, frame, decision, learned):
    """[ω] Version 2 of the ontology of decide, carried by adapt: a decision by policy v2 when one
    is due."""
    if not decision_due(frame, decision):
        return None
    return {"round": frame["round"], "literals": choose_by_activity(names, clauses, variables, frame, learned)}


def check_decision(variables, frame, decision, candidate):
    """[τ] The criterion of decide, for both versions of its ontology: when a decision is due, for
    this round, a non-empty consistent set of literals of unassigned variables of the formula.
    Which ones is the policy's choice (D2)."""
    if not decision_due(frame, decision) or candidate["round"] != frame["round"]:
        return False
    literals, values = candidate["literals"], assigned(frame["trail"])
    named = [abs(literal) for literal in literals]
    return (len(literals) > 0 and len(set(named)) == len(named) and all(var in variables for var in named)
            and all(literal not in values and -literal not in values for literal in literals))


# ---- learn: conflict analysis, the certificate, and the abstraction it brings in ----

def analyze(table, frame):
    """[ω] Conflict analysis by resolution to the first unique implication point. Starting from the
    first false clause of the frame, resolve on the literal of the conflict level assigned last,
    with the clause that forced it, until one literal of that level remains, or, at level 0, none
    (the empty clause). Returns (start, chain, literals, level): each step {"clause", "literal"}
    names the clause resolved with and its literal on the trail; level is the highest level of the
    other literals of the learned clause, where it forces its own (0 if there are none)."""
    trail, conflict_level = frame["trail"], frame["level"]
    start = frame["conflicts"][0]
    level, reason, position = {}, {}, {}
    for i in range(len(trail)):
        literal = trail[i]["literal"]
        level[literal], reason[literal], position[literal] = trail[i]["level"], trail[i]["reason"], i
    current, chain = set(table[start]), []
    for _ in range(len(trail)):
        at_level = [literal for literal in current if level[-literal] == conflict_level]
        if not at_level or (conflict_level > 0 and len(at_level) == 1):
            break
        last = at_level[0]
        for literal in at_level:
            if position[-literal] > position[-last]:
                last = literal
        if reason[-last] == "decide":
            break
        parent = reason[-last]
        current = (current - {last}) | {literal for literal in table[parent] if literal != -last}
        chain.append({"clause": parent, "literal": -last})
    literals = sorted(current)
    lower = [level[-literal] for literal in literals if level[-literal] != conflict_level]
    return start, chain, literals, max(lower) if lower else 0


def without_authority(specification):
    """A carried specification as written, without the criterion that Z₀ binds a carried ontology
    to."""
    return {key: value for key, value in specification.items() if key != "criterion"}


def brought_in(templates, name, literals, version, sources):
    """The specifications a non-empty learned clause carries, in order: the criterion and the
    ontology of its clause abstraction, made from those of c1 (templates[0:2]) with its name and
    literals; and the criterion and the ontology of round in the given version, made from version 1
    (templates[2:4]), whose binding of the speeches reads the lineages of sources, the new clause
    among them."""
    out = []
    for spec in templates[:2]:
        context = {key: ({**value, "from": name} if key == "mine" else value)
                   for key, value in spec["inputs"]["context"].items()}
        constants = {**spec["constants"], "CLAUSE": literals, "NAME": name}
        out.append({**spec, "abstraction": name, "constants": constants,
                    "inputs": {**spec["inputs"], "context": context}})
    for spec in templates[2:]:
        context = {key: ({**value, "from": sources} if key == "said" else value)
                   for key, value in spec["inputs"]["context"].items()}
        out.append({**spec, "version": version, "inputs": {**spec["inputs"], "context": context}})
    return out


def carried_for(names, learned, templates, name, literals):
    """What a learned clause carries: nothing for the empty clause; otherwise its abstraction and
    the next version of round (brought_in)."""
    if not literals:
        return []
    sources = clause_names(names, learned) + [name]
    return brought_in(templates, name, literals, round_version(names, learned), sources)


def propose_learned(names, clauses, frame, last_learned, learned, count, templates):
    """[ω] The ontology of learn: on a frame with a conflict, once, the clause derived by analysis
    with its certificate (start, chain), the level to go back to, and what it carries."""
    if frame is None or not frame["conflicts"]:
        return None
    if last_learned is not None and last_learned["round"] >= frame["round"]:
        return None
    start, chain, literals, level = analyze(clause_table(clauses, learned), frame)
    name = learned_name(count)
    return {"round": frame["round"], "name": name, "start": start, "chain": chain, "literals": literals,
            "level": level, "specifications": carried_for(names, learned, templates, name, literals)}


def resolves(table, start, chain, literals):
    """Whether the chain is a resolution derivation of the literals from known clauses: from the
    clause start, each step resolves with a known clause that contains the step's literal, on that
    literal, whose complement is in the clause derived so far; no step yields a tautology."""
    if start not in table:
        return False
    current = set(table[start])
    for step in chain:
        parent, literal = step["clause"], step["literal"]
        if parent not in table or literal not in table[parent] or -literal not in current:
            return False
        current = (current - {-literal}) | {other for other in table[parent] if other != literal}
        if any(-other in current for other in current):
            return False
    return len(literals) == len(set(literals)) and set(literals) == current


def check_learned(names, clauses, frame, last_learned, learned, count, templates, candidate):
    """[τ] The criterion of learn: on a frame with a conflict, once, starting from one of its false
    clauses, the chain derives the stated clause by resolution from clauses already known (D2: any
    derivation is admitted, not only the one to the first unique implication point); the level is
    a level of the trail, the name is the next one, and the clause carries exactly what
    carried_for gives for it."""
    if frame is None or not frame["conflicts"] or candidate["round"] != frame["round"]:
        return False
    if last_learned is not None and last_learned["round"] >= frame["round"]:
        return False
    name, literals = candidate["name"], candidate["literals"]
    if name != learned_name(count) or candidate["start"] not in frame["conflicts"]:
        return False
    if not resolves(clause_table(clauses, learned), candidate["start"], candidate["chain"], literals):
        return False
    if not 0 <= candidate["level"] <= frame["level"]:
        return False
    expected = carried_for(names, learned, templates, name, literals)
    return [without_authority(s) for s in candidate["specifications"]] == [without_authority(s) for s in expected]


# ---- adapt: the governed change of the decision policy ----

def propose_switch(after, learn_count, switches, upgrade):
    """[ω] The ontology of adapt: once `after` clauses are learned, carry version 2 of the ontology
    of decide (upgrade), stating the number of conflicts as its evidence."""
    if switches or learn_count < after:
        return None
    return {"conflicts": learn_count, "specifications": upgrade}


def check_switch(after, learn_count, switches, upgrade, candidate):
    """[τ] The criterion of adapt, the authority over the policy: once, on the evidence of at least
    `after` admitted conflicts, stated truly, carrying exactly the designated version of decide."""
    carried = candidate["specifications"]
    return (not switches and learn_count >= after and candidate["conflicts"] == learn_count
            and [without_authority(s) for s in carried] == [without_authority(s) for s in upgrade])


# ---- verdict: consensus, or the refutation ----

def propose_verdict(frame, learned, verdicts):
    """[ω] The ontology of verdict, once: unsatisfiable when the empty clause is learned;
    satisfiable when every clause voted on a total frame, the model being its trail."""
    if verdicts:
        return None
    if any(len(learned[name]) == 0 for name in learned):
        return {"sat": False, "model": []}
    if frame is not None and frame["votes"]:
        return {"sat": True, "model": sorted(assigned(frame["trail"]), key=abs)}
    return None


def check_verdict(formula, variables, names, frame, learned, verdicts, candidate):
    """[τ] The criterion of verdict, once. Satisfiable: the composite criterion τ = τ₁ ∧ … ∧ τₘ —
    every clause abstraction of the formula voted on the frame — and the model is its trail, a
    consistent assignment of every variable that satisfies every clause. Unsatisfiable: the empty
    clause was learned, with a derivation admitted by the criterion of learn."""
    if verdicts:
        return False
    if not candidate["sat"]:
        return candidate["model"] == [] and any(len(learned[name]) == 0 for name in learned)
    model = candidate["model"]
    named = [abs(literal) for literal in model]
    return (frame is not None and set(names) <= set(frame["votes"]) and set(model) == assigned(frame["trail"])
            and len(set(named)) == len(named) == len(variables) and all(var in variables for var in named)
            and all(satisfied(clause, set(model)) for clause in formula))
