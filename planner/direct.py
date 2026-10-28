"""The direct approach: the LLM reads the message and the course data and writes the plan itself. Owner: Javier."""
import json

from planner.data import load_catalogs, load_requirements
from planner.llm import ask

# design.md sections 2 and 4 in plain words. It follows the data in the system prompt.
RULES = """You plan the rest of an NUS Computer Science degree (BComp Computer Science, single degree). Above are \
the degree requirements, and a catalog of courses for each academic year, keyed by academic year and course code.

The student's message says when they matriculated, which semester they are about to start, the courses they have \
completed, their focus area, the minimum and maximum units they want each semester, and any courses they insist on.

Semesters are numbered 1 to 8: Year 1 Semester 1 is 1, Year 1 Semester 2 is 2, and so on up to Year 4 Semester 2, \
which is 8. Odd semesters are Semester 1 of an academic year and even ones are Semester 2. For a student who \
matriculated in academic year Y-(Y+1), semester k falls in academic year Y + (k-1)//2; for the 2025-2026 cohort, \
semesters 3 and 4 fall in 2026-2027. Each semester uses its own academic year's catalog. A year with no catalog uses \
the newest catalog. A course's "semesters" holds the semesters it is offered in ("1", "2"), each with its lectures as \
[day, start, end] in 24-hour time, and its exam as {"start": Singapore time, "minutes": length}, or null for no exam.

Plan every semester from the one the student is about to start through semester 8. Besides catalog courses you may \
use "ELECTIVE", which stands for any course outside the catalog: 4 units, always offered, with no prerequisites, \
lectures or exam, and usable any number of times. It counts towards units only, never towards required, focus-area \
or insisted-on courses.

"Taken" means completed or planned. The plan must follow every one of these rules:
1. Every planned entry is a course code from the catalogs, or ELECTIVE.
2. No course is planned twice, or planned after it was completed. ELECTIVE is exempt.
3. Courses are planned only from the semester the student is about to start through semester 8.
4. A course planned in a semester is in that semester's catalog and offered in that semester (1 or 2).
5. Its "prereq", from that semester's catalog, is met by courses completed or planned in earlier semesters; the same \
semester does not count. A prereq is null (none), a course code, false (never met), {"and": [...]}, {"or": [...]}, \
or {"nOf": [n, [...]]}, meaning at least n of the list.
6. For each pair in "same_semester", both courses are completed, or both are planned in the same semester.
7. No planned course is precluded by another taken course. Two courses preclude each other if either lists the \
other in its "preclusions" in any catalog.
8. No two courses in the same semester have lectures on the same day with overlapping times. One ending exactly \
when the other starts is fine.
9. No two courses in the same semester have overlapping exams, each running from its start for its length.
10. Every planned semester has between the student's minimum and maximum units, inclusive. Units come from that \
semester's catalog, and ELECTIVE is 4.
11. Every "required" course is taken.
12. At least "min_primaries" courses from the student's focus area in "focus_areas" are taken, and at least \
"min_primaries_level_4000" of them are level 4000 or above (the first digit of the code's number is 4 or more).
13. Every course the student insists on is taken.

If no plan can follow every rule, say so. Reply with only a JSON object and no other text, either
{"status": "plan", "semesters": {"<semester number>": ["<course code or ELECTIVE>", ...], ...}}
with a key for every semester from the one the student is about to start through 8, or
{"status": "impossible", "reason": "<one sentence>"}"""


def system_prompt():
    """The requirements, every catalog year and the rules (design.md section 6.1). It is the same for every student,
    so ask() caches it."""
    catalogs = load_catalogs()
    # shortcut: one requirements file covers every cohort we model; send every file once a second one is added
    requirements = load_requirements(max(catalogs))
    courses = {ay: {code: {k: v for k, v in course.items() if k not in ("title", "hours")}  # no rule needs these
                    for code, course in catalog["courses"].items()} for ay, catalog in catalogs.items()}
    return (f"<requirements>\n{json.dumps(requirements)}\n</requirements>\n\n"
            f"<catalogs>\n{json.dumps(courses, separators=(',', ':'))}\n</catalogs>\n\n{RULES}")


def plan_direct(text):
    """Return a plan dict in the design.md section 5 format, or None if the reply can't be parsed (scored as no_answer).
    Prompt contents: design.md section 6.1."""
    reply, _ = ask(system_prompt(), text)
    return parse(reply)


def parse(reply):
    """The plan in a model reply, or None if the reply doesn't hold one in the design.md section 5.2 format."""
    try:
        plan = json.loads(reply[reply.index("{"):reply.rindex("}") + 1])
    except ValueError:  # no JSON object in the reply
        return None
    if plan.get("status") == "impossible":
        return {"status": "impossible", "reason": plan.get("reason", "")}
    semesters = plan.get("semesters")
    if plan.get("status") != "plan" or not isinstance(semesters, dict) or not all(
            k.isdigit() and isinstance(v, list) and all(isinstance(c, str) for c in v) for k, v in semesters.items()):
        return None
    return {"status": "plan", "semesters": semesters}
