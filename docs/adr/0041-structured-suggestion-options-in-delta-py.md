# ADR-0041: Structured suggestion options in `delta.py` — a deliberate deviation from GH #68's filed breakdown

- **Status:** Accepted
- **Date:** 2026-10-29
- **Sources:** GH #68 (epic, sub-issues #140-#151); GH #108 (closed, origin of ADR-0037's
  `modelling-specification` agent); GH #142 (journey-API/Solution-Design rework of the
  agent); `specs/EPIC-003-conversational-model-authoring/spec.md` FR-001;
  `platform/packages/modelling-specification/src/modelling_specification/authoring/delta.py`

## Context

GH #68's epic, as currently filed, re-platforms the conversational agent onto a journey-API
and Solution-Design-editing architecture in `reusable-architecture-library` (#140-#151); #142
frames adapting ADR-0037/#108's agent for that future shape as superseding its current form,
not as extending its existing suggestion-handling behaviour in place. There is no filed GH
issue for "give `delta.py` the ability to return multiple structured, convention-grounded
candidate options" against *today's* agent — the shape ADR-0037 actually shipped, which
edits `architecture/model/` directly. EPIC-003's own spec (FR-001) only requires one
clarifying question for a vague request; it does not require multiple ranked options.

This branch needed a workable demo of the conversational agent suggesting a way forward
("what should I do about X?") rather than only accepting one concrete change or asking a
single clarifying question. Two paths existed: (a) build it now against `delta.py` as it
exists today, as a documented deviation from #68's filed plan, to reconcile with #142 later
if and when that rework starts; or (b) wait and build it only inside the future journey-API
architecture once #142 lands. Given demo priority, (a) was chosen.

## Decision

1. **Built against today's architecture, not #142's.** `delta.py`'s `propose_delta` now
   recognises a "way forward" request and returns `{"options": [...]}` — 2-3 independently
   applicable candidate deltas, each with a `rationale` grounded in existing element ids
   and/or Enterprise Convention Rule ids (`conventions.yaml`), plus `convention_refs`. A
   concrete single-delta request is unaffected (`{"elements": [...], "relationships": [...]}`
   unchanged).
2. **Each option is independently validated before the architect picks one.** `router.py`
   gained `Session.pending_options` and `POST /sessions/{id}/propose/select`: every option is
   run through the same validation/duplicate/pattern-suggestion pipeline
   (`_validate_and_flag`'s pure core, `_validate`) the single-delta path already used, so an
   architect sees each option's standing *before* choosing, not after.
3. **No change to FR-001's spec text.** `spec.md` is left as-is; this is explicitly scoped as
   a deviation from the filed plan rather than a retroactive rewrite of what #108/ADR-0037
   committed to deliver, so a reader comparing spec to code sees the gap and this ADR
   explaining it, not a spec quietly stretched to match.
4. **No GH issue filed for this specific change.** Tracked here and in the branch's own
   commits (`feat(modelling-specification): return structured suggestion options`) instead,
   given the demo-priority rationale above.

## Consequences

- Reconciling this with #142: when that rework starts, its author must decide whether the
  options/`pending_options`/`propose/select` shape migrates into the journey-API agent as-is,
  gets redesigned, or is dropped as superseded. This ADR is the record of what existed and why,
  so that decision has the full picture rather than rediscovering it from the diff.
- Residual risk, not mitigated here: an option's `rationale` text is never mechanically
  checked against the `convention_refs`/element ids it cites — a plausible-sounding but
  ungrounded rationale would only be caught by a human architect reading it, not by
  validation. Validation only runs on the option's `elements`/`relationships`, not its prose.
- GH #68's and #129's issue bodies are not updated by this ADR; if the maintainer wants the
  epic's tracking to reflect this deviation, that is a separate, explicit edit.

## Alternatives considered

- **Wait for #142's journey-API rework and build this there instead** — rejected for this
  branch: blocks on an epic item with no start date, against a demo-priority need now.
- **File a new GH issue first, then implement** — rejected: adds process overhead disproportionate
  to a single-file, already-scoped change; this ADR plus the branch's commit history serves the
  same traceability need (Principle X) without a placeholder issue nobody will revisit before #142 does.
