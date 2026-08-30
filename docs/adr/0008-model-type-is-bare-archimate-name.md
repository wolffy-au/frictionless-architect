# ADR-0008: Model `type` = bare ArchiMate 3.2 concept name

- **Status:** Accepted
- **Date:** 2026-08-30
- **Sources:** session memory `model-storage` (decisions #1, #2)

## Context

The canonical YAML model (ADR-0007) needs a type vocabulary for elements and
relationships. It must round-trip cleanly through the pyArchimate generator and
into a graph.

## Decision

- Element `type` is the **bare ArchiMate 3.2 concept name** — `Driver`,
  `Capability`, `BusinessProcess`, `ApplicationComponent`, `ApplicationFunction`,
  `DataObject`, … — matching `pyArchimate.ArchiType` exactly, so the generator is
  a pass-through. Case-insensitive in YAML, canonicalized against the enum.
- Relationship `type` is likewise the ArchiMate name (`Realization`,
  `Triggering`, `Serving`, `Flow`, `Access`, `Association`, `Composition`), with
  `source` / `target` / `label` / `props`.
- `props.access_type` (`Read` | `Write` | `ReadWrite`) qualifies `Access`;
  `props.c4-label` overrides `label` in the C4 projection only.

## Consequences

- No bespoke type registry to maintain; the ArchiMate metamodel is the schema.
- View/diagram layout is decision #3 and is deferred.
