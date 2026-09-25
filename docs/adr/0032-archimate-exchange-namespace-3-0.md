# ADR-0032: ArchiMate exchange files use the `archimate/3.0/` namespace (schema version 3.1)

- **Status:** Accepted
- **Date:** 2026-09-25
- **Sources:** GitHub issue #51; `sample-data/schema/archimate3_*.xsd`; `specs/002-neo4j-schema-ui/spec.md` Edge Cases

## Context

The Open Group's ArchiMate 3.1 exchange-format XSDs (published under
`http://www.opengroup.org/xsd/archimate/3.1/`) keep the 3.0 target namespace
`http://www.opengroup.org/xsd/archimate/3.0/`; only their `version="3.1"`
attribute and publication URL say 3.1. Our bundled copies had been hand-edited
to a 3.1 `targetNamespace` (present since they were first committed in
`b356043`), while the visualiser's parser and validator — and every model file
in the repo, from Archi and pyArchimate alike — use the 3.0 namespace. Because
ElementTree lookups are namespace-qualified, a document in any other namespace
parsed to zero elements and passed validation silently (issue #51), violating
constitution Principle VII.

## Decision

We accept exactly the `http://www.opengroup.org/xsd/archimate/3.0/` namespace,
defined once as `ARCHIMATE_NS` in `src/frictionless_architect/visualizer/namespaces.py`.
The bundled XSDs are kept identical to the official Open Group files. A document
whose root is not `{ARCHIMATE_NS}model` is rejected loudly: the parser raises
`ArchimateNamespaceError`, the validator returns it as an issue, and the
payload service surfaces it as a warning with `sample_file_status: "invalid"`.

## Consequences

- Archi exports, pyArchimate output, and all existing sample/architecture
  models keep working unchanged.
- A file authored against a non-standard 3.1 namespace fails with an
  actionable message naming the expected namespace, instead of rendering empty.
- `sample_file_status` gains the value `"invalid"`
  (`specs/002-neo4j-schema-ui/contracts/api.md`).
- The bundled XSDs must not be edited locally; refresh them from the Open
  Group only.
- Revisit if The Open Group publishes a new target namespace (e.g. with
  ArchiMate 3.2 or 4.0 exchange-format schemas); supporting it then means
  a migration path per Principle VIII, not a silent second namespace.
- Independent of ADR-0022 (`lxml` + `xmlschema`); full XSD validation there
  would enforce the same namespace.

## Alternatives considered

- **Move to the 3.1 namespace (as #51 proposed)** — rejected: no conforming
  tool emits it, and it would break every model file in the repo.
- **Accept both 3.0 and 3.1 namespaces** — rejected: tolerates a namespace
  that does not exist in the standard and hides schema drift.
