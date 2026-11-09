import json

from planner import feedback
from planner.data import load_scenarios

FEASIBLE = next(e for e in load_scenarios() if e["expected"] == "feasible")
EMPTY_PLAN = json.dumps({"status": "plan", "semesters": {}})  # breaks the required-course rule, among others


def fake_ask(replies, seen):
    def ask(system, messages):
        seen.append(messages)
        return replies.pop(0), dict.fromkeys(feedback.llm.PRICES[feedback.llm.MODEL], 0)
    return ask


def test_message_lists_every_violation():
    message = feedback.feedback_message([{"rule": "prereq", "semester": 4, "courses": ["CS2103T"], "detail": "x"},
                                         {"rule": "required", "courses": ["CS3230"], "detail": "y"}])
    assert "- prereq (semester 4): CS2103T: x" in message and "- required: CS3230: y" in message


def test_stops_at_the_first_valid_plan(monkeypatch):
    seen = []
    monkeypatch.setattr(feedback.llm, "ask", fake_ask([json.dumps(FEASIBLE["witness"])], seen))
    rounds = feedback.revise(FEASIBLE, EMPTY_PLAN, [{"rule": "required", "courses": ["CS3230"], "detail": "y"}])
    assert [r["outcome"] for r in rounds] == ["valid_plan"]
    (messages,) = seen  # the message, the old plan, then the feedback
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert messages[0]["content"] == FEASIBLE["text"] and messages[1]["content"] == EMPTY_PLAN


def test_gives_up_after_the_last_round(monkeypatch):
    seen = []
    monkeypatch.setattr(feedback.llm, "ask", fake_ask([EMPTY_PLAN] * feedback.ROUNDS, seen))
    rounds = feedback.revise(FEASIBLE, EMPTY_PLAN, [{"rule": "required", "courses": ["CS3230"], "detail": "y"}])
    assert len(rounds) == feedback.ROUNDS and rounds[-1]["outcome"] == "invalid_plan"
    assert len(seen[-1]) == 1 + 2 * feedback.ROUNDS  # each round adds the last plan and its feedback
