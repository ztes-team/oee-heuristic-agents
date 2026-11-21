"""Tests of scripts/sweeps.py and scripts/trials.py, the scripts behind the results of the paper over
many seeds and the worker trials.

The full sweeps take minutes; here each script is checked on what can be decided quickly: one run
per form gives the numbers of Table 7 for seed 7, the decompositions of the variance are those of
their definitions on tables built for the purpose, and one run by workers, under a random schedule
and with workers killed, gives the histories of the agenda.
"""
import importlib.util
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sweeps, trials = load("sweeps"), load("trials")


@pytest.mark.parametrize("name, chain, returns, moves", [
    ("v1", [1004, 985, 937], 14, 273),
    ("v2", [1004, 953, 937], 19, 280),
    ("v3", [1004, 985, 974, 937], 11, 271),
    ("v4", [1004, 985, 974, 937], 0, 255),
])
def test_one_run_per_form_gives_the_seed_7_columns_of_table_7(name, chain, returns, moves):
    C, kpi = sweeps.run("vns", 7, sweeps.FORMS[name])
    assert (sweeps.chain(C), kpi["returns"], kpi["moves"]) == (chain, returns, moves)


def test_the_strict_form_never_certifies_the_tour_it_shook():
    start = sweeps.System(sweeps.ROOT / "vns").definition["constants"]["START"]
    assert sweeps.first_return(sweeps.run("vns", 7, sweeps.FORMS["v4"])[0], start) is None
    assert sweeps.first_return(sweeps.run("vns", 7)[0], start) is not None


def test_a_draw_seed_and_a_world_seed_reach_the_record():
    one, two = sweeps.run("vns", 1)[0], sweeps.run("vns", 2)[0]
    assert sweeps.values(one, "draw") != sweeps.values(two, "draw")
    system = trials.system_of("vns-tw", draw=3, world=12)
    assert system.declared_sources["draw"]["random"]["seed"] == 3
    assert system.declared_sources["world"]["random"]["seed"] == 12


def test_paired_counts_shorter_longer_and_the_same():
    assert sweeps.paired([1, 2, 3, 4], [2, 2, 1, 4]) == (1, 1, 2)


def test_the_two_way_decomposition_is_that_of_its_definition():
    rows, cols = (1, 2), (1, 2, 3)
    additive = {(r, c): 10 * r + c for r in rows for c in cols}          # no interaction
    a, b, i = sweeps.shares(additive, rows, cols)
    assert (a, b, i) == (97.4, 2.6, 0.0)                                # rows: 150 of 154; columns: 4
    only_rows = {(r, c): r for r in rows for c in cols}
    assert sweeps.shares(only_rows, rows, cols) == (100, 0, 0)
    checker = {(r, c): (r + c) % 2 for r in (0, 1) for c in (0, 1)}     # pure interaction
    assert sweeps.shares(checker, (0, 1), (0, 1)) == (0, 0, 100)


def test_the_three_way_decomposition_is_that_of_its_definition():
    cube = {(a, b, c): a for a in (0, 1) for b in (0, 1) for c in (0, 1)}
    assert trials.shares3(cube) == (100, 0, 0, 0)
    cube = {(a, b, c): a + 2 * c for a in (0, 1) for b in (0, 1) for c in (0, 1)}
    assert trials.shares3(cube) == (20, 0, 80, 0)
    assert trials.shares3({(0, 0, 0): 5, (1, 1, 1): 5}) == (0, 0, 0, 0)    # no variance at all


def test_workers_under_a_random_schedule_and_killed_give_the_histories_of_the_agenda():
    expected = trials.lineages(trials.by_agenda("vns", None))
    C = trials.by_workers("vns", None, 1)
    assert trials.lineages(C) == expected and trials.verify(C) == []
    C, killed = trials.with_kills("vns", None, 1)
    assert killed > 0 and trials.lineages(C) == expected and trials.verify(C) == []
