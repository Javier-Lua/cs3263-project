"""Tool-assisted step 2: find a plan that meets every rule in docs/design.md section 4, or show there is none.

Owner: Weng Mun. Suggested: OR-Tools CP-SAT (pip install ortools); encoding sketch in design.md section 6.2.
"""
import re

from ortools.sat.python import cp_model

from planner.data import ELECTIVE, ELECTIVE_UNITS, catalog_for, load_catalogs, load_requirements, term


def level(code):
    """Course level from the code: the first digit times 1000, e.g. CS4248 -> 4000."""
    return int(re.search(r"\d", code).group()) * 1000


def build_model(scenario):
    """Return (model, x, e): x[(course, k)] is 1 when the course is taken in semester k, and e[k] is the number of
    ELECTIVE slots in semester k.

    A variable exists only for a course that is offered in that semester (in the catalog of that semester's academic
    year) and that the student has not already completed, so rules 2 `repeat` (part) and 4 `offered` hold by construction.
    """
    k0 = scenario["current_semester"]
    if not 1 <= k0 <= 8:
        raise ValueError(f"current_semester must be 1-8, got {k0}")
    catalogs = load_catalogs()
    completed = set(scenario["completed"])

    model = cp_model.CpModel()
    x, units, prereq = {}, {}, {}
    for k in range(k0, 9):
        ay, sem = term(scenario["matric_ay"], k)
        catalog, _ = catalog_for(catalogs, ay)
        for code, course in catalog["courses"].items():
            if code not in completed and str(sem) in course["semesters"]:
                x[code, k] = model.NewBoolVar(f"x_{code}_{k}")
                units[code, k] = course["units"]
                prereq[code, k] = course["prereq"]

    planned = {}  # course -> its variables, one per semester it can be taken in
    for (code, _), v in x.items():
        planned.setdefault(code, []).append(v)

    def taken(codes):  # the variables of these courses that can still be planned
        return [v for code in codes for v in planned.get(code, [])]

    for vs in planned.values():  # rule 2 `repeat`: a course is planned at most once
        model.Add(sum(vs) <= 1)

    def met(tree, k):
        """True, False, or a variable that may be 1 only if the prereq tree holds for a course taken in semester k.
        Only courses completed or planned in an earlier semester count."""
        if tree is None or tree is True:
            return True
        if tree is False:
            return False
        if isinstance(tree, str):
            if tree in completed:
                return True
            before = [x[tree, j] for j in range(k0, k) if (tree, j) in x]
            if not before:
                return False
            y = model.NewBoolVar(f"met_{tree}_{k}")
            model.Add(sum(before) >= 1).OnlyEnforceIf(y)
            return y
        ((op, args),) = tree.items()
        need, args = args if op == "nOf" else (len(args) if op == "and" else 1, args)
        kids = [met(a, k) for a in args]
        need -= sum(kid is True for kid in kids)
        vs = [kid for kid in kids if not isinstance(kid, bool)]
        if need <= 0:
            return True
        if len(vs) < need:
            return False
        y = model.NewBoolVar(f"met_{op}_{k}")
        model.Add(sum(vs) >= need).OnlyEnforceIf(y)
        return y

    for (code, k), v in x.items():  # rule 5 `prereq`
        ok = met(prereq[code, k], k)
        if ok is False:
            model.Add(v == 0)
        elif ok is not True:
            model.AddImplication(v, ok)

    requirements = load_requirements(scenario["matric_ay"])
    for code in (set(requirements["required"]) | set(scenario["must_take"])) - completed:  # rules 11 and 13
        model.Add(sum(taken([code])) >= 1)

    primaries = requirements["focus_areas"][scenario["focus_area"]]  # rule 12 `focus_area`
    rule = requirements["focus_area_rule"]
    done = [p for p in primaries if p in completed]
    model.Add(len(done) + sum(taken(primaries)) >= rule["min_primaries"])
    done_4000 = sum(level(p) >= 4000 for p in done)
    model.Add(done_4000 + sum(taken(p for p in primaries if level(p) >= 4000)) >= rule["min_primaries_level_4000"])

    e = {k: model.NewIntVar(0, max(scenario["max_units"], 0) // ELECTIVE_UNITS, f"e_{k}") for k in range(k0, 9)}
    for k in e:  # rule 10 `workload`
        total = sum(units[c, kk] * v for (c, kk), v in x.items() if kk == k) + ELECTIVE_UNITS * e[k]
        model.Add(total >= scenario["min_units"])
        model.Add(total <= scenario["max_units"])
    return model, x, e


def solve(scenario):
    """Return {"status": "plan", "semesters": {...}} or {"status": "impossible"} (design.md section 5)."""
    model, x, e = build_model(scenario)
    solver = cp_model.CpSolver()
    if solver.Solve(model) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": "impossible"}
    semesters = {}
    for k in e:
        courses = sorted(c for (c, kk), v in x.items() if kk == k and solver.Value(v))
        semesters[str(k)] = courses + [ELECTIVE] * solver.Value(e[k])
    return {"status": "plan", "semesters": semesters}
