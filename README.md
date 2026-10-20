# Plan My Degree

CS3263 Foundations of AI project (NUS, Semester 1 AY2026/27).

Can a frontier LLM plan an NUS Computer Science student's remaining semesters by itself, or does it do better when it translates the request into a specification that a constraint solver solves? We compare both approaches on real NUSMods course data, using each academic year's own data.

**Read [docs/design.md](docs/design.md) first.** It covers scope, rules, data and file formats, evaluation, and who does what.

## Setup

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

Tests for code that isn't written yet are skipped, not failed.

## Layout

| Path | What |
|---|---|
| `docs/design.md` | The plan everyone builds from |
| `data/catalog/<AY>.json` | Frozen NUSMods data, one file per academic year. Generated; don't edit by hand. |
| `data/requirements/<AY>.json` | Degree rules typed in from the SoC pages, one file per first cohort they apply to |
| `data/build_catalog.py` | Rebuilds the catalogs: `python data/build_catalog.py 2025-2026 2026-2027` |
| `scenarios/` | Test students: English text, gold JSON, expected answer |
| `planner/` | Data loading, validator, solver, LLM approaches, experiment runner (owners in the design doc) |
| `tests/` | Data checks, and acceptance tests for the validator and solver |
