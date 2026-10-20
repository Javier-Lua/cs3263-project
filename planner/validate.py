"""Check a plan against the rules in docs/design.md section 4. Owner: Zechary (proposed).

Share no code with planner/solver.py, so a solver bug can't hide in the checker too. Read data only through planner.data.
"""


def validate(scenario, plan):
    """Return the list of rule violations; [] means the plan is valid.

    plan is {"status": "plan", "semesters": {"3": ["CS2030S", ...], ...}}. Each violation is a dict like
    {"rule": "prereq", "semester": 4, "courses": ["CS2103T"], "detail": "needs CS2030S before semester 4"},
    where "rule" is one of the ids in design.md section 4.
    """
    raise NotImplementedError
