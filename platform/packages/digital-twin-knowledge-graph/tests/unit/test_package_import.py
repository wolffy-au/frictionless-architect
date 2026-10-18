"""Smoke test for the package's public import surface (US4, SC-006).

Importing every public name must succeed with no network/HTTP side effect at import
time -- the library is an ordinary function call, not a service (FR-013).
"""

from __future__ import annotations


def test_public_names_import_cleanly() -> None:
    from digital_twin_knowledge_graph import (
        GraphSettings,
        KnowledgeGraphReadPath,
        ParsedSample,
        ReadPathError,
        SampleParser,
        SchemaManager,
    )

    assert GraphSettings is not None
    assert KnowledgeGraphReadPath is not None
    assert ReadPathError is not None
    assert SampleParser is not None
    assert ParsedSample is not None
    assert SchemaManager is not None
