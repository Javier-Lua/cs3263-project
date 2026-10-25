"""Tool-assisted step 2: find a plan that meets every rule in docs/design.md section 4, or show there is none.

Owner: Weng Mun. Suggested: OR-Tools CP-SAT (pip install ortools); encoding sketch in design.md section 6.2.
"""
import re

from ortools.sat.python import cp_model

from planner.data import catalog_for, load_catalogs, load_requirements, term


def level(code):
    """Course level from the code: the first digit times 1000, e.g. CS4248 -> 4000."""
    return int(re.search(r"\d", code).group()) * 1000


def build_model(scenario):
    """Return (model, x): x[(course, k)] is 1 when the course is taken in semester k.

    A variable exists only for a course that is offered in that semester (in the catalog of that semester's academic
    year) and that the student has not already completed, so rules 2 `repeat` (part) and 4 `offered` hold by construction.
    """
    k0 = scenario["current_semester"]
    if not 1 <= k0 <= 8:
        raise ValueError(f"current_semester must be 1-8, got {k0}")
    catalogs = load_catalogs()
    completed = set(scenario["completed"])

    model = cp_model.CpModel()
    x = {}
    for k in range(k0, 9):
        ay, sem = term(scenario["matric_ay"], k)
        catalog, _ = catalog_for(catalogs, ay)
        for code, course in catalog["courses"].items():
            if code not in completed and str(sem) in course["semesters"]:
                x[code, k] = model.NewBoolVar(f"x_{code}_{k}")

    planned = {}  # course -> its variables, one per semester it can be taken in
    for (code, _), v in x.items():
        planned.setdefault(code, []).append(v)

    def taken(codes):  # the variables of these courses that can still be planned
        return [v for code in codes for v in planned.get(code, [])]

    for vs in planned.values():  # rule 2 `repeat`: a course is planned at most once
        model.Add(sum(vs) <= 1)

    requirements = load_requirements(scenario["matric_ay"])
    for code in (set(requirements["required"]) | set(scenario["must_take"])) - completed:  # rules 11 and 13
        model.Add(sum(taken([code])) >= 1)

    primaries = requirements["focus_areas"][scenario["focus_area"]]  # rule 12 `focus_area`
    rule = requirements["focus_area_rule"]
    done = [p for p in primaries if p in completed]
    model.Add(len(done) + sum(taken(primaries)) >= rule["min_primaries"])
    done_4000 = sum(level(p) >= 4000 for p in done)
    model.Add(done_4000 + sum(taken(p for p in primaries if level(p) >= 4000)) >= rule["min_primaries_level_4000"])
    return model, x


def solve(scenario):
    """Return {"status": "plan", "semesters": {...}} or {"status": "impossible"} (design.md section 5)."""
    model, x = build_model(scenario)
    solver = cp_model.CpSolver()
    if solver.Solve(model) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": "impossible"}
    semesters = {str(k): sorted(c for (c, kk), v in x.items() if kk == k and solver.Value(v))
                 for k in range(scenario["current_semester"], 9)}
    return {"status": "plan", "semesters": semesters}
