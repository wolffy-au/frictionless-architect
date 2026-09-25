- uml diagrams
- find the source and target files
- prepare a golden data set bulk testing framework
- suggest creation of a UI with stubs to begin and validate
- then move onto stubbed api and validate against UI ie UI is using values returned from stubbed API
- eventually build the backend functionality

check diagrams - business layer need work

1. 8-component vs. 6-subsystem decomposition. ADR-0011 replaced the old 8-component split with 6 subsystems, and the canonical architecture/model/ YAML already encodes the new one — but ARCHITECTURE.md §3–4 still describes the old 8. If you're about to do more architecture-doc work (not just wiki), this is the one worth fixing first since it's the narrative doc, not a cache.
2. ArchiMate namespace version mismatch — the bundled XSDs are 3.1, but the visualiser's parser pins the 3.0 namespace string, and the XSDs themselves inconsistently declare 3.0 as default xmlns vs. 3.1 as targetNamespace. This is a live correctness risk: sample data authored strictly against 3.1 wouldn't match the parser's XPath. Worth settling if you touch the parser or add new sample data.
3. Sample file name split — code/config point at Test Model Full.xml; the 002 spec's acceptance criteria reference Test Model.xml. Cosmetic until someone writes a test against the spec's literal wording.
4. Parser library — research doc chose lxml+xmlschema; implementation uses stdlib ElementTree. Only matters if you're validating against the XSDs for real (not just parsing).
