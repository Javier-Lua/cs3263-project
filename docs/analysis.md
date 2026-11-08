# Analysis

The numbers behind the report (design.md section 8), and what they suggest. Every table here comes from

```sh
python -m planner.analyze results/2026-11-03-1932-direct.jsonl results/2026-11-03-1932-tool.jsonl \
  results/2026-11-07-1314-gold.jsonl results/2026-11-04-1117-direct.jsonl results/2026-11-04-1119-tool.jsonl \
  --figures docs/figures
```

which prints the full tables, including some rows left out here.

## Runs

All LLM calls used Claude Sonnet 5.5 with adaptive thinking at effort `high` (design.md 6.4). The "explicit" set is `scenarios/main.json` (M01-M60), whose messages state every field. The "reworded" set is `scenarios/reworded.json` (R01-R60): the same 60 students and gold answers, with loosely worded messages ([scenarios.md](scenarios.md#reworded-set)).

| File | What | Cost |
|---|---|---|
| `results/2026-11-03-1932-direct.jsonl` | Direct, explicit set, 3 runs | $2.83 |
| `results/2026-11-03-1932-tool.jsonl` | Tool, explicit set, 3 runs | $0.51 |
| `results/2026-11-07-1314-gold.jsonl` | Gold ablation, re-run with the solver objective (design.md 6.2) | free |
| `results/2026-11-04-1117-direct.jsonl` | Direct, reworded set, 3 runs | $3.04 |
| `results/2026-11-04-1119-tool.jsonl` | Tool, reworded set, 3 runs | $0.66 |
| `results/2026-11-04-1112-gold.jsonl` | Gold, solver without the objective (only in section 5's last row) | free |
| `results/2026-11-03-1931-tool.jsonl` | Tool pilot on the 5 examples, 1 run (not in the tables) | $0.02 |
| `results/2026-11-04-1114-tool.jsonl` | Tool pilot on the reworded set, 1 run, used only to check the messages (not in the tables) | $0.23 |

These files cost $7.29 in all. The 27 Oct direct pilot adds $0.12. The tool plans saved in both tool files came from earlier versions of the solver. `planner/analyze.py` re-solves every saved translation with the current solver, which has the objective, and no outcome changed.

## Summary

1. **Accuracy is at the ceiling for both approaches, with explicit and with loose wording.**
   - Direct: 99.4% on both sets, 2 wrong answers out of 360.
   - Tool: 100%, none wrong out of 360.
   - Gold: 100%.
   - 2 against 0 is not a significant difference (Fisher's exact test, p ≈ 0.5). Loose wording didn't lower either approach's accuracy.
2. **Translation is nearly perfect.**
   - 98.9% of translations are perfect on the explicit set and 98.3% on the reworded set.
   - Every error is the same one: after "I failed CS2030S", the translator adds CS2030S to `must_take`. It's required anyway, so the answer stays right.
   - No loose phrasing caused a translation error in the full runs. No decoy course went into `must_take` (0 of 75).
3. **Direct's two mistakes are bookkeeping slips on long or tricky plans, and the validator catches both.**
   - It planned CS3282, whose prerequisite is `false`. The other 2 runs saw this.
   - It planned CS2101 twice in an 8-semester plan.
4. **The approaches differ in cost, speed, consistency and how effort scales, not in accuracy.**
   - Direct costs 4.6-5.6 times as much per answer and takes 3.0-3.4 times as long.
   - On 25 of the 37 feasible scenarios, direct gives a different plan each run. Tool always gives the same plan.
   - Direct's effort grows with the number of semesters to plan. The solver's doesn't (milliseconds, section 7).
5. **Plan quality: with an objective, the solver matches direct.**
   - Without an objective, the solver left required courses late. The mean last semester holding a required course was 7.1, against direct's 5.0, and direct finished them earlier in 118 of 149 paired answers. Tool plans also named more catalog courses the student didn't ask for (9.0 a plan against 7.0-7.1).
   - Weng Mun's objective (design.md 6.2) closes both gaps. The mean is now 4.96 for tool against 4.97-5.03 for direct. The two finish in the same semester in 145 of 149 pairs, and tool is earlier in the other 4. Tool names 6.95 catalog courses a plan.
   - We chose the objective after seeing direct's plans, so this shows what an objective can do, not a fair contest.

## 1. Accuracy (design.md 8.1)

| Approach | Set | Answers | valid_plan | invalid_plan | false_impossible | correct_impossible | plan_for_impossible | no_answer | Accuracy (min-max over runs) |
|---|---|---|---|---|---|---|---|---|---|
| Direct | explicit | 180 | 111 | 0 | 0 | 68 | 1 | 0 | 99.4% (98.3-100%) |
| Direct | reworded | 180 | 110 | 1 | 0 | 69 | 0 | 0 | 99.4% (98.3-100%) |
| Tool | explicit | 180 | 111 | 0 | 0 | 69 | 0 | 0 | 100% |
| Tool | reworded | 180 | 111 | 0 | 0 | 69 | 0 | 0 | 100% |
| Gold | explicit | 60 | 37 | 0 | 0 | 23 | 0 | 0 | 100% |

The wrong answers, all from direct:

| Scenario | Run | Outcome | Rules broken | What happened |
|---|---|---|---|---|
| M30 | 2 | plan_for_impossible | prereq | M30 must take CS3282, whose prereq is `false` in both catalogs, so it can never be planned. Runs 1 and 3 said so. Run 2 planned it in semester 6. |
| R57 | 3 | invalid_plan | repeat, same_semester | A new student, 8 semesters to plan. CS2101 went in both semester 2 and semester 3, so CS2101 and CS2103T (semester 3) weren't paired. Runs 1 and 2 were valid. |

**Violations per rule:** direct broke `prereq` once (explicit), and `repeat` and `same_semester` once each (reworded). Tool and gold broke none.

## 2. Where the errors come from (design.md 8.2)

| Set | Translations | Perfect | matric_ay | current_semester | completed | focus_area | must_take |
|---|---|---|---|---|---|---|---|
| explicit | 180 | 98.9% | 0 | 0 | 0 | 0 | 2 |
| reworded | 180 | 98.3% | 0 | 0 | 0 | 0 | 3 |

- All 5 errors are M55 or R55, "I failed CS2030S and still need to pass it": CS2030S was added to `must_take` (2 of 3 runs on M55, 3 of 3 on R55). It's a required course, so the solver plans it either way, and the answers were right.
- **The gold ablation scores 100%.** The solver and the validator agree on every scenario, so any tool error would come from translation.
- **The only outright translation failure** was in the reworded pilot, not the measured runs. On R38, "I have one semester left, counting the coming one", the translator wrote `null` for `current_semester`, which is scored `no_answer`. The same phrasing worked in the other 9 messages that use it, and R38 was translated correctly in all 3 full runs.

## 3. Loose wording

The reworded set changes how each field is said:
- "I just finished Y2S1", "I have five semesters left, counting the coming one"
- "I'm in the AY25/26 cohort"
- "cs2040s"
- "SWE"
- a required course the student failed or dropped
- a decoy course the student mentions but doesn't insist on

[scenarios.md](scenarios.md#reworded-set) lists every phrasing.

- **Accuracy didn't move.** Direct 99.4% and tool 100%, as on the explicit set. Every phrasing gave 100% accuracy for tool. For direct, only the phrasings in R57's message fall below 100%, and its error was a planning slip, not a misreading.
- **Tool: no phrasing caused a translation error,** and no decoy went into `must_take` (0 of 75 translations). The only errors are R55's, the same as on the explicit set.
- **Loose wording costs effort.** Tool's translation output grew from 225 to 310 tokens on average (2.4 s to 3.0 s per answer). Direct's grew from 1146 to 1263 tokens (8.1 s to 8.9 s).

So the ceiling isn't only because the explicit messages spell out every field. Within these kinds of wording, reading the student is easy for this model. Both sets are template-generated, though (section 9).

## 4. Cost and effort

| Approach | Set | Cost per answer | Seconds (mean / median / max) | Output tokens (mean) |
|---|---|---|---|---|
| Direct | explicit | $0.0157 | 8.1 / 6.5 / 19.6 | 1146 |
| Direct | reworded | $0.0169 | 8.9 / 7.7 / 22.5 | 1263 |
| Tool | explicit | $0.0028 | 2.4 / 2.6 / 4.6 | 225 |
| Tool | reworded | $0.0037 | 3.0 / 3.1 / 6.6 | 310 |

The direct prompt carries every catalog year (about 18,400 tokens, cached after the first call). The translation prompt carries only the field definitions and the course codes.

**Direct's effort grows with the planning horizon** (Weng Mun's point). Output tokens and time rise with the number of semesters left to plan:
- 1 semester: about 550-600 tokens and 4.6-5.0 s.
- 7-8 semesters: about 1950-2100 tokens and 12-14 s.
- Spearman correlation per answer: 0.51-0.56 for tokens and 0.50-0.54 for seconds.

The trend isn't smooth, because the scenarios at each horizon differ in difficulty: only 9 answers have 5 semesters left. Both of direct's wrong answers came from multi-semester plans (4 and 8 semesters). The solver's time doesn't depend on the horizon in any way that matters (section 7).

![Direct effort against semesters left](figures/direct-effort.png)

## 5. Plan quality

Measured on valid plans only. None of this affects accuracy. Tool and gold use the solver with its objective (design.md 6.2): required and must-take courses as early as possible, then as few courses planned as possible. The last row is the solver before the objective, as the first version of this analysis measured it.

| Approach | Set | Valid plans | Units sd | Hours/week sd | Catalog courses per plan | Last semester with a required course |
|---|---|---|---|---|---|---|
| Direct | explicit | 111 | 0.00 | 0.42 | 7.00 | 4.97 |
| Direct | reworded | 110 | 0.00 | 0.42 | 7.14 | 5.03 |
| Tool | explicit | 111 | 0.00 | 0.40 | 6.95 | 4.96 |
| Tool | reworded | 111 | 0.00 | 0.40 | 6.95 | 4.96 |
| Gold | explicit | 37 | 0.00 | 0.40 | 6.95 | 4.96 |
| Tool, no objective | both | 111 | 0.00 | 0.52 | 8.97 | 7.12 |

- **Units can't separate the approaches.** All catalog courses but one are 4 units, so 18-23 units forces five courses (20 units) every semester. All 1924 planned semesters in valid plans have exactly 20 units. Hours per week are similarly balanced in both: the mean standard deviation is under 0.6 h, and the largest is 2 h.
- **Required courses: the objective closes the gap.** Without it, the solver only looked for a feasible plan, so it had no reason to schedule early. Pairing direct and tool on the same scenario and run, direct's last required course came earlier in 118 of 149 pairs and later in none. For a new student, the solver's plan still had a required course in semester 6. With the objective, the two land in the same semester in 145 of 149 pairs, and tool is one semester earlier in the other 4 (M57, R22, R53, R56). Both finish a new student's required courses by about semester 3 (figure).
- **Catalog courses: the objective removes the extras.** Without it, the solver filled spare units with arbitrary catalog courses, about 9 a plan where direct names 7. The objective's second part plans as few courses as possible, so tool now names 6.95 and writes `ELECTIVE` for the rest, as direct does.
- **What the objective leaves out:** it doesn't schedule the 3 focus-area courses early. In M56, two of them land in semesters 7 and 8.
- **Tool and gold are identical** because every translation that mattered was right.

![Last semester with a required course](figures/last-required.png)

## 6. Consistency across runs

| Approach | Set | Outcome differs between runs | Same answer in all 3 runs: feasible | impossible |
|---|---|---|---|---|
| Direct | explicit | M30 | 12 of 37 | 22 of 23 |
| Direct | reworded | R57 | 12 of 37 | 23 of 23 |
| Tool | both | none | 37 of 37 | 23 of 23 |

The direct "impossible" answers are compared without their free-text reason. Direct gives a different, usually still valid, plan on most feasible scenarios. That's harmless for accuracy, but a student asking twice would get two different plans. Tool's plans are now repeatable, because the solver runs with one worker and a fixed seed.

## 7. Problem size

Per scenario of the main set, from the solver's model:

| Measure | Min | Median | Max |
|---|---|---|---|
| Course-semester choices `x[c,k]` | 36 | 108 | 388 |
| CP-SAT variables | 38 | 168 | 1155 |
| CP-SAT constraints | 97 | 284 | 1769 |
| Solve time (ms) | 2 | 7 | 39 |

A brute-force search over the course-semester choices alone has up to 2^388 assignments. CP-SAT solves every scenario in under 40 ms in this run, including proving the 23 impossible ones and proving each plan is the best for the objective. Timings vary between runs, and the slowest single solve we saw took about 0.3 s. A direct answer takes a mean of 5-14 s, depending on the horizon.

## 8. Decisions for the team

1. **The ceiling effect.** We ran the reworded set, and accuracy still doesn't separate the approaches.
   - Suggestion: report it as a finding, and compare the approaches on what does differ: cost, speed, consistency, scaling with the horizon, and guarantees. Plan quality differed only until the solver had an objective (section 5).
   - On guarantees: a tool plan is valid whenever the translation is right. A direct plan has to be checked, and the validator catches both of direct's mistakes.
   - Messier input (typos, wrong codes, contradictions, missing fields) could break the tie. But the expected answer then becomes debatable, so it fits better as discussion than as a new experiment this close to the deadline.
2. **Hybrid (open item 5).** Suggestion: drop it, and say why in the report.
   - With 2 wrong answers in 360, there's nothing for it to fix that we could measure.
   - A validator-feedback loop would probably catch both, and it's natural future work.
3. **Optimisation (open item 6). Done.** Weng Mun added the objective to `solver.py` (design.md 6.2), and section 5 shows it closes the plan-quality gap. Evaluating it cost no API money: gold was re-run, and `planner/analyze.py` re-solved the saved translations. The report should say we chose the objective after seeing direct's plans.

## 9. Caveats

- **Both sets were generated from templates** from the gold JSON, so the wording is varied but not as messy as real students' messages. The reworded set deliberately leaves out course titles and phrases like "the usual first-year mods", because neither prompt lists course titles or a recommended schedule.
- **Sample size:** one model, 60 scenarios, 3 runs per approach and set. The 2-against-0 error count is not significant.
- **Stand-in years:** later years use the AY2026/27 data (design.md 2).
- **Plan quality:** we chose the solver's objective after seeing direct's plans, so matching them is what it was built to do. We didn't try other objectives, such as balancing hours.
