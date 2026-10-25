## v0.5.0 (2026-10-25)

### Feat

- **skills**: add pr-preflight checklist skill
- **specs**: add conversational Solution Design modelling spec
- **model**: add conversational solution modelling function
- **scripts**: flag non-imperative commit subjects in the message check
- **specs**: re-home specs to two-tier EPIC-*/package scheme (ADR-0004)
- **digital-twin-knowledge-graph**: implement read path and parser
- **digital-twin-knowledge-graph**: generate tasks.md, add consumer task
- **digital-twin-knowledge-graph**: draft read-path spec, align model
- **model**: decompose usage/product/service-realization views
- **model**: make section-B roles canonical, specialise GH #45 roles
- **model**: extend transition view back to the current-state baseline
- **model**: model the gap from architecture-strategy-mvp to future
- **model**: add collaboration-tool input and the PII gateway

### Fix

- **deps**: bump pyarchimate to 2.0.0, pulling pillow 13.0.0
- **skills**: isolate semsearch's fastembed/numpy from the Poetry graph
- ignore false-positive insecure XML parser finding in platform tests
- **model**: wire delivery choreography's Triggering gaps
- **deps**: bump pyarchimate to 2.0.0, pulling pillow 13.0.0
- **deps**: pin filelock >=4.0 in controls-compliance-catalog
- **scripts**: skip platform packages with no src/ yet
- **model**: drop duplicate product/service-realization view slices
- **skills**: strikethrough closed GitHub work packages in diagrams
- **model**: include Outcome on the Stakeholder view
- **model**: close fn-conversational-authoring view's Outcome gap
- **model**: keep build/render on this worktree's platform source

### Refactor

- **model**: split Goal/Outcome motivation chain and close gaps
- **modelling-specification**: make motivation checks configurable

### Perf

- **scripts**: dedupe platform checks and parallelize Snyk in pre-merge

## v0.4.0 (2026-10-17)

### Feat

- **scripts**: let the weekly wiki audit fix the findings you choose

### Fix

- **model**: drop a closed milestone's done work from its view
- **model**: collapse an epic's duplicate child Realization edges
- **model**: run the build and render wrappers in the platform venv
- **model**: keep an epic's own Deliverable link in the roadmap layer

### Refactor

- **modelling-specification**: define COMPONENT_ID once

## v0.3.0 (2026-10-15)

### Feat

- **modelling-specification**: preview as you go; drop the state step
- **modelling-specification**: preview a pending change before Apply
- **model**: add an interface for conversational authoring
- **modelling-specification**: remember the UI settings across loads
- **modelling-specification**: default the apply state to Target
- **modelling-specification**: view picker, pan/zoom, chat fixes
- **modelling-specification**: list views and report the rendered one
- **modelling-specification**: ground proposals in the model
- **model**: add a work-package dependencies view
- **modelling-specification**: add split-screen authoring UI
- **modelling-specification**: synthesize intermediary on accept-pattern
- **modelling-specification**: add conversational model authoring
- **modelling-specification**: check every outcome has its neighbours
- **model**: hand intent-to-model off into the delivery baseline
- **model**: ban self-type words in Motivation/Strategy names
- **model**: influence the authoring requirement from policy-as-code
- **model**: trace the authoring outcome up to its stakeholder
- **model**: add an altitude convention banning tooling vocabulary
- **model**: add the requirement conversational authoring was missing
- **model**: conversational governance realizes executable governance
- **model**: add bfn-conversational-authoring, jointly owned
- **modelling-specification**: add exclude_elements view scoping
- **modelling-specification**: session store + router skeleton
- **model**: conventions.yaml + business-layer wiring, GH #108
- **modelling-specification**: cli + thin wrappers, GH #108
- **modelling-specification**: port build.py/render_diagrams.py, GH #108
- **modelling-specification**: scaffold new platform package, GH #108
- **specs**: generate tasks.md for conversational authoring, GH #108
- **specs**: add plan, research, data model and contracts (GH #108)
- **specs**: add use-case diagrams to authoring user stories
- **specs**: add conversational model authoring spec (GH #108)
- **model**: anchor conversational model authoring (GH #108)
- **model**: add interfaces for the catalog playground and LLM settings
- **portal**: mount the catalog playground at its own prefix
- **model**: add the portal component, interface and package
- **portal**: scaffold the portal host package
- **model**: add context-level viewpoints

### Fix

- **modelling-specification**: re-sanitize SVG at the response sink
- **modelling-specification**: make staleness tests mtime-safe
- **modelling-specification**: fix NOSONAR placement for S2083
- **modelling-specification**: resolve SonarCloud PR #125 findings
- **modelling-specification**: load contexts and viewpoint views
- **modelling-specification**: sanitise the SVG it serves and inlines
- **modelling-specification**: show a plain-text LLM reply, not a 502
- **modelling-specification**: drop stale state wording from the hint
- **llm-provider-config**: test the global default on its own
- **model**: read the migration overview top-to-bottom
- **model**: drop Serving edges superseded by the new function
- **model**: widen Subsystems & Capabilities' scope via include_types
- **model**: widen Strategy's Capability/Outcome scope via include_types
- **model**: scope Value Stream Hand-offs via include_types, not members
- **model**: scope Capability Map via include_types, not members
- **model**: wire conversational authoring into diagrams correctly
- **model**: scope BusinessFunction via include_types, not members
- **model**: embed Conversational Model Authoring into its view/function
- **specs**: update stale art-* ids after do-* rename (GH #108)
- **specs**: record overrides as ADR stubs, not ledger entries (GH #108)
- **model**: close capability/persistence gaps for GH #108
- **model**: link closed issues to the first release after they close
- **model**: tune layout for dense generic viewpoint diagrams
- **deps**: note litellm 1.105.0 still affected in snyk ignores
- **deps**: ignore litellm SNYK-PYTHON-LITELLM-20840174 for 30d

### Refactor

- **model**: rename the baseline Plateau to Current State
- **model**: rename outcome to name the state, not the activity

### Perf

- **scripts**: parallelize pytest and platform package checks

## v0.2.0 (2026-10-11)

### Feat

- **scripts**: add weekly refactor-analyst audit
- **scripts**: run weekly audits as human-in-the-loop agent sessions
- **model**: wire neo4j schema gap to architecture-strategy-mvp
- **model**: rewire unreleased deliverables and flip Gap associations
- **model**: add MVP milestones for remaining business functions
- **model**: adopt generated roadmap Plateaus and Gaps
- **model**: import GitHub roadmap into the migration layer
- **model**: reframe runtime plateaus around team collaboration
- **visualizer**: warn on duplicate sample ids and time the payload
- **visualizer**: retry failed schema loads in the background
- **scripts**: check commit body wrap in the message checker

### Fix

- **scripts**: accept cz bump commits in the message checker
- **scripts**: avoid git log --grep calls the audit denies
- **skills**: type wiki-librarian's verify_wiki.py under mypy strict
- **skills**: type wiki-librarian's wiki_common.py under mypy strict
- **skills**: type wiki-librarian's semsearch.py under mypy strict
- **skills**: type model-archimate's viewpoints.py under mypy strict
- **model**: record accepted exceptions for derived-relationship dupes
- **model**: re-render migration diagrams after Gap association flip
- **model**: name imported Work Packages GH-<n> instead of #<n>
- **model**: return packaging-track elements to their original section
- **visualizer**: log a failed background refresh; clarify spec numbers
- **visualizer**: treat Neo4j driver outages as load failures
- **scripts**: correct wiki audit tool allowlist pattern
- **scripts**: read .snyk policy files in the weekly vuln audit

### Refactor

- **model**: rename artefact-* diagrams/views to dataflow-*
- **model**: consolidate migration work packages onto GH issues
- **scripts**: delegate derivation check to pyArchimate.derivation
- **model**: align Gaps to speckit specs
- **model**: call imported milestone Deliverables unreleased
- **model**: fold packaging Plateaus into the roadmap Plateaus

## v0.1.1 (2026-10-04)

### Fix

- **scripts**: list ignored Snyk findings in the vuln audit
- **scripts**: make weekly audit runs complete without tool denials

## v0.1.0 (2026-10-04)

### Feat

- enforce refresh backoff after a successful refresh
- **controls-compliance-catalog**: richer sample control, sturdier playground scenarios
- **llm-provider-config**: add the GitHub Copilot provider
- **controls-compliance-catalog**: sync scrolling between the Markdown panes
- **controls-compliance-catalog**: highlight differing words within changed lines
- **controls-compliance-catalog**: teach the conversion prompt Trestle's format
- **controls-compliance-catalog**: take OSCAL as YAML in the playground
- **controls-compliance-catalog**: mount LLM settings and link from playground
- **llm-provider-config**: add mountable settings router
- **controls-compliance-catalog**: populate reference Markdown on load and on edit
- **controls-compliance-catalog**: call a real LLM via llm-provider-config
- **llm-provider-config**: add settings, credential and call resolution
- **llm-provider-config**: add package skeleton per ADR-0034
- **controls-compliance-catalog**: add loading state and diff toggle to playground
- **controls-compliance-catalog**: add AI prose-to-candidate-Markdown playground path
- **controls-compliance-catalog**: add OSCAL-to-Markdown playground spike
- **platform**: add platform/ monorepo with controls-compliance-catalog
- **model**: model per-subsystem UI composition and schema-viz UI home (GH #55)
- **model**: add runtime-target skeleton for local compose -> hosted cluster (#55)
- **model**: add technology layer with OSCAL golden-check and persistence boundary
- **model**: add packaging and migration layers
- **model**: pair the golden baseline catalog with its converter input
- **model**: add OSCAL baseline tailoring and split OSCAL views
- **visualizer**: validate sample XML against ArchiMate XSDs with xmlschema
- **ci**: upload coverage reports to Codecov
- **model**: business-layer views, per-outcome value streams and resolved profile catalog (#62)
- **skills**: verify issue acceptance criteria in pr-wrapup before closing
- **skills**: add pr-wrapup skill for post-merge PR/issue cleanup
- **model**: model AI-assisted policy/standard conversion into OSCAL
- **model**: wire OSCAL Assessment Plan into both cadences, add POA&M sidecar
- **model**: add OSCAL Assessment Plan sidecar to the pre-release gate check
- **model**: group outcome-realization processes into BusinessFunctions
- **model**: add ext-trestle external system to OSCAL conversion
- **third_party**: vendor OSCAL/oscal-content/fedramp submodules
- **model**: close the strategy-view ValueStream orphan with coa-* Serving edges
- **model**: suppress the incidental capability-to-capability mesh across 7 views
- **model**: add per-view relationship exclude mechanism
- **model**: wire GH #7 bfn-* into outcome-realization; fix effectiveness capability target
- **model**: add GH #7 vision view for the controls lifecycle
- **devcontainer**: install herdr in post-create
- **model**: vendor pure-IT4IT views into third_party/it4it/views.yaml
- **model**: vendor IT4IT as third_party/it4it submodule (ADR-0029)
- **model**: import IT4IT stream-level outcomes; fix Flow layout on hub streams
- **model**: import IT4IT stakeholder roles, add Stakeholder view
- **model**: nest IT4IT capabilities under their value-stream domain
- **model**: complete the business-layer controls & compliance catalog
- **model**: add business-layer controls & compliance catalog flow
- **diagram-archimate**: default Realization/Serving up, Triggering/Flow right
- **diagram-c4**: map business-layer ArchiMate elements at Context level
- **model**: bring in remaining IT4IT capabilities, refine capability bridges
- **model**: import IT4IT reference descriptions, drop weak drift/problem bridge
- **model**: bridge platform capabilities to IT4IT capabilities
- **model**: import IT4IT value-stream skeleton and derived capability links
- **architecture**: add IT4IT 3.0 alignment skeleton
- **viz**: validate sample XML against ArchiMate schema
- **skills**: add derived-relationship checker, prune redundant edges
- **architecture**: TOGAF Phase A vision views and render_diagrams.py
- **skills**: standard ArchiMate viewpoint reference and conformance gate
- **skills**: render ArchiMate containment as nested notation
- **architecture**: wire principles & constraints to the requirements they shape
- **architecture**: value stream + motivation spine; emit view connections & layout
- **agents**: add adr-auditor for decision-log drift
- **architecture**: unify the model as graph-loadable YAML; add artefact-flow views
- **agents**: retarget wiki-* skills to project-wiki generation
- **agents**: add maintenance subagent fleet
- **sample-data**: C4 container view of the whole architecture ecosystem
- **skills**: add model-archimate, diagram-archimate, diagram-c4
- **skills**: add diagram-plantuml skill
- **agents**: add commit-message skill and commit-auditor agent
- **sample-data**: add ArchiMate sample model and OSCAL resolution diagrams
- improve schema visualizer
- align spec and sample data
- Add comprehensive data model and research tasks documentation for architecture governance
- sample data and minor script changes
- refactor schema manager
- Integrate FSM principles into documentation. Updated constitution with State Management principle and TECHNICAL.md with FSM pattern, API validation, and DDD relation.
- Initialize project structure and configurations

### Fix

- **platform**: clear the Sonar code smells flagged on the PR
- **controls-compliance-catalog**: stop doubling line breaks in output panes
- **architecture**: add sw-keyring to runtime-migration view
- **visualizer**: handle promise rejections in DOMContentLoaded handlers
- **spec**: align sample-file references with Test Model Full.xml
- **model**: realize golden-data objects as their OSCAL business objects
- **visualizer**: reject non-3.0 ArchiMate namespaces on parse
- **model**: fail the build on YAML values truncated by commas
- **model**: quote flow-style descriptions truncated at commas
- **ci**: pin ruff isort classification of the build import
- **ci**: correct Snyk third_party exclusion mechanism
- **ci**: exclude third_party/ from SonarCloud and Snyk scans
- **tests**: sort import build before pyArchimate per ruff I001
- **diagram-archimate**: render a view's declared connections, not recomputed membership
- **ci**: checkout git submodules in CI workflow
- **ci**: correct import order regression from stale local build/ dir
- **ci**: mark pre_commit_checks.sh and pre_merge_checks.sh executable
- **model**: close two relationship gaps found during GH #7 review
- **devcontainer**: relocate git hooks off drvfs and track Spec Kit workflows
- **devcontainer**: install git hooks via sudo to avoid drvfs EPERM
- **devcontainer**: restore lifecycle order and align feature pinning
- **tests**: drop nonexistent tests/security from pytest testpaths
- **security**: validate --root before chdir/open in dev tooling
- **security**: parse XML via defusedxml to prevent XXE
- sanitize schema visualizer table rendering against XSS
- **speckit**: finish .agents -> .claude path migration in build tooling
- darken badge text color to meet WCAG contrast
- **tests**: split composite assertion in viewpoint test
- resolve SonarQube Quality Gate failures for this PR
- **visualizer**: drop dead schema-visualizer HTML route per ADR-0005
- **model**: correct stale capability-count comment in views.yaml
- **model**: drop Financial Management's stray Request-to-Fulfill aggregation
- **model**: drop stray reversed Operate->root Aggregation edge
- **diagram-archimate**: give Access relationships read/write arrowheads
- **model**: correct motivation-layer chain and lint its conventions
- **model**: reframe Constraints as platform limits, not regulation summaries
- **model**: scope views by member list, not type, where IT4IT overlaps
- **model**: retarget control-plane IT4IT bridge to Build/Integrate/Test stage
- **schema**: repair broken Cypher in SchemaManager audit queries
- **tests**: avoid Sonar S5863 tautological-assertion flag in det_id test
- **pre-commit**: run ruff via poetry instead of a separately pinned rev
- **visualizer**: update TemplateResponse call for starlette 1.x API
- **ci**: skip Quality Gate polling for plain develop pushes
- **deps**: bump fastapi to 0.141.x to resolve high-severity starlette vulns
- sort test_model_build.py imports per ruff 0.16.8 isort rules
- **config**: resolve model-archimate/scripts imports for pyright/mypy
- **devcontainer**: backfill Spec Kit scaffolding when upgrade hits drvfs EPERM
- **skills**: autoscale semsearch embedding to available RAM
- **skills**: batch semsearch embedding; run wiki tools via poetry
- **build**: use the scm version provider for commitizen
- minor script improvements

### Refactor

- **llm-provider-config**: suppress errors on best-effort chmod
- **controls-compliance-catalog**: move conversion prompt to prompts.yaml
- reduce cognitive complexity of SchemaPayloadService._build_payload
- **app**: rename shared FastAPI entry point off the visualiser name
- **model**: consolidate the duplicate controls-lifecycle vision view
- **model**: skip unchanged views in render_diagrams.py
- **model**: number vision diagrams to match TOGAF Phase A order
- **model**: drop redundant realization labels; clarify capability nesting
- **model**: reclassify cross-cutting views to standard viewpoints
- **diagrams**: move diagrams into ArchiMate-layer subfolders
- **model**: drop redundant frictionless-architect-/it4it- prefixes from alignment diagram
- **model**: fold per-stream value stream views into one nested view
- **schema**: drop RelationshipFact node in favour of edge-only relationships
- **skills**: make wiki-librarian tools testable; add --root
- **architecture**: one error channel + O(n) view scoping in build.py
- Enhance cross-referencing between Constitution and Technical Guidelines
- Enhance TECHNICAL.md with tool-agnostic descriptions and automated coverage goals

### Perf

- **tests**: stop paying neo4j's 30s timeout 5x per test run
