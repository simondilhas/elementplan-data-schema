# pragmaticBIM Elementplan Schema

This repository contains the standalone LinkML schema for pragmaticBIM Elementplan data.

This schema is used in the `elementplan.pragmaticbim.ch` app as well as in the requirements editor.


## Philosophy

Elementplan structures BIM information requirements as a chain from intent to technical detail:

```text
Project goals  →  Ausprägungen (levels + complete workflow sets)  →  Workflows  →  BIM requirements
     why              how deep / which AWFs                            how              what
```

Beside that chain, usage scenarios describe how the building is used:

```text
Use  →  Scenario (need)  →  Option  →  Size  →  Room types or unit variants
            what + how         how        how big     the consequence
```

- **Uses (`Use`)** are Nutzungen such as Wohnen, Büro, or Flughafen. One building can hold several uses. Unit types and usage scenarios each belong to one `use`.
- **Unit types (`UnitType`)** are containers with their own gross area and volume that hold rooms, such as a Wohnung (in IFC usually an `IfcZone` grouping `IfcSpace`s). `restrictions` are gross values, and `parent_unit_type` is set when units nest. `variants` are the standard variants shipped with the catalog (`UnitVariant`, e.g. Wohnung 3.5 Zi). Each variant lists its `unit_rooms`: a `room_type` and a `count`. That count defines the variant (3.5 Zi has two bedrooms); it is not a project quantity.
- **Usage scenarios (`UsageScenario`)** are Nutzungsszenarien: one need of a use, such as Wohnen mit Aussenbezug, with the `options` that meet it. What and how are one question:
  - The "kein" option produces no room types and no unit variants and is marked `exclusive: true`. A scenario with a "kein" option is optional; one without is mandatory.
  - One option is chosen, unless `allows_multiple` is true. An `exclusive` option excludes every other option of its scenario.
  - With a single option and no "kein", the question is skipped and the option applies.
- **Options (`ScenarioOption`)** answer *how*. An option produces `required_room_types`, `unit_variants`, or both. `unit_type` is the container its rooms go into (a balcony goes into the Wohnung); omit it when the rooms sit directly in the building (a communal laundry). `excludes` names options or unit variants, in any scenario or boundary condition, that cannot be chosen together with this option. The rule is symmetric: declare it on one side only, and the app reads it in both directions. Example: the option Arbeitszimmer excludes the unit variant Wohnung 1.5 Zi, so choosing a mix with 1.5 Zi rules out the home office.
- **Sizes (`OptionSize`)** are the ordered grades of an option (small, medium, large; `sort_order` is the ordinal). Each size's `size_restrictions` name a `room_type` and its minimum `min_area`, `min_height`, `min_length`, and `min_width`, because one option can produce several rooms. The size question is asked when the chosen option has `sizes`.
- **Room types are the consequence of an option.** `room_relationships` are the directed edges between them (`from_room_type` → `to_room_type`). An optional `name` can label an edge (e.g. Zugang), and optional `max_distance` is the maximum distance in metres. An edge may start at a room another option or unit variant brings, such as the living room a balcony is reached from. The same room type may appear in several options with different neighbors, because the edges live on the option.
- **How much and the programme tree live in the app.** The schema is a catalog. The app builds the programme from the choices (Gebäude > use > unit variant × count > room type × count) and stores the counts, the same way it stores a chosen project goal level.
- **Room types (`RoomType`)** are functional spaces an option or unit variant can require (e.g. Check-in-Halle). They are catalog records with their own ids. The IFC `Reference` lists `raumliste-innen` and `raumliste-aussen` stay value sets on elements such as Innenraum. `attribute_presets` sets values for attributes of that element: `element` + `name` (+ `pset`) identify the attribute (e.g. Innenraum `PredefinedType`), and `value` is the preset (a string such as `INTERNAL`, a number, a boolean, or a localized text such as `LongName`). Attributes left off the list stay open on each room. `restrictions` sets the minimum size: `min_area` in square metres, and `min_height`, `min_length`, and `min_width` in metres. Omit any measure that is not set.
- This programme chain sits beside project goals. It does not replace the workflow “Szenarienentwicklung”, which is urban design variants, not a usage need.
- **Project goals** define *why* information is needed.
- **Ausprägungen (`ProjectGoalLevel`)** are ordered levels of a goal (e.g. grosszügig → mittel → sensitiv). `sort_order` is the ordinal. Each level’s `activated_workflows` is the **complete set** of workflows activated when that level is selected. Higher levels list lower-level workflows explicitly (copied on save).
- **Level selection:** choosing a level activates that level’s stored `activated_workflows` list.
- **Boundary conditions:** a project goal with `is_boundary_condition: true` sets a Rahmenbedingung instead of an information goal. Its levels list `unit_variants`, the complete set of unit variants the level activates, and `activated_workflows` may stay empty. Example: the goal Wohnungsmix has the levels Kleinwohnungen (1.5 and 2.5 Zi), gemischt (2.5, 3.5, and 4.5 Zi), and Familien (3.5 and 4.5 Zi). How many units of each variant lives in the app.
- **Workflows** define *how* those goals are realized in project practice.
- **Elements and attributes** define *what* must be delivered in the model (the technical IDS level). `Attribute.name` is the IFC property name (a string, e.g. `PredefinedType`), not a localized catalog title. Optional `regex` may be a string or `LocalizedText`. Optional `link_uid` is a legacy editor identifier.

Creating the technical IDS is hard work, but banal: properties, datatypes, phases, IFC mapping. The hard part is linking project goals to the requirements — making every attribute answer a real project purpose, not just fill a checklist.

The link from intent to workflows is `ProjectGoalLevel.activated_workflows` on the goal. Attributes still reference workflows (`needed_for_workflows`).

Project complexity / package tags (`workflow_group`) stay a **separate** axis from project goals: complexity tends to drive base coordination workflows; goals drive additional thematic workflows.

Optional `service_kind` on a workflow records whether it is a **Grundleistung** (`basic`) or a **besondere Leistung** (`special`). Omit it when the workflow is not yet classified. The badge is on the workflow, not on attributes: an attribute shows the kind of the workflows it is needed for.

### Jurisdiction (country vs general)

`jurisdiction` is a multivalued list on **Workflow**, **Attribute**, **Model**, **Document**, and **UsageScenario**:

- `[general]` — not country-specific (omit the field to mean the same)
- one or more ISO 3166-1 alpha-2 codes (lowercase), e.g. `[ch]` or `[ch, de, at]`

Do not mix `general` with country codes. A project with country `C` matches an entity if the list is `[general]` (or omitted) **or** contains `C`.

**ValueSets** have no jurisdiction field; they inherit applicability via `Attribute.allowed_values`. Phase catalogs stay country-ish by scheme identity (e.g. SIA vs abstract), not via this slot.

### Domains, models, and documents

**Domains** are the stable discipline grouping (e.g. Architecture, Building services). Requirements are ordered and filtered by domain.

**Models** are optional delivery units (Teilmodelle) under a domain (e.g. Room model, Architecture element model, Facade model under Architecture). They may be predefined in master templates and inherited or extended by projects. Each model links to exactly one domain (`domain`). Optional `included_elements` is the template/default element set used as IDP pretags. Optional `scheduled_milestones` is a list of milestone catalog ids (e.g. `"11:B"`) for when the container is delivered; omit the field or use `[]` if unscheduled. There is no inlined `milestones:` block inside the container YAML.

**Documents** have the same shape as models, for non-IFC containers (e.g. a 2D plan): a required parent `domain` and optional `included_elements` pretags. They may also be predefined in master templates and inherited or extended by projects. Optional `description` is short notes (distinct from `definition`, the catalog purpose). The class is the container type: Model vs Document; the IDP shows both as columns. Neither class carries content requirements or role assignments (audience, reviewer, responsible party, or approver).

### Classifications and document requirements

**Classifications** on Model and Document are `scheme + code` references to external vocabularies (`Classification`, same slot names as the [pragmatic BIM data contract](https://schema.pragmaticbim.ch/)): `classification_scheme` is the `dcterms:identifier` of the SKOS scheme published on schema.pragmaticbim.ch, `classification_code` its `skos:notation`. Expected schemes: `KBOBDocumentTypes2016` (KBOB/IPB Dokumenttypenkatalog, e.g. `V07100` Architekturplan) and `DocumentFunctionClassification` (e.g. `TEC-PLN`) on documents, `AbstractModelClassification` (e.g. `ARC`) on models. `code` (e.g. `ARC-DOC`) stays the pragmaticBIM-internal filename token and is not repeated in `classifications`. Vocabularies are not copied into this repository; codes are not validated against SKOS by the schema check.

**Document requirements** are the document analog of Element attributes, limited to file metadata. `metadata_requirements` lists what the file's own metadata must carry (revision index, status). Each `DocumentRequirement` has a required `name` and `needed_in_phases`, optional `needed_for_workflows`, `allowed_values`, `regex`, `status`, and `jurisdiction`, and no IFC datatype or `ifc_versions`. This closes the goal → workflow → requirement chain for document metadata: a requirement can be justified by a workflow the same way an attribute is. There is no content-requirement list.

**Phases** are pickable catalogs (`Phase`): SIA codes, abstract stages, or other schemes, each with ordered `values` and nested milestones. **PhaseMapping** relates two catalogs (e.g. SIA → abstract) for display and phase-picker translation via `phases` and `milestones` source→target entries.

**Milestones** belong to a **Phase** (`Phase.milestones`): delivery moments with `kind` `B` (beginning), `M` (mid), or `E` (end), an optional `date`, and a phase code. Models and documents reference them only via `scheduled_milestones` ids (no `milestones:` block inside the container YAML). Attribute `needed_in_phases` and Element `needed_for_models` stay phase codes (when an attribute/element is required), distinct from when a container is delivered.

Element catalog membership is `needed_in_domain`. IDP assignment lives on the Element: `needed_in_models` (container IDs of models and documents) and `needed_for_models` (container id → phase ids). `included_elements` on Model/Document are pretags only, until a project-specific `needed_for_models` override exists.

For ordering, only the domain is relevant. In the project, the actual model or document matters — that is what is delivered and named.

## What Is Included

- `schema/elementplan.linkml.yaml`: main Elementplan LinkML schema
- `schema/ifc/`: generated IFC vocabulary modules used alongside the schema
- `examples/`: sample uses, unit types with standard variants, usage scenarios, and room types (Wohnen, Flughafen), project goals (incl. levels and activated workflows), workflows, elements, values, domains, models, documents (incl. classifications and metadata requirements), and phases (incl. nested milestones)
- `scripts/schema_check.sh`: local schema validation entry point
- `.github/workflows/schema-check.yml`: GitHub Actions workflow for automatic validation

## Schema Check

The repository includes a minimal validation pipeline that checks:

- all YAML files in `schema/` parse correctly
- the main LinkML schema passes LinkML metamodel validation
- the main LinkML schema can be compiled to JSON Schema
- schema contracts for `Attribute.unit`, ProjectGoal above Workflow, `Workflow.service_kind`, `jurisdiction` on Workflow/Attribute/Model/Document, `ProjectGoalLevel.activated_workflows`, `ProjectGoal.is_boundary_condition` and `ProjectGoalLevel.unit_variants`, `Use`, `UnitType` with `variants` and `UnitRoom`, `UsageScenario.use` and `allows_multiple`, `ScenarioOption` `unit_type`, `unit_variants`, `required_room_types`, `exclusive`, `excludes`, and `sizes` with `SizeRestriction`, `RoomRelationship.max_distance`, `RoomType.restrictions`, `RoomType.attribute_presets`, `Model.included_elements`, `Document.included_elements`, `Model`/`Document.scheduled_milestones`, `Milestone`, `PhaseMapping`, `Element.needed_in_models`, `Element.attachment_link`, `Classification` on Model/Document, `DocumentRequirement` with `Document.metadata_requirements`, and `Attribute.name` as a string plus `link_uid`
- every reference in the example uses, unit types, usage scenarios, and project goals (`use`, `unit_type`, `unit_variants`, room types, and `excludes`) points to an existing id, and no option excludes itself

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
