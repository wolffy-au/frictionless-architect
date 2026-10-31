# Data Model: Vendor OSCAL/FedRAMP Files Instead of Submodules

## Entities

```plantuml
@startuml
title Vendored file set entities

class VendoredFileSet {
  name: str
  directory: Path
  upstream_repo_url: str
}

class ProvenanceRecord {
  upstream_repo_url: str
  commit_sha: str
  retrieval_date: date
  license: str
}

class LicenseFile {
  path: Path
}

VendoredFileSet "1" *-- "1" ProvenanceRecord : PROVENANCE.md
VendoredFileSet "1" o-- "0..1" LicenseFile : retained upstream LICENSE

class OscalSchemas {
}
class Sp80053CatalogAndBaselines {
}
class FedrampResolvedBaselines {
}

VendoredFileSet <|-- OscalSchemas
VendoredFileSet <|-- Sp80053CatalogAndBaselines
VendoredFileSet <|-- FedrampResolvedBaselines

class GoldenFixtureProvenance <<existing, out of scope>> {
  source_repo: Path
  source_commit: str
}

GoldenFixtureProvenance ..> VendoredFileSet : source_repo still resolves to (R1/R3)
@enduml
```

- **VendoredFileSet**: a named collection of plain, tracked files copied from one upstream
  repository into `third_party/<name>/`, replacing what used to be a git submodule. Three
  instances exist after this feature: `OscalSchemas` (`third_party/oscal`),
  `Sp80053CatalogAndBaselines` (`third_party/oscal-content`), and
  `FedrampResolvedBaselines` (`third_party/fedramp-automation`). `third_party/it4it` is not
  an instance of this entity — it remains a git submodule, out of scope (research R1, R8).
- **ProvenanceRecord**: the content of one `VendoredFileSet`'s `PROVENANCE.md` — upstream
  repository URL, the exact commit SHA the files were copied from, retrieval date, and
  license. Exactly one per `VendoredFileSet` (research R2).
- **LicenseFile**: the upstream `LICENSE`/`LICENSE.md` retained alongside a vendored set,
  because existing docs (`third_party/README.md`, `wiki/oscal-compliance.md`) cite it
  directly as the basis for the public-domain/CC0 license claims (research R5).
- **GoldenFixtureProvenance** (existing entity, not owned by this feature): the
  `source_repo`/`source_commit` fields in `tests/fixtures/golden-oscal/**/*.provenance.yaml`.
  Listed here only to record the relationship this feature must preserve: because
  `VendoredFileSet` keeps the same directory names and relative subpaths a submodule used
  (research R1), every existing `source_repo` value continues to resolve correctly without
  rewriting (research R3) — this feature's work on these files is verification, not a
  mechanical rename pass.

## Lifecycle

```plantuml
@startuml
title third_party/ source lifecycle

[*] --> Submodule : current state (all four sources)

state Submodule {
  state "it4it" as it4it
  state "oscal / oscal-content / fedramp-automation" as ThreeSources
}

Submodule --> it4it : unaffected (ADR-0029, merged by build.py)
it4it --> [*]

ThreeSources --> Deinitialized : git submodule deinit + git rm --cached
Deinitialized --> VendoredFileSet : copy selected files + write PROVENANCE.md (+ LICENSE)
VendoredFileSet --> [*]

VendoredFileSet : plain tracked files under third_party/<name>/
VendoredFileSet : no git submodule registration
@enduml
```

- `it4it` takes no transition in this feature — it stays a `Submodule` (ADR-0029).
- `oscal`, `oscal-content`, and `fedramp-automation` each move `Submodule → Deinitialized →
  VendoredFileSet` exactly once; there is no transition back, and no partial state is
  committed (removal and re-vendoring land together, per FR-001–FR-005).
