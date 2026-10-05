# Contract: importer CLI

```bash
poetry run python architecture/model/import_gh_roadmap.py [--repo OWNER/NAME] [--check]
poetry run python architecture/model/build.py   # then merges the layer
```

| Option | Meaning |
|---|---|
| `--repo OWNER/NAME` | Repository to read. Default: the one `gh repo view` resolves for the cwd. |
| `--check` | Fetch and render, write nothing; exit 1 if the on-disk layer differs from what a run would write. For CI or a pre-merge gate. |

## Behaviour

- Reads GitHub only through `gh` (argv list, no shell). Needs no new credential.
- Renders all three files in memory, then replaces them atomically. It never writes a partial layer.
- Prints one summary line, e.g. `wrote gh-roadmap: 2 milestones, 0 releases, 1 unreleased deliverable, 3 work packages, 0 triggering`, and `unchanged` when the bytes already match.

## Run sequence

```plantuml
@startuml
title Refreshing the roadmap layer
actor Developer
participant "import_gh_roadmap.py" as Imp
participant "gh CLI" as GH
database "GitHub" as API
collections "gh-roadmap/*.yaml" as Layer
participant "build.py" as Build
participant "validate.py" as Val

Developer -> Imp : run
Imp -> GH : gh api (milestones, releases)
GH -> API : REST
API --> GH : JSON
GH --> Imp : JSON
Imp -> GH : gh api graphql (issues, closedAt, parent, blockedBy)
GH -> API : GraphQL
API --> GH : JSON
GH --> Imp : JSON
alt any call fails
  Imp --> Developer : exit 2, nothing written
else all calls succeed
  Imp -> Imp : scope, map, attach Deliverables, derive links, render
  Imp -> Layer : write temp files, then replace
  Imp --> Developer : summary line, exit 0
end

Developer -> Build : run
Build -> Layer : load as a merged layer
Build -> Build : det_id() over every id
Build -> Val : check relationship legality and integrity
Val --> Build : VALID
Build --> Developer : model XML, 0 errors
@enduml
```

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Layer written, or already up to date; with `--check`, layer is current |
| 1 | `--check` only: layer is stale |
| 2 | `gh` missing, not authenticated, rate-limited or errored, or its output was unparseable. Stderr names the failing call and the fix. **No file touched.** (Same code `build.py` uses for input errors.) |

## Contract with `build.py`

`build.py` loads `gh-roadmap/{elements,relationships,views}.yaml` as an optional
layer: a missing directory is skipped silently, and a present-but-malformed file is a
normal `build.py` error. Nothing in `build.py` depends on the importer having run.
