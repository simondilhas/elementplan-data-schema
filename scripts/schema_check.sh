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

if "documents" not in dataset_slots:
    raise SystemExit("ElementplanDataset is missing the documents slot.")
if dataset_slots.index("models") >= dataset_slots.index("documents"):
    raise SystemExit("models must appear before documents on ElementplanDataset.")

workflow_slots = schema["classes"]["Workflow"]["slots"]
if "jurisdiction" in workflow_slots:
    raise SystemExit("Workflow must not include jurisdiction.")
if "needed_for_project_goals" in workflow_slots:
    raise SystemExit("Workflow must not include needed_for_project_goals.")
if "jurisdiction" in schema["slots"]:
    raise SystemExit("jurisdiction slot must be removed.")
if "needed_for_project_goals" in schema["slots"]:
    raise SystemExit("needed_for_project_goals slot must be removed.")
if "JurisdictionEnum" in schema.get("enums", {}):
    raise SystemExit("JurisdictionEnum must be removed.")

print("Schema contract OK: Workflow without jurisdiction or needed_for_project_goals")

if "ServiceKindEnum" not in schema.get("enums", {}):
    raise SystemExit("ServiceKindEnum is missing.")
service_kind_values = set(schema["enums"]["ServiceKindEnum"].get("permissible_values", {}))
if service_kind_values != {"basic", "special"}:
    raise SystemExit("ServiceKindEnum must permit basic and special.")

if "service_kind" not in workflow_slots:
    raise SystemExit("Workflow class is missing the service_kind slot.")

service_kind_slot = schema["slots"].get("service_kind")
if not service_kind_slot or service_kind_slot.get("range") != "ServiceKindEnum":
    raise SystemExit("service_kind slot must have range: ServiceKindEnum")
if service_kind_slot.get("required"):
    raise SystemExit("service_kind must be optional so unclassified workflows stay valid.")

print("Schema contract OK: Workflow.service_kind")

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
activated_desc = activated_workflows_slot.get("description") or ""
if "Complete set of workflows activated when this goal level is selected" not in activated_desc:
    raise SystemExit(
        "activated_workflows description must state the complete set, not a delta"
    )
if "delta" in activated_desc.lower() or "union" in activated_desc.lower():
    raise SystemExit("activated_workflows description must not use delta/union language")

print("Schema contract OK: ProjectGoalLevel.activated_workflows")

if "included_elements" not in schema["classes"]["Model"]["slots"]:
    raise SystemExit("Model class is missing the included_elements slot.")

included_elements_slot = schema["slots"].get("included_elements")
if (
    not included_elements_slot
    or included_elements_slot.get("range") != "Element"
    or not included_elements_slot.get("multivalued")
    or included_elements_slot.get("inlined") is not False
):
    raise SystemExit(
        "included_elements slot must be multivalued Element with inlined: false"
    )

print("Schema contract OK: Model.included_elements")

if "Document" not in schema["classes"]:
    raise SystemExit("Document class is missing.")

if "included_elements" not in schema["classes"]["Document"]["slots"]:
    raise SystemExit("Document class is missing the included_elements slot.")

documents_slot = schema["slots"].get("documents")
if (
    not documents_slot
    or documents_slot.get("range") != "Document"
    or not documents_slot.get("multivalued")
    or not documents_slot.get("inlined_as_list")
):
    raise SystemExit(
        "documents slot must be multivalued Document with inlined_as_list: true"
    )

print("Schema contract OK: Document.included_elements")

if "Milestone" not in schema["classes"]:
    raise SystemExit("Milestone class is missing.")

if "MilestoneKindEnum" not in schema.get("enums", {}):
    raise SystemExit("MilestoneKindEnum is missing.")
kind_values = set(schema["enums"]["MilestoneKindEnum"].get("permissible_values", {}))
if kind_values != {"B", "M", "E"}:
    raise SystemExit("MilestoneKindEnum must permit B, M, and E.")

if "milestones" in dataset_slots:
    raise SystemExit("ElementplanDataset must not include milestones; they belong on Phase.")

if "milestones" not in schema["classes"]["Phase"]["slots"]:
    raise SystemExit("Phase class is missing the milestones slot.")

milestones_slot = schema["slots"].get("milestones")
if (
    not milestones_slot
    or milestones_slot.get("range") != "Milestone"
    or not milestones_slot.get("multivalued")
    or not milestones_slot.get("inlined_as_list")
):
    raise SystemExit(
        "milestones slot must be multivalued Milestone with inlined_as_list: true"
    )

scheduled_milestones_slot = schema["slots"].get("scheduled_milestones")
if (
    not scheduled_milestones_slot
    or scheduled_milestones_slot.get("range") != "Milestone"
    or not scheduled_milestones_slot.get("multivalued")
    or scheduled_milestones_slot.get("inlined") is not False
):
    raise SystemExit(
        "scheduled_milestones slot must be multivalued Milestone with inlined: false"
    )

if "scheduled_milestones" not in schema["classes"]["Model"]["slots"]:
    raise SystemExit("Model class is missing the scheduled_milestones slot.")
if "scheduled_milestones" not in schema["classes"]["Document"]["slots"]:
    raise SystemExit("Document class is missing the scheduled_milestones slot.")

if "idp_content_column" in schema["slots"]:
    raise SystemExit("idp_content_column slot must be removed.")
if "idp_content_column" in schema["classes"]["Model"]["slots"]:
    raise SystemExit("Model must not include idp_content_column.")
if "idp_content_column" in schema["classes"]["Document"]["slots"]:
    raise SystemExit("Document must not include idp_content_column.")

milestone_slots = schema["classes"]["Milestone"]["slots"]
for required_slot in ("id", "code", "sort_order", "name", "status", "phase", "kind", "date"):
    if required_slot not in milestone_slots:
        raise SystemExit(f"Milestone class is missing the {required_slot} slot.")

date_slot = schema["slots"].get("date")
if not date_slot or date_slot.get("range") != "date":
    raise SystemExit("date slot must have range: date")

milestone_phase = schema["classes"]["Milestone"].get("slot_usage", {}).get("phase", {})
if milestone_phase.get("range") != "string" or not milestone_phase.get("required"):
    raise SystemExit("Milestone.phase must be a required string (phase code).")

kind_slot = schema["slots"].get("kind")
if not kind_slot or kind_slot.get("range") != "MilestoneKindEnum":
    raise SystemExit("kind slot must have range: MilestoneKindEnum")

print("Schema contract OK: Milestone and scheduled_milestones")

if "PhaseMapping" not in schema["classes"]:
    raise SystemExit("PhaseMapping class is missing.")
if "PhaseMapEntry" not in schema["classes"]:
    raise SystemExit("PhaseMapEntry class is missing.")

if "phase_mappings" not in dataset_slots:
    raise SystemExit("ElementplanDataset is missing the phase_mappings slot.")
if dataset_slots.index("phases") >= dataset_slots.index("phase_mappings"):
    raise SystemExit("phase_mappings must appear after phases on ElementplanDataset.")

phase_mappings_slot = schema["slots"].get("phase_mappings")
if (
    not phase_mappings_slot
    or phase_mappings_slot.get("range") != "PhaseMapping"
    or not phase_mappings_slot.get("multivalued")
    or not phase_mappings_slot.get("inlined_as_list")
):
    raise SystemExit(
        "phase_mappings slot must be multivalued PhaseMapping with inlined_as_list: true"
    )

mapping_slots = schema["classes"]["PhaseMapping"]["slots"]
for required_slot in (
    "id",
    "source",
    "target",
    "status",
    "name",
    "comment",
    "phases",
    "milestones",
):
    if required_slot not in mapping_slots:
        raise SystemExit(f"PhaseMapping class is missing the {required_slot} slot.")

mapping_usage = schema["classes"]["PhaseMapping"].get("slot_usage", {})
for slot_name in ("source", "target"):
    usage = mapping_usage.get(slot_name, {})
    if usage.get("range") != "Phase" or not usage.get("required") or usage.get("inlined") is not False:
        raise SystemExit(
            f"PhaseMapping.{slot_name} must be a required Phase reference (inlined: false)."
        )
if mapping_usage.get("comment", {}).get("range") != "LocalizedText":
    raise SystemExit("PhaseMapping.comment must have range: LocalizedText")
for slot_name in ("phases", "milestones"):
    usage = mapping_usage.get(slot_name, {})
    if (
        usage.get("range") != "PhaseMapEntry"
        or not usage.get("multivalued")
        or not usage.get("inlined_as_list")
    ):
        raise SystemExit(
            f"PhaseMapping.{slot_name} must be multivalued PhaseMapEntry with inlined_as_list: true"
        )

entry_slots = schema["classes"]["PhaseMapEntry"]["slots"]
if "source" not in entry_slots or "target" not in entry_slots:
    raise SystemExit("PhaseMapEntry must include source and target slots.")

print("Schema contract OK: PhaseMapping")

element_slots = schema["classes"]["Element"]["slots"]
if "needed_in_models" not in element_slots:
    raise SystemExit("Element class is missing the needed_in_models slot.")
if "needed_for_models" not in element_slots:
    raise SystemExit("Element class is missing the needed_for_models slot.")
if "attachment_link" not in element_slots:
    raise SystemExit("Element class is missing the attachment_link slot.")
if "model_link" in element_slots:
    raise SystemExit("Element must use attachment_link, not model_link.")
if "model_link" in schema["slots"]:
    raise SystemExit("model_link slot must be replaced by attachment_link.")

needed_in_models_slot = schema["slots"].get("needed_in_models")
if (
    not needed_in_models_slot
    or needed_in_models_slot.get("range") != "Model"
    or not needed_in_models_slot.get("multivalued")
    or needed_in_models_slot.get("inlined") is not False
):
    raise SystemExit(
        "needed_in_models slot must be multivalued Model with inlined: false"
    )

print("Schema contract OK: Element.needed_in_models and attachment_link")
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
if "needed_for_project_goals" in workflow_props:
    raise SystemExit(
        "Compiled JSON Schema Workflow must not include needed_for_project_goals."
    )
if "jurisdiction" in workflow_props:
    raise SystemExit("Compiled JSON Schema Workflow must not include jurisdiction.")

print("JSON Schema OK: Workflow without jurisdiction or needed_for_project_goals")

if "service_kind" not in workflow_props:
    raise SystemExit("Compiled JSON Schema Workflow is missing service_kind.")

print("JSON Schema OK: Workflow.service_kind")

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

model_props = compiled["$defs"]["Model"]["properties"]
if "included_elements" not in model_props:
    raise SystemExit(
        "Compiled JSON Schema Model is missing included_elements."
    )

print("JSON Schema OK: Model.included_elements")

if "Document" not in compiled["$defs"]:
    raise SystemExit("Compiled JSON Schema is missing Document.")

if "documents" not in dataset_props:
    raise SystemExit("Compiled JSON Schema ElementplanDataset is missing documents.")

document_props = compiled["$defs"]["Document"]["properties"]
if "included_elements" not in document_props:
    raise SystemExit(
        "Compiled JSON Schema Document is missing included_elements."
    )

print("JSON Schema OK: Document.included_elements")

if "Milestone" not in compiled["$defs"]:
    raise SystemExit("Compiled JSON Schema is missing Milestone.")

if "milestones" in dataset_props:
    raise SystemExit(
        "Compiled JSON Schema ElementplanDataset must not include milestones."
    )

phase_props = compiled["$defs"]["Phase"]["properties"]
if "milestones" not in phase_props:
    raise SystemExit("Compiled JSON Schema Phase is missing milestones.")

if "scheduled_milestones" not in model_props:
    raise SystemExit(
        "Compiled JSON Schema Model is missing scheduled_milestones."
    )
if "idp_content_column" in model_props:
    raise SystemExit(
        "Compiled JSON Schema Model must not include idp_content_column."
    )

if "scheduled_milestones" not in document_props:
    raise SystemExit(
        "Compiled JSON Schema Document is missing scheduled_milestones."
    )
if "idp_content_column" in document_props:
    raise SystemExit(
        "Compiled JSON Schema Document must not include idp_content_column."
    )

milestone_props = compiled["$defs"]["Milestone"]["properties"]
for required_prop in ("id", "code", "sort_order", "name", "status", "phase", "kind", "date"):
    if required_prop not in milestone_props:
        raise SystemExit(
            f"Compiled JSON Schema Milestone is missing {required_prop}."
        )

print("JSON Schema OK: Milestone and scheduled_milestones")

if "PhaseMapping" not in compiled["$defs"]:
    raise SystemExit("Compiled JSON Schema is missing PhaseMapping.")
if "PhaseMapEntry" not in compiled["$defs"]:
    raise SystemExit("Compiled JSON Schema is missing PhaseMapEntry.")
if "phase_mappings" not in dataset_props:
    raise SystemExit(
        "Compiled JSON Schema ElementplanDataset is missing phase_mappings."
    )

print("JSON Schema OK: PhaseMapping")

element_props = compiled["$defs"]["Element"]["properties"]
if "needed_in_models" not in element_props:
    raise SystemExit("Compiled JSON Schema Element is missing needed_in_models.")
if "needed_for_models" not in element_props:
    raise SystemExit("Compiled JSON Schema Element is missing needed_for_models.")
if "attachment_link" not in element_props:
    raise SystemExit("Compiled JSON Schema Element is missing attachment_link.")
if "model_link" in element_props:
    raise SystemExit("Compiled JSON Schema Element must not include model_link.")

print("JSON Schema OK: Element.needed_in_models and attachment_link")
PY

echo "Schema check passed."
