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

if "ProjectGoal" not in schema["classes"]:
    raise SystemExit("ProjectGoal class is missing.")

dataset_slots = schema["classes"]["ElementplanDataset"]["slots"]
if "project_goals" not in dataset_slots:
    raise SystemExit("ElementplanDataset is missing the project_goals slot.")
if dataset_slots.index("project_goals") >= dataset_slots.index("workflows"):
    raise SystemExit("project_goals must appear before workflows on ElementplanDataset.")

workflow_slots = schema["classes"]["Workflow"]["slots"]
if "needed_for_project_goals" not in workflow_slots:
    raise SystemExit("Workflow class is missing the needed_for_project_goals slot.")

project_goals_slot = schema["slots"].get("project_goals")
if (
    not project_goals_slot
    or project_goals_slot.get("range") != "ProjectGoal"
    or not project_goals_slot.get("multivalued")
    or not project_goals_slot.get("inlined_as_list")
):
    raise SystemExit(
        "project_goals slot must be multivalued ProjectGoal with inlined_as_list: true"
    )

needed_for_project_goals_slot = schema["slots"].get("needed_for_project_goals")
if (
    not needed_for_project_goals_slot
    or needed_for_project_goals_slot.get("range") != "ProjectGoal"
    or not needed_for_project_goals_slot.get("multivalued")
    or needed_for_project_goals_slot.get("inlined") is not False
):
    raise SystemExit(
        "needed_for_project_goals slot must be multivalued ProjectGoal with inlined: false"
    )

print("Schema contract OK: ProjectGoal above Workflow")
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

if "ProjectGoal" not in compiled["$defs"]:
    raise SystemExit("Compiled JSON Schema is missing ProjectGoal.")

dataset_props = compiled["$defs"]["ElementplanDataset"]["properties"]
if "project_goals" not in dataset_props:
    raise SystemExit("Compiled JSON Schema ElementplanDataset is missing project_goals.")

workflow_props = compiled["$defs"]["Workflow"]["properties"]
if "needed_for_project_goals" not in workflow_props:
    raise SystemExit(
        "Compiled JSON Schema Workflow is missing needed_for_project_goals."
    )

print("JSON Schema OK: ProjectGoal above Workflow")
PY

echo "Schema check passed."
