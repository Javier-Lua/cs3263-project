# Plan My Degree

CS3263 Foundations of AI project (NUS, Semester 1 AY2026/27).

Can a frontier LLM plan an NUS Computer Science student's remaining semesters by itself, or does it do better when it translates the request into a specification that a constraint solver solves? We compare both approaches on real NUSMods course data, using each academic year's own data.

**Read [docs/design.md](docs/design.md) first.** It covers scope, rules, data and file formats, evaluation, and who does what.

## Results

60 test students (37 who can finish their degree, 23 who can't), each asked 3 times in plainly worded and loosely worded messages, with Claude Sonnet 5.5:

- **Both approaches are nearly always right.** Direct scored 99.4% (2 slips in 360 answers) and tool-assisted 100%. The gap isn't statistically significant.
- **Tool-assisted is about 5 times cheaper and 3 times faster, and gives the same plan every time.** Direct's plans differ between runs, and its effort grows with the number of semesters to plan.
- **Plan quality is even** once the solver has an objective, which we chose after seeing direct's plans.

The tables, figures and caveats are in [docs/analysis.md](docs/analysis.md).

## Setup

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

Tests never call the LLM.

To call the LLM, copy `.env.example` to `.env` (git-ignored) and put the Claude API key in it. Then run an approach over a scenario file, for example `python -m planner.run direct examples 1`; the usage is in [planner/run.py](planner/run.py). `gold` runs the solver on the gold scenarios and needs no key. Each run saves a file in `results/`. `python -m planner.analyze <results files>` prints the analysis tables. The exact command is at the top of [docs/analysis.md](docs/analysis.md).

## Layout

| Path | What |
|---|---|
| `docs/design.md` | The plan everyone builds from |
| `docs/analysis.md` | The results, with figures in `docs/figures/` |
| `docs/scenarios.md` | How the test students were chosen and worded |
| `data/catalog/<AY>.json` | Frozen NUSMods data, one file per academic year. Generated; don't edit by hand. |
| `data/requirements/<AY>.json` | Degree rules typed in from the SoC pages, one file per first cohort they apply to |
| `data/build_catalog.py` | Rebuilds the catalogs: `python data/build_catalog.py 2025-2026 2026-2027` |
| `scenarios/` | Test students: English text, gold JSON, expected answer. `main.json` (M01-M60, plainly worded), `reworded.json` (R01-R60, the same students worded loosely), `examples.json` (5 hand-checked examples) |
| `planner/` | Data loading, validator, solver, LLM approaches, experiment runner, analysis (owners in the design doc) |
| `results/` | One file per run: every answer, its score and its cost |
| `tests/` | Data checks, and tests for the validator, solver, both approaches, runner and analysis |
