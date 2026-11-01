# Scenarios

`scenarios/main.json` holds the 60 test students used for the full runs. `scenarios/examples.json` holds the 5 examples (S001-S005) used while building and piloting the approaches, so they are kept out of the main set.

Each scenario was written as JSON first, and its message was written from the JSON, so the message states every field: the matriculation year, the semester the student is about to start, the completed courses, the focus area, the must-take courses and both unit limits. Every label was checked against the solver (`tests/test_examples.py`). Every feasible scenario has a witness plan that the validator accepts: M01-M19 have witnesses written without the solver, and the rest use the solver's plan.

37 scenarios are feasible and 23 are impossible. "Y2S1" means Year 2 Semester 1, which is semester 3 in the scenario format. Unless noted, the student matriculated in AY2025/26.

## What they cover

| What | Scenarios |
|---|---|
| Each point in the degree | Y1S1: M02, M18, M34, M56, M57, M59; Y1S2: M01, M11, M48, M53, M58, M60; Y2S1: M05, M06, M07, M12, M27, M31, M32; Y2S2: M13, M22, M36; Y3S1: M04, M14, M20, M28, M29, M30; Y3S2: M08, M15, M21, M35, M39, M45, M52, M54; Y4S1: M09, M10, M16, M19, M24, M25, M26, M33, M40, M42, M43, M46, M47, M55; Y4S2: M03, M17, M23, M37, M38, M41, M44, M49, M50, M51 |
| Every focus area | Algorithms & Theory: M02, M24, M49; Artificial Intelligence: M04, M05, M08, M09, M19, M22, M26, M27, M28, M29, M31, M34, M39, M51, M52, M57, M60; Computer Graphics and Games: M12, M20, M21, M43, M44; Computer Security: M13, M25, M47, M58; Database Systems: M03, M14, M35, M37, M38, M40, M48, M55; Human-Computer Interaction: M11, M45, M46; Multimedia Information Retrieval: M06, M07, M59; Networking and Distributed Systems: M15, M36; Parallel Computing: M16, M53; Programming Languages: M18, M54; Software Engineering: M01, M10, M17, M23, M30, M32, M33, M41, M42, M50, M56 |
| More courses left than fit under 23 units a semester | M03, M19, M39, M40 |
| Must-take or focus courses with long prerequisite chains | M02, M09, M11, M13, M14, M18, M20, M21, M25, M33, M34, M38, M39, M41, M42, M43, M45, M46, M47, M48, M51, M52, M53, M55, M57, M58 |
| The CS2101/CS2103T same-semester pair | M04, M19, M37, M38 |
| Courses offered in one semester only | M02, M10, M11, M12, M13, M14, M16, M19, M20, M21, M24, M25, M39, M43, M44, M45, M46, M48, M49, M50, M52, M53, M54, M58 |
| Real lecture clashes: CS2108 with CS2109S and CS2106 with CS3230 in Sem 2, CS2100 with CS3230 in Sem 1 | M10, M17, M22, M23, M40 |
| Real exam clash: CS2107 and CS4248 in Sem 1 | M08, M24, M25, M58 |
| The AI preclusions (CS2109S, CS3243, CS3244, CS4263) | M05, M26, M27, M28, M51, M57, M60 |
| Multimedia IR: only CS2108 and CS4248 can still be planned | M06, M07, M59 |
| Must-take courses that can never be planned | M29, M30, M31 |
| Courses that changed between AY2025/26 and AY2026/27 | M31, M32, M48, M50, M54 |
| Few courses left, but every semester needs at least 18 units | M35 |
| Courses mentioned that aren't in the catalog (the translation must leave them out) | M01, M15, M36 |
| Students who matriculated in AY2026/27 | M02, M11, M18, M34, M48, M53, M60 |

## The scenarios

| # | Student | What makes it tricky | Expected |
|---|---|---|---|
| M01 | About to start Y1S2, 3 courses done, Software Engineering | Baseline early in the degree: almost everything still to plan | feasible |
| M02 | New AY2026/27 student, nothing done, Algorithms & Theory, must take CS4234 | A different matric year; CS4234 is Sem 1 only and needs CS3230 and MA1522 first | feasible |
| M03 | Final semester (Y4S2), 6 required courses left | 6 x 4 = 24 units, over the 23-unit limit | impossible |
| M04 | About to start Y3S1, CS2101 and CS2103T both not done, AI, must take CS3263 | The pair must go in the same semester, on top of a heavy load | feasible |
| M05 | About to start Y2S1, AI, must take CS4263 | CS4263 is new in AY2026/27 and precludes CS2109S, which is required | impossible |
| M06 | About to start Y2S1, Multimedia IR, already completed CS3245 | Only CS2108 and CS4248 can still be planned, but with CS3245 that makes 3 primaries | feasible |
| M07 | About to start Y2S1, Multimedia IR, no primary done | Only 2 primaries can be planned, and 3 are needed | impossible |
| M08 | About to start Y3S2, AI, must take CS2107 and CS4248 | Their exams clash in Sem 1, so they can't share a Semester 1 | feasible |
| M09 | About to start Y4S1, must take CS4350, nothing towards it | Its chain needs a Sem 1, then a Sem 2, then a Sem 1; only Y4S1 and Y4S2 are left | impossible |
| M10 | About to start Y4S1, needs CS2109S, must take CS2108 | Their lectures clash in Sem 2, so CS2109S must go in Y4S1 and CS2108 in Y4S2 | feasible |
| M11 | AY2026/27 student about to start Y1S2, HCI, must take CS4249 | CS2111 (Sem 2) -> CS3240 (Sem 1) -> CS4249 (Sem 2) needs three semesters in a row | feasible |
| M12 | About to start Y2S1, Computer Graphics and Games | CS3241 (Sem 1 only) opens every other primary | feasible |
| M13 | About to start Y2S2, Computer Security, must take CS4239 | CS4239 (Sem 1) needs CS3235, which needs CS2105, CS2106 and CS2107, plus CS2103T | feasible |
| M14 | About to start Y3S1, Database Systems, must take CS4221 | CS2102 -> CS3223 -> CS4221, and CS4221 is Sem 2 only | feasible |
| M15 | About to start Y3S2, Networking, CS2105 done | Needs a level-4000 primary; mentions courses outside the catalog | feasible |
| M16 | About to start Y4S1, Parallel Computing, CS3210 done | CS4223 is Sem 1 only and CS3211 Sem 2 only, so each has one slot | feasible |
| M17 | Final semester, only CS2106 and CS3230 left, Software Engineering focus done | Looks like the easiest case, but the two lectures overlap in Sem 2 | impossible |
| M18 | New AY2026/27 student, Programming Languages, must take CS4212 | CS2030S -> CS2104 (Sem 1) -> CS4212 (Sem 2) | feasible |
| M19 | About to start Y4S1 with 5 required courses left, AI, must take CS3231, CS2107 and CS4243 | 9 courses in 2 semesters, with a Sem-1-only course, the pair, and CS4248 waiting on CS2109S | feasible |
| M20 | About to start Y3S1, Computer Graphics and Games, must take CS4350 | CS3241 (Sem 1) -> CS3247 (Sem 2) -> CS4350 (Sem 1) fits exactly in semesters 5-7 | feasible |
| M21 | About to start Y3S2, Computer Graphics and Games, must take CS4350 | Three semesters are left, but they run Sem 2, Sem 1, Sem 2: the wrong order for the chain | impossible |
| M22 | About to start Y2S2, needs CS2109S, must take CS2108 | Both fit Sem 2 by offering, but their lectures clash there | feasible |
| M23 | Final semester, needs CS2109S, must take CS2108 | Both must go in semester 8, and their lectures clash | impossible |
| M24 | About to start Y4S1, Algorithms & Theory, must take CS2107, CS4248 and CS4234 | CS4234 is Sem 1 only, and CS2107 and CS4248 can't share semester 7 because their exams clash | feasible |
| M25 | About to start Y4S1, Computer Security, must take CS4248 and three Sem-2-only courses | Semester 8 fills up, forcing CS4248 into semester 7 with CS2107, whose exam it clashes with | impossible |
| M26 | About to start Y4S1, AI, CS2109S and CS3263 done | Needs a level-4000 AI primary; CS4263 looks natural but is precluded by CS2109S | feasible |
| M27 | About to start Y2S1, AI, must take CS3244 | CS2109S, which is required, precludes CS3244 | impossible |
| M28 | About to start Y3S1, completed CS3243, CS2109S not done | A course already taken precludes a required course | impossible |
| M29 | About to start Y3S1, must take CS4244 | A real course that isn't offered in either year | impossible |
| M30 | About to start Y3S1, Software Engineering, must take CS3282 | Offered every year, but its prerequisites can't be met | impossible |
| M31 | About to start Y2S1, must take CS4347 | Offered in AY2025/26 but dropped in AY2026/27 | impossible |
| M32 | About to start Y2S1, Software Engineering, must take CS3227 | CS3227 is new in AY2026/27, so only the newer data has it | feasible |
| M33 | About to start Y4S1, 2 required courses left, must take CS4218 | CS4218 needs CS3213 or CS3219 (an or-prerequisite) | feasible |
| M34 | New AY2026/27 student, AI, must take CS3263 and CS4246 | CS4246 needs CS3263 (or CS3243, which is precluded), so the order matters over a long horizon | feasible |
| M35 | About to start Y3S2, Database Systems focus done, 1 required course left | Almost done, yet every remaining semester still needs at least 18 units | feasible |
| M36 | About to start Y2S2, Networking, mentions many non-CS courses | Lists five courses that aren't in the catalog, which must be left out of the scenario | feasible |
| M37 | Final semester, CS2101 and CS2103T both left | The pair goes together in the last semester | feasible |
| M38 | Final semester, CS2030S, CS2101 and CS2103T left | CS2103T needs CS2030S first, with one semester left | impossible |
| M39 | About to start Y3S2, 6 required courses left, must take CS3264, CS4262 and CS3231 | Two chains (CS2100 -> CS2106 -> CS4262 and CS2109S -> CS3264) and a Sem-1-only course in 3 semesters | feasible |
| M40 | About to start Y4S1, 8 required courses and 3 must-takes left | 11 courses, room for 10, and CS3230 clashes with CS2100 and CS2106 | impossible |
| M41 | Final semester, CS2109S not done, must take CS3263 | The must-take needs a course that isn't done yet | impossible |
| M42 | About to start Y4S1, CS2109S not done, must take CS3263 | Same as M41 but one semester earlier: CS2109S in Y4S1, CS3263 in Y4S2 | feasible |
| M43 | About to start Y4S1, Computer Graphics and Games, no primary done | CS3241 in Y4S1, then CS3247 and CS4247 in Y4S2: the only way | feasible |
| M44 | Final semester, Computer Graphics and Games, no primary done | One semester left, and it's the wrong one | impossible |
| M45 | About to start Y3S2, HCI, no primary done | CS2111 (Sem 2) -> CS3240 (Sem 1) -> CS4249 (Sem 2) fits exactly | feasible |
| M46 | About to start Y4S1, HCI, no primary done | The HCI chain needs three semesters; two are left | impossible |
| M47 | About to start Y4S1, Computer Security, CS2105 done | CS2107 in Y4S1 opens CS3235 in Y4S2; CS4230 gives the level-4000 primary | feasible |
| M48 | AY2026/27 student about to start Y1S2, Database Systems, must take CS4224 | CS4224 is Sem 1 only and new in AY2026/27; it needs CS3223, which needs CS2102 | feasible |
| M49 | Final semester, Algorithms & Theory, only CS3230 done | Looks impossible, but CS3236 and CS4231 both run in Sem 2 and their prerequisites are done | feasible |
| M50 | Final semester, must take CS4211 | CS4211 ran in both semesters in AY2025/26 but only Sem 1 in AY2026/27 | impossible |
| M51 | Final semester, AI, must take CS4262 | CS4262 needs CS3264 first (CS3244 is precluded) | impossible |
| M52 | About to start Y3S2, AI, must take CS4262 | CS3264 first, then CS4262 in a Sem 2 | feasible |
| M53 | AY2026/27 student about to start Y1S2, Parallel Computing, must take CS4223 | CS2100 -> CS2106 and CS3210 -> CS4223 (Sem 1 only) | feasible |
| M54 | About to start Y3S2, Programming Languages, must take CS4212 | CS4212 moved from Sem 1 (AY2025/26) to Sem 2 (AY2026/27); the newest data decides | feasible |
| M55 | About to start Y4S1, CS2030S not done, must take CS3219 | A three-step chain with two semesters left | impossible |
| M56 | New AY2025/26 student, nothing done, Software Engineering | The whole degree to plan, with nothing else asked: the long-horizon baseline | feasible |
| M57 | New AY2025/26 student, AI, must take CS3264 and CS4262 | CS2109S -> CS3264 -> CS4262 over the whole degree; CS3244, the other way into CS4262, is precluded | feasible |
| M58 | About to start Y1S2, Computer Security, must take CS4239 and CS4248 | CS4239 needs CS3235, which needs CS2105, CS2106 and CS2107; CS4248 can't share a Sem 1 with CS2107 | feasible |
| M59 | New AY2025/26 student, Multimedia IR | Eight semesters left, but only 2 primaries are ever offered | impossible |
| M60 | AY2026/27 student about to start Y1S2, AI, must take CS3243 | Plenty of time left, but CS3243 and the required CS2109S preclude each other | impossible |

## Why each impossible scenario is impossible

- **M03:** Six required courses (CS2101, CS2103T, CS2106, CS2109S, MA1522 and ST2334) are left for the final semester: 24 units, over the 23-unit limit. Units are the only problem: with a 24-unit limit they would fit.
- **M05:** CS4263 (new in AY2026/27) precludes CS2109S, which the degree requires, so the student can't take both.
- **M07:** From AY2026/27 on (the newest data, which stands in for later years), the only Multimedia IR primaries offered are CS2108 and CS4248, and the student has completed none, so 3 primaries can't be reached.
- **M09:** CS4350 (Semester 1) needs CS3247 (Semester 2), which needs CS3241 (Semester 1), and none is done; only semesters 7 and 8 are left.
- **M17:** CS2106 and CS3230 (both required) are left for semester 8, a Semester 2, and in Semester 2 both have their lecture on Wednesday 10:00-12:00.
- **M21:** CS4350 (Semester 1) needs CS3247 (Semester 2), which needs CS3241 (Semester 1). Starting in semester 6, a Semester 2, CS3241 can come no earlier than semester 7, so CS4350 would need a ninth semester.
- **M23:** CS2109S (required) and CS2108 (must-take, Semester 2 only) both have to go in semester 8, and their lectures clash.
- **M25:** Semester 8 must hold CS3235 and CS4230 (they need CS2106, CS2107 and CS3230 from semester 7) and CS4231, CS3236 and CS4222 (Semester 2 only), so CS4248 has to go in semester 7 with CS2107, and their exams clash.
- **M27:** CS3244 is precluded by CS2109S, which the degree requires.
- **M28:** The student completed CS3243, which precludes CS2109S, a required course.
- **M29:** CS4244 is in the catalog but isn't offered in AY2025/26 or AY2026/27, and AY2026/27 stands in for later years, so it can never be planned.
- **M30:** No catalog course can meet CS3282's prerequisites (its prereq is false), so it can never be planned.
- **M31:** CS4347 ran only in AY2025/26 Semester 1, which is past, and AY2026/27, which stands in for later years, doesn't offer it.
- **M38:** CS2103T (required) needs CS2030S in an earlier semester, but both are left for the final semester.
- **M40:** 11 courses are left (8 required, 3 must-take), but two semesters hold at most 10, since 5 x 4 units is the most under the 23-unit limit. It would be impossible even without the limit: CS2106 needs CS2100 first, so CS2100 goes in semester 7 and CS2106 in semester 8, and CS3230's lecture clashes with CS2100's in Semester 1 (Friday 14:00-16:00) and with CS2106's in Semester 2 (Wednesday 10:00-12:00), so CS3230 fits in neither.
- **M41:** CS3263 needs CS2109S in an earlier semester, but CS2109S isn't done and only semester 8 is left.
- **M44:** No Computer Graphics and Games primary is done. CS3241 runs only in Semester 1 and the other plannable primaries need it, so semester 8 can't give 3.
- **M46:** CS2111 runs only in Semester 2, so semester 8 is its earliest, and every other HCI primary needs it first.
- **M50:** CS4211 runs only in Semester 1 in AY2026/27, the newest data, which stands in for later years, and only semester 8, a Semester 2, is left. (It also ran in Semester 2 in AY2025/26.)
- **M51:** CS4262 needs CS3244 or CS3264 in an earlier semester; neither is done (CS3244 is precluded by CS2109S anyway), and only semester 8 is left.
- **M55:** CS3219 needs CS2103T, which needs CS2030S; with CS2030S not done, that chain needs three semesters and only two are left.
- **M59:** From AY2026/27 on (the newest data, which stands in for later years), the only Multimedia IR primaries offered are CS2108 and CS4248, so 3 primaries can't be reached, however many semesters are left.
- **M60:** CS3243 precludes CS2109S, which the degree requires, so the student can't take both.
