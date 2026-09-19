# ArchiMate → C4 mapping convention

There is no official ArchiMate↔C4 mapping. This is **our** convention, and
it is the standardisation artifact — the tooling just applies it. Change it
here deliberately, in review, not ad hoc per diagram.

## Principle

The ArchiMate model is the source of truth. A C4 diagram is a *filtered,
relabelled projection* of it. The standard C4 model has four levels; this
tooling generates two of them:

| C4 level | Generated? | Notes |
|----------|------------|-------|
| **Context** | yes (`--level context`) | the system in focus as one box, plus the people and external systems it interacts with |
| **Container** | yes (`--level container`, default) | the system in focus opened up into its deployable/runnable parts, plus the same external actors |
| **Component** | **no** | intentionally not generated — component breakdown belongs in ArchiMate application-layer views (`diagram-archimate`) |
| **Code** | **no** | out of scope entirely — no ArchiMate layer maps to this level |

Context and Container each have their **own** element mapping (below) —
the same ArchiMate element can resolve to a different C4 macro depending on
which level is being drawn, because Context folds everything inside the
system into one box while Container opens it up.

## The system in focus

Every C4 diagram is drawn *about one system*. Designate it with
`--system "<name>"`, matching either:

- a `Grouping` whose composed/aggregated children are the containers, or
- an `ApplicationComponent` that has an explicit `c4=system` property.

Elements reachable from the system in focus but not part of it become
external.

"Inside the system" (used by both levels below) = composed/aggregated
(directly or transitively) by the system in focus, or carrying
`c4=container`/`c4=containerDb`.

## Element mapping — Context level

`C4_Context.puml` defines exactly 11 element-producing macros — 8 boxes plus
3 boundaries (verified against the upstream `plantuml-stdlib/C4-PlantUML`
source, not just recollection). Every one of them is accounted for below:
either this generator produces it from an ArchiMate source, or it explicitly
does not and why.

**Business layer for Context, application/technology layer for Container.**
Context diagrams are meant to be readable by non-technical stakeholders, so
where a type-based default exists, it favours business-layer ArchiMate
elements (`BusinessActor`/`BusinessRole` → `Person`, `BusinessObject` →
`SystemDb_Ext`, `BusinessService` → `System_Ext`) over the application/
technology-layer elements (`DataObject`, `Artifact`) that drive the
equivalent Container-level boxes. The one deliberate exception: the "system"
boxes (`System`/`SystemDb`/`SystemQueue`) always ground in the actual system
in focus — an `ApplicationComponent`/`Grouping` — because a C4 system has to
be a real, deployable thing, not just a business label.

Resolved in this order: explicit `c4` property on the element → type-based
default below.

| C4 macro | ArchiMate source | How |
|----------|-------------------|-----|
| `Person` | `BusinessActor`, `BusinessRole` | type-based default |
| `Person_Ext` | any element | **explicit only** — `c4=personExt`; no type-based default |
| `System` | the system in focus (`Grouping`/`ApplicationComponent` matched by `--system`/`c4=system`) | implicit — the box for whichever element is the system in focus |
| `SystemDb` | the system in focus | implicit, only if it also carries `c4-kind=db` |
| `SystemQueue` | the system in focus | implicit, only if it also carries `c4-kind=queue` |
| `System_Ext` | `ApplicationComponent` outside the system, `ApplicationService` provided outside the system, `BusinessService` outside the system | type-based default |
| `SystemDb_Ext` | `BusinessObject` outside the system (type-based default) — or any element via `c4=externalDb` | see below |
| `SystemQueue_Ext` | any element | **explicit only** — `c4=externalQueue`; no type-based default |
| `Enterprise_Boundary` | — | **never emitted** — no ArchiMate concept maps here; nothing in the generator produces it |
| `System_Boundary` | — | **not used at context level** — only appears at container level, wrapping the system in focus |
| `Boundary` (generic) | — | **never emitted** — no ArchiMate concept maps here; C4-PlantUML only uses it internally, as what `Enterprise_Boundary`/`System_Boundary` expand into |

`container`/`containerDb`/`containerQueue` overrides have no effect at
context level — inside-elements always fold into the one system box here,
regardless of what they'd be at container level.

`personExt`/`externalQueue` are **explicit-override only** — no ArchiMate type
resolves to them automatically. `BusinessActor`/`BusinessRole` always default
to `Person` regardless of position: there's no reliable "inside the
enterprise" structural signal the way there is for the system boundary
(a person is never *inside* the system box in C4 — the internal/external
split there is organisational, not structural, and this generator has no
ArchiMate concept for "the enterprise" distinct from "the system in focus").
Set `c4=personExt`/`c4=externalQueue` on the specific elements you actually
want drawn that way.

`externalDb` **does** have a type-based default, but only for `BusinessObject`
— a business-layer element is level-appropriate to show as an external
datastore at Context level, where implementation detail is out of scope.
`DataObject`/`Artifact` (application/technology-layer) outside the system
still default to `ignore`, not `SystemDb_Ext` — this model has dozens of
those, and auto-promoting them to boxes on every diagram was tried and
reverted for being noise; they belong in the Container-level `ContainerDb`
mapping instead. Set `c4=externalDb` explicitly on a `DataObject`/`Artifact`
if you specifically want one shown as an external store at Context level
anyway.

`System_Ext` also defaults from `BusinessService` outside the system —
business-layer, and level-appropriate for Context where you'd rather label
an external dependency by the service it provides than by its implementing
component. **Known risk**: if that `BusinessService` is `Realization`d by an
`ApplicationComponent`/`ApplicationService` that's *also* outside the
system, both independently default to `System_Ext` — you'd get two boxes
for what's conceptually one external system. There's no auto-suppression of
the app-layer element for this (it would risk silently dropping
relationships unique to it, which is worse than a duplicate box); mark it
`c4=ignore` explicitly if you want only the `BusinessService` shown.

The system in focus can be drawn as `SystemDb`/`SystemQueue` instead of
`System` by setting a **`c4-kind`** property (`db` or `queue`) on it —
context level only; at container level it's always opened into a
`System_Boundary` regardless of `c4-kind`.

`Enterprise_Boundary` and generic `Boundary` are structurally unreachable
from this generator: there's no `--enterprise`-equivalent grouping concept
in the ArchiMate mapping, and nothing classifies any element to plain
`Boundary`. They exist in the C4-PlantUML vocabulary but not in this
convention — don't expect to see them in generated `.puml`.

Type-based defaults when no `c4` property is set:

| ArchiMate type | Context level |
|----------------|---------------|
| `BusinessActor`, `BusinessRole` | `Person` |
| `ApplicationComponent` inside the system | folded into the system box (no separate macro) |
| `ApplicationComponent` outside the system, `ApplicationService` provided outside the system, `BusinessService` outside the system | `System_Ext` |
| `DataObject`, `Artifact`, `BusinessObject` inside the system | folded into the system box (no separate macro) |
| `DataObject`, `Artifact` outside the system | `ignore` (application/technology-layer implementation detail — see `ContainerDb` at container level instead) |
| `BusinessObject` outside the system | `SystemDb_Ext` (business-layer, level-appropriate for Context) |
| `Node`, `Device`, `SystemSoftware` | `ignore` (deployment, not C4 logical) |
| everything else | `ignore` |

## Element mapping — Container level

Resolved in this order: explicit `c4` property on the element → type-based
default below.

| `c4` property | Meaning |
|---------------|---------|
| `person` | C4 `Person` |
| `personExt` | C4 `Person_Ext` — explicit only |
| `system` | the system in focus → C4 `System_Boundary` (`c4-kind` has no effect at this level) |
| `external` | C4 `System_Ext` |
| `externalDb` | C4 `SystemDb_Ext` — explicit only |
| `externalQueue` | C4 `SystemQueue_Ext` — explicit only |
| `container` | C4 `Container` |
| `containerDb` | C4 `ContainerDb` |
| `containerQueue` | C4 `ContainerQueue` |
| `ignore` | dropped from the diagram |

See the Context section above for why `personExt`/`externalQueue` have no
type-based default, and note that `externalDb`'s Context-only `BusinessObject`
default, and `external`'s Context-only `BusinessService` default, do **not**
apply here — at container level `BusinessObject` and `BusinessService`
outside the system both fall through to `ignore`, same as `DataObject`/
`Artifact`. Business-layer elements are Context's vocabulary, not
Container's — see the "business layer for Context, application layer for
Container" split above.

Type-based defaults when no `c4` property is set:

| ArchiMate type | Container level |
|----------------|----------------|
| `BusinessActor`, `BusinessRole` | `Person` |
| `ApplicationComponent` inside the system | `Container` |
| `ApplicationComponent` outside the system | `System_Ext` |
| `DataObject`, `Artifact`, `BusinessObject` inside the system | `ContainerDb` |
| `ApplicationService` provided outside the system | `System_Ext` |
| `Node`, `Device`, `SystemSoftware` | `ignore` (deployment, not C4 logical) |
| everything else (including `DataObject`/`Artifact`/`BusinessObject`/`BusinessService` outside the system) | `ignore` |

## Element mapping — Component and Code levels

Not generated (see the level table under Principle) — no mapping exists for
either. A `c4` property value implying a component/code-level macro has no
effect; the generator only recognises the Context/Container values listed
above.

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

Edge label resolution: `c4-label` property → the relationship's ArchiMate
`name` → the type default above. Override the technology string with a
`c4-technology` property.

By default every relationship is drawn as `Rel`. Two properties change the
macro:

| Property | Value | Macro |
|----------|-------|-------|
| `c4-direction` | `U`, `D`, `L`, `R` | `Rel_U`/`Rel_D`/`Rel_L`/`Rel_R` — layout hint only, same semantics as `Rel` |
| `c4-birel` | `true` | `BiRel` — draws one bidirectional arrow instead of two overlapping ones |

`c4-birel` wins if both are set. At context level, where multiple
container-level relationships can merge onto the same folded `(source,
target)` pair, the merged edge uses `BiRel` if *any* contributing
relationship asked for it, otherwise the first non-`Rel` direction
requested — set a consistent `c4-direction`/`c4-birel` across the
relationships you expect to merge if you want a predictable result.

### Parallel edges

- **Container level** — distinct labels between the same ordered pair are kept
  as separate arrows; only exact `(source, target, label)` duplicates are
  dropped.
- **Context level** — every interaction with an inside-element folds onto the
  one system box, so many container-level relationships collapse onto the same
  ordered pair. These are **merged into a single `Rel`** whose label lists each
  distinct sub-label on its own line. Give the relationships a shared
  `c4-label` in the model if you want a single tidy phrase instead.

## Layout

`LAYOUT_WITH_LEGEND()` by default. Add `LAYOUT_TOP_DOWN()` /
`LAYOUT_LEFT_RIGHT()` via `--layout` if the auto-layout is poor.
