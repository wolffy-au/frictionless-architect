# slice-3-full

Complete, unmodified copies of every vendored source file — the full
counterpart to `slice-1-minimal`'s three-control excerpt.

## Contents

- `catalog/NIST_SP-800-53_rev5_catalog.json` — the entire SP 800-53 Rev 5
  OSCAL catalog (all 20 control families, full verbatim prose).
- `profiles/` — all four SP 800-53B baseline profiles: LOW, MODERATE, HIGH,
  and PRIVACY (PRIVACY is not present at slice-1 scale).
- `fedramp/` — all three FedRAMP baselines' resolved-profile-as-catalog XML,
  complete with `<back-matter>` (dropped in the slice-1 excerpts for size).
- `csf/NIST_CSF_v2.0_catalog.json` — the complete NIST CSF 2.0 OSCAL catalog
  (not represented at slice-1/slice-2 scale, which are scoped to SP 800-53 /
  FedRAMP control families rather than CSF subcategories).
- `markdown-catalog/` — the full catalog's Trestle-editable Markdown form
  (1,014 files, one per control/enhancement), generated from `catalog/` via
  `trestle import` + `trestle author catalog-generate` (compliance-trestle
  v5.1.0), not hand-authored. This is the input shape the assemble step of
  the converter (`verbatim doc → AI conversion → Trestle-editable Markdown →
  assemble → OSCAL`) consumes — see `markdown-catalog.provenance.yaml`.

Every file under `catalog/`, `profiles/`, `fedramp/`, and `csf/` is a
byte-for-byte copy of its `third_party/` submodule source at the commit
recorded in that subdirectory's `*.provenance.yaml` — no extraction or
modification. Prose can be traced back to the corresponding PDF in
`../standards/`. `markdown-catalog/` is the one generated exception — derived
from `catalog/` by trestle itself, not copied from a submodule.
