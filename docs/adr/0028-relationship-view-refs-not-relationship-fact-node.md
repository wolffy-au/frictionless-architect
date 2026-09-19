# ADR-0028: Relationships are edges only; views reference them by identifier list, not a `RelationshipFact` node

- **Status:** Accepted
- **Date:** 2026-09-05
- **Sources:** `src/frictionless_architect/schema/manager.py`; session design discussion

## Context

The Neo4j schema (`SchemaManager`) previously stored every ArchiMate
relationship twice: once as a real edge (`(source)-[:ARCHIMATE_RELATIONSHIP]->(target)`),
and again as a reified `RelationshipFact` node connected to its endpoints via
`SOURCE_ELEMENT`/`TARGET_ELEMENT` edges. Views and diagrams attached to the
node (`HAS_RELATIONSHIP`, `HAS_CONNECTION`), and `run_audit_checks` queried the
node for missing endpoints and orphan views.

The node existed to work around one real Neo4j constraint: a relationship
cannot be the endpoint of another relationship, so a `View` cannot point an
edge directly at a bare `ARCHIMATE_RELATIONSHIP` edge. Two alternatives were
considered:

1. Keep the edge as sole storage; have views reference relationships by
   identifier (a property list on `View`) instead of a graph edge.
2. Keep the edge as sole storage; query it directly by identifier wherever
   metadata is needed, with no other change.

Option 2 does not actually solve the underlying problem — it has no answer for
view/diagram attachment (the reason the node existed in the first place), so
it collapses into option 1 for that part regardless.

The reified node was also found to weaken referential integrity in one
respect: `RelationshipFact.source_id`/`target_id` were plain string properties
with no enforced link, so an `Element` could be deleted out from under a
`RelationshipFact` silently, with nothing to detect it beyond a manual audit
query. A bare edge doesn't have this problem — Neo4j either cascades the edge
away on `DETACH DELETE` or blocks a plain `DELETE` while edges remain,
inconsistent with a dangling reference. Duplication also meant every
relationship write was three separate statements (existence check, edge
`MERGE`, node `MERGE`) with no transactional guarantee tying the two
representations together.

## Decision

Store each relationship exactly once, as an edge:
`(source)-[:ARCHIMATE_RELATIONSHIP {identifier, type, ...}]->(target)`.

Drop the `RelationshipFact` node and its `SOURCE_ELEMENT`/`TARGET_ELEMENT`
edges entirely. `View` and `Diagram` reference the relationships they depict
via an identifier list property (`v.relationshipIds`, `d.connectionIds`)
rather than a graph edge to a reified node.

Rewrite the two audit checks to scan `ARCHIMATE_RELATIONSHIP` edges directly
instead of `RelationshipFact` nodes.

## Consequences

- Relationship data is stored once; ingestion drops from three write
  statements per relationship to one (plus the existing existence check).
- The `source_id`/`target_id`-as-orphaned-string-property integrity gap is
  eliminated — an edge's endpoints are structurally guaranteed to exist.
- View/diagram-to-relationship lookups ("what views does this relationship
  affect") are no longer index-backed graph traversals. They become a
  two-step query: find the relevant relationship identifier(s) via the edge,
  then scan `View`/`Diagram` nodes checking list membership
  (`ANY(id IN v.relationshipIds WHERE ...)`). This scan is O(views) with no
  index support and will need revisiting if the view/diagram count grows
  large enough to matter.
- Referential integrity on the `View`→relationship association is no longer
  enforced by the graph — a stale or typo'd identifier in `relationshipIds`
  will silently match nothing. `run_audit_checks` should gain a check for
  this (list entries with no matching edge identifier) as a follow-up.
- `_find_missing_relationship_targets` and `_find_orphan_views` in
  `SchemaManager` need to be rewritten against the new shape; the existing
  regression tests in `tests/integration/test_schema_manager_audit.py` need
  updating to match, since they currently seed/query `RelationshipFact` nodes
  directly.
