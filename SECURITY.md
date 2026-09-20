# Security Policy

## Supported Versions

`frictionless-architect` has not yet cut a versioned release (no tags exist
beyond an internal prototype archive). Only the latest commit on `main`
receives security fixes. Once `cz bump` starts producing `v$version` tags
(see [`RELEASE.md`](RELEASE.md)), this section will be updated with a
supported-versions table.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub
issues, discussions, or pull requests.**

Instead, use GitHub's private vulnerability reporting for this repository:

1. Go to the **Security** tab of this repository.
2. Click **Report a vulnerability** under "Reporting".
3. Fill in as much detail as you can — see below for what's helpful.

Alternatively, open a draft security advisory directly at
[Security → Advisories → New draft security advisory](../../security/advisories/new).

This routes the report privately to the maintainers; it is never public until
a fix is ready and the advisory is published.

### What to include

- A description of the vulnerability and its potential impact.
- Steps to reproduce, or a proof-of-concept if you have one.
- The affected component (e.g. the visualiser API, the ArchiMate/Neo4j model
  pipeline, a specific dependency) and, if known, the commit/tag.
- Any suggested mitigation, if you have one.

### What to expect

- Acknowledgement of your report as soon as reasonably possible.
- An assessment of the issue and, if confirmed, a plan and rough timeline for
  a fix, communicated through the advisory thread.
- Credit in the published advisory, unless you'd prefer to remain anonymous.
- If the report turns out not to be a vulnerability, an explanation of why.

Please give us reasonable time to investigate and fix an issue before any
public disclosure.

## Dependency Vulnerabilities

Dependency vulnerabilities are also monitored automatically via Dependabot
(`.github/dependabot.yml`) and the `vulnerability-remediator` agent. If you
notice a Dependabot alert or a `pip-audit`/SonarCloud security finding that
hasn't been addressed, reporting it through the process above still applies
if it's exploitable in this project; otherwise feel free to open a normal
issue.
