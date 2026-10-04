#!/bin/bash
# Report-only run of the vulnerability-remediator agent (.claude/agents/vulnerability-remediator.md).
# Writes the advisory table to .cache/vuln-audit/<date>.md; bumps no dependency, edits no lock file, opens no PR.
# Runs in the CURRENT checkout, not a temp worktree: the scanners need the Poetry venv and gh/Snyk auth.
# Schedule it from cron / a systemd timer / Windows Task Scheduler, or run it by hand.
#
# Usage: scripts/vuln_audit_weekly.sh

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_agent_report.sh"

AGENT=vulnerability-remediator
OUT_NAME=vuln-audit
MODE=root
TOOLS="Read,Grep,Glob,Bash(gh api repos/*/dependabot/alerts*),Bash(poetry run pip-audit:*),Bash(poetry run snyk --version),Bash(poetry run snyk test:*),Bash(poetry run snyk code test:*),Bash(poetry show:*),Bash(poetry check:*),Bash(git log:*),Bash(git -C * log:*)"
# pip-audit would audit whatever is installed in the venv, and platform/ has no venv of its own. Instead export each
# lock's pinned deps to a file and audit that (the agent may not create files itself). Exports never touch the venv.
cd "$(git rev-parse --show-toplevel)"
mkdir -p ".cache/$OUT_NAME"
ROOT_REQS=".cache/$OUT_NAME/root-requirements.txt"
PLATFORM_REQS=".cache/$OUT_NAME/platform-requirements.txt"
trap 'rm -f "$ROOT_REQS" "$PLATFORM_REQS"' EXIT
poetry export -f requirements.txt --without-hashes --all-groups > "$ROOT_REQS" \
  || agent_fail "could not export poetry.lock (is poetry-plugin-export installed?)"
poetry -C platform export -f requirements.txt --without-hashes --all-groups > "$PLATFORM_REQS" \
  || agent_fail "could not export platform/poetry.lock"

TASK="Follow your Steps 2-3 only: skip Steps 1 and 4-9. Gather advisories from every scanner that is available; \
if one is unavailable, say so in the report rather than failing. Cover BOTH dependency sets: the root (pyproject.toml, \
poetry.lock) and platform/ (platform/pyproject.toml, platform/poetry.lock). \
$AGENT_BASH_RULE \
Run these, one call each: 'gh api repos/{owner}/{repo}/dependabot/alerts'; 'poetry run pip-audit -r $ROOT_REQS --no-deps --disable-pip' (root); \
'poetry run pip-audit -r $PLATFORM_REQS --no-deps --disable-pip' (platform/); 'poetry run snyk --version'; then, if snyk is \
present, 'poetry run snyk test --include-ignores' (root), 'poetry run snyk test --file=platform/poetry.lock --package-manager=poetry \
--include-ignores' (platform/) and 'poetry run snyk code test --include-ignores' (first-party code). Open findings are \
the vulnerabilities; list every ignored finding separately with its ID, package/file, severity and ignore reason and expiry, \
so the ignores can be reviewed. The CLI does not print policy-file reasons or expiries: Read '.snyk' and 'platform/.snyk' and \
take them from there (flag any expiring within 14 days or already expired), and list the '.snyk' path excludes too. Only \
ignores absent from those files are Snyk-UI-managed; say 'not shown' for those. Known, expected caveats: pip-audit skips the editable local packages (controls-compliance-catalog, llm-provider-config) because \
they are not on PyPI, so note it in one line without treating it as a gap; Snyk may warn about missing lockfile metadata for \
jaraco.classes/context/functools (keyring dependencies, which ARE in the platform graph: Snyk cannot match the dotted names to \
the lock's dashed ones), so say Snyk cannot check them and pip-audit covers them. Report which dependency set and scanner each finding came from. Do not read .secrets/, run poetry add/lock/update, or install anything. Instead of remediating, give the Output \
advisory table (advisory ID | package/file | severity | current -> fixed | recommended action) plus the unresolved \
list, under '## Findings'."

agent_report_run
