# ADR-0044: A runtime dependency decided by its own ADR gets a Technology-layer element

- **Status:** Proposed
- **Date:** 2026-10-31
- **Sources:** GH #136 (`pii-gateway`, ADR-0043), `architecture/model/elements.yaml` §F
  comment (2026-09-27, GH #55 item 3 — the prior modelling threshold this narrows)

## Context

GH #55 item 3 set a modelling threshold for third-party library dependencies: a library
gets an `ext-*`/Technology-layer element only when it performs "a distinctive capability a
modelled function depends on by name"; pure implementation-detail plumbing
(`xmlschema`/`defusedxml`) stays unmodelled. That threshold is sound for everyday
dependencies, but it left a gap: a library that was itself the subject of a deliberate,
recorded architectural decision — `litellm` (ADR-0034), Presidio (ADR-0043) — could still
end up with no model element, represented only as prose inside the `desc` of the
`ApplicationComponent`/`ApplicationFunction` it backs. That under-represents a load-bearing
choice: Principle X requires every ADR's model impact to be stated, and "mentioned in
another element's description" is not a model element a view can show or a relationship can
connect.

## Decision

A runtime dependency (declared in a `pyproject.toml` `dependencies` list, not the `dev`/
`tests`/`lint`/`docs` groups) gets its own Technology-layer `SystemSoftware` element in
`architecture/model/` whenever **either**:

1. it performs a distinctive, named capability a modelled function depends on by name
   (the existing GH #55 threshold), **or**
2. it was chosen by its own ADR decision — i.e. an ADR's Decision section names the library
   and states why it was picked over alternatives (not merely mentions it in passing).

Generic plumbing (validation, serialization, env loading, transitive security-floor pins)
stays unmodelled under either test. The element is wired to the `ApplicationComponent`/
`ApplicationFunction` it backs with a `Serving` relationship, following the existing
`ext-trestle -> fn-oscal-conversion` pattern.

## Consequences

- **Model impact**: adds four `SystemSoftware` elements and their `Serving` relationships:
  - `sw-litellm -> sub-llm-provider-config` (backfill; decided by ADR-0034)
  - `sw-presidio -> sub-pii-gateway` (decided by ADR-0043)
  - `sw-pyarchimate -> fn-conversational-authoring` (decided by ADR-0037, amended
    alongside this record to make that decision explicit)
  - `sw-rapidfuzz -> fn-conversational-authoring` (decided by ADR-0037, amended alongside
    this record — promotes `research.md` R5's duplicate-detection choice into the ADR)
  `build.py`/`render_diagrams.py` regenerate the affected diagrams in the same change.
- Future ADRs that pick a specific library (as opposed to just using one already on the
  approved list) must include an "Alternatives considered" entry for it to cross this bar —
  a Decision line that only mentions a library in passing does not.
- Does not retroactively require modelling every dependency already in `pyproject.toml`:
  only those meeting test 1 or test 2 above. Most of the current dependency surface
  (`pydantic`, `python-dotenv`, `filelock`, `pyyaml`, `aiohttp`, `certifi`, `tomli-w`, etc.)
  stays unmodelled, matching the GH #55 threshold's original intent.
- Revisit if this produces element sprawl in practice (e.g. every future library pick
  routinely gets its own one-line ADR purely to qualify) — the bar is "a real decision with
  rejected alternatives," not "an ADR filed as a formality."

## Alternatives considered

- **Model every runtime dependency unconditionally** — rejected. Would force elements for
  `pydantic`, `python-dotenv`, `filelock`, `aiohttp`, `certifi`, and similar plumbing that
  carries no architectural decision, bloating the model and every generated diagram with
  detail no view needs.
- **Leave the GH #55 threshold unchanged, accept that ADR'd libraries stay unmodelled** —
  rejected. Left `litellm`/Presidio-grade decisions representable only as prose, which
  Principle X's model-impact requirement is meant to prevent for load-bearing choices.
