from planner.run import outcome


def test_outcomes():
    plan, impossible = {"status": "plan", "semesters": {}}, {"status": "impossible"}
    assert outcome("feasible", plan, []) == "valid_plan"
    assert outcome("feasible", plan, [{"rule": "prereq"}]) == "invalid_plan"
    assert outcome("feasible", impossible, []) == "false_impossible"
    assert outcome("impossible", impossible, []) == "correct_impossible"
    assert outcome("impossible", plan, []) == "plan_for_impossible"
    assert outcome("feasible", None, []) == "no_answer"
