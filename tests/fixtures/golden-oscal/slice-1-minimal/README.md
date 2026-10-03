# slice-1-minimal

The smallest useful golden dataset: exactly 5 entries, chosen to exercise two
different kinds of baseline-diffing signal without needing a full catalog.

## Controls

- **AC-2** — Account Management (base control, plus enhancements
  **AC-2.1** and **AC-2.11**)
- **AU-2** — Event Logging (base control only)
- **IA-3** — Device Identification and Authentication (base control only)

Two distinct variation patterns are represented across the SP 800-53B
LOW/MODERATE/HIGH baselines:

- **Enhancement-set growth** — AC-2 pulls 0 of its tracked enhancements at
  LOW, `ac-2.1` only at MODERATE, and both `ac-2.1`/`ac-2.11` at HIGH.
- **Presence/absence** — IA-3 is not selected at all at LOW, then appears
  (as a bare base control) at MODERATE and HIGH.

AU-2 is included as the flat control: selected, unchanged, at all three
tiers — useful as a contrast case (a control that does *not* vary).

<details>
<summary>History: this slice used to use IA-2 and include a FedRAMP excerpt</summary>

IA-2's enhancement selection turned out to be identical across all three
baselines, so it added bulk without adding signal — replaced with IA-3. The
FedRAMP excerpt was dropped for simplicity. See the 2026-09-28 note in
`catalog/nist-sp800-53-rev5-catalog-excerpt.provenance.yaml`.

</details>

## Layout: two parts, 1a and 1b

This slice covers two of the three spec'd user stories. `catalog/` is
shared between them; everything else lives under whichever part produces or
consumes it:

| Path | User story | Contents |
|---|---|---|
| `catalog/` | (shared) | The 5-entry OSCAL catalog excerpt, with full verbatim statement prose. Consumed by both parts below. |
| `1a-conversion/markdown-catalog/` | 1 → 2 (standard → Markdown → assembled catalog) | Trestle-editable Markdown, one file per entry. |
| `1b-resolution/profiles/` | 3 (catalog + profile → resolved catalog) | The three unmodified LOW/MODERATE/HIGH baseline profiles. |
| `1b-resolution/resolved-catalog/` | 3 | The three profiles resolved against the full catalog, trimmed to these 5 entries. |

Each directory's `*.provenance.yaml` records its exact source, extraction
method, and checksum. Prose in `catalog/` can be traced back to
`../standards/NIST.SP.800-53r5.pdf` for QA.

## Following one entry through the real pipeline

`ac-2.11` (Usage Conditions) is the clearest single-entry example of how the
same piece of data changes shape at each stage. Its content stays verbatim
throughout — only the *container* changes. This is the real target pipeline
(`verbatim doc → AI conversion → Trestle-editable Markdown → assemble →
OSCAL`), with baseline selection and resolution (User Story 3) layered on
afterward:

### 1. Standard (verbatim source)

`../standards/NIST.SP.800-53r5.pdf`, Chapter Three, page 22, control
AC-2(11), exact published text:

> **(11) ACCOUNT MANAGEMENT \| USAGE CONDITIONS**
>
> Enforce \[Assignment: organization-defined circumstances and/or usage
> conditions\] for \[Assignment: organization-defined system accounts\].
>
> *Discussion:* Specifying and enforcing usage conditions helps to enforce
> the principle of least privilege, increase user accountability, and
> enable effective account monitoring. Account monitoring includes alerts
> generated if the account is used in violation of organizational
> parameters. Organizations can describe specific conditions or
> circumstances under which system accounts can be used, such as by
> restricting usage to certain days of the week, time of day, or specific
> durations of time.
>
> *Related Controls:* None.

### 2. `1a-conversion/markdown-catalog/ac/ac-2.11.md`

The same statement and guidance prose, in Trestle-editable Markdown +
YAML-frontmatter shape — what the pipeline's **AI conversion** step is
meant to produce from stage 1:

```markdown
---
x-trestle-set-params:
  ac-02.11_odp.01:
    values:
  ac-02.11_odp.02:
    values:
x-trestle-global:
  sort-id: ac-02.11
---

# ac-2.11 - \[Access Control\] Usage Conditions

## Control Statement

Enforce {{ insert: param, ac-02.11_odp.01 }} for {{ insert: param, ac-02.11_odp.02 }}.

## Control guidance

Specifying and enforcing usage conditions helps to enforce the principle of
least privilege, ...
```

> **Fixture caveat:** in the real pipeline this file is AI conversion's
> output, produced by reading stage 1's PDF prose. There is no AI converter
> to run yet, so this fixture builds the file the other way round — from
> stage 3's already-published catalog JSON, via `trestle author
> catalog-generate` — as a shortcut to get *valid* Markdown for testing the
> next step. See `1a-conversion/markdown-catalog/markdown-catalog.provenance.yaml`
> for exactly why.

### 3. `catalog/nist-sp800-53-rev5-catalog-excerpt.json`

The same prose, in OSCAL's control-enhancement JSON shape, nested under
`ac-2`. In the real pipeline this is **assemble**'s output (`trestle
author catalog-assemble`, consuming stage 2's Markdown):

```json
{
  "id": "ac-2.11",
  "title": "Usage Conditions",
  "params": [ ... ],
  "parts": [
    {
      "name": "statement",
      "prose": "Enforce {{ insert: param, ac-02.11_odp.01 }} for {{ insert: param, ac-02.11_odp.02 }}."
    },
    { "name": "guidance", "prose": "Specifying and enforcing usage conditions helps to enforce the principle of least privilege, increase user accountability, and enable effective account monitoring. ..." }
  ]
}
```

Here too, this fixture already has stage 3 (it's a copy of the real
published NIST catalog) rather than having produced it by actually running
assemble against stage 2 — see "Why this fixture is built in reverse"
below.

### 4. Baseline selection — `1b-resolution/profiles/NIST_SP-800-53_rev5_<TIER>-baseline_profile.json`

A separate, downstream concern, not part of the doc→OSCAL conversion
pipeline itself. Each profile carries no prose at all; it just decides
whether to *pull in* the `ac-2.11` id via
`imports[].include-controls[].with-ids`. This is where the growth signal
this slice was chosen for actually lives — the same JSON structure, three
different outcomes:

| Tier | `ac-2` family ids pulled in |
|---|---|
| LOW | `ac-2` |
| MODERATE | `ac-2`, `ac-2.1`, `ac-2.2`, `ac-2.3`, `ac-2.4`, `ac-2.5`, `ac-2.13` |
| HIGH | `ac-2`, `ac-2.1`, `ac-2.2`, `ac-2.3`, `ac-2.4`, `ac-2.5`, `ac-2.11`, `ac-2.12`, `ac-2.13` |

`ac-2.11` only appears in the HIGH row — LOW and MODERATE never select it.
`ac-2.1` shows the middle case: absent at LOW, present at MODERATE and HIGH.

### 5. `1b-resolution/resolved-catalog/NIST_SP-800-53_rev5_<TIER>-baseline_resolved-catalog-excerpt.json`

The pipeline's other real, forward-run stage (User Story 3: Catalog +
Profile → resolved Catalog). This *is* what you get from actually running
`trestle author profile-resolve` against stage 3's catalog and stage 4's
profile — flattening the profile's selection against the catalog's prose
into one self-contained document per tier. The resulting entry counts match
the table above exactly: LOW has 2 entries (`ac-2`, `au-2`), MODERATE has 4
(adds `ac-2.1`, `ia-3`), HIGH has 5 (adds `ac-2.11`). See
`1b-resolution/resolved-catalog/resolved-catalog.provenance.yaml` for the
exact `trestle` invocation and a caveat about a local href-retargeting
workaround it needed.

### Summary

The *prose* is identical from stage 1 through stage 3, and carried through
unchanged into stage 5 (it's the same sentence in the PDF, the Markdown,
the catalog JSON, and the resolved catalog); what changes is the
*container* it's held in, and — at stage 5 — which controls got pulled in
at all. `ac-2`/`au-2`/`ia-3` follow the same path; see their own files
under `catalog/`, `1a-conversion/markdown-catalog/`, and
`1b-resolution/profiles/`.

### Why this fixture is built in reverse (mostly)

Slice-1 exists to test the pipeline's later stages independently of a
working AI converter, which doesn't exist yet. Stages 2 and 3 here were
both derived mechanically from the real published NIST catalog (stage 3
copied, then stage 2 generated from it by `trestle`) rather than produced
by actually running AI conversion then assemble on stage 1 — the prose
happens to be identical at every stage regardless of which direction
produced it, which is what makes this a valid fixture for testing assemble
without needing AI conversion built first. Stage 5 is the one part of this
fixture that runs the *real* pipeline direction: `1b-resolution/
resolved-catalog/` was produced by actually invoking `profile-resolve`
against stages 3 and 4, not derived backwards.

## Known issue

The vendored FedRAMP resolved baselines (`../slice-2-medium/fedramp/`,
`../slice-3-full/fedramp/`) are SP 800-53 **rev4**, not rev5 — they are not
a valid comparison target against this slice's rev5-derived
`1b-resolution/resolved-catalog/` output. See
`docs/adr/0030-vendor-oscal-reference-content.md`'s 2026-09-28 "Known
issue" note.
