"""Validate a pragmaticBIM-reference checkout against the Elementplan schema.

Usage: python scripts/validate_reference.py PATH/TO/pragmaticBIM-reference [collection ...]

Assembles an ElementplanDataset from the reference folders and validates it
with the JSON Schema generated from schema/elementplan.linkml.yaml (closed
classes, so unknown fields are reported). Collections default to the ones this
schema models field by field: room_types, usage_scenarios, components.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
import yaml
from linkml.generators.jsonschemagen import JsonSchemaGenerator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "elementplan.linkml.yaml"
FOLDERS = {
    "room_types": "room_types",
    "usage_scenarios": "usage_scenarios",
    "components": "components",
    "elements": "elements",
}
DEFAULT = ("room_types", "usage_scenarios", "components")


def load_dataset(reference: Path, collections: tuple[str, ...]) -> dict:
    dataset: dict[str, list] = {}
    for slot in collections:
        folder = reference / FOLDERS[slot]
        dataset[slot] = [
            yaml.safe_load(path.read_text(encoding="utf-8")) for path in sorted(folder.glob("*.yaml"))
        ]
    return dataset


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    reference = Path(argv[0])
    collections = tuple(argv[1:]) or DEFAULT
    schema = json.loads(JsonSchemaGenerator(str(SCHEMA), not_closed=False, top_class="ElementplanDataset").serialize())
    validator = jsonschema.validators.validator_for(schema)(schema)
    dataset = load_dataset(reference, collections)
    errors = list(validator.iter_errors(dataset))
    for error in errors:
        where = "/".join(str(p) for p in list(error.absolute_path)[:2])
        print(f"{where}: {error.message[:200]}")
    print()
    for slot in collections:
        print(f"{slot}: {len(dataset[slot])} records")
    print(f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
