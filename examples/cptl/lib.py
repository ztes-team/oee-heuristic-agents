def decision_order(guard_first):
    if guard_first:
        return [3, 1, 2, 4]
    return [1, 3, 2, 4]


def module_valid(bits, guard_first, order):
    if len(bits) != 4 or any(bit not in [0, 1] for bit in bits):
        return False
    if order != decision_order(guard_first):
        return False
    weights = [4, 3, 4, 3]
    if sum(bits) % 2 != 1 or sum(weights[i] * bits[i] for i in range(4)) >= 8:
        return False
    return guard_first or bits[0] == 0 or bits[1] != bits[3]


def transition_allowed(guard_first, incoming, link):
    # Three active bits weigh at least ten. Every valid module activates exactly one.
    return incoming == 0 or (guard_first and link == 0)


def terminal_row(size):
    # The right boundary requires a final link equal to one.
    return {"stage": size, "best": [-1, 0], "count": [0, 1]}


def suffix_row(stage, guard_first, tail):
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
    tail = terminal_row(len(guards)) if last["stage"] < 0 else last
    stage = tail["stage"] - 1
    if stage >= 0:
        return suffix_row(stage, guards[stage], tail)
    return None


def step(stage, incoming, link, guard_first, trial):
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
    if trial["stage"] >= 0 or previous["stage"] >= 0 or len(guards) < 2:
        return None
    return step(0, 0, 1, guards[0], True)


def tail_row(guards, rows, stage):
    if stage + 1 == len(guards):
        return terminal_row(len(guards))
    return rows.get(stage + 1)


def planned_link(guard_first, incoming, row, tail):
    for link in [1, 0]:
        if (transition_allowed(guard_first, incoming, link) and tail["count"][link]
                and row["best"][incoming] == link + tail["best"][link]):
            return link
    return None


def planned_step(guards, rows, previous):
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
    return (len(guards) > 1 and trial["stage"] == 0
            and not any(transition_allowed(guards[1], trial["link"], link) for link in [0, 1]))


def without_authority(specification):
    return {name: value for name, value in specification.items() if name != "criterion"}


def check_adaptation(guards, upgrade, made, trial, candidate):
    carried = candidate["specifications"]
    return (made == 0 and blocked_probe(guards, trial) and candidate["blocked_stage"] == 1
            and candidate["incoming"] == trial["link"] and len(carried) == 1
            and without_authority(carried[0]) == without_authority(upgrade[0]))
