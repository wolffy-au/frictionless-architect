# ADR-0022: Schema visualiser parses ArchiMate with `defusedxml` ElementTree, validates with `xmlschema`

- **Status:** Accepted
- **Date:** 2026-04-04
- **Sources:** `specs/002-neo4j-schema-ui/research.md`; `wiki/data-model.md`;
  `src/frictionless_architect/visualizer/sample_parser.py`;
  `src/frictionless_architect/visualizer/sample_validator.py`; `pyproject.toml`

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

**Implemented (2026-09-26, GitHub issue #53):** until then the `xmlschema`
half of this decision was recorded but not built — `xmlschema` was not a
dependency, and `sample_validator.py` ran only hand-written checks. It is now
a Poetry runtime dependency and the validator performs full XSD validation;
the details below describe that implementation.

## Decision

Use **`defusedxml`-wrapped `xml.etree.ElementTree`** for parsing (fast enough
for the small sample data, no C-extension dependency, XXE/entity-expansion
hardened out of the box) plus **`xmlschema`** to validate against the
XSD-defined structure, normalising into a JSON payload contract. `xmlschema`
loads the schema and re-reads the sample through its own `defuse="always"`
mode, so both get the same hardening as the parse path, and with
`allow="local"` so nothing is fetched over the network.

- **Entry XSD:** `sample-data/schema/archimate3_Diagram.xsd`, which includes
  `archimate3_View.xsd` and `archimate3_Model.xsd`. The Model XSD alone does
  not define the `Diagram` view type the sample uses.
- **Remote import:** `archimate3_Model.xsd` imports
  `http://www.w3.org/2001/xml.xsd`; it resolves from the copy bundled with
  `xmlschema`, so the bundled XSDs stay unedited (ADR-0032).
- **Check order:** ArchiMate namespace (ADR-0032, short-circuits with one clear
  error) → declared `xsi:type` values (`xmlschema` raises rather than reports
  an unknown type, so this runs first and skips the XSD pass when it fails) →
  XSD validation → relationship-endpoint and view-reference checks.

## Consequences

- JSON normalisation keeps the front-end contract simple and enables coverage-gap
  detection before the database is populated.
- `xmlschema` is a runtime dependency (added via Poetry only; pulls in
  `elementpath`); `lxml` is not.
- XSD violations surface as `XSD:`-prefixed warnings in `/schema-payload`,
  capped at `MAX_XSD_ISSUES`; they are warnings, not failures, so the
  visualiser still renders an imperfect sample.
- The compiled schema is cached per path (`functools.lru_cache`): building it
  takes roughly 200 ms, which must not recur on every payload build
  (Principle IV).
- The hand-written relationship/view reference checks are kept alongside the
  XSD's `xs:keyref` constraints because they name the dangling identifier; a
  dangling reference therefore produces both kinds of warning.
- **Known defect (resolved):** the XSDs are ArchiMate 3.1 but `sample_parser.py`
  pinned the 3.0 namespace, and `specs/002` variously said "3" / "3.2".
  Strict-3.1 sample data would not have matched the parser's lookups.
  **Resolved by ADR-0032** (GitHub issue #51 / PR #52): the 3.0 namespace is
  the correct, standard one, and the parser/validator now reject any other
  namespace loudly instead of silently matching nothing.
- **Follow-up closed:** this record previously listed full XSD-structural
  validation as an open follow-up of #51; no such issue was ever filed. It was
  implemented under #53.

## Alternatives considered

- **`lxml` + `xmlschema` (this record's original choice)** — rejected on
  reflection: adds a C-extension build dependency the code never needed;
  `defusedxml`/`ElementTree` already does everything the parse path requires.
- **Custom regex/XML parsing** — fragile.
- **Neo4j only** — loses the ability to show sample coverage before ingestion.
