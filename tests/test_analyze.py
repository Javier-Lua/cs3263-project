"""Checks for the analysis helpers (planner/analyze.py)."""
from planner.analyze import quality


def test_quality_counts_units_required_courses_and_real_courses():
    entry = {"scenario": {"matric_ay": "2025-2026", "current_semester": 7, "completed": []}}
    plan = {"status": "plan", "semesters": {"7": ["CS2100"] + ["ELECTIVE"] * 4, "8": ["ELECTIVE"] * 5}}
    q = quality(entry, plan)
    assert q["units_sd"] == 0  # 20 units in both semesters
    assert q["last_required"] == 7  # CS2100 is required
    assert q["real_courses"] == 1
