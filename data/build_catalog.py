"""Freeze NUSMods data, one file per academic year, for every course named in data/requirements/.

Run from the repo root:  python data/build_catalog.py 2025-2026 2026-2027
Writes data/catalog/<AY>.json. Everyone uses the committed files; rebuild only if the team agrees to change the data.
"""
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API = "https://api.nusmods.com/v2"
HTTP = requests.Session()  # one connection for ~75 requests per year; retries connection drops, not 404s
HTTP.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1)))
DATA = Path(__file__).parent
CODE = re.compile(r"\b[A-Z]{2,4}\d{4}[A-Z]{0,3}\b")
ASSUMED = {"MA1301", "MA1301X"}  # bridging maths: we assume every student has A-level H2 Maths or equivalent


def prune(tree, codes):
    """Rewrite a NUSMods prereqTree using catalog codes only.
    True = always met, False = cannot be met inside the catalog."""
    if isinstance(tree, str):
        code = tree.split(":")[0]  # drop the minimum-grade suffix, e.g. "CS2040S:D"
        if code in ASSUMED:
            return True
        if code.endswith("%"):  # wildcard, e.g. "CS1010%"
            return prune({"or": [c for c in sorted(codes) if c.startswith(code[:-1])]}, codes)
        return code if code in codes else False
    ((op, args),) = tree.items()
    if op == "nOf":
        need, args = args
    kids = [prune(a, codes) for a in args]
    need = (len(kids) if op == "and" else 1 if op == "or" else need) - kids.count(True)
    ok = [k for k in kids if k is not True and k is not False]
    if need <= 0:
        return True
    if len(ok) < need:
        return False
    if len(ok) == 1:
        return ok[0]
    if need == len(ok):
        return {"and": ok}
    return {"or": ok} if need == 1 else {"nOf": [need, ok]}


def lectures(sem):
    lessons = [l for l in sem.get("timetable", []) if l["lessonType"] == "Lecture"]
    if not lessons:
        return []
    group = min(l["classNo"] for l in lessons)  # shortcut: one fixed lecture group per course (lowest classNo)
    return sorted({(l["day"][:3], l["startTime"], l["endTime"]) for l in lessons if l["classNo"] == group})


def exam(sem):
    if not sem.get("examDate"):
        return None
    start = datetime.fromisoformat(sem["examDate"].replace("Z", "+00:00")) + timedelta(hours=8)  # UTC -> Singapore
    return {"start": start.strftime("%Y-%m-%dT%H:%M"), "minutes": sem["examDuration"]}


def build(ay, codes):
    raw = {}
    for code in sorted(codes):
        r = HTTP.get(f"{API}/{ay}/modules/{code}.json", timeout=30)
        if r.status_code == 404:
            print(f"FLAG not in {ay}: {code}")
            continue
        r.raise_for_status()
        raw[code] = r.json()

    courses = {}
    for code, m in sorted(raw.items()):
        sems = {str(s["semester"]): {"lectures": lectures(s), "exam": exam(s)}
                for s in m.get("semesterData", []) if s["semester"] in (1, 2)}
        prereq = prune(m["prereqTree"], codes) if m.get("prereqTree") else None
        if prereq is True:
            prereq = None
        if prereq is False:  # kept in the catalog (a student may have completed it) but never plannable
            print(f"FLAG {ay} prereq cannot be met inside the catalog: {code}  raw={json.dumps(m['prereqTree'])}")
        if not sems:
            print(f"FLAG {ay} not offered in Sem 1 or 2: {code}")
        for s, d in sems.items():
            if not d["exam"]:
                print(f"note {ay} no exam: {code} sem {s}")
            if not d["lectures"]:
                print(f"note {ay} no lecture: {code} sem {s}")
        rule = m.get("preclusionRule") or m.get("preclusion") or ""
        courses[code] = {
            "title": m["title"],
            "units": int(m["moduleCredit"]),
            "level": int(re.search(r"\d", code).group()) * 1000,
            "hours": sum(m["workload"]) if isinstance(m.get("workload"), list) else None,  # per week; stats only
            "prereq": prereq,
            "preclusions": sorted(set(CODE.findall(rule)) & codes - {code}),
            "semesters": sems,
        }
    return courses


def main():
    ays = sys.argv[1:]
    if not ays or not all(re.fullmatch(r"\d{4}-\d{4}", ay) for ay in ays):
        sys.exit("usage: python data/build_catalog.py 2025-2026 [2026-2027 ...]")
    # Prune against every course we model, not just this year's, so a course taken in an earlier year still counts.
    codes = set()
    for path in sorted((DATA / "requirements").glob("*.json")):
        reqs = json.loads(path.read_text())
        codes |= set(reqs["required"]) | {c for area in reqs["focus_areas"].values() for c in area}
    (DATA / "catalog").mkdir(exist_ok=True)
    for ay in ays:
        if HTTP.head(f"{API}/{ay}/moduleList.json", timeout=30).status_code == 404:
            print(f"FLAG NUSMods has not published {ay}; the planner uses the newest year we have instead")
            continue
        catalog = {"acad_year": ay, "source": f"{API}/", "built": datetime.now().strftime("%Y-%m-%d"),
                   "courses": build(ay, codes)}
        (DATA / "catalog" / f"{ay}.json").write_text(json.dumps(catalog, indent=1) + "\n")
        print(f"wrote {len(catalog['courses'])} courses to data/catalog/{ay}.json")


if __name__ == "__main__":
    main()
