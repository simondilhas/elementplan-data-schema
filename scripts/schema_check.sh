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
if "jurisdiction" not in workflow_slots:
    raise SystemExit("Workflow class is missing the jurisdiction slot.")

jurisdiction_slot = schema["slots"].get("jurisdiction")
if not jurisdiction_slot or jurisdiction_slot.get("range") != "JurisdictionEnum":
    raise SystemExit("jurisdiction slot must have range: JurisdictionEnum")

jurisdiction_enum = schema.get("enums", {}).get("JurisdictionEnum", {})
jurisdiction_values = set((jurisdiction_enum.get("permissible_values") or {}).keys())
required_jurisdictions = {"general", "at", "ch", "us", "de"}
if not required_jurisdictions.issubset(jurisdiction_values):
    raise SystemExit(
        "JurisdictionEnum must include general and ISO codes at, ch, us, de"
    )
iso_codes = {value for value in jurisdiction_values if value != "general"}
if "en" in iso_codes:
    raise SystemExit("JurisdictionEnum must not include language code en")
if len(iso_codes) < 249:
    raise SystemExit(
        "JurisdictionEnum must include all ISO 3166-1 alpha-2 country codes"
    )
if any(len(code) != 2 or not code.isalpha() or not code.islower() for code in iso_codes):
    raise SystemExit(
        "ISO jurisdiction codes must be lowercase ISO 3166-1 alpha-2"
    )

print("Schema contract OK: Workflow.jurisdiction")

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

if "ProjectGoalLevel" not in schema["classes"]:
    raise SystemExit("ProjectGoalLevel class is missing.")

project_goal_slots = schema["classes"]["ProjectGoal"]["slots"]
if "levels" not in project_goal_slots:
    raise SystemExit("ProjectGoal class is missing the levels slot.")

level_slots = schema["classes"]["ProjectGoalLevel"]["slots"]
if "activated_workflows" not in level_slots:
    raise SystemExit("ProjectGoalLevel class is missing the activated_workflows slot.")

levels_slot = schema["slots"].get("levels")
if (
    not levels_slot
    or levels_slot.get("range") != "ProjectGoalLevel"
    or not levels_slot.get("multivalued")
    or not levels_slot.get("inlined_as_list")
):
    raise SystemExit(
        "levels slot must be multivalued ProjectGoalLevel with inlined_as_list: true"
    )

activated_workflows_slot = schema["slots"].get("activated_workflows")
if (
    not activated_workflows_slot
    or activated_workflows_slot.get("range") != "Workflow"
    or not activated_workflows_slot.get("multivalued")
    or activated_workflows_slot.get("inlined") is not False
):
    raise SystemExit(
        "activated_workflows slot must be multivalued Workflow with inlined: false"
    )

print("Schema contract OK: ProjectGoalLevel.activated_workflows")
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
if "jurisdiction" not in workflow_props:
    raise SystemExit("Compiled JSON Schema Workflow is missing jurisdiction.")

print("JSON Schema OK: Workflow.jurisdiction")

print("JSON Schema OK: ProjectGoal above Workflow")

if "ProjectGoalLevel" not in compiled["$defs"]:
    raise SystemExit("Compiled JSON Schema is missing ProjectGoalLevel.")

goal_props = compiled["$defs"]["ProjectGoal"]["properties"]
if "levels" not in goal_props:
    raise SystemExit("Compiled JSON Schema ProjectGoal is missing levels.")

level_props = compiled["$defs"]["ProjectGoalLevel"]["properties"]
if "activated_workflows" not in level_props:
    raise SystemExit(
        "Compiled JSON Schema ProjectGoalLevel is missing activated_workflows."
    )

print("JSON Schema OK: ProjectGoalLevel.activated_workflows")
PY

echo "Schema check passed."
