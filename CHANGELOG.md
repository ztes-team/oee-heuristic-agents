# Changelog

Section, table and theorem numbers refer to version 4 of the base paper, *A Calculus of Execution
for Interacting Binary Relations* (https://doi.org/10.20944/preprints202608.1545.v4). The companion
paper, *Observable, Governable, Cooperative: Execution Analytics and Adaptive Heuristic Agents in the
OEE Calculus*, is in preparation and is named by its title only.

## 1.0.2 (2026-11-26)

No example and no record changed: the same plans give the same records, and the same checks pass.
What changed is the version of ZTES, how the repository refers to the two papers, and the
documentation.

**The papers**
* The README names both papers in a new section, "The two papers": the base paper by its new title
  and version 4 of the preprint, the companion paper by its title, in preparation. `CITATION.cff`
  and `.zenodo.json` cite the same.
* "The paper" no longer stands for two papers. References to the base paper give its v4 numbers
  (§8.9 and Table 8 for the examples, §7.1 for `sat4`). References to the companion paper give no
  numbers, because its numbering is not final; the scripts print their results under descriptive
  headings instead of table numbers.
* The `DESIGN.md` files of `vns`, `vns-atsp`, `vns-tw`, `vns-hk` and `vns-adaptive` no longer say
  that the examples are not in the base paper: it lists them in §8.9 and Table 8.
* "The same record under every schedule" now reads "the same history of every lineage under every
  schedule", which is what Theorem K gives and the tests check; the order of the whole record may
  differ (README, the `DESIGN.md` of `vns` and `ksat`, the notes in `system.json`).

**Documentation**
* `REPRODUCING.md`: every result of both papers that comes from this repository, with its command
  and its test.
* README: "Before you start" with the eight terms needed to read the output, "Repository layout"
  and "References". The table of tests moved to `docs/tests.md`.
* `ksat`, PHP(4,3): six clauses are learned and the sixth is the empty clause, so five are brought
  in as abstractions.
* `examples/vns-tw/DESIGN.md` reports a third execution of the asynchronous trials, on ZTES 0.1.1:
  4 of the 9 combinations changed their final tour with the schedule, and the shares of the variance
  were 23 %, 23 %, 0 % and 54 %. The asynchronous form depends on the schedule by design.

**ZTES**
* `requirements.txt` pins ZTES v0.1.1 (https://doi.org/10.5281/zenodo.24563789) instead of commit
  78153ed, and the links to its documentation point to that release. ZTES 0.1.1 fixes a race in the
  coordinator of workers: an abstraction brought in during a run, as a learned clause of `ksat` is,
  could be left uninvoked when the run was judged terminal. It also classifies case 3 of the eight
  defects as S1.2. Records under the agenda are unchanged.

## 1.0.1 (2026-11-21)

https://doi.org/10.5281/zenodo.24419725

* Scripts for every result that rests on many runs: `sweeps.py` (the forms over many seeds) and
  `trials.py` (workers under random schedules and with workers killed), with their tests
  (`tests/test_scripts.py`).

## 1.0.0 (2026-11-21)

https://doi.org/10.5281/zenodo.24416247

* `vns`, `vns-atsp`, `vns-tw`, `vns-hk`, `vns-adaptive`: cooperative variable neighborhood search,
  the asymmetric neighborhood and the certificate relative to the record, time windows under a
  recorded environment, Held–Karp city abstractions, and an adaptive agent.
* `cptl`, the exact reference case, with a native dynamic program; `sat4`, the two-clause worked
  example; `ksat`, k-SAT as evolutive consensus, every clause an abstraction.
* `scripts/profiles.py` (the KPI profiles), `scripts/timings.py` (the run and both replays of every
  example), `scripts/benchmark_cptl.py`, `scripts/benchmark_ksat.py` and `scripts/ksat_system.py`.
* ZTES pinned at commit 78153ed.
