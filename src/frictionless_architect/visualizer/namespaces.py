"""XML namespaces shared by the visualiser's ArchiMate parser and validator."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

# XML namespace identifiers, not fetched endpoints — these are the literal,
# spec-defined strings (W3C XML Schema, The Open Group's ArchiMate exchange
# format) that real documents declare; switching the scheme would stop
# matching them and break parsing and schema validation.
#
# The ArchiMate 3.1 exchange-format XSDs keep the 3.0 target namespace (only
# their `version` attribute and publication URL say 3.1), so 3.0 is the
# namespace every conforming export — Archi, pyArchimate — declares.
XSD_NS = "http://www.w3.org/2001/XMLSchema"
ARCHIMATE_NS = "http://www.opengroup.org/xsd/archimate/3.0/"  # NOSONAR
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


class ArchimateNamespaceError(ValueError):
    """The document root is not an ArchiMate exchange-format `<model>`."""


def _split_tag(tag: str) -> tuple[str, str]:
    """Split an ElementTree `{namespace}local` tag; namespace is "" when absent."""
    if not tag.startswith("{"):
        return "", tag
    namespace, _, local_name = tag[1:].partition("}")
    return namespace, local_name


def require_archimate_namespace(root: ET.Element, source: Path | str) -> None:
    """Raise `ArchimateNamespaceError` unless `root` is `{ARCHIMATE_NS}model`.

    Namespaced lookups silently match nothing on a document in any other
    namespace, so the mismatch is checked up front and reported explicitly.
    """
    namespace, local_name = _split_tag(root.tag)
    if not namespace:
        raise ArchimateNamespaceError(
            f'{source}: root <{local_name}> has no namespace; declare xmlns="{ARCHIMATE_NS}" on the <model> element.'
        )
    if namespace != ARCHIMATE_NS:
        raise ArchimateNamespaceError(
            f"{source}: root element uses namespace {namespace}, expected {ARCHIMATE_NS}; "
            "ArchiMate exchange files (including version 3.1) must declare the 3.0 namespace."
        )
    if local_name != "model":
        raise ArchimateNamespaceError(
            f"{source}: root element is <{local_name}>, expected an ArchiMate exchange-format <model>."
        )
