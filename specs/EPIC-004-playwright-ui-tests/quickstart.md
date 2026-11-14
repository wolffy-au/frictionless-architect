# Quickstart: Browser-Level Tests for the HTML UIs

Validates SC-004 (a contributor with no prior setup can run the full UI test suite locally
using only this guide).

## Prerequisites

- `poetry install` already run at the repo root and inside `platform/` (see `AGENTS.md` →
  Toolchain).
- No live LLM provider or Neo4j cluster needed — both surfaces use deterministic stand-ins
  (see `research.md` → "Deterministic stand-ins for external dependencies").

## One-time setup

```bash
poetry run playwright install --with-deps chromium   # root
cd platform && poetry run playwright install --with-deps chromium && cd ..  # platform packages
```

## Run the tests

```bash
# Root-level @ui scenarios (visualiser placeholder page)
poetry run behave tests/features/ --tags=@ui

# Platform packages' existing UI coverage (playground, LLM provider config page)
bash scripts/platform_checks.sh
```

Or run everything the merge gate runs, end to end:

```bash
bash scripts/pre_merge_checks.sh
```

## Expected outcome

- Every in-scope UI surface (playground, LLM provider config page, visualiser placeholder
  page) reports a pass/fail result — never "Skipping…" (SC-003).
- A failing scenario names the page and the error (console error or broken interaction), per
  FR-001/FR-002, and is retried exactly once before being reported as a failure (FR-008).

## Verifying the merge gate actually catches a regression (SC-002)

1. On a throwaway branch, break one in-scope page's main interaction (e.g. comment out the
   playground's convert button's click handler, or the visualiser placeholder's
   schema-summary rendering).
2. Run `bash scripts/pre_merge_checks.sh` (or just the relevant `behave`/`platform_checks.sh`
   command above).
3. Confirm it fails and names the broken page/interaction.
4. Revert the breakage and confirm it passes again.

See `data-model.md` for the visualiser placeholder page's content shape and
`contracts/visualiser-placeholder-page.md` for its route contract.
