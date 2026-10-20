"""Run one approach over a scenario file, score every answer and save the results. Owner: Javier.

Usage, once the approaches exist:  python -m planner.run direct examples
"""
CORRECT = {"valid_plan", "correct_impossible"}  # accuracy = share of answers with one of these outcomes


def outcome(expected, plan, violations):
    """Score one answer (design.md section 8.1). plan is None when the reply could not be parsed."""
    if plan is None:
        return "no_answer"
    if plan["status"] == "impossible":
        return "correct_impossible" if expected == "impossible" else "false_impossible"
    if expected == "impossible":
        return "plan_for_impossible"
    return "invalid_plan" if violations else "valid_plan"


def main():
    """For each scenario: run the approach, validate its plan, score it with outcome() and append one JSON line
    (id, approach, model, raw reply, plan, violations, outcome, tokens, seconds) to results/<date>-<approach>.jsonl.
    Then print the outcome table and the accuracy."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
