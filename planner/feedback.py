"""The hybrid (design.md section 6.3): send the validator's findings back to the direct approach and let it revise.
Owner: Javier.

Usage:  python -m planner.feedback <direct results file> ...
Every wrong plan in the files (outcome invalid_plan or plan_for_impossible) gets up to ROUNDS more calls, each showing
the model its last plan and the rules the validator says it breaks. The validator checks against the gold scenario,
as if the student had confirmed their details. An "impossible" answer gets no feedback: the validator can't check it.
Saves results/<date>-<time>-feedback.jsonl and prints the outcomes per model setting.
"""
import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from planner import llm
from planner.data import ROOT, load_scenarios
from planner.direct import parse, system_prompt
from planner.run import CORRECT, score

ROUNDS = 3
FIXABLE = {"invalid_plan", "plan_for_impossible"}
SETS = ["main", "reworded", "adversarial"]


def feedback_message(violations):
    """The follow-up turn: every broken rule, as the validator reports it."""
    lines = [f"- {v['rule']}" + (f" (semester {v['semester']})" if "semester" in v else "")
             + f": {', '.join(v['courses'])}: {v['detail']}" for v in violations]
    return ("A rule checker found that your plan breaks these rules:\n" + "\n".join(lines) + "\nRevise the plan so "
            "that it follows every rule, or say that no plan can. Reply with only the JSON object, in the same format.")


def revise(entry, reply, violations):
    """Feed the violations back for up to ROUNDS rounds, stopping at the first answer with none (a valid plan,
    "impossible" or no answer). Returns one {"plan", "violations", "outcome", "reply", "usage"} per round."""
    messages = [{"role": "user", "content": entry["text"]}]
    rounds = []
    for _ in range(ROUNDS):
        messages += [{"role": "assistant", "content": reply}, {"role": "user", "content": feedback_message(violations)}]
        reply, usage = llm.ask(system_prompt(), messages)
        plan = parse(reply)
        violations, result = score(entry, plan)
        rounds.append({"plan": plan, "violations": violations, "outcome": result, "reply": reply, "usage": usage})
        if not violations:
            break
    return rounds


def main(argv=None):
    paths = list(sys.argv[1:] if argv is None else argv)
    if not paths:
        sys.exit(__doc__)
    entries = {e["id"]: e for name in SETS for e in load_scenarios(name)}
    out_path = ROOT / "results" / f"{datetime.now():%Y-%m-%d-%H%M}-feedback.jsonl"
    out_path.parent.mkdir(exist_ok=True)
    totals, rows = Counter(), []
    with out_path.open("a") as out:
        for path in paths:
            for line in Path(path).read_text().splitlines():
                old = json.loads(line)
                setting = (old["model"], old.get("thinking", True))  # runs before 8 Nov had thinking on
                totals[setting, old["outcome"] in CORRECT] += 1
                if old["approach"] != "direct" or old["outcome"] not in FIXABLE:
                    continue
                llm.MODEL, llm.THINKING = setting
                start = time.monotonic()
                rounds = revise(entries[old["id"]], old["calls"][-1]["reply"], old["violations"])
                row = {"id": old["id"], "run": old["run"], "source": Path(path).name, "model": llm.MODEL,
                       "thinking": llm.THINKING, "first_outcome": old["outcome"], "outcome": rounds[-1]["outcome"],
                       "rounds": rounds, "cost": round(sum(llm.cost(r["usage"]) for r in rounds), 4),
                       "seconds": round(time.monotonic() - start, 1)}
                out.write(json.dumps(row) + "\n")
                out.flush()
                rows.append(row)
                print(f"{old['id']} run {old['run']} {llm.MODEL}: {old['outcome']} -> {row['outcome']} "
                      f"in {len(rounds)} round(s)  ${row['cost']:.3f}")
    report(rows, totals)
    print(f"saved to {out_path.relative_to(ROOT)}")


def report(rows, totals):
    """Per model setting: what the fed-back answers became, and accuracy before and after feedback."""
    for setting in sorted({key for key, _ in totals}, key=str):
        mine = [row for row in rows if (row["model"], row["thinking"]) == setting]
        right, wrong = totals[setting, True], totals[setting, False]
        fixed = sum(row["outcome"] in CORRECT for row in mine)
        print(f"{setting}: fed back {len(mine)}, now {dict(Counter(row['outcome'] for row in mine))}, rounds "
              f"{dict(Counter(len(row['rounds']) for row in mine))}; accuracy {right}/{right + wrong} -> "
              f"{right + fixed}/{right + wrong}; extra cost ${sum(row['cost'] for row in mine):.2f}")


if __name__ == "__main__":
    main()
