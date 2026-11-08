#!/usr/bin/env python3
"""Command-line helper that wires the schema manager to the Neo4j database."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv

from frictionless_architect.schema.manager import SchemaManager

logger = logging.getLogger("schema_cli")


def load_env() -> None:
    """Load the repository-root ``.env`` file, if present.

    The file is loaded with ``override=True``, so its values replace any
    ``NEO4J_*`` variables already exported in the environment.
    """
    dotenv_path = Path(__file__).resolve().parents[1] / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path, override=True)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    The ``--uri``, ``--user`` and ``--password`` defaults are read from
    ``NEO4J_URI``, ``NEO4J_USER`` and ``NEO4J_PASSWORD`` when the parser is
    built, so call ``load_env`` first for ``.env`` values to count.

    Returns:
        The parser, taking one positional ``command`` (``constraints``,
        ``ingest``, ``version``, ``audit`` or ``all``).
    """
    parser = argparse.ArgumentParser(description="Bootstrap the ArchiMate schema in Neo4j.")
    parser.add_argument(
        "--uri",
        default=os.environ.get("NEO4J_URI", "neo4j://localhost:7687"),
        help="Neo4j bolt URI (default: %(default)s)",
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("NEO4J_USER", "neo4j"),
        help="Neo4j username (default: %(default)s)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("NEO4J_PASSWORD", "neo4j"),
        help="Neo4j password (default: %(default)s)",
    )
    parser.add_argument(
        "--data-file",
        "-f",
        type=Path,
        help="JSON fixture describing elements, relationships, views, and diagrams.",
    )
    parser.add_argument(
        "--version-name",
        default="initial-constraints",
        help="Schema version name to record (default: %(default)s)",
    )
    parser.add_argument(
        "command",
        choices=["constraints", "ingest", "version", "audit", "all"],
        help="Operation to perform.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging output.",
    )
    return parser


def load_payload(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Read a JSON fixture describing the schema to ingest.

    Args:
        path: JSON file with optional ``elements``, ``relationships``,
            ``views`` and ``diagrams`` lists.

    Returns:
        The decoded mapping, as passed to ``SchemaManager.ingest_payload``.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    with path.open(encoding="utf-8") as fh:
        return cast("dict[str, list[dict[str, Any]]]", json.load(fh))


def configure_logger(debug: bool) -> None:
    """Configure logging for the CLI.

    Args:
        debug: Log at DEBUG instead of INFO.
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level)
    logger.setLevel(level)
    if debug:
        logger.debug("Debug logging enabled.")


def execute_command(manager: SchemaManager, args: argparse.Namespace) -> None:
    """Run the requested command (``all`` runs every step in order).

    Args:
        manager: The schema manager to act through.
        args: Parsed arguments; ``command`` selects the step(s), ``data_file``
            feeds ``ingest`` and ``version_name`` feeds ``version``.

    Raises:
        ValueError: If ``ingest`` or ``all`` is requested without ``--data-file``.
    """
    if args.command in ("constraints", "all"):
        manager.apply_constraints()
        print("Constraints and indexes applied.")

    if args.command in ("ingest", "all"):
        if not args.data_file:
            raise ValueError("--data-file is required for ingesting data.")
        payload = load_payload(args.data_file)
        manager.ingest_payload(payload)
        print("Data ingested with validation.")

    if args.command in ("version", "all"):
        manager.record_schema_version(args.version_name)
        print(f"Schema version '{args.version_name}' recorded.")

    if args.command in ("audit", "all"):
        missing, orphan = manager.run_audit_checks()
        if missing:
            print("Views/diagrams referencing missing relationships:")
            for row in missing:
                print(f" - {row['kind']} {row['identifier']} references missing relationship {row['missing']}")
        else:
            print("All view/diagram relationship references are valid.")

        if orphan:
            print("Views with no members:")
            for row in orphan:
                print(f" - {row['identifier']}, missing {row['kind']}")
        else:
            print("All views have referenced members.")


def main() -> int:
    """Run the CLI.

    Returns:
        ``0`` on success, ``1`` if the command failed. A missing
        ``--data-file`` exits through the argument parser instead.
    """
    load_env()
    parser = build_parser()
    args = parser.parse_args()
    configure_logger(args.debug)
    manager = SchemaManager(args.uri, args.user, args.password)
    try:
        execute_command(manager, args)
    except ValueError as exc:
        parser.error(str(exc))  # noreturn: argparse exits the process
    except Exception as exc:  # pragma: no cover - inspect in production
        print(f"Schema command failed: {exc}", file=sys.stderr)
        return 1
    finally:
        manager.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
