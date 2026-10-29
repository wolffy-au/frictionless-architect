# Quickstart: Vendor OSCAL/FedRAMP Files Instead of Submodules

## Prerequisites

- A clone of this repository on this branch, after the migration lands.
- `git` and (on this devcontainer's drvfs-mounted workspace) `sudo` available, per
  `AGENTS.md`'s documented submodule/chmod quirk — see research R7.

## Validate the submodule removal (User Story 1)

```bash
git submodule status
```

Expect exactly one line, for `third_party/it4it`. No line for `oscal`, `oscal-content`, or
`fedramp-automation`.

```bash
git clone --recurse-submodules <this-repo-url> /tmp/fresh-clone && cd /tmp/fresh-clone
```

Expect the clone to fetch only `it4it`'s upstream, and `third_party/oscal`,
`third_party/oscal-content`, `third_party/fedramp-automation` to already contain the
vendored files (not an empty submodule placeholder) — see data-model.md's entity list for
exactly which files.

## Validate provenance (User Story 2)

```bash
ls third_party/oscal/PROVENANCE.md third_party/oscal-content/PROVENANCE.md \
   third_party/fedramp-automation/PROVENANCE.md
```

Expect all three to exist; each must name its upstream repository, a commit SHA, and a
retrieval date (see data-model.md's `ProvenanceRecord`).

## Validate existing tests still pass (User Story 1)

```bash
cd platform && poetry run pytest -k golden_oscal -k oscal
```

Expect the OSCAL schema-alignment checks and the `tests/fixtures/golden-oscal/` golden-
fixture tests to pass unchanged — they read vendored files, and (per research R3) the
golden-fixture `*.provenance.yaml` `source_repo` fields already resolve correctly.

## Validate documentation consistency (User Story 3)

```bash
grep -rn "submodule update --init.*\(oscal-content\|fedramp-automation\)" \
  platform/packages/controls-compliance-catalog/specs/001-oscal-ai-conversion/ \
  third_party/README.md docs/adr/0030-vendor-oscal-reference-content.md
```

Expect no matches — any remaining hit is a stale instruction that still needs updating
(data-model.md's lifecycle + research R4/R6 describe where each fact now lives).

```bash
grep -n "oscal" docs/adr/0030-vendor-oscal-reference-content.md | tail -5
```

Expect a new, dated implementation note recording the submodule → vendored-files switch for
`oscal`/`oscal-content`/`fedramp-automation`, with `it4it` unchanged (research R4).

Re-run the `wiki-librarian` skill after the above lands; confirm
`wiki/oscal-compliance.md`, `wiki/architecture.md`, `wiki/controls-compliance-catalog.md`,
and `wiki/index.md` reflect the updated decision (research R6) rather than hand-editing them.
