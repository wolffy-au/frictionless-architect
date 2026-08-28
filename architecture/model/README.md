# Architecture skeleton

The load-bearing subset of the ArchiMate model prototyped on branch
`prototype-neo4j` — the ~30 nodes that stay true regardless of how the platform's
component boundaries finally land. This is **decomposition input**, not the final
architecture: it feeds the component split in [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md).

## Files

| File | Contents |
|---|---|
| `nodes.yaml` | 4 drivers · 4 principles · 5 constraints · 5 functional requirements · 6 primary capabilities · 6 business processes |
| `relationships.yaml` | 13 edges: capability→requirement realization, process→capability realization, and the end-to-end process chain |

Format is kept graph-loadable (`label` / `identifier` / `properties`) so it can be
seeded into a graph later without reshaping.

## What was deliberately left out

The full prototype had **95 nodes / 143 relationships** across three ArchiMate
layers. The rest lives on tag `archive/prototype-neo4j` and is **not** carried
forward centrally:

- Stakeholders, assessments (SWOT), goals
- Outcomes with target metrics (e.g. "≥99% alignment score", "10× oversight coverage") — placeholder numbers pending real baselines
- Non-functional requirements (drift latency, ledger immutability, spec determinism, control-plane availability, audit-query performance, KG freshness)
- The 6 "enabler" capabilities — each existed only to realize one NFR of one primary capability; they are implementation detail, not architecture-level
- 10 business roles (incl. speculative named AI agents), 9 business objects, the KG "Connect → Enrich → Serve" value stream

**Why:** the detailed model was running ahead of the decisions. NFR targets,
agent rosters, and enabler capabilities should be rebuilt inside each package's
own spec *when that package is real* — not modelled centrally against boundaries
that are still being decided.

## Mapping to the 8-component grouping

The 6 primary capabilities map almost 1:1 onto the platform grouping in
`PROJECT_SPECIFICATION.md`, which is part of why they are trusted as the skeleton:

| Capability | Component |
|---|---|
| `cap-digital-twin` | knowledge-graph |
| `cap-spec-engine` | governance-engine |
| `cap-control-plane` | policy-enforcement |
| `cap-drift-dashboard` | drift-management |
| `cap-forensic-ledger` | audit-query |
| `cap-human-approval-workflow` | decision-capture |

`cap-digital-twin` and `cap-forensic-ledger` have no edges in `relationships.yaml`
— their realization targets were NFRs, which were left on the archive branch.

## Provenance

Extracted from `prototype/nodes.yaml` and `prototype/relationships.yaml` at
`prototype-neo4j` (commit `d0c30b4`). Wording is verbatim from the source except
where a product-specific term ("Woven Control Plane", "ACP") was generalised;
a full technology-agnostic pass is still owed.
