import json

import pytest

from planner.data import MAX_UNITS, MIN_UNITS, ROOT, catalog_for, load_catalogs, load_requirements, load_scenarios, term

SCENARIO_FIELDS = {"matric_ay", "current_semester", "completed", "focus_area", "min_units", "max_units", "must_take"}


def codes(tree):
    """Every course code in a prereq tree."""
    if isinstance(tree, str):
        return {tree}
    if not isinstance(tree, dict):  # None (no prereq) or False (never met)
        return set()
    ((op, args),) = tree.items()
    return set().union(*map(codes, args[1] if op == "nOf" else args))


def test_semesters_map_to_academic_years():
    assert term("2025-2026", 1) == ("2025-2026", 1)
    assert term("2025-2026", 4) == ("2026-2027", 2)
    assert term("2025-2026", 8) == ("2028-2029", 2)


def test_unpublished_years_use_the_newest_catalog():
    catalogs = load_catalogs()
    assert catalog_for(catalogs, "2099-2100")[1] == max(catalogs)
    with pytest.raises(KeyError):
        catalog_for(catalogs, "1999-2000")


def test_rules_apply_to_their_cohort_and_later():
    assert load_requirements("2026-2027") == load_requirements("2025-2026")
    with pytest.raises(KeyError):
        load_requirements("1999-2000")


def test_catalogs_only_mention_modelled_courses():
    modelled = set()
    for path in (ROOT / "data" / "requirements").glob("*.json"):
        reqs = json.loads(path.read_text())
        modelled |= set(reqs["required"]) | {c for area in reqs["focus_areas"].values() for c in area}
    for ay, catalog in load_catalogs().items():
        assert set(catalog["courses"]) <= modelled, ay
        for code, course in catalog["courses"].items():
            assert codes(course["prereq"]) | set(course["preclusions"]) <= modelled, (ay, code)


def test_required_courses_are_offered_every_year():
    for ay, catalog in load_catalogs().items():
        for code in load_requirements(ay)["required"]:
            assert catalog["courses"][code]["semesters"], (ay, code)


def test_example_scenarios_are_well_formed():
    known = set().union(*(c["courses"] for c in load_catalogs().values()))
    for e in load_scenarios():
        s = e["scenario"]
        assert set(s) == SCENARIO_FIELDS, e["id"]
        assert s["focus_area"] in load_requirements(s["matric_ay"])["focus_areas"], e["id"]
        assert set(s["completed"]) | set(s["must_take"]) <= known, e["id"]
        assert 1 <= s["current_semester"] <= 8 and (s["min_units"], s["max_units"]) == (MIN_UNITS, MAX_UNITS), e["id"]
        assert e["expected"] in ("feasible", "impossible"), e["id"]
        assert ("witness" in e) == (e["expected"] == "feasible") == ("why" not in e), e["id"]
