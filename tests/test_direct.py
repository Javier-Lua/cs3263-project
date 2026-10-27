import pytest

from planner import direct
from planner.data import load_catalogs


@pytest.mark.parametrize("reply, plan", [
    ('{"status": "impossible", "reason": "CS4234 is Sem 1 only"}', {"status": "impossible", "reason": "CS4234 is Sem 1 only"}),
    ('```json\n{"status": "plan", "semesters": {"8": ["CS3263", "ELECTIVE"]}}\n```',
     {"status": "plan", "semesters": {"8": ["CS3263", "ELECTIVE"]}}),
    ("Sorry, I can't plan this.", None),
    ('{"status": "plan", "semesters": {"8": ', None),  # cut off
    ('{"status": "plan", "semesters": {"8": "CS3263"}}', None),  # not a list
    ('{"status": "plan", "semesters": {"Y4S2": ["CS3263"]}}', None),  # not a semester number
    ('{"status": "maybe"}', None),
])
def test_parse(reply, plan):
    assert direct.parse(reply) == plan


def test_prompt_holds_every_catalog_year_and_the_message(monkeypatch):
    seen = {}

    def fake_ask(system, user):
        seen.update(system=system, user=user)
        return '{"status": "impossible"}', {}

    monkeypatch.setattr(direct, "ask", fake_ask)
    assert direct.plan_direct("Plan my degree.") == {"status": "impossible", "reason": ""}
    assert seen["user"] == "Plan my degree."
    assert all(f'"{ay}":' in seen["system"] for ay in load_catalogs())
