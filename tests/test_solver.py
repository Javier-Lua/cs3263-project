"""Unit tests for the solver. Each scenario here is small and checked by hand."""
import pytest
from ortools.sat.python import cp_model

from planner.data import catalog_for, load_catalogs, term
from planner.solver import build_model, solve


def scenario(**overrides):
    base = {"matric_ay": "2025-2026", "current_semester": 7, "completed": [], "focus_area": "Artificial Intelligence",
            "min_units": 0, "max_units": 40, "must_take": []}
    return {**base, **overrides}


def max_courses(s):
    """Solve the model while taking as many courses as possible, so the variables are actually exercised."""
    model, x = build_model(s)
    model.Maximize(sum(x.values()))
    solver = cp_model.CpSolver()
    assert solver.Solve(model) == cp_model.OPTIMAL
    return x, {key: solver.Value(v) for key, v in x.items()}


def test_variables_exist_only_for_offered_courses():
    s = scenario()
    x, _ = max_courses(s)
    catalogs = load_catalogs()
    for code, k in x:
        ay, sem = term(s["matric_ay"], k)
        assert str(sem) in catalog_for(catalogs, ay)[0]["courses"][code]["semesters"], (code, k)
    assert ("CS4234", 7) in x and ("CS4234", 8) not in x  # CS4234 runs in Sem 1 only


def test_no_variables_before_current_semester_or_for_completed_courses():
    x, _ = max_courses(scenario(current_semester=5, completed=["CS1101S", "CS2040S"]))
    assert {k for _, k in x} == {5, 6, 7, 8}
    assert not {c for c, _ in x} & {"CS1101S", "CS2040S"}


def test_each_course_is_taken_at_most_once():
    x, value = max_courses(scenario(current_semester=3))
    for code in {c for c, _ in x}:
        assert sum(v for (c, _), v in value.items() if c == code) <= 1, code


def test_solve_returns_a_semester_for_every_open_term():
    plan = solve(scenario(current_semester=7))
    assert plan["status"] == "plan"
    assert set(plan["semesters"]) == {"7", "8"}


@pytest.mark.parametrize("k", [0, 9])
def test_current_semester_must_be_1_to_8(k):
    with pytest.raises(ValueError):
        solve(scenario(current_semester=k))
