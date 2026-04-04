#!/usr/bin/env python3
"""Command-line helper that wires the schema manager to the Neo4j database."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from frictionless_architect.schema.manager import SchemaManager

logger = logging.getLogger("schema_cli")


def load_env() -> None:
    dotenv_path = Path(__file__).resolve().parents[1] / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)


def build_parser() -> argparse.ArgumentParser:
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
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def configure_logger(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level)
    logger.setLevel(level)
    if debug:
        logger.debug("Debug logging enabled.")


def execute_command(manager: SchemaManager, args: argparse.Namespace) -> None:
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
            print("Relationships with missing endpoints:")
            for row in missing:
                print(f" - {row['identifier']} missing {row['missing']} node(s)")
        else:
            print("All relationships point to valid elements.")

        if orphan:
            print("Views with no members:")
            for row in orphan:
                print(f" - {row['identifier']}, missing {row['kind']}")
        else:
            print("All views have referenced members.")


def main() -> int:
    load_env()
    parser = build_parser()
    args = parser.parse_args()
    configure_logger(args.debug)
    manager = SchemaManager(args.uri, args.user, args.password)
    try:
        execute_command(manager, args)
    except ValueError as exc:
        parser.error(str(exc))
        return 1
    except Exception as exc:  # pragma: no cover - inspect in production
        print(f"Schema command failed: {exc}", file=sys.stderr)
        return 1
    finally:
        manager.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
