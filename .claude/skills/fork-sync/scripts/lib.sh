# shellcheck shell=bash
# Shared helpers for fork-sync scripts. Source this; do not execute.

set -euo pipefail

FS_SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FS_MANIFEST="${FORK_SYNC_MANIFEST:-$FS_SKILL_DIR/forks.yml}"

# Security-relevant keywords scanned in upstream commit subjects/bodies.
FS_SECURITY_RE='(?i)(CVE-[0-9]{4}-[0-9]+|CWE-[0-9]+|security|vulnerab|exploit|RCE|SSRF|XXE|injection|deserial|sanitiz|auth bypass|privilege escalation|path traversal|hardcoded (secret|password|key)|prototype pollution)'

log()  { printf '  %s\n' "$*" >&2; }
warn() { printf '  ! %s\n' "$*" >&2; }
die()  { printf '  FATAL: %s\n' "$*" >&2; exit "${2:-1}"; }

# workspace root (expanded) --------------------------------------------------
fs_workspace() {
  python3 - "$FS_MANIFEST" <<'PY'
import os, sys, yaml
m = yaml.safe_load(open(sys.argv[1])) or {}
print(os.path.expanduser(m.get("workspace", "~/forks")))
PY
}

# newline-separated list of fork names --------------------------------------
fs_names() {
  python3 - "$FS_MANIFEST" <<'PY'
import sys, yaml
m = yaml.safe_load(open(sys.argv[1])) or {}
for f in (m.get("forks") or []):
    print(f["name"])
PY
}

# merged config for one fork as compact JSON -------------------------------
fs_fork_json() {
  python3 - "$FS_MANIFEST" "$1" <<'PY'
import json, sys, yaml
m = yaml.safe_load(open(sys.argv[1])) or {}
name = sys.argv[2]
d = dict(m.get("defaults") or {})
match = next((f for f in (m.get("forks") or []) if f.get("name") == name), None)
if match is None:
    print(json.dumps({"error": f"fork '{name}' not in manifest"})); sys.exit(0)
LIST_KEYS = ("fix_branches", "private_branches", "security_paths")
out = dict(d)
for k, v in match.items():
    if k in LIST_KEYS:
        out[k] = list(dict.fromkeys((d.get(k) or []) + (v or [])))
    else:
        out[k] = v
for k in LIST_KEYS:
    out.setdefault(k, list(d.get(k) or []))
out.setdefault("upstream_branch", "main")
out.setdefault("dist_branch", "dist")
out.setdefault("test_cmd", "")
req = [k for k in ("upstream", "fork") if not out.get(k)]
if req:
    print(json.dumps({"error": f"fork '{name}' missing keys: {', '.join(req)}"})); sys.exit(0)
print(json.dumps(out))
PY
}

fs_j() { printf '%s' "$1" | jq -r "$2"; }

# do any of the newline-separated paths ($2) match any glob in JSON array $1?
fs_paths_hit() {
  python3 - "$1" <<'PY'
import fnmatch, json, sys
globs = json.loads(sys.argv[1])
files = [l.strip() for l in sys.stdin if l.strip()]
hits = sorted({f for f in files for g in globs
               if fnmatch.fnmatch(f, g) or fnmatch.fnmatch(f, g.lstrip("*/"))})
print(json.dumps(hits))
PY
}

# emit one result object and exit with the mapped code
# usage: fs_emit <json-object>
fs_emit() {
  printf '%s\n' "$1"
  local st; st="$(printf '%s' "$1" | jq -r '.status')"
  case "$st" in
    clean|up_to_date) exit 0 ;;
    conflict)         exit 1 ;;
    test_failure)     exit 2 ;;
    remote_error)     exit 3 ;;
    config_error)     exit 4 ;;
    *)                exit 1 ;;
  esac
}
