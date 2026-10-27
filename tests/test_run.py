import json

from planner import run
from planner.data import load_scenarios
from planner.run import outcome

EXAMPLES = load_scenarios()


def test_outcomes():
    plan, impossible = {"status": "plan", "semesters": {}}, {"status": "impossible"}
    assert outcome("feasible", plan, []) == "valid_plan"
    assert outcome("feasible", plan, [{"rule": "prereq"}]) == "invalid_plan"
    assert outcome("feasible", impossible, []) == "false_impossible"
    assert outcome("impossible", impossible, []) == "correct_impossible"
    assert outcome("impossible", plan, []) == "plan_for_impossible"
    assert outcome("feasible", None, []) == "no_answer"


def test_main_scores_and_saves_every_answer(tmp_path, monkeypatch, capsys):
    def label_answer(text):  # the witness for a feasible example, "impossible" otherwise
        return next(e.get("witness", {"status": "impossible"}) for e in EXAMPLES if e["text"] == text)

    monkeypatch.setattr(run, "ROOT", tmp_path)
    monkeypatch.setattr(run, "plan_direct", label_answer)
    monkeypatch.setattr(run, "validate", lambda scenario, plan: [])
    run.main(["direct", "examples", "2"])
    (path,) = (tmp_path / "results").iterdir()
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [(row["run"], row["id"]) for row in rows] == [(k, e["id"]) for k in (1, 2) for e in EXAMPLES]
    assert {row["outcome"] for row in rows} == {"valid_plan", "correct_impossible"}
    assert "accuracy: 100% (runs: 100% to 100%)" in capsys.readouterr().out


def test_plans_stay_unscored_without_a_validator(monkeypatch):
    def missing(scenario, plan):
        raise NotImplementedError

    monkeypatch.setattr(run, "validate", missing)
    feasible, impossible = (next(e for e in EXAMPLES if e["expected"] == x) for x in ("feasible", "impossible"))
    assert run.score(feasible, feasible["witness"]) == (None, "unscored")
    assert run.score(impossible, feasible["witness"]) == (None, "plan_for_impossible")
    assert run.score(impossible, {"status": "impossible"}) == ([], "correct_impossible")


def test_wrong_fields_compares_lists_as_sets():
    gold = EXAMPLES[0]["scenario"]
    assert run.wrong_fields(gold, {**gold, "completed": gold["completed"][::-1]}) == []
    assert run.wrong_fields(gold, {**gold, "current_semester": 4, "must_take": []}) == ["current_semester", "must_take"]
    assert run.wrong_fields(gold, None) == sorted(gold)
