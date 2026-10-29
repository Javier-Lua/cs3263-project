"""Tool-assisted step 2: find a plan that meets every rule in docs/design.md section 4, or show there is none.

Owner: Weng Mun. Suggested: OR-Tools CP-SAT (pip install ortools); encoding sketch in design.md section 6.2.
"""
import re
from datetime import datetime, timedelta
from itertools import combinations

from ortools.sat.python import cp_model

from planner.data import ELECTIVE, ELECTIVE_UNITS, catalog_for, load_catalogs, load_requirements, term


def level(code):
    """Course level from the code: the first digit times 1000, e.g. CS4248 -> 4000."""
    return int(re.search(r"\d", code).group()) * 1000


def lectures_clash(lectures_a, lectures_b):
    """True if two lecture lists ([[day, start, end], ...]) overlap. One ending exactly as the other starts is fine."""
    return any(day_a == day_b and start_a < end_b and start_b < end_a
               for day_a, start_a, end_a in lectures_a
               for day_b, start_b, end_b in lectures_b)


def exams_clash(exam_a, exam_b):
    """True if two exams ({"start": ISO time, "minutes": n}, or None for no exam) overlap."""
    if exam_a is None or exam_b is None:
        return False
    start_a = datetime.fromisoformat(exam_a["start"])
    start_b = datetime.fromisoformat(exam_b["start"])
    end_a = start_a + timedelta(minutes=exam_a["minutes"])
    end_b = start_b + timedelta(minutes=exam_b["minutes"])
    return start_a < end_b and start_b < end_a


def add_course_variables(model, scenario, completed):
    """Create one 0/1 variable for every course the student could take in each remaining semester.

    A variable exists only for a course that is offered in that semester (in the catalog of that semester's academic
    year) and that the student has not already completed, so rules 2 `repeat` (part) and 4 `offered` hold by
    construction.

    Returns (planned_in, details). planned_in[(course, semester)] is the variable, 1 when the course is taken in that
    semester. details[(course, semester)] holds that offering's "units", "prereq", "lectures" and "exam".
    """
    catalogs = load_catalogs()
    planned_in, details = {}, {}
    for semester in range(scenario["current_semester"], 9):
        academic_year, term_number = term(scenario["matric_ay"], semester)
        catalog, _ = catalog_for(catalogs, academic_year)
        for code, course in catalog["courses"].items():
            if code in completed or str(term_number) not in course["semesters"]:
                continue
            offering = course["semesters"][str(term_number)]
            planned_in[code, semester] = model.NewBoolVar(f"x_{code}_{semester}")
            details[code, semester] = {"units": course["units"], "prereq": course["prereq"],
                                       "lectures": offering["lectures"], "exam": offering["exam"]}
    return planned_in, details


def variables_by_course(planned_in):
    """{course: [its variables, one per semester it can still be taken in]}."""
    by_course = {}
    for (code, _), variable in planned_in.items():
        by_course.setdefault(code, []).append(variable)
    return by_course


def variables_of(codes, by_course):
    """The variables of these courses that can still be planned. A completed course has none."""
    return [variable for code in codes for variable in by_course.get(code, [])]


def add_each_course_at_most_once(model, by_course):
    """Rule 2 `repeat`: a course is planned at most once."""
    for variables in by_course.values():
        model.Add(sum(variables) <= 1)


def prereq_condition(model, tree, semester, planned_in, completed, first_semester):
    """Whether the prereq tree holds for a course taken in this semester. Only courses completed or planned in an
    earlier semester count.

    Returns True, False, or a variable that can be 1 only if the tree holds.
    """
    if tree is None or tree is True:
        return True
    if tree is False:
        return False
    if isinstance(tree, str):  # a single course code
        if tree in completed:
            return True
        planned_earlier = [planned_in[tree, earlier] for earlier in range(first_semester, semester)
                           if (tree, earlier) in planned_in]
        if not planned_earlier:
            return False
        holds = model.NewBoolVar(f"met_{tree}_{semester}")
        model.Add(sum(planned_earlier) >= 1).OnlyEnforceIf(holds)
        return holds
    ((operator, arguments),) = tree.items()  # {"and": [...]}, {"or": [...]} or {"nOf": [n, [...]]}
    if operator == "nOf":
        needed, arguments = arguments
    elif operator == "and":
        needed = len(arguments)
    else:
        needed = 1
    parts = [prereq_condition(model, argument, semester, planned_in, completed, first_semester)
             for argument in arguments]
    needed -= sum(part is True for part in parts)
    open_parts = [part for part in parts if not isinstance(part, bool)]
    if needed <= 0:
        return True
    if len(open_parts) < needed:
        return False
    holds = model.NewBoolVar(f"met_{operator}_{semester}")
    model.Add(sum(open_parts) >= needed).OnlyEnforceIf(holds)
    return holds


def add_prereq_rules(model, planned_in, details, completed, first_semester):
    """Rule 5 `prereq`: a course can be taken only if its prereq tree holds."""
    for (code, semester), variable in planned_in.items():
        condition = prereq_condition(model, details[code, semester]["prereq"], semester, planned_in, completed,
                                     first_semester)
        if condition is False:
            model.Add(variable == 0)
        elif condition is not True:
            model.AddImplication(variable, condition)


def add_clash_rules(model, planned_in, details, first_semester):
    """Rules 8 `lecture_clash` and 9 `exam_clash`: two courses whose lectures or exams overlap are not taken together."""
    for semester in range(first_semester, 9):
        codes = sorted(code for code, planned_semester in planned_in if planned_semester == semester)
        for code_a, code_b in combinations(codes, 2):
            a, b = details[code_a, semester], details[code_b, semester]
            if lectures_clash(a["lectures"], b["lectures"]) or exams_clash(a["exam"], b["exam"]):
                model.Add(planned_in[code_a, semester] + planned_in[code_b, semester] <= 1)


def add_preclusion_rules(model, by_course, completed):
    """Rule 7 `preclusion`: two courses that preclude each other (either lists the other, in any year's catalog) are not
    both taken."""
    precluding_pairs = {frozenset((code, precluded))
                        for catalog in load_catalogs().values()
                        for code, course in catalog["courses"].items()
                        for precluded in course["preclusions"]}
    for pair in precluding_pairs:
        code_a, code_b = pair
        if code_a in completed and code_b in completed:  # two completed courses can no longer be changed
            continue
        taken_count = sum(1 if code in completed else sum(variables_of([code], by_course)) for code in pair)
        model.Add(taken_count <= 1)


def add_same_semester_rules(model, planned_in, requirements, first_semester):
    """Rule 6 `same_semester`: for each pair, both courses are taken in the same semester."""
    for code_a, code_b in requirements["same_semester"]:
        for semester in range(first_semester, 9):
            variable_a = planned_in.get((code_a, semester))
            variable_b = planned_in.get((code_b, semester))
            if variable_a is not None and variable_b is not None:
                model.Add(variable_a == variable_b)
            else:  # one is missing: already completed (so the other can't share its semester) or not offered then
                for variable in (variable_a, variable_b):
                    if variable is not None:
                        model.Add(variable == 0)


def add_required_and_must_take_rules(model, scenario, requirements, by_course, completed):
    """Rules 11 `required` and 13 `must_take`: every required course and every course the student insists on is taken."""
    wanted = set(requirements["required"]) | set(scenario["must_take"])
    for code in wanted - completed:
        model.Add(sum(variables_of([code], by_course)) >= 1)


def add_focus_area_rule(model, scenario, requirements, by_course, completed):
    """Rule 12 `focus_area`: enough primaries of the student's focus area are taken, and enough of them are level 4000
    or above."""
    primaries = requirements["focus_areas"][scenario["focus_area"]]
    rule = requirements["focus_area_rule"]
    completed_primaries = [code for code in primaries if code in completed]
    model.Add(len(completed_primaries) + sum(variables_of(primaries, by_course)) >= rule["min_primaries"])
    completed_level_4000 = sum(level(code) >= 4000 for code in completed_primaries)
    planned_level_4000 = variables_of([code for code in primaries if level(code) >= 4000], by_course)
    model.Add(completed_level_4000 + sum(planned_level_4000) >= rule["min_primaries_level_4000"])


def add_workload_rules(model, scenario, planned_in, details):
    """Rule 10 `workload`: every remaining semester has between min_units and max_units. The gap is filled with
    ELECTIVE slots of 4 units each.

    Returns elective_slots[semester], the number of ELECTIVE slots in that semester.
    """
    slots_at_most = max(scenario["max_units"], 0) // ELECTIVE_UNITS
    elective_slots = {semester: model.NewIntVar(0, slots_at_most, f"e_{semester}")
                      for semester in range(scenario["current_semester"], 9)}
    for semester, slots in elective_slots.items():
        course_units = sum(details[code, planned_semester]["units"] * variable
                           for (code, planned_semester), variable in planned_in.items() if planned_semester == semester)
        total_units = course_units + ELECTIVE_UNITS * slots
        model.Add(total_units >= scenario["min_units"])
        model.Add(total_units <= scenario["max_units"])
    return elective_slots


def build_model(scenario):
    """Return (model, planned_in, elective_slots): planned_in[(course, semester)] is 1 when the course is taken in that
    semester, and elective_slots[semester] is the number of ELECTIVE slots in that semester."""
    first_semester = scenario["current_semester"]
    if not 1 <= first_semester <= 8:
        raise ValueError(f"current_semester must be 1-8, got {first_semester}")
    completed = set(scenario["completed"])

    model = cp_model.CpModel()
    planned_in, details = add_course_variables(model, scenario, completed)
    by_course = variables_by_course(planned_in)
    requirements = load_requirements(scenario["matric_ay"])

    add_each_course_at_most_once(model, by_course)
    add_prereq_rules(model, planned_in, details, completed, first_semester)
    add_clash_rules(model, planned_in, details, first_semester)
    add_preclusion_rules(model, by_course, completed)
    add_same_semester_rules(model, planned_in, requirements, first_semester)
    add_required_and_must_take_rules(model, scenario, requirements, by_course, completed)
    add_focus_area_rule(model, scenario, requirements, by_course, completed)
    elective_slots = add_workload_rules(model, scenario, planned_in, details)
    return model, planned_in, elective_slots


def solve(scenario):
    """Return {"status": "plan", "semesters": {...}} or {"status": "impossible"} (design.md section 5)."""
    model, planned_in, elective_slots = build_model(scenario)
    solver = cp_model.CpSolver()
    if solver.Solve(model) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": "impossible"}
    semesters = {}
    for semester, slots in elective_slots.items():
        courses = sorted(code for (code, planned_semester), variable in planned_in.items()
                         if planned_semester == semester and solver.Value(variable))
        semesters[str(semester)] = courses + [ELECTIVE] * solver.Value(slots)
    return {"status": "plan", "semesters": semesters}
