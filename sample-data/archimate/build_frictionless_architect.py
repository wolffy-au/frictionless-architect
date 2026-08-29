#!/usr/bin/env python3
"""Build the Frictionless Architecture Platform ArchiMate model.

Regenerates ``frictionless-architect.archimate`` from code so the model stays
reproducible and reviewable. The model is the single source of truth; the C4
Container diagram is a projection of it (see ``.agents/skills/diagram-c4``).

    poetry run python sample-data/archimate/build_frictionless_architect.py

The platform is modelled as six subsystems rather than fifteen fine-grained
capabilities — the finer decomposition is recorded in each subsystem's
description ("Includes: ..."). A ``Grouping`` marked ``c4=system`` composes the
subsystems (``ApplicationComponent``) and the shared stores (``DataObject``);
``BusinessRole`` elements become C4 ``Person``; ``ApplicationComponent`` elements
outside the grouping become ``System_Ext``.
"""

from __future__ import annotations

from pathlib import Path

from pyArchimate import Model

OUT = Path(__file__).with_name("frictionless-architect.archimate")

m = Model("frictionless-architect")

# --------------------------------------------------------------------------
# System in focus
# --------------------------------------------------------------------------
platform = m.add(
    concept_type="Grouping",
    name="Frictionless Architecture Platform",
    desc="Governs architecture from authored policy through to BAU control effectiveness.",
)
platform.prop("c4", "system")


def container(name: str, desc: str, includes: str = ""):
    e = m.add(concept_type="ApplicationComponent", name=name, desc=desc)
    if includes:
        e.prop("includes", includes)
    m.add_relationship(rel_type="Composition", source=platform, target=e)
    return e


def store(name: str, desc: str):
    e = m.add(concept_type="DataObject", name=name, desc=desc)
    m.add_relationship(rel_type="Composition", source=platform, target=e)
    return e


def person(name: str, desc: str):
    return m.add(concept_type="BusinessRole", name=name, desc=desc)


def ext(name: str, desc: str):
    return m.add(concept_type="ApplicationComponent", name=name, desc=desc)


def serves(provider, consumer, label: str = ""):
    r = m.add_relationship(rel_type="Serving", source=provider, target=consumer)
    if label:
        r.prop("c4-label", label)
    return r


def flow(src, tgt, label: str):
    r = m.add_relationship(rel_type="Flow", source=src, target=tgt)
    r.prop("c4-label", label)
    return r


def access(comp, data, mode: str, label: str):
    r = m.add_relationship(rel_type="Access", source=comp, target=data, access_type=mode)
    r.prop("c4-label", label)
    return r


def assoc(src, tgt, label: str):
    r = m.add_relationship(rel_type="Association", source=src, target=tgt)
    r.prop("c4-label", label)
    return r


# --------------------------------------------------------------------------
# Subsystems (C4 containers)
# --------------------------------------------------------------------------
catalog = container(
    "Controls & Compliance Catalog",
    "Authors custom policies and standards and converts them to OSCAL Catalogs and Profiles.",
    "Policy & Standards Authoring Workspace (Trestle Markdown catalogs); "
    "Trestle Conversion Service (Markdown <-> OSCAL Catalogs & Profiles).",
)
library = container(
    "Reusable Architecture Library",
    "Composable patterns, blueprints and solution designs with OSCAL references, plus threat modelling.",
    "Architecture Pattern Library (technology-agnostic; -> OSCAL Profiles); "
    "Implementation Blueprint Library (parent/child of patterns; -> OSCAL Components); "
    "Solution Design Composer (SolutionComponents under a SolutionDesign; -> OSCAL SSP); "
    "Threat Modelling Service (attaches threats & mitigations).",
)
twin_kg = container(
    "Digital Twin & Knowledge Graph",
    "Maintains the Architecture Knowledge Graph: an intent plane and a current-state digital twin plane.",
    "Digital Twin Ingestion Service (builds the current-state plane from live infra & pipeline data).",
)
governance = container(
    "Architecture Governance",
    "Models candidate future-state / solution options, evaluates them, decides, and archives the rest with reasons.",
    "Future-State & Options Modeller (one or more candidate architectures, e.g. RFP vendor responses); "
    "Architecture Governance Service (comparative evaluation, impact assessment, ADR decisions, "
    "archival of rejected options with rationale).",
)
assurance = container(
    "Conformance & Drift Assurance",
    "Enforces controls at release, monitors effectiveness in BAU, and detects and reports architecture drift.",
    "Controls Enforcement Gate (release-time); Controls Effectiveness Monitor (BAU); "
    "Drift & Deviation Engine (intent vs twin); Architecture Drift Dashboard & Backlog.",
)
modelling = container(
    "Modelling & Specification",
    "Out-of-the-box ArchiMate / C4 / UML modelling, and generation of development specifications.",
    "Modelling & Notation Engine (ArchiMate, C4, UML); "
    "Specification Generator (specs from patterns, blueprints & designs for spec-driven development).",
)

# --------------------------------------------------------------------------
# Shared stores
# --------------------------------------------------------------------------
oscal_repo = store(
    "OSCAL Repository",
    "OSCAL Catalogs, Profiles, Components and SSPs.",
)
pb_repo = store(
    "Pattern & Blueprint Repository",
    "Architecture patterns, implementation blueprints and solution designs.",
)
akg = store(
    "Architecture Knowledge Graph",
    "One graph store, two planes: Architecture Intent and Current-State Digital Twin.",
)
framework_packs = store(
    "Framework Pack Library",
    "NIST / FedRAMP baselines; ArchiMate / C4 / UML metamodels.",
)

# --------------------------------------------------------------------------
# People
# --------------------------------------------------------------------------
ea = person("Enterprise Architect", "Owns principles, target patterns, options and governance decisions.")
sa = person("Solution Architect", "Composes blueprints into solution designs.")
sec = person("Security Architect / Threat Modeller", "Runs threat models over patterns, blueprints and designs.")
dev = person("Developer", "Consumes generated specifications for delivery.")
compliance = person("Compliance Officer / Auditor", "Authors control content and verifies traceability.")
ops = person("Platform Operations (BAU)", "Watches control effectiveness and drift in run.")

# --------------------------------------------------------------------------
# External systems
# --------------------------------------------------------------------------
scm = ext("Source Control", "Git repositories for specifications and delivery code.")
cicd = ext("CI/CD Pipeline", "Builds, tests and releases; invokes the enforcement gate.")
cloud = ext("Cloud & Infrastructure Platforms", "Runtime platforms whose live state feeds the digital twin.")
itsm = ext("IT Service Management / Backlog", "Delivery backlog and ticketing (e.g. Jira).")
reg_sources = ext("Regulatory Content Sources", "Upstream NIST OSCAL content and FedRAMP baselines.")
llm = ext("LLM Provider", "Language model used for drafting specs, ADRs, evaluations and threat narratives.")
vendor_rfp = ext(
    "RFP / Vendor Submissions",
    "Requests for proposal and competing vendor solution responses assessed at engagement time.",
)

# --------------------------------------------------------------------------
# People -> platform (Serving: subsystem serves the person)
# --------------------------------------------------------------------------
serves(catalog, compliance, "authors control content in")
serves(library, ea, "curates patterns in")
serves(library, sa, "composes blueprints & designs in")
serves(library, sec, "runs threat models in")
serves(governance, ea, "models options & records decisions in")
serves(governance, compliance, "verifies traceability in")
serves(assurance, ea, "reviews drift in")
serves(assurance, sa, "reviews drift in")
serves(assurance, ops, "watches control effectiveness & drift in")
serves(assurance, compliance, "watches control status in")
serves(modelling, ea, "models with")
serves(modelling, sa, "models with")
serves(modelling, dev, "consumes specifications from")

# --------------------------------------------------------------------------
# Authoring / OSCAL chain
# --------------------------------------------------------------------------
flow(reg_sources, catalog, "baseline catalogs")
access(catalog, oscal_repo, "Write", "writes Catalogs & Profiles")
access(catalog, framework_packs, "Read", "reads NIST / FedRAMP packs")

# --------------------------------------------------------------------------
# Reusable Architecture Library
# --------------------------------------------------------------------------
access(library, oscal_repo, "ReadWrite", "references Profiles & Components; emits SSP")
access(library, pb_repo, "Write", "stores patterns, blueprints & designs")
access(library, akg, "Write", "publishes approved patterns (intent plane)")
serves(llm, library, "requests threat narratives from")

# --------------------------------------------------------------------------
# Digital Twin & Knowledge Graph
# --------------------------------------------------------------------------
flow(cloud, twin_kg, "current-state configuration")
flow(cicd, twin_kg, "deployment events")
access(twin_kg, akg, "Write", "writes the digital twin plane")

# --------------------------------------------------------------------------
# Architecture Governance: options, evaluation, decisions
# --------------------------------------------------------------------------
flow(vendor_rfp, governance, "candidate solution inputs")
access(
    governance,
    akg,
    "ReadWrite",
    "reads intent & twin for impact; writes decisions, impacts & archived options (intent plane)",
)
assoc(governance, library, "governs patterns & assesses solution designs")
flow(governance, library, "hands chosen solution to Composer for detailed design")
serves(llm, governance, "requests ADR & evaluation drafts from")
serves(modelling, governance, "renders candidate models with")

# --------------------------------------------------------------------------
# Conformance & Drift Assurance
# --------------------------------------------------------------------------
access(assurance, oscal_repo, "Read", "reads control baselines & expected controls")
flow(cicd, assurance, "release candidate")
flow(assurance, cicd, "gate decision")
flow(cloud, assurance, "runtime control signals")
access(assurance, akg, "ReadWrite", "diffs intent vs twin; writes effectiveness evidence")
flow(assurance, itsm, "remediation backlog items")

# --------------------------------------------------------------------------
# Modelling & Specification
# --------------------------------------------------------------------------
access(modelling, framework_packs, "Read", "reads ArchiMate / C4 / UML metamodels")
access(modelling, pb_repo, "Read", "reads patterns, blueprints & designs")
serves(llm, modelling, "requests draft specifications from")
flow(modelling, scm, "specifications")

m.write(str(OUT))
print(f"wrote {OUT}  ({len(m.elements)} elements, {len(m.relationships)} relationships)")
