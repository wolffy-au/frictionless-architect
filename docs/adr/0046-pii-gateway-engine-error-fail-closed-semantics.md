# ADR-0046: `pii-gateway`'s engine-error fail-closed redaction replaces the whole text, and `Resolution.ALLOW` is rejected for it

- **Status:** Accepted
- **Date:** 2026-11-05
- **Sources:** `platform/packages/pii-gateway/specs/001-pii-gateway/spec.md` Assumptions
  (flags fail-closed as "not yet covered by an ADR"); `research.md` R6;
  `data-model.md` `Match`/`PendingConfirmation` notes;
  `platform/packages/pii-gateway/src/pii_gateway/{scrub,models}.py`;
  `platform/packages/modelling-specification/src/modelling_specification/router.py`
  `resolve_pii`

## Context

`scrub()`'s fail-closed behaviour for a detector-engine exception (research.md R6)
converts the exception into a synthetic `Match(category="_ENGINE_ERROR", location=(0,
0), confidence=0.0)` and runs it through the same auto-redact / flag-for-review logic
as a real match. That synthetic match is a zero-length span. Redacting only the span
(the original implementation) was therefore a no-op: `anonymize()` had nothing to
replace at a zero-width location, so `REDACTED_AND_PROCEEDED`'s `result.text` and
`FLAGGED_FOR_REVIEW`'s `Resolution.REDACT` output both came back as the *original*
text with only `<_ENGINE_ERROR>` prepended — the real PII/PHI the engine never
inspected was sent to the LLM provider unredacted while being reported as redacted or
reviewable. This was a bug, not a deliberate design, and is fixed by this ADR's
decision 1.

Separately, `PendingConfirmation.resolve(Resolution.ALLOW)` returns `original_text`
unconditionally — by design for a *real* flagged match, where ALLOW is the architect's
informed judgment call having seen what was actually detected. For the synthetic
engine-error match, there is nothing for the architect to have seen: the detector
never ran. Decision 1 alone (whole-text replacement) fixes what `REDACT` produces, but
does not address `ALLOW`, which would still hand back the fully unexamined original
text under the same "the architect decided this is fine" framing used for a real
match. The spec's own Assumptions section already flags fail-closed itself as "a new
default this spec introduces, not yet covered by an ADR" — this record closes that gap
for both the redaction-shape bug fix and this additional ALLOW question, decided
together on 2026-11-05.

## Decision

1. **Engine-error redaction replaces the whole text, not the zero-length span.**
   `scrub()` detects the synthetic `_ENGINE_ERROR` match among a call's results and, for
   both `REDACTED_AND_PROCEEDED` and `FLAGGED_FOR_REVIEW`'s `REDACT` resolution, sets the
   redacted text to the literal `<_ENGINE_ERROR>` marker in place of the *entire* input,
   instead of running `anonymize()` over the (zero-length) span. No part of text the
   engine never inspected survives in the redacted output.
2. **`Resolution.ALLOW` is rejected outright for a pending confirmation backed by the
   synthetic engine-error match.** `PendingConfirmation.resolve(Resolution.ALLOW)` raises
   `EngineErrorAllowRejected` when `detection_failed` is true; this is enforced in
   `pii_gateway` itself (not just by callers) so no caller can reach the original text via
   `ALLOW` for this case. `REDACT` and `EDIT` are unaffected and still resolve the pending
   confirmation. `modelling-specification`'s `POST .../propose/resolve-pii` maps the
   rejection to `409`, leaves `session.pending_pii_confirmation` in place (the architect can
   still redact or edit), and never makes the LLM call. The flag-for-review response
   (`pii_review_required`) also carries a `detection_failed: bool` field so a caller is told
   detection failed outright rather than left to infer it from the `_ENGINE_ERROR` category
   string inside `matches`.
3. **ALLOW on a real match is unchanged.** This decision only narrows the engine-error
   case; `Resolution.ALLOW` on an actual detected match still returns the original text, same
   as before.

## Consequences

- Fixes the fail-closed bypass: `auto-redact` contexts and `flagged-for-review`'s
  `REDACT` path no longer send real PII/PHI to an LLM provider while reporting it as
  handled.
- `pii_gateway` gains a new public exception, `EngineErrorAllowRejected`, and a new
  `PendingConfirmation.detection_failed` property — both exported from the package
  `__init__.py`. Any caller resolving a flag-for-review match (today, only
  `modelling-specification`) must handle this exception or its own `ALLOW` calls will
  raise uncaught.
- The flag-for-review JSON response shape gains `detection_failed`; existing consumers
  that don't read it are unaffected (additive field).
- An architect who hits this case can no longer get unscrubbed text through by choosing
  "allow" — their only paths forward are `redact` (loses the whole message, not just the
  PII) or `edit` (retype without whatever the engine would have flagged, blind to what
  that might have been). This is a usability cost accepted in exchange for closing the
  bypass; if it proves too disruptive in practice (e.g. frequent transient detector
  failures), revisit — candidates would be a retry-the-detection affordance before
  falling back to this rejection, or a narrower fail-closed scope.
- Does not retroactively resolve the spec's wider "fail-closed has no ADR" Assumption
  for every future caller context — only this specific redaction-shape bug and the ALLOW
  question it exposed. A context added later with a different failure-mode shape should
  still check this ADR's reasoning, not just copy its mechanism blindly.

## Alternatives considered

- **Redact only the zero-length span via the normal `anonymize()` path** — this was the
  original implementation; rejected (fixed by this ADR) because it is a no-op on a
  zero-width span and was the actual bug: the real text survived untouched, prefixed
  with a marker that implied it had been handled.
- **Treat `ALLOW` on an engine-error match identically to `ALLOW` on a real match** —
  this was the original behaviour; rejected because it silently permits the exact bypass
  fail-closed exists to prevent, just moved one step later into the human
  resolution step instead of the automated one.
- **Escalate to a hard block (reject the request outright) across all contexts on any
  engine error** — rejected, same reasoning ADR-0014's own Alternatives considered
  already rejected hard-block as a global default: out of scope here, since this
  decision only changes what the engine-error case's three normal resolutions
  (`redact`/`allow`/`edit`) do, not the global failure-mode policy.
