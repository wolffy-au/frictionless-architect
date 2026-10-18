"""modelling-specification is digital-twin-knowledge-graph's first real consumer.

Proves spec.md's US4 Acceptance Scenario / FR-013 / SC-006: another package in the
`platform/` workspace adds this one as an ordinary Poetry path dependency and calls its
read interface as an ordinary function call -- no router, port, or wire format introduced
(tasks.md T021). The dependency edge is kept permanently, not reverted; see
`digital-twin-knowledge-graph/specs/001-knowledge-graph-read-path/plan.md` Structure
Decision.
"""

from __future__ import annotations

from digital_twin_knowledge_graph import GraphSettings, KnowledgeGraphReadPath


def test_read_path_is_callable_as_an_ordinary_function_from_this_package() -> None:
    read_path = KnowledgeGraphReadPath(GraphSettings(neo4j_uri=""))
    try:
        payload = read_path.collect()
    finally:
        read_path.close()
    assert payload == {"elements": [], "relationships": [], "views": []}
