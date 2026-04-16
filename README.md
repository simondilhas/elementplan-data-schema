# pragmaticBIM Elementplan Schema

This repository contains the standalone LinkML schema for pragmaticBIM Elementplan data.

This schema is used in the `elementplan.pragmaticbim.ch` app as well as in the requirements editor.

It is intended to be published as its own GitHub repository so the schema can be versioned, reviewed, and reused independently from the application code that consumes it.

## What Is Included

- `schema/elementplan.linkml.yaml`: main Elementplan LinkML schema
- `schema/ifc/`: generated IFC vocabulary modules used alongside the schema
- `scripts/schema_check.sh`: local schema validation entry point
- `.github/workflows/schema-check.yml`: GitHub Actions workflow for automatic validation

## Schema Check

The repository includes a minimal validation pipeline that checks:

- all YAML files in `schema/` parse correctly
- the main LinkML schema passes LinkML metamodel validation
- the main LinkML schema can be compiled to JSON Schema

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
