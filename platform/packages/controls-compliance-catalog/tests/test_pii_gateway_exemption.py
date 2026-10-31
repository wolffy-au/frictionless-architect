"""`fn-ai-markdown-conversion`/`fn-policy-quality-feedback` still bypass pii-gateway
entirely (FR-008, ADR-0031's policy-document exemption). Confirmed statically, since
both paths are policy/regulatory-standard document conversion the ADR exempts by
design -- no runtime wiring to assert against."""

from __future__ import annotations

import ast
from pathlib import Path

_SRC_ROOT = Path(__file__).parent.parent / "src" / "controls_compliance_catalog"

# The AI-markdown-conversion (`llm_client.py`) call site and its known callers.
_EXEMPT_MODULES = [
    _SRC_ROOT / "llm_client.py",
    _SRC_ROOT / "app.py",
    _SRC_ROOT / "playground" / "convert.py",
]


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_llm_client_module_exists() -> None:
    assert (_SRC_ROOT / "llm_client.py").is_file()


def test_exempt_modules_import_no_pii_gateway() -> None:
    for module_path in _EXEMPT_MODULES:
        assert module_path.is_file(), f"expected {module_path} to exist"
        imported = _imported_names(module_path)
        assert not any(name == "pii_gateway" or name.startswith("pii_gateway.") for name in imported), (
            f"{module_path} imports pii_gateway, but ADR-0031 exempts policy-document "
            "conversion from the scrubbing gateway"
        )
