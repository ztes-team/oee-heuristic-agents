# Helper functions shared by the specifications of the cptl system.
# A specification receives a copy of the helpers it uses, so its recorded form stays self-contained.
# No helper contains an unbounded loop: every loop runs over the four bits of a stage or the two
# values of a link. The path itself is not a loop here: the suffix rows and the route are lineages
# of the record, one event per stage.

def decision_order(guard_first):
    """The declared order of the four decisions of a stage: guard-first decides x3 before x1,
    input-first x1 before x3. A stage witness must state the order of its stage's gate mode."""
    if guard_first:
        return [3, 1, 2, 4]
    return [1, 3, 2, 4]


def module_valid(bits, guard_first, order):
    """[τ] Whether four bits are a valid stage witness: odd parity, total weight below 8 with the
    weights (4, 3, 4, 3), the order of the gate mode, and, under input-first precedence, x1 = 1
    only with x2 ⊕ x4 = 1 (which the parity and the budget then forbid)."""
    if len(bits) != 4 or any(bit not in [0, 1] for bit in bits):
        return False
    if order != decision_order(guard_first):
        return False
    weights = [4, 3, 4, 3]
    if sum(bits) % 2 != 1 or sum(weights[i] * bits[i] for i in range(4)) >= 8:
        return False
    return guard_first or bits[0] == 0 or bits[1] != bits[3]


def transition_allowed(guard_first, incoming, link):
    """The projected local relation: whether a stage with this gate mode can pass from the incoming
    link to the outgoing one. From 0 both are possible; from 1 only 0, and only at a guard-first
    gate (tests/test_cptl.py checks it against all 16 assignments of a stage)."""
    # Three active bits weigh at least ten. Every valid module activates exactly one.
    return incoming == 0 or (guard_first and link == 0)


def terminal_row(size):
    """[C] The row after the last stage: the boundary b_k = 1 is the only feasible end, with value 0
    and one completion; -1 stands for no feasible completion."""
    # The right boundary requires a final link equal to one.
    return {"stage": size, "best": [-1, 0], "count": [0, 1]}


def suffix_row(stage, guard_first, tail):
    """[ω] The suffix row of a stage from the row after it: for each incoming link, the best sum of
    the remaining links and the number of feasible remaining link words (Bellman recurrence)."""
    best, count = [], []
    for incoming in [0, 1]:
        scores = []
        completions = 0
        for link in [0, 1]:
            if transition_allowed(guard_first, incoming, link) and tail["count"][link]:
                scores.append(link + tail["best"][link])
                completions += tail["count"][link]
        best.append(max(scores) if scores else -1)
        count.append(completions)
    return {"stage": stage, "best": best, "count": count}


def next_row(guards, last):
    """[ω][τ] The next suffix row to record, working back from the terminal boundary; None once
    the row of stage 0 is recorded. The criterion of suffix admits exactly this row."""
    tail = terminal_row(len(guards)) if last["stage"] < 0 else last
    stage = tail["stage"] - 1
    if stage >= 0:
        return suffix_row(stage, guards[stage], tail)
    return None


def step(stage, incoming, link, guard_first, trial):
    """A route step: the stage, its incoming and outgoing links, the one active bit that realizes
    them, and the declared order of its gate mode; trial marks the greedy probe."""
    if incoming:
        bits = [1, 0, 0, 0]
    elif link:
        bits = [0, 0, 0, 1]
    else:
        bits = [0, 1, 0, 0]
    return {
        "stage": stage, "incoming": incoming, "link": link, "trial": trial,
        "bits": bits, "order": decision_order(guard_first),
    }


def greedy_probe(guards, trial, previous):
    """[ω] Ontology v1 of route: once, at the start, the greedy trial b_1 = 1 at stage 0; nothing
    afterwards."""
    if trial["stage"] >= 0 or previous["stage"] >= 0 or len(guards) < 2:
        return None
    return step(0, 0, 1, guards[0], True)


def tail_row(guards, rows, stage):
    """[C] The recorded row after a stage, or the terminal row after the last; None if not yet
    recorded."""
    if stage + 1 == len(guards):
        return terminal_row(len(guards))
    return rows.get(stage + 1)


def planned_link(guard_first, incoming, row, tail):
    """The outgoing link that attains the recorded optimum of the row, preferring 1; None if none
    does."""
    for link in [1, 0]:
        if (transition_allowed(guard_first, incoming, link) and tail["count"][link]
                and row["best"][incoming] == link + tail["best"][link]):
            return link
    return None


def planned_step(guards, rows, previous):
    """[ω] Ontology v2 of route: the next committed step, chosen from the recorded suffix rows;
    None after the last stage or while a row it needs is not yet recorded."""
    stage = previous["stage"] + 1
    if stage == len(guards):
        return None
    row, tail = rows.get(stage), tail_row(guards, rows, stage)
    if row is None or tail is None:
        return None
    link = planned_link(guards[stage], previous["link"], row, tail)
    if link is None:
        return None
    return step(stage, previous["link"], link, guards[stage], False)


def check_step(guards, rows, trial, previous, candidate):
    """[τ] The criterion of route. Every step is a valid stage witness whose links are its first and
    last bit. A trial is admitted only at stage 0, before any other step. A committed step must
    continue the previous committed step (next stage, same link) and attain the optimum stated by
    the recorded suffix row of its stage, with a feasible remainder."""
    stage = candidate["stage"]
    incoming, link = candidate["incoming"], candidate["link"]
    bits = candidate["bits"]
    if not 0 <= stage < len(guards) or not module_valid(bits, guards[stage], candidate["order"]):
        return False
    if (incoming, link) != (bits[0], bits[3]):
        return False
    if candidate["trial"]:
        return stage == 0 and incoming == 0 and trial["stage"] < 0 and previous["stage"] < 0
    if stage != previous["stage"] + 1 or incoming != previous["link"]:
        return False
    row, tail = rows.get(stage), tail_row(guards, rows, stage)
    return (row is not None and tail is not None and tail["count"][link] > 0
            and row["best"][incoming] == link + tail["best"][link])


def blocked_probe(guards, trial):
    """[C] Whether the recorded trial is obstructed: no outgoing link of stage 2 is reachable from
    its link."""
    return (len(guards) > 1 and trial["stage"] == 0
            and not any(transition_allowed(guards[1], trial["link"], link) for link in [0, 1]))


def without_authority(specification):
    """A carried specification as written, without the criterion that Z₀ binds a carried ontology
    to."""
    return {name: value for name, value in specification.items() if name != "criterion"}


def check_adaptation(guards, upgrade, made, trial, candidate):
    """[τ] The criterion of adapt, the authority over the change of policy: once, only when the
    recorded trial is obstructed, stating the obstruction truly, and carrying exactly the designated
    version of the route ontology."""
    carried = candidate["specifications"]
    return (made == 0 and blocked_probe(guards, trial) and candidate["blocked_stage"] == 1
            and candidate["incoming"] == trial["link"] and len(carried) == 1
            and without_authority(carried[0]) == without_authority(upgrade[0]))
