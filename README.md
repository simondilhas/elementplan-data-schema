# pragmaticBIM Elementplan Schema

This repository contains the standalone LinkML schema for pragmaticBIM Elementplan data.

This schema is used in the `elementplan.pragmaticbim.ch` app as well as in the requirements editor.


## Philosophy

Elementplan structures BIM information requirements as a chain from intent to technical detail:

```text
Project goals  →  Ausprägungen (levels + complete workflow sets)  →  Workflows  →  BIM requirements
     why              how deep / which AWFs                            how              what
```

- **Project goals** define *why* information is needed.
- **Ausprägungen (`ProjectGoalLevel`)** are ordered levels of a goal (e.g. grosszügig → mittel → sensitiv). `sort_order` is the ordinal. Each level’s `activated_workflows` is the **complete set** of workflows activated when that level is selected. Higher levels list lower-level workflows explicitly (copied on save).
- **Level selection:** choosing a level activates that level’s stored `activated_workflows` list.
- **Workflows** define *how* those goals are realized in project practice.
- **Elements and attributes** define *what* must be delivered in the model (the technical IDS level). `Attribute.name` is the IFC property name (a string, e.g. `PredefinedType`), not a localized catalog title. Optional `regex` may be a string or `LocalizedText`. Optional `link_uid` is a legacy editor identifier.

Creating the technical IDS is hard work, but banal: properties, datatypes, phases, IFC mapping. The hard part is linking project goals to the requirements — making every attribute answer a real project purpose, not just fill a checklist.

The link from intent to workflows is `ProjectGoalLevel.activated_workflows` on the goal. Attributes still reference workflows (`needed_for_workflows`).

Project complexity / package tags (`workflow_group`) stay a **separate** axis from project goals: complexity tends to drive base coordination workflows; goals drive additional thematic workflows.

Optional `service_kind` on a workflow records whether it is a **Grundleistung** (`basic`) or a **besondere Leistung** (`special`). Omit it when the workflow is not yet classified. The badge is on the workflow, not on attributes: an attribute shows the kind of the workflows it is needed for.

### Jurisdiction (country vs general)

`jurisdiction` is a multivalued list on **Workflow**, **Attribute**, **Model**, and **Document**:

- `[general]` — not country-specific (omit the field to mean the same)
- one or more ISO 3166-1 alpha-2 codes (lowercase), e.g. `[ch]` or `[ch, de, at]`

Do not mix `general` with country codes. A project with country `C` matches an entity if the list is `[general]` (or omitted) **or** contains `C`.

**ValueSets** have no jurisdiction field; they inherit applicability via `Attribute.allowed_values`. Phase catalogs stay country-ish by scheme identity (e.g. SIA vs abstract), not via this slot.

### Domains, models, and documents

**Domains** are the stable discipline grouping (e.g. Architecture, Building services). Requirements are ordered and filtered by domain.

**Models** are optional delivery units (Teilmodelle) under a domain (e.g. Room model, Architecture element model, Facade model under Architecture). They may be predefined in master templates and inherited or extended by projects. Each model links to exactly one domain (`domain`). Optional `included_elements` is the template/default element set used as IDP pretags. Optional `scheduled_milestones` is a list of milestone catalog ids (e.g. `"11:B"`) for when the container is delivered; omit the field or use `[]` if unscheduled. There is no inlined `milestones:` block inside the container YAML.

**Documents** have the same shape as models, for non-IFC containers (e.g. a 2D plan): a required parent `domain` and optional `included_elements` pretags. They may also be predefined in master templates and inherited or extended by projects. Optional `description` is a short checkable list of required contents (distinct from `definition`, the catalog purpose). The class is the container type: Model vs Document; the IDP shows both as columns.

### Classifications, roles, and document requirements

**Classifications** on Model and Document are `scheme + code` references to external vocabularies (`Classification`, same slot names as the [pragmatic BIM data contract](https://schema.pragmaticbim.ch/)): `classification_scheme` is the `dcterms:identifier` of the SKOS scheme published on schema.pragmaticbim.ch, `classification_code` its `skos:notation`. Expected schemes: `KBOBDocumentTypes2016` (KBOB/IPB Dokumenttypenkatalog, e.g. `V07100` Architekturplan) and `DocumentFunctionClassification` (e.g. `TEC-PLN`) on documents, `AbstractModelClassification` (e.g. `ARC`) on models. `code` (e.g. `ARC-DOC`) stays the pragmaticBIM-internal filename token and is not repeated in `classifications`. Vocabularies are not copied into this repository; codes are not validated against SKOS by the schema check.

**Roles** are `Classification` entries with scheme `AbstractRoles` and codes such as `aec.architect`: `responsible_role` (single, produces the container), `reviewing_roles`, and `audience_roles` (readers). They are template defaults expressed as roles, not persons; projects override them.

**Document requirements** are the document analog of Element attributes. `content_requirements` lists what must be inside the document (legend, scale, revision table, report sections; non-element content, distinct from `included_elements`), `metadata_requirements` what the file's own metadata must carry (revision index, status). Each `DocumentRequirement` has a required `name` and `needed_in_phases`, optional `needed_for_workflows`, `allowed_values`, `regex`, `status`, and `jurisdiction`, and no IFC datatype or `ifc_versions`. This closes the goal → workflow → requirement chain for documents: a document requirement can be justified by a workflow the same way an attribute is.

**Phases** are pickable catalogs (`Phase`): SIA codes, abstract stages, or other schemes, each with ordered `values` and nested milestones. **PhaseMapping** relates two catalogs (e.g. SIA → abstract) for display and phase-picker translation via `phases` and `milestones` source→target entries.

**Milestones** belong to a **Phase** (`Phase.milestones`): delivery moments with `kind` `B` (beginning), `M` (mid), or `E` (end), an optional `date`, and a phase code. Models and documents reference them only via `scheduled_milestones` ids (no `milestones:` block inside the container YAML). Attribute `needed_in_phases` and Element `needed_for_models` stay phase codes (when an attribute/element is required), distinct from when a container is delivered.

Element catalog membership is `needed_in_domain`. IDP assignment lives on the Element: `needed_in_models` (container IDs of models and documents) and `needed_for_models` (container id → phase ids). `included_elements` on Model/Document are pretags only, until a project-specific `needed_for_models` override exists.

For ordering, only the domain is relevant. In the project, the actual model or document matters — that is what is delivered and named.

## What Is Included

- `schema/elementplan.linkml.yaml`: main Elementplan LinkML schema
- `schema/ifc/`: generated IFC vocabulary modules used alongside the schema
- `examples/`: sample project goals (incl. levels and activated workflows), workflows, elements, values, domains, models, documents (incl. classifications, roles, and content requirements), and phases (incl. nested milestones)
- `scripts/schema_check.sh`: local schema validation entry point
- `.github/workflows/schema-check.yml`: GitHub Actions workflow for automatic validation

## Schema Check

The repository includes a minimal validation pipeline that checks:

- all YAML files in `schema/` parse correctly
- the main LinkML schema passes LinkML metamodel validation
- the main LinkML schema can be compiled to JSON Schema
- schema contracts for `Attribute.unit`, ProjectGoal above Workflow, `Workflow.service_kind`, `jurisdiction` on Workflow/Attribute/Model/Document, `ProjectGoalLevel.activated_workflows`, `Model.included_elements`, `Document.included_elements`, `Model`/`Document.scheduled_milestones`, `Milestone`, `PhaseMapping`, `Element.needed_in_models`, `Element.attachment_link`, `Classification` and role slots on Model/Document, `DocumentRequirement` with `Document.content_requirements`/`metadata_requirements`, and `Attribute.name` as a string plus `link_uid`

Run the check locally with:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip linkml
make schema-check
```

## Repository Layout

```text
.
|-- .github/workflows/schema-check.yml
|-- LICENSE
|-- Makefile
|-- README.md
|-- examples/
|-- schema/
`-- scripts/schema_check.sh
```

## Suggested GitHub Setup

1. Create a new repository, for example `pragmaticbim-elementplan-schema`.
2. Copy these files into that repository.
3. Initialize git and push to GitHub.
4. Enable branch protection if you want the schema check to be required before merge.

## License

This repository is licensed under the Apache License 2.0.
