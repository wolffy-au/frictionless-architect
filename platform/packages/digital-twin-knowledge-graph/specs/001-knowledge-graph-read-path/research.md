# Phase 0 Research: Digital Twin Knowledge Graph — Read Path

## R1. Primary interface shape

- **Decision**: A plain Python library interface — a `KnowledgeGraphReadPath` class plus a
  `ReadPathError` exception in `digital_twin_knowledge_graph.read_path` — with no FastAPI
  app, router, or CLI.
- **Rationale**: ADR-0005's explicit choice: one consumer today, no HTTP boundary until a
  second one needs it. Matches FR-002/FR-013.
- **Alternatives considered**: HTTP microservice — rejected, no second consumer exists yet
  and it would add a contract this feature doesn't need. gRPC — rejected for the same reason.

## R2. Scope boundary: build fresh, don't cut over flat-`src/` yet

- **Decision**: Implement `read_path.py`, `sample_parser.py`, `schema_manager.py` and
  `namespaces.py` as new modules in this package, using flat-`src/`'s
  `visualizer/data_loader.py`, `visualizer/sample_parser.py`, `visualizer/namespaces.py` and
  `schema/manager.py` as the reference behavior and test cases. Do not delete the flat-`src/`
  originals or repoint `visualizer/api.py` / `scripts/neo4j_schema.py` in this increment.
- **Rationale**: The repo root and `platform/` are separate Poetry projects with separate
  lockfiles (root `pyproject.toml` excludes `platform/` from its own tooling —
  `ARCHITECTURE.md` §8 Status). ADR-0005 says the modules "move to"
  `digital-twin-knowledge-graph`, but doesn't resolve how a root-project consumer
  (`visualizer/api.py`) would then depend on a `platform/packages/*` path dependency across
  that boundary — no ADR documents that mechanism. Introducing it now would be new,
  undocumented cross-boundary tooling (two lockfiles to keep in sync, CI gating to extend)
  decided inside a feature plan rather than as its own reviewed choice. Confirmed with the
  maintainer during planning (see spec.md Assumptions).
- **Alternatives considered**: Full cutover now (wire a root→`platform/` path dependency,
  delete flat-`src/` copies, repoint both callers) — rejected for this increment; it's a
  bigger, separately-reviewable change, better timed with the visualiser API/UI split
  (`ARCHITECTURE.md` §8.2, step 7) when the flat root project is retired anyway. Partial
  cutover (move only the two pure-Neo4j modules, leave `sample_parser.py` behind) — rejected,
  it doesn't avoid the cross-boundary question (`visualizer/api.py` still imports
  `DataLoader`) and it contradicts ADR-0006/ADR-0005's naming of `sample_parser.py` as part of
  this move.

## R3. Driver-type leakage boundary

- **Decision**: Confine all `neo4j` imports to `read_path.py` and `schema_manager.py`; every
  public function/method returns plain data (`dict`, `list[dict]`, dataclasses) or raises
  `ReadPathError`/a package-defined ingestion error — never a `neo4j.Driver`, `Session` or
  `Record`.
- **Rationale**: FR-002 (`if-twin-read-path` must be free of leaked Neo4j driver types,
  ADR-0005). Flat-`src/`'s `DataLoader.collect()` already returns
  `dict[str, list[dict[str, Any]]]` and `SchemaManager`'s methods already return
  `list[dict]`/`None`/`tuple[list[dict], list[dict]]` — so this is a packaging boundary to
  preserve, not an interface redesign.
- **Alternatives considered**: Wrap the whole `neo4j.Driver` behind a duck-typed `Protocol` —
  rejected as unneeded; the existing public methods already avoid leaking driver types.

## R4. Which `prototype-neo4j` ideas to port

- **Decision**: Port only the ArchiMate business/motivation-layer element/relationship
  vocabulary and the batched (`UNWIND`-style) ingestion approach, reimplemented fresh inside
  `schema_manager.py`, attributed to ADR-0006 in code comments/tests.
- **Rationale**: ADR-0006 names five ideas in the retired spike (KG model, `UNWIND` bulk
  seeding, ArchiMate business/motivation layers, layer-scoped visualisers, a forensic ledger).
  Of those: the KG model's load-bearing subset was already extracted to
  `architecture/model/` (ADR-0010); layer-scoped visualisers are a UI concern for
  `schema-visualizer-ui` once it exists (§8.2); the forensic ledger is out of scope — it's
  presently backed by `controls-compliance-catalog`'s own ledger (see that package's `plan.md`
  Structure Decision), and `sub-twin`'s eventual ownership of it is a separate future spec.
  That leaves the vocabulary and the batched-ingestion idea as this increment's genuine,
  scoped-in port (FR-010).
- **Alternatives considered**: Cherry-pick files from the `archive/prototype-neo4j` tag —
  rejected outright, ADR-0006 is explicit that the tag is "a reference, not a merge source."
  Port the forensic ledger too, since `cap-forensic-ledger` is modeled as `sub-twin`'s —
  rejected for this increment; it would duplicate `controls-compliance-catalog`'s existing
  ledger with no consumer here yet, and absorbing it is its own future spec (see spec.md
  Assumptions).

## R5. Interface naming

- **Decision**: Rename `DataLoader` → `KnowledgeGraphReadPath` in the new package, keeping
  `DataLoaderError` → `ReadPathError`. Other classes (`SampleParser`, `SchemaManager`) keep
  their names.
- **Rationale**: `KnowledgeGraphReadPath` directly matches the model's own name for this
  interface ("Knowledge Graph Read Path", `if-twin-read-path`) — worth the one rename for
  traceability between code and model. `SampleParser`/`SchemaManager` already read clearly on
  their own and aren't named in the model, so they move unrenamed (minimal churn, Principle I).
- **Alternatives considered**: Keep `DataLoader` unrenamed throughout — rejected, loses the
  direct name-matching to the model's interface, the one rename most worth making.

## R6. Connection settings

- **Decision**: A small `GraphSettings(BaseSettings)` in this package's own `config.py`
  (`pydantic-settings`), reading `neo4j_uri` / `neo4j_user` / `neo4j_password` under the same
  `FRICTIONLESS_ARCHITECT_` env prefix flat-`src/`'s `VisualizerSettings` already uses — not a
  shared Python object (separate packages/lockfiles), just the same env var convention.
- **Rationale**: Flat-`src/` keeps running its own copy against the same Neo4j instance during
  this interim (R2); matching the env var prefix means an operator configures Neo4j once, not
  under two different prefixes for the same database. `ARCHITECTURE.md` §8.2 already decided
  to keep this prefix as-is until the prefix-wide rename epic (§9).
  `pydantic`/`pydantic-settings` are already this repo's convention for settings
  (`controls-compliance-catalog`, `llm-provider-config` both use them).
- **Alternatives considered**: A new package-specific prefix (e.g. `DIGITAL_TWIN_KG_`) —
  rejected for this increment; would force dual-configuring the same Neo4j connection under
  two prefixes with no present benefit. Revisit only if this package ever needs to point at a
  different graph than the flat app.

## R7. Test strategy

- **Decision**: Carry over the existing unit tests for `DataLoader`/`SampleParser`/
  `SchemaManager` as new test modules (`tests/unit/test_read_path.py`,
  `test_sample_parser.py`, `test_namespaces.py`, `test_schema_manager.py`) exercising the
  renamed/relocated classes, plus the one integration test
  (`tests/integration/test_schema_manager_audit.py`) that needs a real Neo4j instance,
  unchanged in its assertions.
- **Rationale**: FR-011/SC-003 — behavioral equivalence is proven by reusing the same test
  cases against the new code, not by writing a new test suite from scratch that might miss an
  edge case the old one already covered (e.g. duplicate-identifier warnings, missing-endpoint
  relationship errors, orphan-view detection).
- **Alternatives considered**: Write an entirely new test suite — rejected, higher risk of
  silently dropping coverage of an edge case; the existing tests are the proof the ported
  behavior is correct.
