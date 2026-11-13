---
title: 'Architecture Views & Diagrams: Application Layer'
generated: '2026-11-13'
generator: claude-sonnet-5
sources:
- architecture/model/README.md
- architecture/model/diagrams/application/1-policy-conversion.puml
- architecture/model/diagrams/application/1-policy-conversion.svg
- architecture/model/diagrams/application/2-pattern-solution-design.puml
- architecture/model/diagrams/application/2-pattern-solution-design.svg
- architecture/model/diagrams/application/3-control-assurance.puml
- architecture/model/diagrams/application/3-control-assurance.svg
- architecture/model/diagrams/application/catalog-structure.puml
- architecture/model/diagrams/application/catalog-structure.svg
- architecture/model/diagrams/application/cooperation-standard/architecture-governance.puml
- architecture/model/diagrams/application/cooperation-standard/architecture-governance.svg
- architecture/model/diagrams/application/cooperation-standard/conformance-drift-assurance.puml
- architecture/model/diagrams/application/cooperation-standard/conformance-drift-assurance.svg
- architecture/model/diagrams/application/cooperation-standard/controls-compliance-catalog.puml
- architecture/model/diagrams/application/cooperation-standard/controls-compliance-catalog.svg
- architecture/model/diagrams/application/cooperation-standard/digital-twin-knowledge-graph.puml
- architecture/model/diagrams/application/cooperation-standard/digital-twin-knowledge-graph.svg
- architecture/model/diagrams/application/cooperation-standard/llm-provider-config.puml
- architecture/model/diagrams/application/cooperation-standard/llm-provider-config.svg
- architecture/model/diagrams/application/cooperation-standard/modelling-specification.puml
- architecture/model/diagrams/application/cooperation-standard/modelling-specification.svg
- architecture/model/diagrams/application/cooperation-standard/pii-gateway.puml
- architecture/model/diagrams/application/cooperation-standard/pii-gateway.svg
- architecture/model/diagrams/application/cooperation-standard/reusable-architecture-library.puml
- architecture/model/diagrams/application/cooperation-standard/reusable-architecture-library.svg
- architecture/model/diagrams/application/cooperation-standard/schema-visualizer-api.puml
- architecture/model/diagrams/application/cooperation-standard/schema-visualizer-api.svg
- architecture/model/diagrams/application/cooperation/architecture-governance.puml
- architecture/model/diagrams/application/cooperation/architecture-governance.svg
- architecture/model/diagrams/application/cooperation/conformance-drift-assurance.puml
- architecture/model/diagrams/application/cooperation/conformance-drift-assurance.svg
- architecture/model/diagrams/application/cooperation/controls-compliance-catalog.puml
- architecture/model/diagrams/application/cooperation/controls-compliance-catalog.svg
- architecture/model/diagrams/application/cooperation/digital-twin-knowledge-graph.puml
- architecture/model/diagrams/application/cooperation/digital-twin-knowledge-graph.svg
- architecture/model/diagrams/application/cooperation/llm-provider-config.puml
- architecture/model/diagrams/application/cooperation/llm-provider-config.svg
- architecture/model/diagrams/application/cooperation/modelling-specification.puml
- architecture/model/diagrams/application/cooperation/modelling-specification.svg
- architecture/model/diagrams/application/cooperation/pii-gateway.puml
- architecture/model/diagrams/application/cooperation/pii-gateway.svg
- architecture/model/diagrams/application/cooperation/reusable-architecture-library.puml
- architecture/model/diagrams/application/cooperation/reusable-architecture-library.svg
- architecture/model/diagrams/application/cooperation/schema-visualizer-api.puml
- architecture/model/diagrams/application/cooperation/schema-visualizer-api.svg
- architecture/model/diagrams/application/dataflow-assurance-spec.puml
- architecture/model/diagrams/application/dataflow-assurance-spec.svg
- architecture/model/diagrams/application/dataflow-library.puml
- architecture/model/diagrams/application/dataflow-library.svg
- architecture/model/diagrams/application/dataflow-oscal-resolve.puml
- architecture/model/diagrams/application/dataflow-oscal-resolve.svg
- architecture/model/diagrams/application/dataflow-oscal.puml
- architecture/model/diagrams/application/dataflow-oscal.svg
- architecture/model/diagrams/application/dataflow-twin-governance.puml
- architecture/model/diagrams/application/dataflow-twin-governance.svg
- architecture/model/diagrams/application/modelling-specification-cooperation.puml
- architecture/model/diagrams/application/modelling-specification-cooperation.svg
- architecture/model/diagrams/application/strategy-drift.puml
- architecture/model/diagrams/application/strategy-drift.svg
- architecture/model/diagrams/application/structure.puml
- architecture/model/diagrams/application/structure.svg
- architecture/model/diagrams/application/usage/architecture-governance.puml
- architecture/model/diagrams/application/usage/architecture-governance.svg
- architecture/model/diagrams/application/usage/conformance-drift-assurance.puml
- architecture/model/diagrams/application/usage/conformance-drift-assurance.svg
- architecture/model/diagrams/application/usage/controls-compliance-catalog.puml
- architecture/model/diagrams/application/usage/controls-compliance-catalog.svg
- architecture/model/diagrams/application/usage/digital-twin-knowledge-graph.puml
- architecture/model/diagrams/application/usage/digital-twin-knowledge-graph.svg
- architecture/model/diagrams/application/usage/llm-provider-config.puml
- architecture/model/diagrams/application/usage/llm-provider-config.svg
- architecture/model/diagrams/application/usage/modelling-specification.puml
- architecture/model/diagrams/application/usage/modelling-specification.svg
- architecture/model/diagrams/application/usage/pii-gateway.puml
- architecture/model/diagrams/application/usage/pii-gateway.svg
- architecture/model/diagrams/application/usage/reusable-architecture-library.puml
- architecture/model/diagrams/application/usage/reusable-architecture-library.svg
- architecture/model/diagrams/application/usage/schema-visualizer-api.puml
- architecture/model/diagrams/application/usage/schema-visualizer-api.svg
- architecture/model/views-viewpoints.yaml
- architecture/model/views.yaml
---

> Generated by `wiki-librarian` from the sources above. Edit `wiki/sources.yaml`
> and rebuild rather than editing this page.

This topic covers the application-layer ArchiMate views rendered under
`architecture/model/diagrams/application/` — the bounded-context Application
Cooperation views (GH #129), the application-usage slices (GH #105 follow-up),
and the Controls & OSCAL data-flow views. It was split out of [Architecture
Views & Diagrams: Vision, Business & Viewpoints](architecture-diagrams.md)
once that page passed ~500 lines; that page covers the vision/business sets,
the generic per-viewpoint views, and the general bounded-context split
mechanism. For the Implementation & Migration and Technology-layer views, see
[Architecture Views & Diagrams: Platform, Migration &
Rendering](architecture-diagrams-platform.md). For what the model itself
*means*, see [Architecture Model](architecture-model.md).

## Application Cooperation (GH #129 bounded-context split)

`view-application-cooperation` (`application/cooperation/<context>`, in
`views.yaml`) pulls same-layer neighbours only, so each per-context diagram
stays Application-layer. It is the one to read.
`view-application-cooperation-standard` keeps the literal viewpoint with
unrestricted neighbours, for comparison
(`architecture/model/views.yaml`; `architecture/model/views-viewpoints.yaml`).
Both use the general `split_by: context` / `include_neighbours: true`
mechanism described on [Architecture Views & Diagrams: Vision, Business &
Viewpoints](architecture-diagrams.md#bounded-context-views-gh-129): each
renders one `<diagram>/<context>.puml` per bounded context actually on it,
pulling in any directly-connected element from another context so a
cross-context edge still has both endpoints on the page.

## Application-usage slices (GH #105 follow-up, 2026-10-18)

Four more capability-scoped diagrams render under `diagrams/application/`,
mirroring the business-layer numbered-slice pattern (see [Architecture Views
& Diagrams: Vision, Business & Viewpoints](architecture-diagrams.md)) but cut
from the `application_usage` viewpoint instead:

| View | Diagram | Covers |
|---|---|---|
| Application — 1. Policy-to-OSCAL Conversion | `application/1-policy-conversion` | Application-layer slice 1 |
| Application — 2. Pattern, Blueprint & Solution Design | `application/2-pattern-solution-design` | Application-layer slice 2 |
| Application — 3. Control Assurance | `application/3-control-assurance` | Application-layer slice 3 |
| Application — Strategy & Drift | `application/strategy-drift` | Application-layer strategy/drift slice |

They were first generated as three identical variants each (also under
`diagrams/product/` and `diagrams/service-realization/`), but the Product and
Service Realization copies were byte-for-byte identical to the
`application_usage` ones — only the title differed — because the model has
no `Product`/`Contract`/`Value`/`Service` elements yet to make those
viewpoints actually render differently. The duplicate copies were dropped,
keeping only the `application/` slices
(`architecture/model/diagrams/application/`; git history: "decompose usage/
product/service-realization views" followed by "drop duplicate product/
service-realization view slices").

The rest of the application-layer catalogue — `catalog-structure`,
`structure`, `modelling-specification-cooperation`,
`dataflow-assurance-spec`, `dataflow-library`, `dataflow-twin-governance` —
is covered under "Application structure and remaining data-flow views"
below.

## The Controls & OSCAL data-flow views

The Controls & OSCAL stage is drawn as **two** application-layer views
(`architecture/model/views.yaml:484-529`):

- `Data Flow — Controls & OSCAL` (`application/dataflow-oscal`, renamed from
  `artefact-oscal` 2026-10-08, GH #109 / ADR-0036). The LLM
  Provider serves AI-assisted Markdown conversion, and Trestle serves the
  round-trip into an OSCAL Catalog. The view is conversion only: its one
  golden-dataset object is the baseline catalog, the expected output for the
  Regulatory Standard Document it converts. Since ADR-0034 the view also shows the
  shared LLM Provider Configuration component, associated with the LLM Provider
  ("configures provider/model & resolves credentials for calls to"), and the
  container view carries the same edge
  (`architecture/model/diagrams/application/dataflow-oscal.puml`,
  `architecture/model/diagrams/c4/container.puml`).
- `Data Flow — OSCAL Profile Resolution`
  (`application/dataflow-oscal-resolve`, renamed from `artefact-oscal-resolve`). OSCAL Baseline Tailoring reads the
  OSCAL Catalog and writes the OSCAL Profile, and Trestle's `profile-resolve`
  turns the profile and its catalog into the **Resolved OSCAL Profile
  Catalog**. OSCAL Catalog Generation is repeated from the first view as the
  Catalog's writer. Trestle's round-trip `Serving` of that function is excluded
  here, because the first view already shows it. The golden-dataset baseline
  profile and FedRAMP's pre-resolved baselines sit alongside as validation
  data. The split follows GH #61 decision A: each OSCAL object appears with
  its writer and every reader (`architecture/model/views.yaml` comments).

The other three `Data Flow — …` views use the same `application_cooperation`
viewpoint for the remaining stages, each a `members`-scoped (not
`include_types`) cut (`architecture/model/views.yaml`):

| View | Diagram | Covers |
|---|---|---|
| Data Flow — Library & Design | `application/dataflow-library` | `sub-library`'s pattern/blueprint/threat-model authoring and solution-design composition, reading the resolved OSCAL catalog |
| Data Flow — Digital Twin & Governance | `application/dataflow-twin-governance` | `sub-twin`, `sub-governance`, `sub-library` and `sub-modelling` together: twin ingest, ADR/option governance, the conversational-authoring/notation-engine functions, and the CI/CD and RFP external touchpoints |
| Data Flow — Assurance & Specification | `application/dataflow-assurance-spec` | `sub-assurance` and `sub-modelling`: spec generation, build supervision, the enforcement gate, effectiveness monitoring and drift, against the SCM/CI/CD/ITSM externals |

See [Architecture Views & Diagrams: Vision, Business & Viewpoints](architecture-diagrams.md)
for the C4 diagrams these application-layer data flows correspond to at the
container level.

## Application structure

- `application/structure` (`view-application-structure`, Application
  Structure viewpoint, GH #105) is the generic, whole-platform sweep —
  `include_types` on `ApplicationComponent`/`ApplicationInterface`/
  `ApplicationCollaboration`/`DataObject`, so a new one appears
  automatically (`architecture/model/views-viewpoints.yaml`).
- `application/catalog-structure` (`view-application-structure-catalog`) is
  the single-application zoom of the same viewpoint, scoped to
  `sub-catalog` alone: `ApplicationFunction` isn't a viewpoint-legal element
  here, so ownership is shown via `sub-catalog → do-*` `Aggregation`s instead
  (`architecture/model/views.yaml`).
- `application/modelling-specification-cooperation`
  (`view-application-cooperation-modelling-specification`) plays the same
  single-application-zoom role for the Application Cooperation viewpoint,
  scoped to `modelling-specification` alone — deliberately distinct from the
  whole-platform per-context `cooperation`/`cooperation-standard` sweeps
  above, which pull in every one-hop neighbour regardless of layer
  (`architecture/model/views.yaml`).

Not covered by current sources: per-view rationale comments for this group
beyond what `views.yaml`'s own inline comments give.
