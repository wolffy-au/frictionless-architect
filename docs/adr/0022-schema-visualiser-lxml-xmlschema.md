# ADR-0022: Schema visualiser parses ArchiMate with `defusedxml` ElementTree, validates with `xmlschema`

- **Status:** Accepted
- **Date:** 2026-04-04
- **Sources:** `specs/002-neo4j-schema-ui/research.md`; `wiki/data-model.md`;
  `src/frictionless_architect/visualizer/sample_parser.py`;
  `src/frictionless_architect/visualizer/sample_validator.py`

## Context

The visualiser must load `sample-data/schema/*.xsd` and the sample model XML,
extract element/relationship/view definitions, normalise them to JSON shared by
both Neo4j ingestion and the front-end, and detect schema-vs-sample coverage gaps.

**Correction (2026-09-25):** this record originally said `lxml` + `xmlschema`,
but the implementation never adopted `lxml` — it parses with the standard
library's `xml.etree.ElementTree`, loaded through `defusedxml` for XXE /
entity-expansion hardening. `lxml` was never a project dependency. The record
below has been corrected to match what was actually built, rather than left to
drift or superseded by a near-duplicate ADR for a decision that didn't change.

## Decision

Use **`defusedxml`-wrapped `xml.etree.ElementTree`** for parsing (fast enough
for the small sample data, no C-extension dependency, XXE/entity-expansion
hardened out of the box) plus **`xmlschema`** to validate against the
XSD-defined structure, normalising into a JSON payload contract. `xmlschema`
should load and validate through its own `defuse="always"` mode so schema
loading gets the same hardening as the parse path.

## Consequences

- JSON normalisation keeps the front-end contract simple and enables coverage-gap
  detection before the database is populated.
- `xmlschema` is a runtime dependency (added via Poetry only); `lxml` is not.
- **Known defect (resolved):** the XSDs are ArchiMate 3.1 but `sample_parser.py`
  pinned the 3.0 namespace, and `specs/002` variously said "3" / "3.2".
  Strict-3.1 sample data would not have matched the parser's lookups.
  **Resolved by ADR-0032** (GitHub issue #51 / PR #52): the 3.0 namespace is
  the correct, standard one, and the parser/validator now reject any other
  namespace loudly instead of silently matching nothing.
- **Open follow-up:** full XSD-structural validation in `sample_validator.py`
  (surfacing violations beyond the namespace/root check ADR-0032 added) is
  not yet implemented — tracked as the #51 follow-up issue.

## Alternatives considered

- **`lxml` + `xmlschema` (this record's original choice)** — rejected on
  reflection: adds a C-extension build dependency the code never needed;
  `defusedxml`/`ElementTree` already does everything the parse path requires.
- **Custom regex/XML parsing** — fragile.
- **Neo4j only** — loses the ability to show sample coverage before ingestion.
