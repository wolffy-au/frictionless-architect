---
name: User story
about: File a dev-workflow issue with acceptance criteria and work items
title: ''
labels: ''
assignees: ''

---

## Summary

A clear and concise one- or two-sentence description of what is changing. Link related commits/ADRs. Ex. Move diagrams under `architecture/model/diagrams/` into layer-based subfolders and update every reference to the new paths.

## Why

The motivation — a problem being fixed, a standard being followed, an ADR being implemented. Ex. The flat naming scheme repeated the repo name in every filename and gave no signal of which ArchiMate layer a diagram belonged to. Delete this section if the Summary already covers it.

## What changed / approach

Concrete bullets of the actual change (structure, files, config, schema). Fine to leave as an outline while work is in progress; fill in fully once done. Ex.
- New submodule `third_party/it4it` merged in by `build.py` at build time.
- `views.yaml`, `ARCHITECTURE.md`, and affected ADRs updated to match new paths.

## Work items

A checklist of concrete steps, in the order they'll be done. Mark any already-staged/committed steps `[x]`. Delete this section if the issue is filed after the fact (i.e. "What changed" above already covers it).

- [ ] Ex. `git mv` the affected files into their new location
- [ ] Update path/slug pointers in dependent files
- [ ] Update any ADRs that cite the old paths

## Acceptance criteria

Each item should be objectively verifiable — an exact command plus its expected output/exit code/count, a grep that returns nothing, a specific file/state that must exist. Prefer criteria a reviewer (or CI) can check without re-deriving intent.

- [ ] Ex. `grep -r <old-pattern> <affected-files>` returns nothing.
- [ ] `bash scripts/pre_commit_checks.sh` passes.

## Verification (this work)

Fill in once done: which of the above commands/checks were actually run, and their result. Ex.
- `bash scripts/pre_merge_checks.sh`: lint/pyright/mypy/tests all green.

Delete this section while still in progress.

## Follow-ups (not in this branch)

Anything explicitly deferred, so it isn't silently dropped. Ex. `third_party/it4it/README.md` isn't covered by any `wiki/sources.yaml` topic. Delete if none.

Branch: `<branch-name>`

Claude Code session link, if applicable: https://claude.ai/code/session_...
