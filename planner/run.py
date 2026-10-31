"""Run one approach over a scenario file, score every answer and save the results. Owner: Javier.

Usage:  python -m planner.run <approach> <scenario file> [runs]      e.g.  python -m planner.run direct examples 1
  direct  the LLM writes the plan itself (planner/direct.py)
  tool    the LLM turns the message into a scenario and the solver plans (planner/translate.py, planner/solver.py)
  gold    the solver plans from the gold scenario: the perfect-translation ablation (design.md section 8.2)
Runs default to 3, or to 1 for gold, which is deterministic.
"""
import json
import sys
import time
from collections import Counter
from datetime import datetime
from statistics import mean

from planner import llm
from planner.data import ROOT, load_scenarios
from planner.direct import plan_direct
from planner.solver import solve
from planner.translate import translate
from planner.validate import validate

CORRECT = {"valid_plan", "correct_impossible"}  # accuracy = share of answers with one of these outcomes
OUTCOMES = ["valid_plan", "invalid_plan", "false_impossible", "correct_impossible", "plan_for_impossible", "no_answer"]


def outcome(expected, plan, violations):
    """Score one answer (design.md section 8.1). plan is None when the reply could not be parsed."""
    if plan is None:
        return "no_answer"
    if plan["status"] == "impossible":
        return "correct_impossible" if expected == "impossible" else "false_impossible"
    if expected == "impossible":
        return "plan_for_impossible"
    return "invalid_plan" if violations else "valid_plan"


def score(entry, plan):
    """(violations, outcome) for one answer. A plan is checked against the gold scenario, never the approach's reading."""
    if plan is None or plan["status"] != "plan":
        return [], outcome(entry["expected"], plan, [])
    violations = validate(entry["scenario"], plan)
    return violations, outcome(entry["expected"], plan, violations)


def wrong_fields(gold, translated):
    """The fields translate() got wrong, comparing lists as sets (design.md section 8.2). No translation gets all wrong."""
    def norm(value):
        return set(value) if isinstance(value, list) else value
    return sorted(f for f in gold if translated is None or norm(translated.get(f)) != norm(gold[f]))


def answer(approach, entry):
    """(plan, extra fields for the results line) for one scenario."""
    if approach == "direct":
        return plan_direct(entry["text"]), {}
    if approach == "gold":
        return solve(entry["scenario"]), {}
    translated = translate(entry["text"])
    extra = {"translation": translated, "wrong_fields": wrong_fields(entry["scenario"], translated)}
    try:
        plan = None if translated is None else solve(translated)
    except Exception as error:  # a bad value got past translate()'s check; keep the error so a solver bug can't hide
        plan, extra["solver_error"] = None, repr(error)
    return plan, extra


def main(argv=None):
    """For each scenario: run the approach, validate its plan, score it with outcome() and append one JSON line
    (id, approach, run, model, plan, violations, outcome, each LLM call's raw reply and tokens, cost, seconds) to
    results/<date>-<time>-<approach>.jsonl. Then print the outcome table, the accuracy and the cost."""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) not in (2, 3) or argv[0] not in ("direct", "tool", "gold"):
        sys.exit(__doc__)
    approach, name = argv[:2]
    runs = int(argv[2]) if len(argv) == 3 else 1 if approach == "gold" else 3
    entries = load_scenarios(name)
    path = ROOT / "results" / f"{datetime.now():%Y-%m-%d-%H%M}-{approach}.jsonl"
    path.parent.mkdir(exist_ok=True)
    rows = []
    with path.open("a") as out:
        for run in range(1, runs + 1):
            for entry in entries:
                llm.CALLS.clear()
                start = time.monotonic()
                plan, extra = answer(approach, entry)
                violations, result = score(entry, plan)
                row = {"id": entry["id"], "approach": approach, "run": run, "model": llm.MODEL if llm.CALLS else None,
                       "plan": plan, "violations": violations, "outcome": result, **extra, "calls": list(llm.CALLS),
                       "cost": round(sum(llm.cost(call["usage"]) for call in llm.CALLS), 4),
                       "seconds": round(time.monotonic() - start, 1)}
                out.write(json.dumps(row) + "\n")
                out.flush()  # finished answers survive a crash later in the run
                rows.append(row)
                print(f"run {run} {entry['id']}: {result}  ${row['cost']:.3f}  {row['seconds']} s")
    report(rows)
    print(f"saved to {path.relative_to(ROOT)}")


def report(rows):
    """Print the outcome table (design.md section 8.1), accuracy over the runs, translation accuracy and cost."""
    counts = Counter(row["outcome"] for row in rows)
    for name in OUTCOMES:
        print(f"  {name:20} {counts[name]}")
    per_run = [mean(row["outcome"] in CORRECT for row in rows if row["run"] == run)
               for run in sorted({row["run"] for row in rows})]
    print(f"accuracy: {mean(per_run):.0%} (runs: {min(per_run):.0%} to {max(per_run):.0%})")
    translations = [row["wrong_fields"] for row in rows if "wrong_fields" in row]
    if translations:
        print(f"translated perfectly: {mean(not wrong for wrong in translations):.0%}; "
              f"errors by field: {dict(Counter(f for wrong in translations for f in wrong))}")
    calls = [call for row in rows for call in row["calls"]]
    if calls:
        total = sum(row["cost"] for row in rows)
        tokens = {name: sum(call["usage"][name] for call in calls) for name in llm.PRICES}
        print(f"cost: ${total:.2f}, ${total / len(rows):.3f} per answer, {sum(row['seconds'] for row in rows):.0f} s; "
              f"tokens: {tokens}")


if __name__ == "__main__":
    main()
