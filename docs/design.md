# Plan My Degree: design

Draft for the team review on **Thu 22 Oct 2026**. Items marked **(new)** were in neither teammate's proposal, so please challenge them. **(proposed)** marks smaller calls made while writing this doc. Owners are proposals until we agree on Thursday.

## 1. What we are building

A student describes their situation in plain English. Each approach answers with a semester-by-semester plan up to Year 4 Semester 2, or says no plan exists. We compare three approaches:

- **Direct.** The LLM reads the message and the course data, then writes the plan itself.
- **Tool-assisted.** The LLM only turns the message into a structured scenario (JSON), and a constraint solver finds the plan. This is the LLM+P pattern (proposal reference [4]). **(new: the LLM's only job here is translation.)** Every wrong answer then has one of two causes: the LLM misread the student, or our model or solver is wrong. §8.2 separates the two.
  - **Decision (team, 21 Oct): translation stays.** The project guidelines require the model to translate the problem into a specification that a tool solves, so we do not feed gold JSON to the solver in the main comparison. Translation errors are reported separately (§8.2), which addresses the worry that they add noise.
- **Hybrid** (stretch goal, **definition undecided**, see §6.3 and §11). Not built until the Direct and Tool-assisted approaches run.

Any plan that breaks none of the rules in §4 counts as correct. We don't look for a best plan (tutor Q1). Optimising plan quality is a stretch goal.

## 2. Scope and assumptions

- **Students:** single-degree BComp (Computer Science), matriculating in AY2025/26 or later.
- **Semester numbering:** semesters are numbered 1–8 (Y1S1 = 1 … Y4S2 = 8). Odd numbers are Sem 1 and even numbers are Sem 2. Special terms are not modelled.
- **Year-by-year data (new).** This replaces "one AY's timetable as a proxy".
  - Each semester uses NUSMods data from its own academic year. For a student who matriculated in AY *y*, semester *k* falls in AY *y* + ⌊(*k*−1)/2⌋.
  - Years NUSMods hasn't published yet (AY2027/28 onwards, as of 20 Oct) use the newest published year, currently AY2026/27. Which semesters use a stand-in depends only on the scenario, so the runner records it and the approaches don't have to **(proposed)**.
- **What is checked.** Only the modelled requirements:
  - the 13 required courses
  - the focus-area rule
  - the CS2101/CS2103T same-semester rule **(new; from the curriculum page)**
- **What is not modelled:**
  - common curriculum, unrestricted electives and the 160-unit total
  - the 12-unit level-4000 breadth & depth rule and industry experience
  - CFCs counting as primaries
  - grades and S/U
  - blocked semesters (internship, exchange). Dropped by team decision to keep the implementation simple.
  - other routes into a prerequisite, such as UTC2851 instead of CS1101S
- **ELECTIVE slot (new).** `ELECTIVE` is a 4-unit requirement placeholder, not a course a student can register for. Every course outside the catalog is treated as a generic `ELECTIVE`: 4 units, always offered, with no prereqs, lectures or exam, and it can repeat. It counts towards units only, never towards required, focus-area or must-take courses. Without it, the minimum workload would force random CS courses into every semester.
- **Timetable detail.** We use lectures and exams only, with no tutorials or labs. Each course keeps one fixed lecture group: the lowest class number.
- **Prerequisites.** Minimum grades are ignored. Every student is assumed to have A-level H2 Maths, so MA1301/MA1301X prereqs count as met **(new)**.
- **CS1101S.** We assume the standard CS1101S route into CS1010-type prerequisites. Approved alternatives such as UTC2851 are out of scope.
- **Workload** is counted in units: 18 to 23 in every semester from `current_semester` to 8, in every scenario **(team decision)**. Scenarios keep `min_units` and `max_units`, always 18 and 23 (`tests/test_data.py` checks this), so the solver needed no change.

Where the two proposals differed:

| Question | Decision |
|---|---|
| Workload limit: units or hours/week? | Units, 18 to 23 a semester. Hours/week is only a balance statistic. |
| Preclusions: keep or skip? | Keep. They are cheap, and the AI ones are a real trap (§3.3). |
| Planning period | From `current_semester` to semester 8 |
| Preferred ("fun") courses | `must_take`, a hard constraint |
| Focus area | The student picks exactly one |

## 3. Data

### 3.1 Files

| File | What it is |
|---|---|
| `data/catalog/<AY>.json` | NUSMods data for every course we model, one file per academic year. Generated with `python data/build_catalog.py 2025-2026 2026-2027` (built 20 Oct 2026). Committed and frozen: rebuild only if the team agrees. |
| `data/requirements/<AY>.json` | Degree rules typed by hand from the SoC pages; sources and the retrieval date are inside. A file applies to that cohort and every later cohort until a newer file is added. `2025-2026.json` covers what SoC calls "CS cohort 2025 and after". |
| `planner/data.py` | The only code that reads these files. `load_catalogs()`; `term(matric_ay, k)` → (AY, 1 or 2); `catalog_for(catalogs, ay)` → (catalog, AY the data really comes from); `load_requirements(matric_ay)`; `load_scenarios()`. |

The courses we model are the 13 required courses plus every focus-area primary, 74 codes in all. The AY2026/27 catalog has 73 of them and the AY2025/26 catalog has 67.

### 3.2 Fields (tutor Q3)

| Needed for | NUSMods field | Catalog field | What we do to it |
|---|---|---|---|
| Units | `moduleCredit` | `units` | Convert to an integer |
| Level 4000 rule | course code | `level` | First digit × 1000 |
| Prerequisites | `prereqTree` | `prereq` | An and/or/nOf tree of catalog codes. We drop grade suffixes and expand `CS1010%` wildcards. Courses outside the catalog become `false`, and MA1301/MA1301X become `true`. `null` means no prereq; `false` means the course can never be planned. |
| Preclusions | `preclusionRule` | `preclusions` | The catalog codes named in the rule |
| Semesters offered | `semesterData[].semester` | keys of `semesters` (`"1"`, `"2"`) | Special terms dropped |
| Lectures | `semesterData[].timetable`, Lecture rows | `semesters[s].lectures` = `[[day, start, end]]` | Lowest `classNo` group only |
| Exam | `examDate` (UTC), `examDuration` | `semesters[s].exam` = `{start, minutes}` or `null` | Converted to Singapore time |
| Hours per week | `workload` | `hours` | Sum of its five numbers. Used for plan-quality statistics only. |
| Degree requirements | none | requirements file | Typed by hand |

Example entry, AY2026/27:

```json
"CS2109S": {"title": "Introduction to AI and Machine Learning", "units": 4, "level": 2000, "hours": 10,
  "prereq": {"and": ["CS2040S", "MA1521"]}, "preclusions": ["CS3243", "CS3244"],
  "semesters": {"1": {"lectures": [["Thu", "0800", "1000"]], "exam": {"start": "2026-11-26T17:00", "minutes": 120}},
                "2": {"lectures": [["Tue", "1000", "1200"]], "exam": {"start": "2027-05-03T17:00", "minutes": 120}}}}
```

### 3.3 What the build flagged

- **The data really does change by year.** From AY2025/26 to AY2026/27:
  - Prereqs changed for 5 courses. For example, CS2109S no longer needs CS1231S.
  - Offerings changed for 8 courses. For example, CS3243 went from both semesters to Sem 2 only, and CS4212 moved from Sem 1 to Sem 2.
- **Missing from NUSMods:**
  - CS4232 is missing in both years; SoC says it is no longer offered from AY2021/22.
  - AY2025/26 is also missing CS2111, CS3227, CS4263, CS4310, CS4353 and CS4430.
- **Listed but not offered in Sem 1 or 2:**
  - AY2025/26: CS4224, CS4242, CS4244.
  - AY2026/27: CS3217, CS3245, CS4242, CS4244, CS4310, CS4347.
  - So once AY2026/27 stands in for later years, only CS2108 and CS4248 can be planned for **Multimedia Information Retrieval**. This focus area is not impossible for everyone: a student who has already completed another qualifying primary can still meet the "at least 3 primaries" rule.
- **Wildcard and CS1101S check (checked against the NUSMods API on 25 Oct).** No modelled course has a `%` wildcard in its prereq tree in AY2025/26 or AY2026/27, so the wildcard branch in `build_catalog.py` never runs. CS2030S, CS2040S, CS2100, CS2107 and (in AY2026/27) CS2111 list explicit codes including CS1101S, and the catalog keeps CS1101S as their prereq, so CS1101S is recognised. If a `%` wildcard ever appears, it expands to catalog codes only, so a `CS1010%` pattern would become `false`. Check this before relying on it.
- **CS2109S blocks three AI primaries.** Every CS student must take CS2109S, and it precludes CS3243, CS3244 and CS4263. So those three can't count towards the AI focus area. Expect the direct LLM to trip on this.
- **Prereqs we can't model:** CS3242 needs physics, CS3282 needs CS3281 and CS4330 needs biology. These courses are never plannable, but they still count if the student has completed them.
- **No-clash course:** CS2101 has no lectures or exam in the data, so it never clashes.
- **CS4263's preclusion rule** lacks the "(1)" count the other rules have. Its text says any of CS2109S/CS3243/CS3263 precludes it, so we treat it that way.
- **Single-semester courses:** 37 of the 73 AY2026/27 courses run in only one semester, for example CS4234 (Sem 1).

## 4. Validity rules

A plan is valid if it breaks none of these rules.

- "Taken" means completed or planned.
- Data for semester *k* comes from `catalog_for(catalogs, ay)`, where `ay, sem = term(matric_ay, k)`.
- The validator reports each break with the rule's id.

| # | id | Rule |
|---|---|---|
| 1 | `known` | Every planned entry is a course code in some catalog, or `ELECTIVE`. |
| 2 | `repeat` | No course is planned twice, or planned after it was completed. `ELECTIVE` is exempt. |
| 3 | `horizon` | Courses are planned only in semesters `current_semester` … 8. |
| 4 | `offered` | A course planned in semester *k* is in that year's catalog and offered in that semester (1 or 2). |
| 5 | `prereq` | Its prereq tree, from that year's catalog, is met by courses completed or planned in *earlier* semesters. The same semester doesn't count, and `false` is never met. |
| 6 | `same_semester` | For each pair in the requirements' `same_semester` list (CS2101 + CS2103T), both are completed, or both are planned in the same semester. |
| 7 | `preclusion` | No planned course is precluded by another taken course. Two courses preclude each other if either lists the other in any year's catalog. |
| 8 | `lecture_clash` | No two courses in the same semester have lectures on the same day with overlapping times. One ending exactly when the other starts is fine. |
| 9 | `exam_clash` | No two courses in the same semester have overlapping exams, each running from `start` to `start + minutes`. |
| 10 | `workload` | Every semester from `current_semester` to 8 has `min_units` ≤ units ≤ `max_units`. Units come from that year's catalog, and `ELECTIVE` = 4. |
| 11 | `required` | Every required course is taken. |
| 12 | `focus_area` | At least 3 primaries of the chosen focus area are taken, and at least one of them is level 4000+. |
| 13 | `must_take` | Every `must_take` course is taken. |

The validator (`planner/validate.py`) shares no code with the solver, so a solver bug can't be copied into the checker. `tests/test_examples.py` already holds the validator's acceptance tests: the S001 witness must pass, and 12 broken versions of it must fail with the right ids. Every broken case is a real clash, preclusion and so on from the AY2026/27 data, checked by hand.

## 5. Formats

### 5.1 Scenario

This is the format of the gold scenarios, and also what `translate()` must output.

| Field | Meaning |
|---|---|
| `matric_ay` | Matriculation year, e.g. `"2025-2026"` |
| `current_semester` | First semester to plan, 1–8. Every earlier semester is finished. |
| `completed` | Course codes already passed. Catalog codes only; anything else the student mentions is left out. |
| `focus_area` | Exactly one key of `focus_areas` in the requirements file |
| `min_units`, `max_units` | Limits for every semester from `current_semester` to 8: always 18 and 23 (`MIN_UNITS`, `MAX_UNITS` in `planner/data.py`) |
| `must_take` | Catalog courses the student insists on |

`translate()` checks its output against this table: every field present with the right type, every code known, `focus_area` a real key, semesters within 1–8, and `min_units` ≤ `max_units`. Output that fails becomes `None` and is scored `no_answer`; it never reaches the solver **(proposed)**. If a bad value still gets past the check and the solver raises an error, the runner scores that answer `no_answer` as well and saves the error in the results line as `solver_error`, so that a solver bug can't pass for a bad translation.

A scenario file (`scenarios/*.json`) is a list of entries with these fields:

- `id`
- `text`: the student's message
- `scenario`
- `expected`: `"feasible"` or `"impossible"`
- `witness` (feasible entries only): a plan the validator accepts
- `why` (impossible entries only): one sentence on why no plan exists
- `tags` (optional), e.g. `["exam_clash", "tight_units"]`, for breaking results down

See [scenarios/examples.json](../scenarios/examples.json): S001 is feasible and S002 is impossible.

### 5.2 Plan

Every approach returns a plan in this format:

```json
{"status": "plan", "semesters": {"3": ["CS2030S", "CS2040S", "CS2100", "ST2334"], "6": [], "8": ["ELECTIVE", "ELECTIVE"]}}
{"status": "impossible", "reason": "free text, not graded"}
```

A semester that is missing from `semesters` has no courses. A model reply that can't be parsed into this format becomes `None`, which is scored `no_answer`.

## 6. Approaches

### 6.1 Direct (Javier)

One LLM call. The prompt contains:

- the rules of §4 in plain words
- the requirements file
- every catalog year in a compact form
- the year-mapping and stand-in rule
- the student's message

The reply is a plan in the §5.2 format. Both LLM approaches get the same message and the same data, so the comparison is fair.

### 6.2 Tool-assisted (Weng Mun)

1. `translate(text)`: one LLM call that returns scenario JSON. The prompt gives the field definitions, the focus-area names and the catalog codes. It also says how to read "Year 2 Semester 1" as semester 3 and "AY2025/26" as `"2025-2026"`.
2. `solve(scenario)`: returns a plan that meets §4, or `impossible`. The LLM never sees timetables.

A suggested encoding for OR-Tools CP-SAT (Weng Mun's call):

- **Variables.** `x[c,k]` ∈ {0,1} for each catalog course *c* offered in semester *k*, and an integer `e[k]` ≥ 0 for ELECTIVE slots.
- **Course counts.** Each course is taken at most once, and never if already completed. A required or must-take course that isn't completed has Σₖ `x[c,k]` = 1.
- **Prereqs.** Turn the tree into Booleans: `and` → all, `or` → any, `nOf` → sum ≥ n. The leaves are "completed, or Σ_{j<k} `x[c',j]`".
- **Clashes.** Precompute the clashing pairs per semester, then add `x[a,k] + x[b,k]` ≤ 1.
- **Preclusions.** Σₖ `x[a,k]` + Σₖ `x[b,k]` ≤ 1. If the other course is completed, the sum must be 0.
- **Same semester.** `x[CS2101,k]` = `x[CS2103T,k]` for every *k*.
- **Workload.** min ≤ Σ units·x + 4·`e[k]` ≤ max in every semester from `current_semester` to 8.
- **Focus area.** At least 3 primaries taken, at least 1 of them level 4000+.
- **Objective.** Feasibility only. The stretch goal adds an objective, such as balance.

### 6.3 Hybrid (stretch, Javier; definition undecided)

Two candidate definitions, to settle after Direct and Tool-assisted run (§11):

- **Validator feedback (this doc's earlier draft).** Run the direct approach. Then, for up to 3 rounds, send the validator's violations back and ask for a revised plan. The report must say that this approach uses the evaluator as a tool. It gives no feedback on "impossible" answers, and costs up to 4 calls per scenario.
- **Structured steps (the proposal).** One call whose prompt tells the LLM to follow course methods itself, such as checking rules one at a time or assigning semesters with backtracking, with no solver and no validator.

### 6.4 LLM settings (all approaches)

- Every approach calls the LLM through `planner/llm.py: ask()`, so all of them use the same model and settings: Claude Sonnet 5.5 (`claude-sonnet-5-5`) with adaptive thinking at effort `high`. Sonnet 5.5 doesn't accept a temperature setting, so the 3 runs below are what measure how much answers vary.
- A refused or cut-off reply can't be parsed, so it is scored `no_answer`. There is no fallback to another model, which would mix models in the results.
- Each (scenario, approach) pair runs 3 times. Accuracy is computed per run, and we report the mean and the min–max over the 3 runs **(proposed)**. `solve()` is deterministic, so the ablation on gold scenarios runs once.
- The runner (`python -m planner.run direct|tool|gold <scenario file> [runs]`) writes `results/<date>-<time>-<approach>.jsonl`, one line per answer, with every LLM reply and its tokens, seconds and cost. Prompts aren't logged; they are rebuilt from the code and data at that commit. Commit the runs the report uses, so its numbers can be reproduced **(proposed)**.
- Before the full run, a 5-scenario pilot measures tokens and cost against the $100 claim.
  - **Pilot, 27 Oct** (direct, the 5 examples, 1 run, `results/2026-10-27-2038-direct.jsonl`): $0.12 in all, 2.4 cents per answer, 3–14 s each. Caching worked: one write of the 18,400-token prompt, then reads. At this rate the full direct run (about 60 scenarios × 3) costs about $5, so the budget isn't the limit.
  - It called S002, S003 and S005 impossible for the right reasons. Its S001 and S004 plans stay unscored until `validate()` exists, but the solver's model accepts both. Harder scenarios are needed to separate the approaches.
- `ask()` caches the system prompt, so the shared data belongs there. The direct prompt is about 18,400 tokens, and a cached read of it costs under half a cent.

## 7. Scenarios and ground truth

- **Count.** About 60 scenarios: 15 by Mon 26 Oct and the rest by Thu 29 Oct. Roughly two-thirds should be feasible.
  - **Done:** `scenarios/main.json` holds 55 test students (34 feasible, 21 impossible), listed with what each one tests in [scenarios.md](scenarios.md). The 5 examples in `scenarios/examples.json` were used to build and pilot the approaches, so they stay out of the main set. The full runs use `main`.
- **Write the scenario JSON first, then the English text from it (new).** The text states every field explicitly, so there are no defaults to guess: the matriculation year as "AY2025/26", semesters as "Year 2 Semester 1", and both unit limits.
- **Ground truth.**
  - Each feasible scenario carries a witness plan that the validator accepts. Write the first 15 witnesses by hand. After that, a plan from the solver is fine, because the validator checks it independently **(proposed)**.
  - Each impossible scenario is impossible on purpose, with the reason in `why`.
  - The solver must agree with every label (`tests/test_examples.py`). When it doesn't, find the bug (solver, validator or scenario) before changing a label.
- **What to cover:**
  - students early and late in the degree
  - too many courses left to fit under 23 units a semester
  - must-take courses with long prereq chains
  - the CS2101/CS2103T pair
  - single-semester courses
  - real clashes: the CS2107 and CS4248 exams clash in AY2026/27 Sem 1, and CS2108 and CS2109S lectures clash in Sem 2
  - the AI preclusions
  - Multimedia IR: only CS2108 and CS4248 can be planned, so it is feasible only for students who already completed another primary
- **Stretch.** Several phrasings of the same scenario, to test robustness to wording.

## 8. Evaluation

### 8.1 Outcomes and accuracy (tutor Q4)

Every answer gets exactly one outcome, computed by `planner/run.py: outcome()`, which is already written and tested:

| Expected | Answer | Outcome | Correct |
|---|---|---|---|
| feasible | plan with no violations | `valid_plan` | yes |
| feasible | plan with violations | `invalid_plan` | no |
| feasible | impossible | `false_impossible` | no |
| impossible | impossible | `correct_impossible` | yes |
| impossible | any plan | `plan_for_impossible` | no |
| either | unparseable reply | `no_answer` | no |

**Accuracy** = (`valid_plan` + `correct_impossible`) / number of answers. Report the whole table for each approach, not just the accuracy, because the table shows *how* each approach fails.

### 8.2 Where tool-assisted errors come from (new)

- **Translation accuracy.** Compare `translate(text)` with the gold scenario field by field, comparing lists as sets. Report the share of scenarios translated perfectly, and the error rate for each field.
- **Perfect-translation ablation.** Run `solve()` on the gold scenarios. This should score 100%, and if it does, every tool-assisted error is a translation error.

`python -m planner.run tool` reports translation accuracy, and `python -m planner.run gold` runs the ablation.

### 8.3 Secondary metrics

- **Violations per rule id (§4):** which rules each approach breaks most often.
- **Cost:** time, tokens and API cost per scenario.
- **Plan quality (tutor Q2).** Descriptive only, measured on valid plans:
  - the spread of units, and of hours per week, across the planned semesters (an ELECTIVE counts as 10 h/week, using NUS's 2.5 hours per unit)
  - the last semester that still holds a required course

  None of these affect accuracy.

## 9. Code layout

```
data/build_catalog.py      rebuild data/catalog/ from NUSMods (team decision)       Zechary
data/catalog/<AY>.json     frozen NUSMods data, generated                           Zechary
data/requirements/<AY>.json  degree rules, hand-typed                               Zechary
scenarios/*.json           test students                                            Zechary
planner/data.py            loaders and the semester-to-year mapping (done)          shared
planner/validate.py        checks a plan against section 4                          Zechary (proposed)
planner/solver.py          finds a plan or proves none exists (written)             Weng Mun
planner/translate.py       LLM: message -> scenario JSON                            Weng Mun
planner/llm.py             the one place that calls the LLM API (written)           Javier
planner/direct.py          LLM writes the plan itself (written)                     Javier
planner/run.py             runs an approach on the scenarios, scores it (written)   Javier
tests/                     data checks and solver tests (pass); acceptance tests (skip until validate() exists)
```

The stubs define the inputs and outputs of the functions that aren't written yet. Run `pytest` before pushing.

## 10. Work plan

| When | What | Who |
|---|---|---|
| Thu 22 Oct | Review this doc. Agree owners, LLM provider and model. | all |
| Mon 26 Oct | `validate()` passing `tests/test_examples.py`; first 15 scenarios | Zechary (proposed) |
| Tue 27 Oct | `solve()` | Weng Mun |
| Tue 27 Oct | `llm.ask()` and `plan_direct()` | Javier |
| Wed 28 Oct | `translate()` | Weng Mun |
| Wed 28 Oct | `run.py` end to end on 15 scenarios, plus the cost pilot | Javier |
| Thu 29 Oct | All ~60 scenarios, with the solver agreeing on every label | Zechary |
| Fri 30 Oct | First full run: every approach × 3 runs | Javier |
| Wed 4 Nov | Analysis. Stretch goals: hybrid, phrasings, optimisation | all |
| Fri 6 Nov | Draft report and slides | all |
| Week of 9 Nov | Presentation (15 min + 5 min Q&A) | all |
| Fri 13 Nov | Final report: at most 10 pages, stating each member's contributions and which parts AI did | all |

The proposal's FP2 milestone (multi-semester planning by Fri 23 Oct) becomes the first full run on Fri 30 Oct.

## 11. Open items

1. **LLM provider and model. Decided:** Anthropic's Claude Sonnet 5.5 (§6.4). Put the API key in `.env` as `ANTHROPIC_KEY="..."`; `.env` is git-ignored. Up to $100 can be claimed. SoC-hosted open-weight models are free and could still serve as a second model.
2. **Topics covered since the proposal.** Two candidates fit the project. Pick at most one, after the core runs.
   - *Probabilistic offerings:* estimate how likely a course is to be offered in a future semester from past years, instead of assuming AY2026/27 repeats. NUSMods has AY2018/19 onwards, and `build_catalog.py` can fetch any year.
   - *Re-planning as an MDP* when a course turns out not to be offered.
3. **Repo visibility.** The GitHub repo is public. `.gitignore` keeps the proposal (which has matric numbers and emails) and the guidelines out of it. Consider making the repo private.
4. **Older cohorts.** A student who matriculated before AY2025/26 (e.g. a real Year 4 student today) needs their own requirements file.
5. **Hybrid definition.** The proposal and §6.3 differ; pick one or drop it. The structured-steps version is simpler to build.
6. **Optimisation** stays a stretch goal and is not decided.
7. **Responsible AI section.** Possible points: the risk of trusting an LLM-made plan, stand-in years, and the validator as a safeguard.
