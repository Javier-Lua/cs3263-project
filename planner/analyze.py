"""Analyse results files (design.md section 8) and print the tables as markdown. Owner: Javier.

Usage:  python -m planner.analyze <results file> ... [--figures <dir>]
        e.g. python -m planner.analyze results/2026-11-03-1932-direct.jsonl results/2026-11-03-1932-tool.jsonl

Tool plans are re-solved from their saved translations with the current solver, so plan quality and consistency use
the deterministic solver. The outcome can't change (whether a plan exists never depended on the solver's search), and
any that does is printed. "explicit" is the main set (M01-M60), "reworded" the same scenarios loosely worded (R01-R60).
"""
import json
import sys
import time
from collections import Counter, defaultdict
from statistics import mean, median, pstdev

from planner.data import ROOT, catalog_for, load_catalogs, load_requirements, load_scenarios, term
from planner.run import CORRECT, OUTCOMES, score
from planner.solver import build_model, solve

GOLD = {e["id"]: e for path in sorted((ROOT / "scenarios").glob("*.json")) for e in load_scenarios(path.stem)}
SETS = {"M": "explicit", "R": "reworded", "S": "examples"}
FIELDS = ["matric_ay", "current_semester", "completed", "focus_area", "must_take"]


def load(paths):
    """(rows, changed): every results line, with tool plans re-solved, and the (id, run, old, new) outcome changes."""
    rows, changed = [], []
    for path in paths:
        for line in open(path):
            row = json.loads(line)
            row["set"] = SETS[row["id"][0]]
            if row["approach"] == "tool" and row.get("translation") is not None and "solver_error" not in row:
                plan = solve(row["translation"])
                violations, result = score(GOLD[row["id"]], plan)
                if result != row["outcome"]:
                    changed.append((row["id"], row["run"], row["outcome"], result))
                row.update(plan=plan, violations=violations, outcome=result)
            rows.append(row)
    return rows, changed


def left(row):
    return 9 - GOLD[row["id"]]["scenario"]["current_semester"]


def out_tokens(row):
    return sum(call["usage"]["output_tokens"] for call in row["calls"])


def quality(entry, plan):
    """Plan quality on one valid plan (design.md section 8.3). An ELECTIVE counts as 4 units and 10 h/week."""
    sc, catalogs = entry["scenario"], load_catalogs()
    loads = []
    for k in range(sc["current_semester"], 9):
        courses = catalog_for(catalogs, term(sc["matric_ay"], k)[0])[0]["courses"]
        planned = plan["semesters"].get(str(k), [])
        loads.append((sum(4 if c == "ELECTIVE" else courses[c]["units"] for c in planned),
                      sum(10 if c == "ELECTIVE" else courses[c]["hours"] for c in planned)))
    required = set(load_requirements(sc["matric_ay"])["required"]) - set(sc["completed"])
    return {"units_sd": pstdev(u for u, _ in loads), "hours_sd": pstdev(h for _, h in loads),
            "last_required": max((int(k) for k, cs in plan["semesters"].items() if required & set(cs)), default=None),
            "real_courses": sum(c != "ELECTIVE" for cs in plan["semesters"].values() for c in cs)}


def table(header, rows):
    print("| " + " | ".join(header) + " |\n|" + "---|" * len(header))
    for row in rows:
        print("| " + " | ".join(str(x) for x in row) + " |")
    print()


def pct(x):
    return f"{x:.1%}"


def groups(rows):
    by = defaultdict(list)
    for row in rows:
        by[(row["approach"], row["set"])].append(row)
    return dict(sorted(by.items()))


def accuracy(rows):
    """(mean, min, max) of accuracy over the runs."""
    per_run = [mean(r["outcome"] in CORRECT for r in rows if r["run"] == k) for k in sorted({r["run"] for r in rows})]
    return mean(per_run), min(per_run), max(per_run)


def outcomes(rows):
    print("## Outcomes and accuracy (design.md 8.1)\n")
    table(["approach", "set", "answers"] + OUTCOMES + ["accuracy (min-max over runs)", "feasible", "impossible"],
          [[a, s, len(rs)] + [Counter(r["outcome"] for r in rs)[o] for o in OUTCOMES] +
           ["{} ({}-{})".format(*map(pct, accuracy(rs)))] +
           [pct(mean(r["outcome"] in CORRECT for r in rs if GOLD[r["id"]]["expected"] == label))
            for label in ("feasible", "impossible")] for (a, s), rs in groups(rows).items()])
    print("Wrong answers:\n")
    table(["approach", "set", "id", "run", "outcome", "rules broken", "fields mistranslated"],
          [[r["approach"], r["set"], r["id"], r["run"], r["outcome"],
            ", ".join(sorted({v["rule"] for v in r["violations"]})), ", ".join(r.get("wrong_fields", []))]
           for r in rows if r["outcome"] not in CORRECT])


def translation(rows):
    print("## Translation (design.md 8.2)\n")
    tool = {s: rs for (a, s), rs in groups(rows).items() if a == "tool"}
    table(["set", "translations", "perfect"] + FIELDS,
          [[s, len(rs), pct(mean(not r["wrong_fields"] for r in rs))] +
           [sum(f in r["wrong_fields"] for r in rs) for f in FIELDS] for s, rs in tool.items()])
    reworded = [r for r in rows if r["set"] == "reworded"]
    if not reworded:
        return
    print("Reworded set: errors by wording. Accuracy is over every answer with that wording; \"field wrong\" is the share "
          "of tool translations that got the matching field wrong.\n")
    features = defaultdict(list)
    for r in reworded:
        wording = GOLD[r["id"]]["wording"]
        for f in ("matric_ay", "current_semester", "focus_area", "must_take"):
            features[(f, wording[f])].append(r)
        plain = "exact_codes" if GOLD[r["id"]]["scenario"]["completed"] else "nothing_completed"
        for feature in wording["completed"] or [plain]:
            features[("completed", feature)].append(r)
        features[("must_take", "decoy" if "distractor" in wording else "no_decoy")].append(r)
    lines = []
    for (field, form), rs in sorted(features.items()):
        by = {a: [r for r in rs if r["approach"] == a] for a in ("direct", "tool")}
        lines.append([field, form, len({r["id"] for r in rs})] +
                     [pct(mean(r["outcome"] in CORRECT for r in by[a])) if by[a] else "" for a in ("direct", "tool")] +
                     [pct(mean(field in r["wrong_fields"] for r in by["tool"])) if by["tool"] else ""])
    table(["field", "wording", "scenarios", "direct accuracy", "tool accuracy", "tool: field wrong"], lines)
    decoys = [r for r in reworded if r["approach"] == "tool" and "distractor" in GOLD[r["id"]]["wording"]]
    if decoys:
        taken = sum(r["translation"] is not None and GOLD[r["id"]]["wording"]["distractor"] in r["translation"]
                    ["must_take"] for r in decoys)
        print(f"Decoy course (\"looks interesting, but it's fine if it doesn't fit\") put into must_take: {taken} of "
              f"{len(decoys)} translations.\n")


def violations(rows):
    print("## Violations per rule (design.md 8.3)\n")
    table(["approach", "set", "violations by rule"],
          [[a, s, dict(Counter(v["rule"] for r in rs for v in r["violations"])) or "none"]
           for (a, s), rs in groups(rows).items()])


def cost(rows):
    print("## Cost and time per answer (design.md 8.3)\n")
    table(["approach", "set", "cost per answer", "total cost", "seconds: mean", "median", "max", "output tokens: mean"],
          [[a, s, f"${mean(r['cost'] for r in rs):.4f}", f"${sum(r['cost'] for r in rs):.2f}",
            f"{mean(r['seconds'] for r in rs):.1f}", f"{median(r['seconds'] for r in rs):.1f}",
            f"{max(r['seconds'] for r in rs):.1f}", f"{mean(out_tokens(r) for r in rs):.0f}"]
           for (a, s), rs in groups(rows).items()])
    print("Direct: effort against semesters left to plan\n")
    lines = []
    for (a, s), rs in groups(rows).items():
        if a == "direct":
            for n in sorted({left(r) for r in rs}):
                sub = [r for r in rs if left(r) == n]
                lines.append([s, n, len(sub), f"{mean(r['seconds'] for r in sub):.1f}",
                              f"{mean(out_tokens(r) for r in sub):.0f}", pct(mean(r["outcome"] in CORRECT for r in sub))])
    table(["set", "semesters left", "answers", "seconds", "output tokens", "accuracy"], lines)


def plan_quality(rows):
    print("## Plan quality on valid plans (design.md 8.3)\n")
    q = {key: [quality(GOLD[r["id"]], r["plan"]) for r in rs if r["outcome"] == "valid_plan"]
         for key, rs in groups(rows).items()}
    table(["approach", "set", "valid plans", "units sd", "hours/week sd", "real courses", "last required semester"],
          [[a, s, len(qs)] + [f"{mean(x[k] for x in qs if x[k] is not None):.2f}"
                              for k in ("units_sd", "hours_sd", "real_courses", "last_required")]
           for (a, s), qs in q.items() if qs])
    valid = {(r["approach"], r["set"], r["id"], r["run"]): quality(GOLD[r["id"]], r["plan"])
             for r in rows if r["outcome"] == "valid_plan"}
    print("Last semester holding a required course, direct against tool on the same scenario and run:\n")
    lines = []
    for s in sorted({key[1] for key in valid}):
        pairs = [(valid[k], valid[("tool",) + k[1:]]) for k in valid if k[0] == "direct" and k[1] == s
                 and ("tool",) + k[1:] in valid and valid[k]["last_required"] and valid[("tool",) + k[1:]]["last_required"]]
        if pairs:
            d, t = [x["last_required"] for x, _ in pairs], [y["last_required"] for _, y in pairs]
            lines.append([s, len(pairs), sum(x < y for x, y in zip(d, t)), sum(x == y for x, y in zip(d, t)),
                          sum(x > y for x, y in zip(d, t)), f"{mean(d):.2f}", f"{mean(t):.2f}"])
    table(["set", "pairs", "direct earlier", "same", "direct later", "direct mean", "tool mean"], lines)


def answer(row):
    """The answer without direct's free-text reason, so two "impossible" answers count as the same."""
    plan = row["plan"]
    return None if plan is None else json.dumps([plan["status"], plan.get("semesters")], sort_keys=True)


def consistency(rows):
    print("## Consistency across runs\n")
    lines = []
    for (a, s), rs in groups(rows).items():
        by = defaultdict(list)
        for r in rs:
            by[r["id"]].append(r)
        if len({len(v) for v in by.values()}) == 1 and len(next(iter(by.values()))) > 1:
            mixed = sorted(i for i, v in by.items() if len({r["outcome"] for r in v}) > 1)
            same = sum(len({answer(r) for r in v}) == 1 for v in by.values())
            lines.append([a, s, len(by), ", ".join(mixed) or "none", f"{same} of {len(by)}"])
    table(["approach", "set", "scenarios", "outcome differs between runs", "identical answer in every run"], lines)


def problem_size():
    print("## Problem size (main set, the gold scenarios)\n")
    sizes = []
    for e in (e for i, e in GOLD.items() if i[0] == "M"):
        model, planned_in, _ = build_model(e["scenario"])
        start = time.perf_counter()
        solve(e["scenario"])
        proto = model.Proto()
        sizes.append((len(planned_in), len(proto.variables), len(proto.constraints), 1000 * (time.perf_counter() - start)))
    names = ["course-semester choices x[c,k]", "CP-SAT variables", "CP-SAT constraints", "solve time (ms)"]
    table(["measure", "min", "median", "max"],
          [[name, f"{min(col):.0f}", f"{median(col):.0f}", f"{max(col):.0f}"] for name, col in zip(names, zip(*sizes))])


def figures(rows, out):
    """Two figures for the report: direct's effort against semesters left, and when each approach finishes the
    required courses."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out.mkdir(parents=True, exist_ok=True)
    blue, orange = "#2a78d6", "#eb6834"  # categorical slots 1-2, checked for colour-blind separation and contrast
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#52514e", "axes.grid": True, "axes.grid.axis": "y",
                         "grid.color": "#e4e3df", "grid.linewidth": 0.6, "axes.axisbelow": True})
    bar = {"edgecolor": "white", "linewidth": 2}  # a white gap between neighbouring bars

    direct = [r for r in rows if r["approach"] == "direct" and r["set"] == "explicit"]
    ns = sorted({left(r) for r in direct})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.5, 2.8))
    ax1.bar(ns, [mean(out_tokens(r) for r in direct if left(r) == n) for n in ns], 0.7, color=blue, **bar)
    ax1.set(xlabel="semesters left to plan", ylabel="output tokens (mean)", xticks=ns)
    ax2.bar(ns, [mean(r["seconds"] for r in direct if left(r) == n) for n in ns], 0.7, color=blue, **bar)
    ax2.set(xlabel="semesters left to plan", ylabel="seconds (mean)", xticks=ns)
    fig.suptitle("Direct approach: effort per answer against the planning horizon", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "direct-effort.png", dpi=200)
    plt.close(fig)

    # gold is left out: with every translation right, its plans are the tool plans
    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    width = 0.38
    for i, (a, colour) in enumerate([("direct", blue), ("tool", orange)]):
        last = defaultdict(list)
        for r in rows:
            if r["approach"] == a and r["set"] == "explicit" and r["outcome"] == "valid_plan":
                x = quality(GOLD[r["id"]], r["plan"])["last_required"]
                if x:
                    last[left(r)].append(x)
        ks = sorted(last)
        ax.bar([k + (i - 0.5) * width for k in ks], [mean(last[k]) for k in ks], width, color=colour, label=a, **bar)
    ax.set(xlabel="semesters left to plan", ylabel="last semester with a\nrequired course (mean)", ylim=(0, 10),
           yticks=range(0, 9, 2), xticks=sorted({left(r) for r in rows if r["set"] == "explicit"}))
    ax.legend(frameon=False, ncols=2, loc="upper left")
    fig.suptitle("When the plan finishes the required courses (valid plans, explicit set)", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "last-required.png", dpi=200)
    plt.close(fig)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = None
    if "--figures" in argv:
        i = argv.index("--figures")
        out, argv = ROOT / argv[i + 1], argv[:i] + argv[i + 2:]
    if not argv:
        sys.exit(__doc__)
    rows, changed = load(argv)
    if changed:
        print(f"**Re-solving changed these tool outcomes (id, run, before, after): {changed}**\n")
    outcomes(rows)
    if any(r["approach"] == "tool" for r in rows):
        translation(rows)
    violations(rows)
    cost(rows)
    plan_quality(rows)
    consistency(rows)
    problem_size()
    if out:
        figures(rows, out)
        print(f"figures saved to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
