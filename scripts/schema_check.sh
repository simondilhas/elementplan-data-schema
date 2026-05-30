#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python - <<'PY'
from pathlib import Path

import yaml

schema_files = sorted(Path("schema").rglob("*.yaml"))

if not schema_files:
    raise SystemExit("No schema YAML files found under schema/.")

for path in schema_files:
    with path.open("r", encoding="utf-8") as handle:
        yaml.safe_load(handle)
    print(f"YAML OK: {path}")

schema_path = Path("schema/elementplan.linkml.yaml")
with schema_path.open("r", encoding="utf-8") as handle:
    schema = yaml.safe_load(handle)

attribute_slots = schema["classes"]["Attribute"]["slots"]
if "unit" not in attribute_slots:
    raise SystemExit("Attribute class is missing the unit slot.")

unit_slot = schema["slots"].get("unit")
if unit_slot.get("range") != "string":
    raise SystemExit("unit slot must have range: string")

print("Schema contract OK: Attribute.unit (string)")
PY

echo "Running LinkML metamodel validation..."
linkml lint --validate-only schema/elementplan.linkml.yaml

echo "Compiling LinkML schema to JSON Schema..."
gen-json-schema schema/elementplan.linkml.yaml > /tmp/elementplan.schema.json

python - <<'PY'
import json
from pathlib import Path

compiled = json.loads(Path("/tmp/elementplan.schema.json").read_text(encoding="utf-8"))
unit_property = compiled["$defs"]["Attribute"]["properties"].get("unit")
if not unit_property or "string" not in unit_property.get("type", []):
    raise SystemExit("Compiled JSON Schema Attribute.unit must allow string values.")

print("JSON Schema OK: Attribute.unit (string)")
PY

echo "Schema check passed."
