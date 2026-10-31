import json

import pytest

from planner import translate
from planner.data import load_scenarios

GOLD = {e["id"]: e["scenario"] for e in load_scenarios()}
SCENARIO = GOLD["S001"]


def changed(**fields):
    """A copy of the S001 scenario with some fields replaced."""
    return {**SCENARIO, **fields}


def without(field):
    """A copy of the S001 scenario with one field removed."""
    return {name: value for name, value in SCENARIO.items() if name != field}


def test_parse_reads_plain_and_fenced_json():
    assert translate.parse(json.dumps(SCENARIO)) == SCENARIO
    assert translate.parse(f"```json\n{json.dumps(SCENARIO)}\n```") == SCENARIO


def test_parse_reads_only_the_first_object():
    scenario_json = json.dumps(SCENARIO)
    assert translate.parse(f"Here you go: {scenario_json}\nNote: a {{brace}} in a note.") == SCENARIO
    assert translate.parse(f"{scenario_json} {scenario_json}") == SCENARIO


@pytest.mark.parametrize("reply", [
    "Sorry, I can't do that.",
    '{"matric_ay": "2025-2026", "current_semester": ',  # cut off
    "[1, 2, 3]",  # JSON, but not an object
    "",
])
def test_parse_gives_none_when_there_is_no_scenario(reply):
    assert translate.parse(reply) is None


@pytest.mark.parametrize("scenario", GOLD.values(), ids=list(GOLD))
def test_check_accepts_every_gold_scenario(scenario):
    assert translate.check(scenario) == scenario


@pytest.mark.parametrize("scenario", [
    None,
    without("must_take"),
    {**SCENARIO, "blocked_semesters": [4]},  # a field the design no longer has
    changed(current_semester=None),  # the message didn't say, and the prompt tells the model to write null
    changed(focus_area=None),
    changed(current_semester="3"),  # not an integer
    changed(current_semester=True),  # a bool is not an integer
    changed(current_semester=0),
    changed(current_semester=9),
    changed(matric_ay="AY2025/26"),
    changed(matric_ay="2025-2027"),
    changed(matric_ay="2024-2025"),  # a well-formed year, but we have no degree rules for that cohort
    changed(focus_area="Quantum Cooking"),
    changed(min_units=16, max_units=20),  # the unit limits are fixed
    changed(completed="CS1231S"),  # not a list
    changed(completed=["CS1231S", 2030]),  # not a code
    changed(completed=["CS9999"]),  # not in any catalog
    changed(must_take=["cs3263"]),  # not written exactly as in the catalog
])
def test_check_rejects(scenario):
    assert translate.check(scenario) is None


def test_prompt_lists_every_focus_area_and_course_code():
    prompt = translate.system_prompt()
    assert all(name in prompt for name in translate.focus_area_names())
    assert all(code in prompt for code in translate.course_codes())


def test_translate_sends_the_message_and_returns_the_scenario(monkeypatch):
    seen = {}

    def fake_ask(system, user):
        seen.update(system=system, user=user)
        return f"```json\n{json.dumps(SCENARIO)}\n```", {}

    monkeypatch.setattr(translate, "ask", fake_ask)
    assert translate.translate("Plan my degree.") == SCENARIO
    assert seen["user"] == "Plan my degree."
    assert seen["system"] == translate.system_prompt()


def test_translate_gives_none_for_a_bad_reply(monkeypatch):
    monkeypatch.setattr(translate, "ask", lambda system, user: (json.dumps(changed(current_semester=9)), {}))
    assert translate.translate("Plan my degree.") is None
