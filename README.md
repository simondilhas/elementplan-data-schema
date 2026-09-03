# pragmaticBIM Elementplan Schema

This repository contains the standalone LinkML schema for pragmaticBIM Elementplan data.

This schema is used in the `elementplan.pragmaticbim.ch` app as well as in the requirements editor.


## Philosophy

Elementplan structures BIM information requirements as a chain from intent to technical detail:

```text
Project goals  →  Ausprägungen (levels + workflow deltas)  →  Workflows  →  BIM requirements
     why              how deep / which AWFs                      how              what
```

- **Project goals** define *why* information is needed.
- **Ausprägungen (`ProjectGoalLevel`)** are ordered levels of a goal (e.g. grosszügig → mittel → sensitiv). `sort_order` is the ordinal. Each level’s `activated_workflows` is the **delta** newly enabled at that level (Goal × Level → Workflow).
- **Cumulative selection:** choosing level N activates the union of all deltas for levels of that goal with `sort_order <= N`.
- **Workflows** define *how* those goals are realized in project practice.
- **Elements and attributes** define *what* must be delivered in the model (the technical IDS level).

Creating the technical IDS is hard work, but banal: properties, datatypes, phases, IFC mapping. The hard part is linking project goals to the requirements — making every attribute answer a real project purpose, not just fill a checklist.

The preferred link from intent to workflows is `ProjectGoalLevel.activated_workflows` on the goal. Attributes still reference workflows (`needed_for_workflows`). The older binary slot `Workflow.needed_for_project_goals` remains for transition and is deprecated in favor of level-based activation.

Project complexity / package tags (`workflow_group`) stay a **separate** axis from project goals: complexity tends to drive base coordination workflows; goals drive additional thematic workflows.

### Domains and models

**Domains** are the stable ordering and grouping level (e.g. Architecture, Building services). Requirements are ordered and filtered by domain.

**Models** are optional, project-specific Teilmodelle under a domain (e.g. Room model, Architecture element model, Facade model under Architecture). They are used in projects, not in templates. Each model links to exactly one domain (`domain`). Optional `included_elements` lists catalog element IDs delivered in that Teilmodell (a subset; omitted or empty means unspecified, not the full domain). An element may appear on more than one model. Element catalog membership stays on `needed_in_domain`; do not put model membership on Element.

For ordering, only the domain is relevant. In the project, the actual model matters — that is what is delivered and named.

## What Is Included

- `schema/elementplan.linkml.yaml`: main Elementplan LinkML schema
- `schema/ifc/`: generated IFC vocabulary modules used alongside the schema
- `examples/`: sample project goals (incl. levels and activated workflows), workflows, elements, values, domains, models, and phases
- `scripts/schema_check.sh`: local schema validation entry point
- `.github/workflows/schema-check.yml`: GitHub Actions workflow for automatic validation

## Schema Check

The repository includes a minimal validation pipeline that checks:

- all YAML files in `schema/` parse correctly
- the main LinkML schema passes LinkML metamodel validation
- the main LinkML schema can be compiled to JSON Schema
- schema contracts for `Attribute.unit`, ProjectGoal above Workflow, `ProjectGoalLevel.activated_workflows`, and `Model.included_elements`

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
