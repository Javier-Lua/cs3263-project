"""Checks for the analysis helpers (planner/analyze.py)."""
from planner.analyze import quality


def test_quality_counts_units_required_courses_and_real_courses():
    entry = {"scenario": {"matric_ay": "2025-2026", "current_semester": 7, "completed": []}}
    plan = {"status": "plan", "semesters": {"7": ["CS2100"] + ["ELECTIVE"] * 4, "8": ["ELECTIVE"] * 5}}
    q = quality(entry, plan)
    assert q["units_sd"] == 0  # 20 units in both semesters
    assert q["last_required"] == 7  # CS2100 is required
    assert q["real_courses"] == 1


def test_intervals_and_tests_count_students_not_answers():
    from planner.analyze import interval, paired_p

    def rows(flags):  # one row per answer; the student is the id without its set letter
        return [{"id": f"M{s:02d}", "outcome": "valid_plan" if ok else "invalid_plan"}
                for s, answers in enumerate(flags) for ok in answers]
    perfect, one_wrong = rows([[1, 1, 1]] * 10), rows([[0, 0, 0]] + [[1, 1, 1]] * 9)
    assert interval(perfect)[0] < 0.75  # every answer right: a Wilson interval for 10 students, not 30 answers
    lo, hi = interval(one_wrong)
    assert lo <= 0.9 <= hi
    assert paired_p(one_wrong, perfect) == 1.0  # one student differs: half the sign flips are as extreme
    assert paired_p(perfect, perfect) == 1.0
    assert paired_p(rows([[0, 0, 0]] * 6 + [[1, 1, 1]] * 4), perfect) == 2 / 64  # only both all-same signs


def test_feedback_replaces_only_the_fed_back_answers(capsys):
    from planner.analyze import feedback

    rows = [{"id": "M01", "run": k, "approach": a, "setting": "Haiku", "set": "explicit", "model": "claude-haiku-5-5",
             "outcome": "invalid_plan" if (a, k) == ("direct", 1) else "valid_plan"} for a in ("direct", "tool")
            for k in (1, 2)]
    fed = [{"id": "M01", "run": 1, "model": "claude-haiku-5-5", "thinking": True, "first_outcome": "invalid_plan",
            "outcome": "valid_plan", "rounds": [{}], "cost": 0.01}]
    feedback(rows, fed)
    line = next(l for l in capsys.readouterr().out.splitlines() if l.startswith("| Haiku | explicit and reworded"))
    assert "| 50.0% | 100.0% |" in line and "$0.0050" in line  # 1 of 2 direct answers fixed; cost spread over both
