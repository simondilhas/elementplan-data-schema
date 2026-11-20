"""Check a solution folder against the solution schema and the Elementplan catalog.

    python scripts/check_solution.py examples/solutions/authored
    python scripts/check_solution.py examples/solutions/site

1. Loads one record per file into a SolutionDataset (folder name = collection).
   For a non-site slug, merges the sibling site/ folder when present.
2. Validates the dataset against schema/solution.linkml.yaml.
3. Checks what JSON Schema cannot: references resolve, configurations belong
   to their room type and suit the selected goal levels, openings sit on an
   existing edge, solution-box answers match scope/exclusive/excludes rules,
   outline levels are unique, the programme is fulfilled.

Exit code 1 when an error is found. Warnings do not fail.
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import yaml
from linkml.validator import validate

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "schema"
SCHEMA = SCHEMA_DIR / "solution.linkml.yaml"
CATALOG = ROOT / "examples"

SINGLE = {
    "selection.yaml": "selection",
    "project.yaml": "projects",
    "solution.yaml": "solution",
}
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


def _load_folder(folder: Path, data: dict, files: dict[str, Path]) -> None:
    for name, key in SINGLE.items():
        path = folder / name
        if not path.exists():
            continue
        record = yaml.safe_load(path.read_text())
        _normalize_values(record)
        if key in ("selection", "solution"):
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


def load_dataset(folder: Path) -> tuple[dict, dict[str, Path], Path | None]:
    """Load a solution folder; merge sibling site/ when folder is not site itself."""
    data: dict = {}
    files: dict[str, Path] = {}
    site_dir: Path | None = None
    if folder.name != "site":
        sibling = folder.parent / "site"
        if sibling.is_dir():
            site_dir = sibling
            _load_folder(sibling, data, files)
    _load_folder(folder, data, files)
    return data, files, site_dir


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

    for sub in (
        "room-types",
        "usage-scenarios",
        "project-goals",
        "components",
        "solution-dimensions",
    ):
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


def _dimension_of_option(catalog: dict[str, dict], option_id: str) -> dict | None:
    parent = (catalog.get(option_id) or {}).get("_parent")
    return catalog.get(parent) if parent else None


def _check_answer_set(
    rid: str,
    solution_options: list[str] | None,
    open_dimensions: list[str] | None,
    allowed_scopes: set[str],
    catalog: dict[str, dict],
    report: Report,
) -> None:
    opts = list(solution_options or [])
    opens = set(open_dimensions or [])
    by_dim: dict[str, list[str]] = {}

    for oid in opts:
        if oid not in catalog:
            report.error(rid, f"solution option {oid} is not in the Elementplan catalog")
            continue
        dim = _dimension_of_option(catalog, oid)
        if not dim:
            report.error(rid, f"solution option {oid} has no parent dimension")
            continue
        did = dim["id"]
        if dim.get("scope") not in allowed_scopes:
            report.error(
                rid,
                f"option {oid} has scope {dim.get('scope')!r}, expected one of {sorted(allowed_scopes)}",
            )
        by_dim.setdefault(did, []).append(oid)
        if did in opens:
            report.error(rid, f"dimension {did} is both selected and open")

    for did, chosen in by_dim.items():
        dim = catalog[did]
        dim_opts = {o["id"]: o for o in (dim.get("options") or [])}
        if len(chosen) > 1 and not dim.get("allows_multiple"):
            report.error(rid, f"dimension {did} does not allow multiple options")
        exclusives = [oid for oid in chosen if dim_opts.get(oid, {}).get("exclusive")]
        if exclusives and len(chosen) > 1:
            report.error(rid, f"exclusive option {exclusives[0]} combined with others on {did}")

    # Excludes: if A excludes B and both are selected, fail (symmetric).
    selected = set(opts)
    for oid in opts:
        for other in (catalog.get(oid) or {}).get("excludes") or []:
            if other in selected:
                report.error(rid, f"options {oid} and {other} exclude each other")

    for did in opens:
        if did not in catalog:
            report.error(rid, f"open dimension {did} is not in the Elementplan catalog")
            continue
        dim = catalog[did]
        if dim.get("scope") not in allowed_scopes:
            report.error(
                rid,
                f"open dimension {did} has scope {dim.get('scope')!r}, expected one of {sorted(allowed_scopes)}",
            )


def _check_outlines(rid: str, outlines: list[dict] | None, by_id: dict, report: Report) -> set[str]:
    levels: set[str] = set()
    for entry in outlines or []:
        level = entry.get("level")
        if level in levels:
            report.error(rid, f"duplicate outline for level {level}")
        if level:
            levels.add(level)
            if level not in by_id:
                report.error(rid, f"outline level {level} does not exist")
            elif by_id[level].get("kind") != "level":
                report.error(rid, f"outline level {level} must be kind level")
        outline = entry.get("outline") or []
        if len(outline) < 3:
            report.error(rid, "outline needs at least three points")
    return levels


def check(data: dict, catalog: dict[str, dict], report: Report) -> None:
    for key, records in data.items():
        if key in ("selection", "solution"):
            continue
        for rec in records:
            _check_values(rec["id"], rec.get("values"), report)
            for served in rec.get("serves") or []:
                _check_values(rec["id"], served.get("values"), report)
    ids = {r["id"] for key in data if key not in ("selection", "solution") for r in data[key]}
    by_id = {r["id"]: r for key in data if key not in ("selection", "solution") for r in data[key]}
    selection = data.get("selection") or {}
    goal_levels = set(selection.get("goal_levels") or [])
    options = set(selection.get("options") or [])

    solution = data.get("solution")
    if solution:
        based = solution.get("based_on")
        if based and based not in ids and based != solution.get("id"):
            # based_on points at another solution id, not necessarily loaded
            if not str(based).startswith("solution/"):
                report.error(solution["id"], f"based_on {based} is not a solution id")

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

    _check_answer_set(
        "selection",
        selection.get("solution_options"),
        selection.get("open_dimensions"),
        {"project", "site"},
        catalog,
        report,
    )
    for answer in selection.get("unit_type_answers") or []:
        rt = answer.get("room_type")
        ref("selection", rt, "unit_type_answers.room_type", in_catalog=True)
        if rt in catalog and catalog[rt].get("room_type_kind") != "container":
            report.error("selection", f"unit_type_answers.room_type {rt} must be a container")
        _check_answer_set(
            f"selection/{rt}",
            answer.get("solution_options"),
            answer.get("open_dimensions"),
            {"unit"},
            catalog,
            report,
        )

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

    unit_outline_levels: dict[str, set[str]] = {}
    for unit in data.get("units", []):
        check_typed(unit)
        ref(unit["id"], unit.get("parent_building"), "parent_building")
        for neighbour in unit.get("adjacent_to") or []:
            ref(unit["id"], neighbour, "adjacent_to")
        unit_outline_levels[unit["id"]] = _check_outlines(
            unit["id"], unit.get("outlines"), by_id, report
        )

    for space in data.get("spaces", []):
        rid = space["id"]
        check_typed(space)
        ref(rid, space.get("parent_level"), "parent_level")
        ref(rid, space.get("parent_unit"), "parent_unit")
        for neighbour in space.get("adjacent_to") or []:
            ref(rid, neighbour, "adjacent_to")
        outline, kinds = space.get("outline") or [], space.get("edge_kinds") or []
        if outline and kinds and len(kinds) != len(outline):
            report.error(rid, f"{len(kinds)} edge_kinds for {len(outline)} edges")
        if space.get("review_status") == "proposed":
            report.warn(rid, "proposed, needs review")
        parent_unit = space.get("parent_unit")
        level = space.get("parent_level")
        if parent_unit and level and parent_unit in unit_outline_levels:
            levels = unit_outline_levels[parent_unit]
            if levels and level not in levels:
                report.error(rid, f"parent_level {level} is not in unit {parent_unit} outlines")

    for ctx in data.get("contexts", []):
        rid = ctx["id"]
        kind = ctx.get("kind")
        ref(rid, ctx.get("parent_project"), "parent_project")
        ref(rid, ctx.get("parent_site"), "parent_site")
        ref(rid, ctx.get("parent_envelope"), "parent_envelope")
        ref(rid, ctx.get("parent_building"), "parent_building")
        if kind == "envelope":
            if not ctx.get("parent_site"):
                report.error(rid, "envelope needs parent_site")
            else:
                site = by_id.get(ctx["parent_site"])
                if site and site.get("kind") not in ("parcel", "perimeter"):
                    report.error(
                        rid,
                        f"parent_site {ctx['parent_site']} must be parcel or perimeter",
                    )
            if not ctx.get("outline"):
                report.error(rid, "envelope needs outline")
            elif len(ctx["outline"]) < 3:
                report.error(rid, "outline needs at least three points")
            if ctx.get("height") is None:
                report.error(rid, "envelope needs height")
            if not rid.startswith("envelope/"):
                report.warn(rid, "envelope id should use the envelope/<slug> pattern")
        if kind == "building":
            if ctx.get("parent_envelope"):
                env = by_id.get(ctx["parent_envelope"])
                if env and env.get("kind") != "envelope":
                    report.error(
                        rid,
                        f"parent_envelope {ctx['parent_envelope']} must be an envelope",
                    )
            _check_answer_set(
                rid,
                ctx.get("solution_options"),
                ctx.get("open_dimensions"),
                {"building"},
                catalog,
                report,
            )
            _check_outlines(rid, ctx.get("outlines"), by_id, report)

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
        met = [
            r
            for key in ("units", "spaces")
            for r in data.get(key, [])
            if item["id"] in (r.get("fulfils") or [])
        ]
        if len(met) < item.get("count", 1):
            report.warn(item["id"], f"{len(met)} of {item.get('count', 1)} required instances")


def main(folder: str) -> int:
    path = Path(folder)
    data, _, site_dir = load_dataset(path)
    report = Report()
    if path.name != "site" and not data.get("solution"):
        report.error(path.name, "solutions/<slug>/solution.yaml is required")
    if path.name == "site" and data.get("solution"):
        report.error("site", "reserved slug site must not have solution.yaml")

    # Imports resolve relative to CWD; run validation from schema/.
    prev = Path.cwd()
    try:
        os.chdir(SCHEMA_DIR)
        result = validate(data, SCHEMA.name, "SolutionDataset")
    finally:
        os.chdir(prev)
    for r in result.results:
        report.errors.append(f"schema: {r.message}")
    check(data, load_catalog(), report)
    for e in report.errors:
        print("ERROR  ", e)
    for w in report.warnings:
        print("warning", w)
    n = sum(
        len(v)
        for k, v in data.items()
        if k not in ("selection", "solution") and isinstance(v, list)
    )
    site_note = f" (+site {site_dir})" if site_dir else ""
    print(f"{folder}{site_note}: {n} records, {len(report.errors)} errors, {len(report.warnings)} warnings")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(max(main(f) for f in sys.argv[1:]))
