"""Acceptance tests for the validator and the solver on every scenario file. They skip until that code exists."""
import copy

import pytest

from planner.data import ROOT, load_scenarios
from planner.solver import solve
from planner.validate import validate

EVERY = [e for path in sorted((ROOT / "scenarios").glob("*.json")) for e in load_scenarios(path.stem)]
S001 = next(e for e in EVERY if e["id"] == "S001")

# Edits to the S001 witness as (semester, course out, course in), and the rule ids the validator must report.
# It may report more (e.g. a workload break alongside). Each case was checked against the AY2026/27 data.
BROKEN = [
    ([("8", "ELECTIVE", "CS9999")], {"known"}),
    ([("8", "ELECTIVE", "CS2030S")], {"repeat"}),
    ([("2", None, "ELECTIVE")], {"horizon"}),
    ([("8", "ELECTIVE", "CS4234")], {"offered"}),  # Sem 1 only
    ([("4", "CS2103T", None), ("3", None, "CS2103T")], {"prereq", "same_semester", "workload"}),
    ([("8", "ELECTIVE", "CS3243")], {"preclusion"}),  # precluded by CS2109S and CS3263
    ([("4", None, "CS2108")], {"lecture_clash"}),  # with CS2109S
    ([("7", "ELECTIVE", "CS2107")], {"exam_clash"}),  # with CS4248
    ([("3", None, "ELECTIVE"), ("3", None, "ELECTIVE")], {"workload"}),  # 24 units
    ([("4", "CS2106", "ELECTIVE")], {"required"}),
    ([("7", "CS4248", "ELECTIVE")], {"focus_area"}),  # no level-4000 primary left
    ([("5", "CS3263", "ELECTIVE")], {"must_take"}),
]


def needs(fn, *args):
    try:
        return fn(*args)
    except NotImplementedError:
        pytest.skip(f"{fn.__module__}.{fn.__name__} is not written yet")


def edited(edits):
    plan = copy.deepcopy(S001["witness"])
    for k, out, into in edits:
        courses = plan["semesters"].setdefault(k, [])
        if out:
            courses.remove(out)
        if into:
            courses.append(into)
    return plan


@pytest.mark.parametrize("e", [e for e in EVERY if e["expected"] == "feasible"], ids=lambda e: e["id"])
def test_witness_is_valid(e):
    assert needs(validate, e["scenario"], e["witness"]) == []


@pytest.mark.parametrize("edits, rules", BROKEN, ids=[" ".join(sorted(r)) for _, r in BROKEN])
def test_validator_catches(edits, rules):
    assert rules <= {v["rule"] for v in needs(validate, S001["scenario"], edited(edits))}


@pytest.mark.parametrize("e", EVERY, ids=lambda e: e["id"])
def test_solver_agrees_with_label(e):
    plan = needs(solve, e["scenario"])
    assert plan["status"] == ("plan" if e["expected"] == "feasible" else "impossible")
    if plan["status"] == "plan":
        assert needs(validate, e["scenario"], plan) == []


def test_empty_semesters_before_the_current_one_are_fine():
    plan = edited([("1", None, None), ("2", None, None)])  # adds "1": [] and "2": []; S001 starts at semester 3
    assert needs(validate, S001["scenario"], plan) == []
