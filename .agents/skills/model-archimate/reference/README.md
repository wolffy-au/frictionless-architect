# Viewpoint reference

The authority for **which ArchiMate concepts a view may show** when it declares
a `viewpoint:`.

## `archi-viewpoints.xml` — vendored, authoritative

A **verbatim copy** of Archi's viewpoint definition file:

  https://raw.githubusercontent.com/archimatetool/archi/master/com.archimatetool.model/model/viewpoints.xml

Archi (Phillip Beauvoir) tracks the ArchiMate specification's example
viewpoints closely, and this is the closest machine-readable form of the
standard's viewpoint tables that is freely available. Re-sync by overwriting
the file from that URL:

```bash
curl -sSL https://raw.githubusercontent.com/archimatetool/archi/master/com.archimatetool.model/model/viewpoints.xml \
  -o .agents/skills/model-archimate/reference/archi-viewpoints.xml
```

Content is otherwise unmodified; pre-commit trims trailing whitespace and
fixes the final newline, which changes no viewpoint data.

### How Archi interprets it (`ViewpointManager` / `Viewpoint`)

- Each `<concept>` is an element class, a relationship class, or a **collection
  token** (`$BusinessElements$`, `$StrategyElements$`, …). `viewpoints.py`
  expands the tokens using `COLLECTIONS`, transcribed from
  `com.archimatetool.model/.../ArchimateModelUtils.java`.
- A viewpoint has an **element** allow-set and a **relationship** allow-set.
  If either set is **empty, that half is unrestricted** — so `layered` (no
  concepts) allows everything, and every current viewpoint has an empty
  relationship set, i.e. **relationships are not filtered** in practice.
- `Junction` and `Grouping` are **always allowed**, in every viewpoint.
- A relationship on a view is shown only if the relationship type is allowed
  **and both endpoints are allowed** — the rule `build.py` already applies by
  only drawing connections whose endpoints are both on the view.

### Slugs

Use Archi's `id` attribute as the `viewpoint:` value in `views.yaml`
(`strategy`, `value_stream`, `capability`, `application_cooperation`,
`application_structure`, `resource`, …). `viewpoints.py list` prints them.
`custom` is our own escape hatch for a deliberate cross-layer view — it is
not an Archi viewpoint and is never conformance-checked.

## `viewpoints-guidance.yaml` — advisory

Purpose / abstraction / concerns / stakeholders / rough TOGAF ADM phase per
slug, for choosing a viewpoint. Transcribed from ArchiMate 3.2 §14.2; it does
**not** affect conformance checking. Missing slugs just have no annotation.
