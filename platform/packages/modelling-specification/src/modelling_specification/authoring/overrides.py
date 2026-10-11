"""Draft an Override Decision Record as a `Status: Proposed` ADR stub under
`docs/adr/` (FR-014, R7, data-model.md Override Decision Record) when an architect
overrides the agent's rejection, duplicate, or pattern objection. Not a model element
and not a `store-ledger` entry -- architecture-decision traceability stays on the ADR
log, which `adr-auditor`'s normal sweep already picks the stub up for review from.
"""

from __future__ import annotations

import datetime
import re
from typing import Any

from modelling_specification import model_io

ADR_DIR = model_io.REPO_ROOT / "docs" / "adr"
_NUMBER_RE = re.compile(r"^(\d{4})-")


def _next_adr_number() -> str:
    numbers = [int(m.group(1)) for f in ADR_DIR.glob("*.md") if (m := _NUMBER_RE.match(f.name))]
    return f"{(max(numbers) + 1) if numbers else 1:04d}"


def draft_override(
    overridden_objection: str,
    objection_detail: str,
    rationale: str | None,
    applied_delta_summary: str,
) -> dict[str, Any]:
    """Write the ADR stub and return the Override Decision Record's fields
    (data-model.md), `id` being the ADR number just assigned. Rationale is optional
    (R11, Edge Case 7) -- recorded as `null`/"(none given)", never blocking the write."""
    adr_id = _next_adr_number()
    timestamp = datetime.datetime.now(datetime.UTC).isoformat()
    title = f"Conversational authoring override: {overridden_objection}"
    body = (
        f"# ADR-{adr_id}: {title}\n\n"
        "- **Status:** Proposed\n"
        f"- **Date:** {timestamp[:10]}\n\n"
        "## Context\n\n"
        f"An architect overrode a conversational-authoring {overridden_objection} objection:\n"
        f"{objection_detail}\n\n"
        "## Decision\n\n"
        "The architect proceeded with the change anyway.\n\n"
        f"- **Rationale:** {rationale or '(none given)'}\n"
        f"- **Applied:** {applied_delta_summary}\n\n"
        "## Consequences\n\n"
        "- Recorded for later review by the `adr-auditor` sweep (Constitution Principle X).\n"
    )
    slug = re.sub(r"[^a-z0-9]+", "-", overridden_objection.lower()).strip("-") or "objection"
    (ADR_DIR / f"{adr_id}-conversational-authoring-override-{slug}.md").write_text(body)
    return {
        "id": adr_id,
        "overridden_objection": overridden_objection,
        "objection_detail": objection_detail,
        "rationale": rationale,
        "applied_delta_summary": applied_delta_summary,
        "timestamp": timestamp,
    }
