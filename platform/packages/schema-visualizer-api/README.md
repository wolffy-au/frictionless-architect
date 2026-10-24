# schema-visualizer-api

Not yet extracted — this is a **specs-only placeholder**. The package itself (today's
`src/frictionless_architect/visualizer/`) extracts in migration step 7
(`ARCHITECTURE.md` §8, §8.2, ADR-0005), after the knowledge-graph scaffold it will consume
(`digital-twin-knowledge-graph`, GH #106) delivers the read path.

This directory exists now only to home the re-homed `002-neo4j-schema-ui` spec under the
two-tier scheme (ADR-0004, GH #107) — see [`specs/`](specs/README.md). `.specify` is a
symlink back to the root Spec Kit install (`scripts/speckit-package.sh`), not a per-package
copy, so this package gets its own `NNN-` spec sequence without duplicating `.specify/`.
