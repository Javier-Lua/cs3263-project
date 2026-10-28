"""Tool-assisted step 1: turn the student's message into scenario JSON with one LLM call. Owner: Weng Mun."""
import json
import re

from planner.data import MAX_UNITS, MIN_UNITS, load_catalogs, load_requirements
from planner.llm import ask

# The scenario format of design.md section 5.1, in plain words. The course codes and focus areas follow it in the prompt.
TASK = """You read a message from an NUS Computer Science student (BComp Computer Science, single degree) and write \
down what it says as a scenario: a JSON object with exactly the seven fields below. Do not plan anything yourself."""

FIELDS = f"""Fields:
- "matric_ay": the academic year the student matriculated in, as a string "YYYY-YYYY". "AY2025/26" is "2025-2026".
- "current_semester": the semester the student is about to start, as an integer from 1 to 8. Year 1 Semester 1 is 1, \
Year 1 Semester 2 is 2, Year 2 Semester 1 is 3, and so on up to Year 4 Semester 2, which is 8.
- "completed": the courses the student has already completed, as a list of course codes.
- "focus_area": the student's focus area, copied exactly from the list of focus areas.
- "min_units": always {MIN_UNITS}.
- "max_units": always {MAX_UNITS}.
- "must_take": the courses the student insists on taking, as a list of course codes. An empty list if there are none."""

NOTES = """Notes:
- Use only course codes from the list of course codes. Leave out any course the student mentions that is not in it.
- Write each code exactly as in the list, in capital letters, e.g. "CS2030S".
- Do not add any other field."""

REPLY_FORMAT = """Reply with only the JSON object and no other text, for example
{"matric_ay": "2025-2026", "current_semester": 3, "completed": ["CS1231S"], "focus_area": "<a focus area>", \
"min_units": 18, "max_units": 23, "must_take": ["CS2030S"]}"""

FIELD_TYPES = {"matric_ay": str, "current_semester": int, "completed": list, "focus_area": str,
               "min_units": int, "max_units": int, "must_take": list}


def course_codes():
    """The set of every course code in any catalog year."""
    catalogs = load_catalogs()
    codes = set()
    for catalog in catalogs.values():
        codes.update(catalog["courses"])
    return codes


def focus_area_names():
    """The list of focus area names the student can choose from."""
    # shortcut: one requirements file covers every cohort we model; use the newest one
    requirements = load_requirements(max(load_catalogs()))
    return list(requirements["focus_areas"])


def system_prompt():
    """The task, the fields, the allowed focus areas and course codes, and the reply format. It is the same for every
    student, so ask() caches it."""
    codes = ", ".join(sorted(course_codes()))
    focus_areas = "\n".join(f"- {name}" for name in focus_area_names())
    return (f"{TASK}\n\n{FIELDS}\n\nFocus areas:\n{focus_areas}\n\nCourse codes:\n{codes}\n\n{NOTES}\n\n{REPLY_FORMAT}")


def parse(reply):
    """The JSON object in a model reply, or None if the reply doesn't hold one."""
    try:
        scenario = json.loads(reply[reply.index("{"):reply.rindex("}") + 1])
    except ValueError:  # no braces in the reply, or the JSON is cut off or malformed
        return None
    return scenario if isinstance(scenario, dict) else None


def has_valid_types(scenario):
    """True if the scenario has exactly the seven fields, each of the right type (a bool is not an int)."""
    if set(scenario) != set(FIELD_TYPES):
        return False
    for field, expected_type in FIELD_TYPES.items():
        value = scenario[field]
        if not isinstance(value, expected_type) or isinstance(value, bool):
            return False
    for field in ("completed", "must_take"):
        if not all(isinstance(code, str) for code in scenario[field]):
            return False
    return True


def has_valid_values(scenario):
    """True if every value of a scenario with the right types is allowed: a real academic year, semester 1-8, the fixed
    unit limits, a real focus area and only known course codes."""
    years = re.fullmatch(r"([0-9]{4})-([0-9]{4})", scenario["matric_ay"])
    if years is None or int(years[2]) != int(years[1]) + 1:
        return False
    if not 1 <= scenario["current_semester"] <= 8:
        return False
    if (scenario["min_units"], scenario["max_units"]) != (MIN_UNITS, MAX_UNITS):
        return False
    if scenario["focus_area"] not in focus_area_names():
        return False
    known_codes = course_codes()
    return all(code in known_codes for code in scenario["completed"] + scenario["must_take"])


def check(scenario):
    """The scenario if it follows design.md section 5.1, otherwise None."""
    if scenario is None or not has_valid_types(scenario) or not has_valid_values(scenario):
        return None
    return scenario


def translate(text):
    """Return a scenario dict in the design.md section 5 format, or None if the reply can't be parsed into one
    (scored as no_answer). Call the model through planner.llm.ask so every approach shares one model and cost log."""
    reply, _ = ask(system_prompt(), text)
    return check(parse(reply))
