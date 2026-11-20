# Helper functions shared by the specifications of the sat4 system.
# A specification receives a copy of the helpers it uses, so its recorded form stays self-contained.
# A literal is a signed variable number (-2 is "not a"); a clause and an assignment are lists of
# literals. No helper contains an unbounded loop: every loop runs over the literals of a clause, the
# clauses of the formula and the learned clause, or the variables.

def consistent_assignment(variables, assignment):
    """Whether an assignment gives each of its variables one value, and only variables of the
    formula."""
    assigned = [abs(literal) for literal in assignment]
    return len(set(assigned)) == len(assigned) and all(var in variables for var in assigned)


def check_branch(variables, branches, candidate):
    """[τ] The criterion of branch: the next branch, whose assumptions are a consistent assignment of
    variables of the formula. Which branch to try is the ontology's choice (D2): version 1 proposes
    the probe and nothing after it, and the retry rule is in force only from the governing event of
    adapt that carries version 2 (R1). The later steps are checked against the original clauses and
    their admitted resolvents, so any branch admitted here leaves the conflict, the resolvent and
    the witness sound."""
    return candidate["id"] == len(branches) and consistent_assignment(variables, candidate["assumptions"])


def unit_literal(clause, assignment):
    """The literal a clause forces under an assignment: None if the clause is already satisfied or
    has more or less than one literal left unassigned."""
    if any(literal in assignment for literal in clause):
        return None
    remaining = [literal for literal in clause if -literal not in assignment]
    return remaining[0] if len(remaining) == 1 else None


def available_clauses(formula, learned):
    """[C] The clauses visible to propagation: the original ones (indices 0 and 1) followed by the
    admitted resolvents."""
    return formula + [proof["literals"] for proof in learned]


def propose_unit(formula, branches, propagations, learned):
    """[ω] The propagation of the latest branch: the first visible clause that is unit under its
    assumptions, as reason, with the literal it forces; None if the branch is already propagated."""
    if len(branches) != len(propagations) + 1:
        return None
    branch = branches[-1]
    clauses = available_clauses(formula, learned)
    for index in range(len(clauses)):
        literal = unit_literal(clauses[index], branch["assumptions"])
        if literal is not None:
            return {"branch": branch["id"], "reason": index, "literal": literal}
    return None


def check_unit(formula, branches, propagations, learned, candidate):
    """[τ] The criterion of propagate: a propagation of the latest branch whose stated reason is a
    visible clause that forces exactly the stated literal under the branch's assumptions."""
    if len(branches) != len(propagations) + 1:
        return False
    branch = branches[-1]
    clauses = available_clauses(formula, learned)
    index = candidate["reason"]
    return (candidate["branch"] == branch["id"] and 0 <= index < len(clauses)
            and unit_literal(clauses[index], branch["assumptions"]) == candidate["literal"])


def trial_assignment(branches, propagations, conflicts):
    """[C] The first branch with its propagated literal, while no conflict is recorded; None
    otherwise."""
    if len(branches) == 1 and len(propagations) == 1 and not conflicts:
        return branches[0]["assumptions"] + [propagations[0]["literal"]]
    return None


def falsified(clause, assignment):
    """Whether every literal of a clause is false under an assignment."""
    return all(-literal in assignment for literal in clause)


def propose_conflict(formula, branches, propagations, conflicts):
    """[ω] The first original clause that the propagated first branch falsifies, if any."""
    assignment = trial_assignment(branches, propagations, conflicts)
    if assignment is None:
        return None
    for index in range(len(formula)):
        if falsified(formula[index], assignment):
            return {"branch": branches[0]["id"], "clause": index}
    return None


def check_conflict(formula, branches, propagations, conflicts, candidate):
    """[τ] The criterion of conflict: the stated original clause is falsified by the first branch
    with its propagated literal, and the conflict names that branch."""
    assignment = trial_assignment(branches, propagations, conflicts)
    index = candidate["clause"]
    return (assignment is not None and candidate["branch"] == branches[0]["id"]
            and 0 <= index < len(formula) and falsified(formula[index], assignment))


def resolution_certificate(formula, propagations, conflicts):
    """[ω][τ] The resolvent of the reason clause of the first propagation and the conflict clause,
    both original: the pivot is the propagated variable, positive in the reason and negative in
    the conflict clause, and the resolvent is the union of the other literals. None if the parents
    do not clash on the pivot or the resolvent would be a tautology. Since both parents are clauses
    of the formula, the formula implies the resolvent in every branch."""
    if not propagations or not conflicts:
        return None
    unit, conflict = propagations[0], conflicts[0]
    left, right = unit["reason"], conflict["clause"]
    if unit["branch"] != conflict["branch"] or not (0 <= left < len(formula) and 0 <= right < len(formula)):
        return None
    literal = unit["literal"]
    if literal not in formula[left] or -literal not in formula[right]:
        return None
    pivot = abs(literal)
    # Remove the pivot from the two original clauses, then merge their other literals.
    literals = sorted({value for value in formula[left] + formula[right] if abs(value) != pivot})
    if any(-value in literals for value in literals):
        return None
    return {"left": left, "right": right, "pivot": pivot, "literals": literals}


def without_authority(specification):
    """A carried specification as written, without the criterion that Z₀ binds a carried ontology
    to."""
    return {name: value for name, value in specification.items() if name != "criterion"}


def check_switch(conflicts, learned, switches, upgrade, candidate):
    """[τ] The criterion of adapt, the authority over the change of policy: once, after a recorded
    conflict and its admitted resolvent, stating the number of conflicts truly, and carrying
    exactly the designated version of the branch ontology."""
    carried = candidate["specifications"]
    return (not switches and len(conflicts) > 0 and len(learned) == 1
            and candidate["conflicts"] == len(conflicts) and len(carried) == 1
            and without_authority(carried[0]) == without_authority(upgrade[0]))


def retry_assignment(branches, propagations):
    """[C] The retry with its propagated literal, once both are recorded; None otherwise."""
    if len(branches) == len(propagations) == 2:
        return branches[-1]["assumptions"] + [propagations[-1]["literal"]]
    return None


def propose_witness(variables, branches, propagations):
    """[ω] A full assignment that extends the propagated retry, the other variables false."""
    assignment = retry_assignment(branches, propagations)
    if assignment is None:
        return None
    # Once c is forced, this instance allows either sign of x. Choose false.
    return [var if var in assignment else -var for var in variables]


def check_witness(formula, variables, branches, propagations, candidate):
    """[τ] The criterion of witness: a consistent assignment of every variable that extends the
    propagated retry and satisfies every original clause. Any model that extends the retry is
    admitted, not only the one the ontology chose (D2)."""
    prefix = retry_assignment(branches, propagations)
    return (prefix is not None and len(candidate) == len(variables)
            and consistent_assignment(variables, candidate)
            and all(literal in candidate for literal in prefix)
            and all(any(literal in candidate for literal in clause) for clause in formula))
