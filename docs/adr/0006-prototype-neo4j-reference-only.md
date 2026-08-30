# ADR-0006: `prototype-neo4j` is a reference, not a merge source

- **Status:** Accepted
- **Date:** unknown (pre-dates this log; recorded in `ARCHITECTURE.md` §7)
- **Sources:** `ARCHITECTURE.md` §7; `architecture/model/README.md`

## Context

The `prototype-neo4j` branch holds exploratory work — KG model, UNWIND bulk
seeding, ArchiMate business/motivation layers, layer-scoped visualisers, a
forensic ledger. It diverged early, so it is more rewrite than cherry-pick
(95 nodes / 143 relationships, much of it ahead of the decisions).

## Decision

Treat `prototype-neo4j` as a **reference, not a merge source**. When
`packages/knowledge-graph` is scaffolded, port the model and seeding ideas
deliberately into the new structure. Tag the branch `archive/prototype-neo4j`
before it rots. Do not block the restructure on it.

## Consequences

- The load-bearing ~30-node subset was extracted to `architecture/model/`
  (see ADR-0010); the rest stays only on the archive tag.
- NFR targets, agent rosters, and enabler capabilities from the prototype are
  rebuilt inside each package's own spec when that package is real.
