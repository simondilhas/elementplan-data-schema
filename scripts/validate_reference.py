"""Validate a pragmaticBIM-reference checkout against the Elementplan schema.

Usage: python scripts/validate_reference.py PATH/TO/pragmaticBIM-reference [collection ...]

Assembles an ElementplanDataset from the reference folders and validates it
with the JSON Schema generated from schema/elementplan.linkml.yaml (closed
classes, so unknown fields are reported). Components are also checked for
lengths that name a parameter the component does not define. Collections
default to the ones this schema models field by field: room_types,
usage_scenarios, components, product_sheets. Container room types (unit types)
must list exactly one use. The schema requires uses on containers; the
generated JSON Schema cannot cap it at one, so more than one use is checked
here.

goal_level_errors checks the levels a project picked: one per goal unless the
goal allows_multiple, and an exclusive level never together with another.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
import yaml
from linkml.generators.jsonschemagen import JsonSchemaGenerator

from component_checks import parameter_reference_errors

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "elementplan.linkml.yaml"
FOLDERS = {
    "project_goals": "project_goals",
    "uses": "uses",
    "room_types": "room_types",
    "usage_scenarios": "usage_scenarios",
    "components": "components",
    "elements": "elements",
    "product_sheets": "products",
    "rules": "rules",
    "workflows": "workflows",
}
DEFAULT = ("room_types", "usage_scenarios", "components", "product_sheets")


def load_dataset(reference: Path, collections: tuple[str, ...]) -> dict:
    dataset: dict[str, list] = {}
    for slot in collections:
        folder = reference / FOLDERS[slot]
        dataset[slot] = [
            yaml.safe_load(path.read_text(encoding="utf-8"))
            for path in sorted(folder.glob("*.yaml"))
            if not path.name.startswith("_")  # generated indexes and config, not records
        ]
    return dataset


def container_use_errors(room_types: list[dict]) -> list[str]:
    return [
        f"{record.get('id')}: a container (unit type) must list exactly one use, found {len(record['uses'])}"
        for record in room_types
        if record.get("room_type_kind") == "container" and len(record.get("uses") or []) > 1
    ]


def goal_level_errors(project_goals: list[dict], picked_levels: list[str]) -> list[str]:
    errors = []
    for goal in project_goals:
        picked = [level for level in goal.get("levels") or [] if level["id"] in picked_levels]
        if len(picked) < 2:
            continue
        if not goal.get("allows_multiple"):
            errors.append(f"{goal['id']}: allows one level, found {len(picked)}")
        for level in picked:
            if level.get("exclusive"):
                errors.append(f"{goal['id']}: {level['id']} is exclusive and cannot be combined with other levels")
    return errors


def rule_reference_errors(dataset: dict) -> list[str]:
    """Resolve uses, applies_to, adjacent room types and workflows on rules."""
    errors: list[str] = []
    use_ids = {r["id"] for r in dataset.get("uses") or []}
    element_ids = {r["id"] for r in dataset.get("elements") or []}
    room_type_ids = {r["id"] for r in dataset.get("room_types") or []}
    workflow_ids = {r["id"] for r in dataset.get("workflows") or []}
    for rule in dataset.get("rules") or []:
        rid = rule.get("id", "?")
        for use in rule.get("uses") or []:
            if use_ids and use not in use_ids:
                errors.append(f"{rid}: unknown use {use}")
        applies = rule.get("applies_to")
        if applies and element_ids and applies not in element_ids:
            errors.append(f"{rid}: unknown applies_to {applies}")
        when = rule.get("when") or {}
        for rt in when.get("adjacent_room_types") or []:
            if room_type_ids and rt not in room_type_ids:
                errors.append(f"{rid}: unknown adjacent_room_type {rt}")
        for wf in rule.get("needed_for_workflows") or []:
            if workflow_ids and wf not in workflow_ids:
                errors.append(f"{rid}: unknown workflow {wf}")
        if not rule.get("pattern") and not rule.get("shacl"):
            errors.append(f"{rid}: set pattern or shacl")
    return errors


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    reference = Path(argv[0])
    collections = tuple(argv[1:]) or DEFAULT
    # Rules resolve against uses / elements / room_types / workflows when present.
    needed = set(collections)
    if "rules" in needed:
        needed.update(("uses", "elements", "room_types", "workflows"))
    schema = json.loads(JsonSchemaGenerator(str(SCHEMA), not_closed=False, top_class="ElementplanDataset").serialize())
    validator = jsonschema.validators.validator_for(schema)(schema)
    dataset = load_dataset(reference, tuple(sorted(needed)))
    # Validate only the collections the caller asked for.
    validate_dataset = {slot: dataset[slot] for slot in collections if slot in dataset}
    errors = list(validator.iter_errors(validate_dataset))
    for error in errors:
        where = "/".join(str(p) for p in list(error.absolute_path)[:2])
        print(f"{where}: {error.message[:200]}")
    for component in dataset.get("components") or []:
        for message in parameter_reference_errors(component):
            errors.append(message)
            print(message)
    extra = container_use_errors(dataset.get("room_types", []))
    for message in extra:
        print(f"room_types: {message}")
    if "rules" in collections:
        for message in rule_reference_errors(dataset):
            print(f"rules: {message}")
            extra.append(message)
    print()
    for slot in collections:
        print(f"{slot}: {len(dataset.get(slot, []))} records")
    total = len(errors) + len(extra)
    print(f"{total} error(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
