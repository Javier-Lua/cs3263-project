"""Checks for the counterfactual explanations (planner/explain.py)."""
import pytest

from planner.data import load_scenarios
from planner.explain import OVERLOAD_UNITS, apply, describe, explain
from planner.solver import solve
from planner.validate import validate

MAIN = {e["id"]: e for e in load_scenarios("main")}


@pytest.mark.parametrize("scenario_id, fixes", [
    ("M30", [[("drop", "CS3282")]]),  # CS3282's prerequisite is false, so only dropping it helps
    ("M03", [[("units", OVERLOAD_UNITS)]]),  # 24 units left for one semester
    ("M28", []),  # a completed course precludes a required one: no choice of the student's helps
])
def test_explain_finds_the_smallest_change(scenario_id, fixes):
    assert explain(MAIN[scenario_id]["scenario"]) == fixes


def test_every_suggested_change_gives_a_plan_the_validator_accepts():
    for e in MAIN.values():
        if e["expected"] == "impossible":
            for fix in explain(e["scenario"]):
                changed = apply(e["scenario"], fix)
                assert validate(changed, solve(changed)) == [], (e["id"], fix)


def test_describe():
    assert describe([]) == "no change of choices helps"
    assert describe([[("drop", "CS3282")], [("units", 27)]]) == "drop CS3282; or raise the unit cap to 27"
    assert describe([[("focus", "AI")], [("focus", "HCI")]]) == "switch focus area (any of 2)"
