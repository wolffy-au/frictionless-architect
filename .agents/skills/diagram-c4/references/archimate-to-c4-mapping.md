# ArchiMate → C4 mapping convention

There is no official ArchiMate↔C4 mapping. This is **our** convention, and
it is the standardisation artifact — the tooling just applies it. Change it
here deliberately, in review, not ad hoc per diagram.

## Principle

The ArchiMate model is the source of truth. A C4 diagram is a *filtered,
relabelled projection* of it at one of two levels:

- **Context** — the system in focus as one box, plus the people and
  external systems it interacts with.
- **Container** — the system in focus opened up into its deployable/runnable
  parts, plus the same external actors.

C4 "Component" level is intentionally **not** generated — component
breakdown belongs in ArchiMate application-layer views (`diagram-archimate`).

## The system in focus

Every C4 diagram is drawn *about one system*. Designate it with
`--system "<name>"`, matching either:

- a `Grouping` whose composed/aggregated children are the containers, or
- an `ApplicationComponent` that has an explicit `c4=system` property.

Elements reachable from the system in focus but not part of it become
external.

## Element mapping

Resolved in this order: explicit `c4` property on the element → type-based
default below.

| `c4` property | Meaning |
|---------------|---------|
| `person` | C4 `Person` |
| `system` | the system in focus (`System_Boundary` at container level, `System` at context level) |
| `external` | C4 `System_Ext` |
| `container` | C4 `Container` |
| `containerDb` | C4 `ContainerDb` |
| `containerQueue` | C4 `ContainerQueue` |
| `ignore` | dropped from the diagram |

Type-based defaults when no `c4` property is set:

| ArchiMate type | Context level | Container level |
|----------------|---------------|----------------|
| `BusinessActor`, `BusinessRole` | `Person` | `Person` |
| `ApplicationComponent` inside the system | (folded into the system box) | `Container` |
| `ApplicationComponent` outside the system | `System_Ext` | `System_Ext` |
| `DataObject`, `Artifact` inside the system | (folded in) | `ContainerDb` |
| `ApplicationService` provided outside the system | `System_Ext` | `System_Ext` |
| `Node`, `Device`, `SystemSoftware` | `ignore` (deployment, not C4 logical) | `ignore` |
| everything else | `ignore` | `ignore` |

"Inside the system" = composed/aggregated (directly or transitively) by the
system in focus, or carrying `c4=container`/`c4=containerDb`.

## Relationship mapping

A C4 `Rel(source, target, "label", "technology")` is emitted for each
ArchiMate relationship whose **both** endpoints survived mapping:

| ArchiMate relationship | C4 edge direction | Default label |
|------------------------|-------------------|---------------|
| `Serving` (A serves B) | `Rel(B, A)` — the served party depends on the server | "uses" |
| `Flow` (A→B) | `Rel(A, B)` | "sends data to" |
| `Triggering` (A→B) | `Rel(A, B)` | "triggers" |
| `Access` (A→store) | `Rel(A, store)` | read/write per access type ("reads from", "writes to", "reads from and writes to") |
| `Realization`, `Assignment`, `Composition`, `Aggregation` | not drawn (structural, already expressed by nesting) | — |
| `Association` | `Rel(A, B)` dashed | "related to" |

Override any label with a `c4-label` property on the relationship, and the
technology string with `c4-technology`.

## Layout

`LAYOUT_WITH_LEGEND()` by default. Add `LAYOUT_TOP_DOWN()` /
`LAYOUT_LEFT_RIGHT()` via `--layout` if the auto-layout is poor.
