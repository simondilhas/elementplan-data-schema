# pragmaticBIM Elementplan Schema

This repository contains the standalone LinkML schema for pragmaticBIM Elementplan data.

This schema is used in the `elementplan.pragmaticbim.ch` app as well as in the requirements editor.


## Philosophy

Elementplan structures BIM information requirements as a chain from intent to technical detail:

```text
Project goals  →  Workflows  →  BIM requirements (elements / attributes)
     why              how                 what
```

- **Project goals** define *why* information is needed.
- **Workflows** define *how* those goals are realized in project practice.
- **Elements and attributes** define *what* must be delivered in the model (the technical IDS level).

Creating the technical IDS is hard work, but banal: properties, datatypes, phases, IFC mapping. The hard part is linking project goals to the requirements — making every attribute answer a real project purpose, not just fill a checklist.

The schema encodes that link explicitly: workflows reference project goals (`needed_for_project_goals`); attributes reference workflows (`needed_for_workflows`). Requirements stay traceable from delivery detail back to intent.

### Domains and models

**Domains** are the stable ordering and grouping level (e.g. Architecture, Building services). Requirements are ordered and filtered by domain.

**Models** are optional, project-specific Teilmodelle under a domain (e.g. Room model, Architecture element model, Facade model under Architecture). They are used in projects, not in templates. Each model links to exactly one domain (`domain`).

For ordering, only the domain is relevant. In the project, the actual model matters — that is what is delivered and named.

## What Is Included

- `schema/elementplan.linkml.yaml`: main Elementplan LinkML schema
- `schema/ifc/`: generated IFC vocabulary modules used alongside the schema
- `examples/`: sample project goals, workflows, elements, values, domains, models, and phases
- `scripts/schema_check.sh`: local schema validation entry point
- `.github/workflows/schema-check.yml`: GitHub Actions workflow for automatic validation

## Schema Check

The repository includes a minimal validation pipeline that checks:

- all YAML files in `schema/` parse correctly
- the main LinkML schema passes LinkML metamodel validation
- the main LinkML schema can be compiled to JSON Schema
- schema contracts for `Attribute.unit` and ProjectGoal above Workflow

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
