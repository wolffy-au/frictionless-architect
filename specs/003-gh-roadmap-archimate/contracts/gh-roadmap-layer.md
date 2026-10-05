# Contract: generated `gh-roadmap/` layer

Generated, committed, **never hand-edited**. Same schema as `architecture/model/elements.yaml`
(ADR-0007/0008). Ids, relationships and the Deliverable rule: [data-model.md](../data-model.md).

```yaml
# elements.yaml (illustrative; real output is block style)
- type: Plateau
  id: plat-policy-to-oscal-mvp-1
  name: policy-to-oscal-mvp
  props: {gh-number: "1", gh-state: open, gh-url: "https://github.com/…/milestone/1"}
- type: Deliverable
  id: del-policy-to-oscal-mvp-1-unreleased
  name: policy-to-oscal-mvp (unreleased)
- type: WorkPackage
  id: wp-markdown-catalogue-converter-gh-44
  name: "#44 Markdown catalogue converter"
  props: {gh-number: "44", gh-state: open, gh-url: "…"}
# relationships.yaml
- {type: Realization, source: wp-markdown-catalogue-converter-gh-44, target: del-policy-to-oscal-mvp-1-unreleased}
- {type: Realization, source: del-policy-to-oscal-mvp-1-unreleased, target: plat-policy-to-oscal-mvp-1}
# views.yaml: one view per milestone, viewpoint implementation_migration, diagram migration/<plateau id>
```

## Guarantees

1. Output is sorted and has no timestamps, so a no-change re-run is byte-identical.
2. Every relationship passes the ArchiMate 3.2 matrix and every `members` id exists.
3. Free text is escaped by `yaml.safe_dump`.
4. Gaps, the baseline Plateau and Strategy elements are never emitted.

The remaining rules (scope, ids, one Deliverable per Work Package, unreleased Deliverable
condition) are the invariants in [data-model.md](../data-model.md).
