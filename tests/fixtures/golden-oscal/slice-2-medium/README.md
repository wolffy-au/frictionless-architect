# slice-2-medium

The middle tier: two complete control **families** rather than slice-1's
three individual controls, and far smaller than slice-3's full 20-family
catalog.

## Families

- **AC** — Access Control
- **AU** — Audit and Accountability

41 top-level controls between the two families, plus their enhancements. Both
families are present in every SP 800-53B baseline and every FedRAMP baseline,
with the enhancement set growing at higher impact levels (LOW keeps 21
AC/AU controls after FedRAMP tailoring, MODERATE 29, HIGH 30) — useful for
exercising baseline-diffing / profile-resolution logic across a whole family
rather than single controls.

## Contents

- `catalog/nist-sp800-53-rev5-catalog-ac-au-excerpt.json` — a derived, valid
  (but not official) OSCAL catalog containing only the AC and AU groups, with
  full verbatim statement prose and all their enhancements.
- `profiles/` — the three SP 800-53B baseline profile files, copied in full
  from `slice-1-minimal/profiles/` (byte-identical; nothing to excerpt).
- `fedramp/` — the three FedRAMP baselines' resolved-catalog form, trimmed to
  just the AC and AU `<group>` XML subtrees.
- `markdown-catalog/` — the Trestle-editable Markdown form of
  `catalog/nist-sp800-53-rev5-catalog-ac-au-excerpt.json` (187 files across
  `ac/` and `au/`), generated via `trestle import` + `trestle author
  catalog-generate` (compliance-trestle v5.1.0), not hand-authored. This is
  the input shape the assemble step of the converter (`verbatim doc → AI
  conversion → Trestle-editable Markdown → assemble → OSCAL`) consumes — see
  `markdown-catalog.provenance.yaml`.

See each subdirectory's `*.provenance.yaml` for exact source, extraction
method, and checksums. Prose in `catalog/` can be traced back to
`../standards/NIST.SP.800-53r5.pdf` for QA.
