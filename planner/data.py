"""Load the frozen data files. The solver, the validator and the LLM prompts all read data through here, so they agree."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ELECTIVE = "ELECTIVE"  # any course outside the catalog: always offered, no prereqs, lectures or exam; may repeat
ELECTIVE_UNITS = 4


def load_catalogs():
    """{AY: catalog} for every year in data/catalog/, e.g. {"2026-2027": {"courses": {...}}}."""
    return {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / "data" / "catalog").glob("*.json"))}


def term(matric_ay, k):
    """Semester k of a degree (1 = Y1S1 ... 8 = Y4S2) -> (AY, 1 or 2). term("2025-2026", 3) == ("2026-2027", 1)."""
    start = int(matric_ay[:4]) + (k - 1) // 2
    return f"{start}-{start + 1}", 1 if k % 2 else 2


def catalog_for(catalogs, ay):
    """(catalog, the AY its data comes from). A year NUSMods has not published yet uses the newest year we have."""
    if ay in catalogs:
        return catalogs[ay], ay
    newest = max(catalogs)
    if ay > newest:
        return catalogs[newest], newest
    raise KeyError(f"no catalog for {ay}; build it with: python data/build_catalog.py {ay}")


def load_requirements(matric_ay):
    """Degree rules for a cohort: the newest data/requirements/<AY>.json whose first cohort is at or before matric_ay."""
    files = sorted(p for p in (ROOT / "data" / "requirements").glob("*.json") if p.stem <= matric_ay)
    if not files:
        raise KeyError(f"no degree rules encoded for the {matric_ay} cohort")
    return json.loads(files[-1].read_text())


def load_scenarios(name="examples"):
    """The list of scenarios in scenarios/<name>.json."""
    return json.loads((ROOT / "scenarios" / f"{name}.json").read_text())
