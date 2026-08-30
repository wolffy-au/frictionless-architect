# ADR-0022: Schema visualiser parses ArchiMate with `lxml` + `xmlschema`

- **Status:** Accepted
- **Date:** 2026-04-04
- **Sources:** `specs/002-neo4j-schema-ui/research.md`; `wiki/data-model.md`

## Context

The visualiser must load `sample-data/schema/*.xsd` and the sample model XML,
extract element/relationship/view definitions, normalise them to JSON shared by
both Neo4j ingestion and the front-end, and detect schema-vs-sample coverage gaps.

## Decision

Use **`lxml`** for fast parsing plus **`xmlschema`** to validate against the
XSD-defined structure, normalising into a JSON payload contract.

## Consequences

- JSON normalisation keeps the front-end contract simple and enables coverage-gap
  detection before the database is populated.
- **Known defect:** the XSDs are ArchiMate 3.1 but `sample_parser.py` pins the
  3.0 namespace, and `specs/002` variously says "3" / "3.2". Strict-3.1 sample
  data would not match the parser's XPath. Track and reconcile.

## Alternatives considered

- **Custom regex/XML parsing** — fragile.
- **Neo4j only** — loses the ability to show sample coverage before ingestion.
