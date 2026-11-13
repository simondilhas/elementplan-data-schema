"""Check a solution folder against the solution schema and the Elementplan catalog.

    python scripts/check_solution.py examples/solution/demo-wohnhaus

1. Loads one record per file into a SolutionDataset (folder name = collection).
2. Validates the dataset against schema/solution.linkml.yaml.
3. Checks what JSON Schema cannot: references resolve, configurations belong
   to their room type and suit the selected goal levels, openings sit on an
   existing edge, the programme is fulfilled.

Exit code 1 when an error is found. Warnings do not fail.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import yaml
from linkml.validator import validate

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema" / "solution.linkml.yaml"
CATALOG = ROOT / "examples"

SINGLE = {"selection.yaml": "selection", "project.yaml": "projects"}
FOLDERS = {
    "programme": "programme_items",
    "contexts": "contexts",
    "units": "units",
    "spaces": "spaces",
    "openings": "openings",
    "equipment": "equipment",
    "zones": "zones",
    "systems": "systems",
    "overrides": "overrides",
}
VALUE_MAPS = ("values",)


def _normalize_values(record: dict) -> None:
    """Bare attribute values are shorthand for {value: x} (confirmed)."""
    for key in VALUE_MAPS:
        values = record.get(key)
        if isinstance(values, dict):
            record[key] = {
                name: v if isinstance(v, dict) and "value" in v else {"value": v}
                for name, v in values.items()
            }
    for served in record.get("serves") or []:
        _normalize_values(served)
    for key in ("parameters", "set"):
        params = record.get(key)
        if isinstance(params, dict):
            record[key] = {
                name: v if isinstance(v, dict) and "value" in v else {"value": v}
                for name, v in params.items()
            }


def load_dataset(folder: Path) -> tuple[dict, dict[str, Path]]:
    data: dict = {}
    files: dict[str, Path] = {}
    for name, key in SINGLE.items():
        path = folder / name
        if path.exists():
            record = yaml.safe_load(path.read_text())
            _normalize_values(record)
            if key == "selection":
                data[key] = record
            else:
                data.setdefault(key, []).append(record)
                files[record["id"]] = path
    for sub, key in FOLDERS.items():
        for path in sorted((folder / sub).glob("*.yaml")):
            record = yaml.safe_load(path.read_text())
            _normalize_values(record)
            data.setdefault(key, []).append(record)
            files[record["id"]] = path
    return data, files


def load_catalog() -> dict[str, dict]:
    """Every catalog record by id, including nested configurations, options and sizes."""
    catalog: dict[str, dict] = {}

    def walk(node, parent=None):
        if isinstance(node, dict):
            if isinstance(node.get("id"), str):
                node = dict(node, _parent=parent)
                catalog[node["id"]] = node
                parent = node["id"]
            for value in node.values():
                walk(value, parent)
        elif isinstance(node, list):
            for item in node:
                walk(item, parent)

    for sub in ("room-types", "usage-scenarios", "project-goals", "components"):
        for path in (CATALOG / sub).glob("*.yaml"):
            walk(yaml.safe_load(path.read_text()))
    return catalog


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, rid: str, msg: str) -> None:
        self.errors.append(f"{rid}: {msg}")

    def warn(self, rid: str, msg: str) -> None:
        self.warnings.append(f"{rid}: {msg}")


VALUE_KEYS = {"value", "unit", "source", "review_status"}
REVIEW = {"proposed", "confirmed", "rejected", "superseded"}


def _check_values(rid: str, values: dict | None, report: Report) -> None:
    """Generated JSON Schema accepts any object as a value (SimpleDict form), so check here."""
    for name, v in (values or {}).items():
        extra = set(v) - VALUE_KEYS
        if extra:
            report.error(rid, f"value {name} has unknown fields {sorted(extra)}")
        if v.get("review_status") not in (None, *REVIEW):
            report.error(rid, f"value {name} has review_status {v['review_status']!r}")


def check(data: dict, catalog: dict[str, dict], report: Report) -> None:
    for key, records in data.items():
        if key == "selection":
            continue
        for rec in records:
            _check_values(rec["id"], rec.get("values"), report)
            for served in rec.get("serves") or []:
                _check_values(rec["id"], served.get("values"), report)
    ids = {r["id"] for key in data if key != "selection" for r in data[key]}
    by_id = {r["id"]: r for key in data if key != "selection" for r in data[key]}
    selection = data.get("selection") or {}
    goal_levels = set(selection.get("goal_levels") or [])
    options = set(selection.get("options") or [])

    def ref(rid: str, target: str | None, where: str, in_catalog: bool = False) -> None:
        if target is None:
            return
        if in_catalog:
            if target not in catalog:
                report.error(rid, f"{where} {target} is not in the Elementplan catalog")
        elif target not in ids:
            report.error(rid, f"{where} {target} does not exist")

    for oid in options:
        ref("selection", oid, "option", in_catalog=True)
    for gid in goal_levels:
        ref("selection", gid, "goal level", in_catalog=True)

    for item in data.get("programme_items", []):
        ref(item["id"], item.get("room_type"), "room_type", in_catalog=True)
        opt = item.get("from_option")
        if opt:
            ref(item["id"], opt, "from_option", in_catalog=True)
            if opt not in options:
                report.error(item["id"], f"from_option {opt} is not selected")
            elif item["room_type"] not in (catalog.get(opt, {}).get("adds") or []):
                report.error(item["id"], f"{opt} does not add {item['room_type']}")

    def check_typed(rec: dict) -> None:
        rid = rec["id"]
        rt, conf = rec.get("room_type"), rec.get("configuration")
        ref(rid, rt, "room_type", in_catalog=True)
        ref(rid, conf, "configuration", in_catalog=True)
        if conf in catalog and rt and catalog[conf]["_parent"] != rt:
            report.error(rid, f"configuration {conf} does not belong to {rt}")
        levels = set((catalog.get(conf) or {}).get("project_goal_levels") or [])
        if levels and goal_levels and not levels & goal_levels:
            report.error(rid, f"configuration {conf} does not suit the selected goal levels")
        origin = rec.get("origin") or {}
        if origin.get("kind") in ("requirement", "authored") and not rt:
            report.error(rid, "a designed record needs a room_type")
        if origin.get("kind") in ("requirement", "authored") and rt and not conf:
            report.warn(rid, "no configuration chosen yet")
        if origin.get("option") and origin["option"] not in options:
            report.error(rid, f"origin option {origin['option']} is not selected")
        for p in rec.get("fulfils") or []:
            ref(rid, p, "fulfils")

    for unit in data.get("units", []):
        check_typed(unit)
        ref(unit["id"], unit.get("parent_building"), "parent_building")

    for space in data.get("spaces", []):
        rid = space["id"]
        check_typed(space)
        ref(rid, space.get("parent_level"), "parent_level")
        ref(rid, space.get("parent_unit"), "parent_unit")
        outline, kinds = space.get("outline") or [], space.get("edge_kinds") or []
        if outline and kinds and len(kinds) != len(outline):
            report.error(rid, f"{len(kinds)} edge_kinds for {len(outline)} edges")
        if space.get("review_status") == "proposed":
            report.warn(rid, "proposed, needs review")

    for ctx in data.get("contexts", []):
        ref(ctx["id"], ctx.get("parent_project"), "parent_project")
        ref(ctx["id"], ctx.get("parent_building"), "parent_building")

    def edge_length(space: dict, edge: int) -> float | None:
        pts = space.get("outline") or []
        if not 0 <= edge < len(pts):
            return None
        (x1, y1), (x2, y2) = pts[edge], pts[(edge + 1) % len(pts)]
        return math.hypot(x2 - x1, y2 - y1)

    for op in data.get("openings", []):
        rid = op["id"]
        ref(rid, op.get("host"), "host")
        ref(rid, op.get("connects_to"), "connects_to")
        ref(rid, op.get("component"), "component", in_catalog=True)
        if op.get("connects_to") and op.get("exterior"):
            report.error(rid, "set connects_to or exterior, not both")
        host = by_id.get(op.get("host"))
        if host:
            length = edge_length(host, op["edge"])
            if length is None:
                report.error(rid, f"edge {op['edge']} does not exist on {host['id']}")
            elif op["offset"] + (op.get("width") or 0) > length + 1e-6:
                report.error(rid, f"does not fit on edge {op['edge']} ({length:.2f} m)")
        if not op.get("connects_to") and not op.get("exterior"):
            report.warn(rid, "neighbour unknown")

    for eq in data.get("equipment", []):
        ref(eq["id"], eq.get("parent_space"), "parent_space")
        ref(eq["id"], eq.get("component"), "component", in_catalog=True)

    for zone in data.get("zones", []):
        for m in zone.get("members") or []:
            ref(zone["id"], m, "member")

    for system in data.get("systems", []):
        ref(system["id"], system.get("parent_building"), "parent_building")
        for served in system.get("serves") or []:
            ref(system["id"], served.get("space"), "serves")
            ref(system["id"], served.get("zone"), "serves")

    for ov in data.get("overrides", []):
        owner = ov["target"].split("/equipment/")[0]
        ref(ov["id"], owner, "target owner")

    # Programme: every item is met by enough instances (only in design projects).
    for item in data.get("programme_items", []):
        met = [r for key in ("units", "spaces") for r in data.get(key, [])
               if item["id"] in (r.get("fulfils") or [])]
        if len(met) < item.get("count", 1):
            report.warn(item["id"], f"{len(met)} of {item.get('count', 1)} required instances")


def main(folder: str) -> int:
    data, _ = load_dataset(Path(folder))
    report = Report()
    result = validate(data, str(SCHEMA), "SolutionDataset")
    for r in result.results:
        report.errors.append(f"schema: {r.message}")
    check(data, load_catalog(), report)
    for e in report.errors:
        print("ERROR  ", e)
    for w in report.warnings:
        print("warning", w)
    n = sum(len(v) for k, v in data.items() if k != "selection")
    print(f"{folder}: {n} records, {len(report.errors)} errors, {len(report.warnings)} warnings")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(max(main(f) for f in sys.argv[1:]))
