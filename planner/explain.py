"""Explain an impossible scenario with the smallest change to the student's own choices that makes a plan exist
(a counterfactual explanation, design.md section 8.5). Owner: Javier.

Usage:  python -m planner.explain [scenario file]      e.g.  python -m planner.explain main

The choices a student controls are their must-take courses, their focus area and their workload. explain() tries
every single change (drop one must-take course, switch focus area, raise the unit cap to OVERLOAD_UNITS), then every
pair, and returns the smallest that the solver says work. Changes the student can't make, such as more semesters or
a course offered in another term, are out of reach: if nothing works, the answer is "no change of choices helps".
"""
import sys
from itertools import combinations

from planner.data import load_requirements, load_scenarios
from planner.solver import solve

OVERLOAD_UNITS = 27  # one more 4-unit course a semester than the 23-unit cap


def apply(scenario, change_set):
    """The scenario with each (kind, value) change made: ("drop", course), ("focus", area) or ("units", cap)."""
    s = dict(scenario)
    for kind, value in change_set:
        if kind == "drop":
            s["must_take"] = [c for c in s["must_take"] if c != value]
        elif kind == "focus":
            s["focus_area"] = value
        else:
            s["max_units"] = value
    return s


def explain(scenario, most=2):
    """The smallest change sets (at most `most` changes each) that make a plan exist, or [] if none does."""
    areas = load_requirements(scenario["matric_ay"])["focus_areas"]
    options = ([("drop", c) for c in scenario["must_take"]] +
               [("focus", f) for f in areas if f != scenario["focus_area"]] + [("units", OVERLOAD_UNITS)])
    for size in range(1, most + 1):
        fixes = [list(combo) for combo in combinations(options, size)
                 if sum(kind == "focus" for kind, _ in combo) <= 1 and solve(apply(scenario, combo))["status"] == "plan"]
        if fixes:
            return fixes
    return []


def describe(fixes):
    """One line a student can read, e.g. "drop CS3282" or "switch focus area (any of 9)"."""
    if not fixes:
        return "no change of choices helps"
    single = {(kind, value) for fix in fixes if len(fix) == 1 for kind, value in fix}
    focus = sorted(value for kind, value in single if kind == "focus")
    parts = [f"drop {value}" for kind, value in sorted(single) if kind == "drop"]
    parts += [f"switch focus area to {focus[0]}" if len(focus) == 1 else f"switch focus area (any of {len(focus)})"] \
        if focus else []
    parts += [f"raise the unit cap to {OVERLOAD_UNITS}" for kind, _ in single if kind == "units"]
    parts += [" and ".join(f"drop {v}" if k == "drop" else f"focus {v}" if k == "focus" else f"{v}-unit cap"
                           for k, v in fix) for fix in fixes if len(fix) > 1]
    return "; or ".join(parts)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    print("| id | smallest change that makes a plan exist | why it is impossible (scenario file) |\n|---|---|---|")
    for e in load_scenarios(argv[0] if argv else "main"):
        if e["expected"] == "impossible":
            print(f"| {e['id']} | {describe(explain(e['scenario']))} | {e['why']} |")


if __name__ == "__main__":
    main()
