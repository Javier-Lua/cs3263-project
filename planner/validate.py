"""Check a plan against the rules in docs/design.md section 4. Owner: Zechary (proposed).

Share no code with planner/solver.py, so a solver bug can't hide in the checker too. Read data only through planner.data.
"""

from datetime import datetime, timedelta
from itertools import combinations
import re

from planner.data import ELECTIVE, ELECTIVE_UNITS, catalog_for, load_catalogs, load_requirements, term


def _violation(rule, courses, detail, semester=None):
    """Build one consistently shaped violation record."""
    result = {"rule": rule, "courses": sorted(courses), "detail": detail}
    if semester is not None:
        result["semester"] = semester
    return result


def _prereq_met(tree, taken):
    """Evaluate a catalog prerequisite tree against courses taken *before* a term."""
    if tree is None or tree is True:
        return True
    if tree is False:
        return False
    if isinstance(tree, str):
        return tree in taken

    ((operator, values),) = tree.items()
    if operator == "and":
        return all(_prereq_met(value, taken) for value in values)
    if operator == "or":
        return any(_prereq_met(value, taken) for value in values)
    if operator == "nOf":
        needed, values = values
        return sum(_prereq_met(value, taken) for value in values) >= needed
    raise ValueError(f"unknown prerequisite operator: {operator}")


def _lectures_clash(first, second):
    """Whether two lecture lists overlap. Adjacent sessions do not clash."""
    return any(
        day_a == day_b and start_a < end_b and start_b < end_a
        for day_a, start_a, end_a in first
        for day_b, start_b, end_b in second
    )


def _exams_clash(first, second):
    """Whether two optional exams overlap. Adjacent exams do not clash."""
    if first is None or second is None:
        return False
    start_a = datetime.fromisoformat(first["start"])
    start_b = datetime.fromisoformat(second["start"])
    end_a = start_a + timedelta(minutes=first["minutes"])
    end_b = start_b + timedelta(minutes=second["minutes"])
    return start_a < end_b and start_b < end_a


def _level(code):
    """Return a course's thousand-level from its code (e.g. CS4248 -> 4000)."""
    match = re.search(r"\d", code)
    return int(match.group()) * 1000 if match else 0


def _plan_by_semester(plan):
    """Return integer semester keys where possible, retaining malformed keys for horizon errors."""
    result = {}
    for raw_semester, courses in plan.get("semesters", {}).items():
        try:
            semester = int(raw_semester)
        except (TypeError, ValueError):
            semester = raw_semester
        result.setdefault(semester, []).extend(courses if isinstance(courses, list) else [])
    return result


def validate(scenario, plan):
    """Return the list of rule violations; [] means the plan is valid.

    plan is {"status": "plan", "semesters": {"3": ["CS2030S", ...], ...}}. Each violation is a dict like
    {"rule": "prereq", "semester": 4, "courses": ["CS2103T"], "detail": "needs CS2030S before semester 4"},
    where "rule" is one of the ids in design.md section 4.
    """
    catalogs = load_catalogs()
    requirements = load_requirements(scenario["matric_ay"])
    k0 = scenario["current_semester"]
    completed = set(scenario["completed"])
    by_semester = _plan_by_semester(plan)
    violations = []

    known = set().union(*(catalog["courses"] for catalog in catalogs.values()))
    planned_entries = [
        (semester, code)
        for semester, courses in by_semester.items()
        for code in courses
    ]

    # 1. A code can be known in one AY but absent from another; `known` deliberately
    # checks the union, while `offered` checks the catalog for the planned term.
    for semester, code in planned_entries:
        if code != ELECTIVE and code not in known:
            violations.append(_violation("known", [code], "course is not in any catalog", semester))

    # 2. ELECTIVE is the sole repeatable plan entry.
    locations = {}
    for semester, code in planned_entries:
        if code != ELECTIVE:
            locations.setdefault(code, []).append(semester)
    for code, semesters in locations.items():
        if code in completed:
            violations.append(_violation("repeat", [code], "course was already completed"))
        if len(semesters) > 1:
            violations.append(_violation("repeat", [code], "course is planned more than once"))

    # 3. Preserve every entry under a bad semester key so it cannot disappear
    # silently during the remaining checks.
    for semester, courses in by_semester.items():
        if not isinstance(semester, int) or not k0 <= semester <= 8:
            violations.append(_violation("horizon", courses, f"semester must be between {k0} and 8", semester))

    term_catalogs = {}
    for semester in range(k0, 9):
        ay, term_number = term(scenario["matric_ay"], semester)
        catalog, actual_ay = catalog_for(catalogs, ay)
        term_catalogs[semester] = (catalog, actual_ay, str(term_number))

    # 4. Offering, prerequisites, timetable, and workload all use the catalog for
    # the degree semester being checked, not a single fixed AY.
    for semester in range(k0, 9):
        catalog, _, term_number = term_catalogs[semester]
        courses = by_semester.get(semester, [])
        offered_courses = []
        for code in courses:
            if code == ELECTIVE:
                continue
            course = catalog["courses"].get(code)
            if course is None or term_number not in course["semesters"]:
                violations.append(_violation("offered", [code], "course is not offered in this semester", semester))
            else:
                offered_courses.append(code)

        # 8 and 9: only courses that have a timetable entry for this term can clash.
        for first, second in combinations(offered_courses, 2):
            first_data = catalog["courses"][first]["semesters"][term_number]
            second_data = catalog["courses"][second]["semesters"][term_number]
            if _lectures_clash(first_data["lectures"], second_data["lectures"]):
                violations.append(_violation("lecture_clash", [first, second], "lectures overlap", semester))
            if _exams_clash(first_data["exam"], second_data["exam"]):
                violations.append(_violation("exam_clash", [first, second], "exams overlap", semester))

        units = 0
        for code in courses:
            if code == ELECTIVE:
                units += ELECTIVE_UNITS
            elif code in catalog["courses"]:
                units += catalog["courses"][code]["units"]
        if not scenario["min_units"] <= units <= scenario["max_units"]:
            violations.append(_violation(
                "workload", courses,
                f"{units} units is outside {scenario['min_units']}..{scenario['max_units']}", semester,
            ))

    # 5. Check before adding a whole semester, so a co-requisite does not count as
    # an earlier prerequisite.
    taken_before = set(completed)
    for semester in range(k0, 9):
        catalog, _, term_number = term_catalogs[semester]
        for code in by_semester.get(semester, []):
            course = catalog["courses"].get(code)
            if code != ELECTIVE and course is not None and term_number in course["semesters"]:
                if not _prereq_met(course["prereq"], taken_before):
                    violations.append(_violation(
                        "prereq", [code], "prerequisites are not met before this semester", semester
                    ))
        taken_before.update(by_semester.get(semester, []))

    planned = set(locations)
    taken = completed | planned

    # 6. A pair is valid only if both were completed, or both appear in one planned term.
    for first, second in requirements["same_semester"]:
        if first in completed and second in completed:
            continue
        first_semesters = set(locations.get(first, []))
        second_semesters = set(locations.get(second, []))
        if not first_semesters or first_semesters != second_semesters:
            violations.append(_violation(
                "same_semester", [first, second], "courses must be completed together or planned in the same semester"
            ))

    # 7. A one-direction entry in any frozen catalog is sufficient to preclude the pair.
    pairs = {
        frozenset((code, precluded))
        for catalog in catalogs.values()
        for code, course in catalog["courses"].items()
        for precluded in course["preclusions"]
    }
    for pair in pairs:
        first, second = sorted(pair)
        if first in taken and second in taken and not ({first, second} <= completed):
            violations.append(_violation("preclusion", [first, second], "taken courses preclude each other"))

    # 11--13 are degree-level conditions, so completed courses count just like planned ones.
    missing_required = set(requirements["required"]) - taken
    if missing_required:
        violations.append(_violation("required", missing_required, "required courses were not taken"))

    primaries = set(requirements["focus_areas"][scenario["focus_area"]])
    focus_rule = requirements["focus_area_rule"]
    focus_taken = primaries & taken
    focus_4000 = {code for code in focus_taken if _level(code) >= 4000}
    if (len(focus_taken) < focus_rule["min_primaries"]
            or len(focus_4000) < focus_rule["min_primaries_level_4000"]):
        violations.append(_violation("focus_area", sorted(focus_taken), "focus-area primary requirement is not met"))

    missing_must_take = set(scenario["must_take"]) - taken
    if missing_must_take:
        violations.append(_violation("must_take", missing_must_take, "must-take courses were not taken"))

    return violations
