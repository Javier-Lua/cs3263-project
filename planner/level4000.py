"""Would the real "at least 12 units at level 4000" rule, which we don't model, change any label? Owner: Javier.

Usage:  python -m planner.level4000
Re-solves every feasible main scenario with that rule added. Only CS courses in our catalog can count towards it,
and real students have more to choose from, so the count of scenarios that turn impossible is an upper bound.
"""
from ortools.sat.python import cp_model

from planner import solver
from planner.data import load_catalogs, load_scenarios

UNITS_AT_4000 = 12


def is_cs_4000(code):
    return code.startswith("CS") and solver.level(code) >= 4000


def feasible(scenario, with_rule):
    model, planned_in, _ = solver.build_model(scenario)
    if with_rule:
        units = {code: course["units"] for catalog in load_catalogs().values()
                 for code, course in catalog["courses"].items()}
        done = sum(units.get(code, 4) for code in scenario["completed"] if is_cs_4000(code))
        model.Add(done + sum(units[code] * variable for (code, _), variable in planned_in.items()
                             if is_cs_4000(code)) >= UNITS_AT_4000)
    cp = cp_model.CpSolver()
    cp.parameters.num_workers = 1
    status = cp.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE, cp_model.INFEASIBLE), cp.StatusName(status)
    return status != cp_model.INFEASIBLE


def main():
    entries = [e for e in load_scenarios("main") if e["expected"] == "feasible"]
    assert all(feasible(e["scenario"], False) for e in entries)  # without the rule, every label holds
    flipped = [e["id"] for e in entries if not feasible(e["scenario"], True)]
    short = [e["id"] for e in entries
             if sum(map(is_cs_4000, set(e["scenario"]["completed"])
                        | {c for cs in solver.solve(e["scenario"])["semesters"].values() for c in cs})) * 4
             < UNITS_AT_4000]
    print(f"{len(entries)} feasible; with the rule, {len(flipped)} turn impossible {flipped}; "
          f"{len(short)} of the solver's current plans fall short of it")


if __name__ == "__main__":
    main()
