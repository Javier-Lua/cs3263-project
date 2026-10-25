"""Unit tests for the solver. Each scenario here is small and checked by hand."""
import pytest
from ortools.sat.python import cp_model

from planner.data import catalog_for, load_catalogs, load_requirements, term
from planner.solver import build_model, solve

REQUIRED = load_requirements("2025-2026")["required"]
DONE = REQUIRED + ["CS3263", "CS4248"]  # also meets the AI focus area, so nothing is forced


def scenario(**overrides):
    base = {"matric_ay": "2025-2026", "current_semester": 7, "completed": [], "focus_area": "Artificial Intelligence",
            "min_units": 0, "max_units": 40, "must_take": []}
    return {**base, **overrides}


def max_courses(s):
    """Solve the model while taking as many courses as possible, so the variables are actually exercised."""
    model, x, _ = build_model(s)
    model.Maximize(sum(x.values()))
    solver = cp_model.CpSolver()
    assert solver.Solve(model) == cp_model.OPTIMAL
    return x, {key: solver.Value(v) for key, v in x.items()}


def test_variables_exist_only_for_offered_courses():
    s = scenario(completed=DONE)
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
    plan = solve(scenario(current_semester=7, completed=DONE))
    assert plan["status"] == "plan"
    assert set(plan["semesters"]) == {"7", "8"}


@pytest.mark.parametrize("k", [0, 9])
def test_current_semester_must_be_1_to_8(k):
    with pytest.raises(ValueError):
        solve(scenario(current_semester=k))


def planned(plan):
    return {c for courses in plan["semesters"].values() for c in courses}


def test_required_courses_are_planned_unless_completed():
    done = ["CS1101S", "CS1231S", "MA1521", "MA1522"]
    plan = solve(scenario(current_semester=3, completed=done))
    assert plan["status"] == "plan"
    assert set(REQUIRED) <= set(done) | planned(plan)


def test_nothing_needs_planning_when_the_rules_are_already_met():
    assert solve(scenario(completed=DONE))["status"] == "plan"


def test_must_take_course_is_planned():
    plan = solve(scenario(completed=REQUIRED, must_take=["CS4234"]))
    assert "CS4234" in planned(plan)


def test_must_take_course_that_is_not_offered_in_the_remaining_semesters_is_impossible():
    s = scenario(current_semester=8, completed=REQUIRED, must_take=["CS4234"])  # CS4234 runs in Sem 1 only
    assert solve(s) == {"status": "impossible"}


def test_must_take_course_outside_the_catalog_is_impossible():
    assert solve(scenario(completed=REQUIRED, must_take=["CS9999"])) == {"status": "impossible"}


def test_focus_area_needs_three_primaries():
    # In Sem 2 only CS2108 and CS4248 of Multimedia IR can be planned.
    s = scenario(current_semester=8, completed=REQUIRED, focus_area="Multimedia Information Retrieval")
    assert solve(s) == {"status": "impossible"}
    plan = solve({**s, "completed": REQUIRED + ["CS3245"]})  # a completed primary still counts
    assert {"CS2108", "CS4248"} <= planned(plan)


def test_focus_area_needs_a_level_4000_primary():
    # Three completed HCI primaries, none at level 4000: CS4249 is the only one offered in Sem 2.
    s = scenario(current_semester=8, completed=REQUIRED + ["CS2111", "CS3240", "CS3249"],
                 focus_area="Human-Computer Interaction")
    assert "CS4249" in planned(solve(s))


def units_per_semester(s, plan):
    catalogs = load_catalogs()
    result = {}
    for k, courses in plan["semesters"].items():
        courses_in_year = catalog_for(catalogs, term(s["matric_ay"], int(k))[0])[0]["courses"]
        result[int(k)] = sum(4 if c == "ELECTIVE" else courses_in_year[c]["units"] for c in courses)
    return result


def test_every_open_semester_stays_within_the_unit_limits():
    s = scenario(current_semester=3, completed=["CS1101S", "CS1231S", "MA1521", "MA1522"], min_units=16, max_units=20)
    plan = solve(s)
    assert plan["status"] == "plan"
    units = units_per_semester(s, plan)
    assert set(units) == {3, 4, 5, 6, 7, 8}
    assert all(16 <= u <= 20 for u in units.values()), units


def test_semesters_with_no_courses_to_take_are_filled_with_electives():
    # Nothing is left to plan, so with a 4-unit minimum every semester needs something: only ELECTIVE can fill it.
    s = scenario(completed=REQUIRED + ["CS3263", "CS4248"], min_units=4, max_units=4)
    plan = solve(s)
    assert units_per_semester(s, plan) == {7: 4, 8: 4}


def test_unit_limits_can_make_the_required_courses_impossible():
    left = ["CS2106", "CS3230", "ST2334"]  # 12 units, all offered in Sem 2
    s = scenario(current_semester=8, completed=[c for c in REQUIRED if c not in left] + ["CS3263", "CS4248"])
    assert solve({**s, "max_units": 8}) == {"status": "impossible"}
    assert planned(solve({**s, "max_units": 12})) >= set(left)


def test_min_units_above_max_units_is_impossible():
    assert solve(scenario(min_units=20, max_units=16)) == {"status": "impossible"}


def semester_of(plan, code):
    return next(int(k) for k, courses in plan["semesters"].items() if code in courses)


def prereq_met(tree, taken):
    """Independent check of a catalog prereq tree against the set of courses taken earlier."""
    if tree is None or tree is True:
        return True
    if tree is False:
        return False
    if isinstance(tree, str):
        return tree in taken
    ((op, args),) = tree.items()
    if op == "nOf":
        n, args = args
        return sum(prereq_met(a, taken) for a in args) >= n
    return (all if op == "and" else any)(prereq_met(a, taken) for a in args)


def test_every_planned_course_has_its_prerequisites_taken_earlier():
    catalogs = load_catalogs()
    for s in [scenario(current_semester=3, completed=["CS1101S", "CS1231S", "MA1521", "MA1522"], must_take=["CS3263"]),
              scenario(current_semester=1, must_take=["CS3264", "CS4234"])]:
        plan = solve(s)
        assert plan["status"] == "plan"
        taken = set(s["completed"])
        for k in range(s["current_semester"], 9):
            courses = catalog_for(catalogs, term(s["matric_ay"], k)[0])[0]["courses"]
            for c in plan["semesters"][str(k)]:
                if c != "ELECTIVE":
                    assert prereq_met(courses[c]["prereq"], taken), (c, k)
            taken |= set(plan["semesters"][str(k)])


def test_prerequisite_comes_in_an_earlier_semester():
    # CS4234 (Sem 1 only) needs MA1522 and CS3230. CS3230 is not completed, so it must be planned first.
    s = scenario(current_semester=5, completed=[c for c in DONE if c != "CS3230"], must_take=["CS4234"])
    plan = solve(s)
    assert semester_of(plan, "CS3230") < semester_of(plan, "CS4234")


def test_a_prerequisite_in_the_same_semester_does_not_count():
    # Only semester 7 is a Sem 1 in the horizon, so CS3230 would have to share it with CS4234.
    s = scenario(current_semester=7, completed=[c for c in DONE if c != "CS3230"], must_take=["CS4234"])
    assert solve(s) == {"status": "impossible"}


def test_a_course_with_an_unmeetable_prerequisite_is_never_planned():
    # CS3242 needs physics, which the catalog cannot express, so its prereq is false.
    assert solve(scenario(completed=DONE, must_take=["CS3242"])) == {"status": "impossible"}
    assert solve(scenario(completed=DONE + ["CS3242"]))["status"] == "plan"  # but it can already be completed


def test_a_course_cannot_be_planned_if_a_completed_course_precludes_it():
    # CS2109S (completed) precludes CS3243, whose own prereqs CS2040S and CS1231S are met and which runs in Sem 2.
    assert solve(scenario(completed=DONE, must_take=["CS3243"])) == {"status": "impossible"}


def test_two_planned_courses_cannot_preclude_each_other():
    # CS2109S still has to be planned (it is required); CS3243 is precluded by it, both listed in each other's catalog entry.
    s = scenario(completed=[c for c in REQUIRED if c != "CS2109S"] + ["CS3219", "CS4218"], focus_area="Software Engineering")
    plan = solve(s)
    assert plan["status"] == "plan" and "CS2109S" in planned(plan)
    assert solve({**s, "must_take": ["CS3243"]}) == {"status": "impossible"}


def test_a_preclusion_listed_in_only_one_direction_still_applies():
    # Only CS4263's entry lists CS2109S; CS2109S's own entry does not list CS4263.
    assert solve(scenario(completed=DONE, must_take=["CS4263"])) == {"status": "impossible"}


def test_completed_courses_that_preclude_each_other_are_not_an_error():
    assert solve(scenario(completed=DONE + ["CS3243"]))["status"] == "plan"


def test_cs2101_and_cs2103t_are_planned_in_the_same_semester():
    s = scenario(current_semester=5, completed=[c for c in DONE if c not in ("CS2101", "CS2103T")])
    plan = solve(s)
    assert semester_of(plan, "CS2101") == semester_of(plan, "CS2103T")


def test_cs2101_and_cs2103t_cannot_be_split_across_completed_and_planned():
    assert solve(scenario(completed=[c for c in DONE if c != "CS2103T"])) == {"status": "impossible"}


def test_the_same_semester_rule_can_make_a_scenario_impossible():
    # Exactly 4 units a semester: CS2101 and CS2103T (4 units each) fit in separate semesters but not in the same one.
    s = scenario(current_semester=5, completed=[c for c in DONE if c not in ("CS2101", "CS2103T")],
                 min_units=4, max_units=4)
    assert solve(s) == {"status": "impossible"}
    assert solve({**s, "max_units": 8, "min_units": 0})["status"] == "plan"
