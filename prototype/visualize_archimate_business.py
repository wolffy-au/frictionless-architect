#!/usr/bin/env python3
"""Script to generate a PlantUML ArchiMate Business Layer diagram from the Neo4j database."""

import os
import logging
from pathlib import Path
from neo4j import GraphDatabase, basic_auth
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("visualizer")


def load_environment() -> None:
    """Load environment variables from .env file."""
    dotenv_path = Path(__file__).resolve().parents[1] / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path, override=True)


def sanitize_id(identifier: str) -> str:
    """PlantUML IDs cannot contain hyphens or spaces."""
    return identifier.replace("-", "_").replace(" ", "_")


def escape_puml(text: str) -> str:
    """Escape single quotes for PlantUML strings using double single-quotes."""
    if not text:
        return ""
    return text.replace("'", "''")


def get_puml_macro(label: str) -> str:
    """Map Neo4j labels to ArchiMate PlantUML macros."""
    mapping = {
        "Business_Role":    "Business_Role",
        "Business_Event":   "Business_Event",
        "Business_Process": "Business_Process",
        "Business_Object":  "Business_Object",
        "Strategy_Capability": "Strategy_Capability",
    }
    return mapping.get(label, "Business_Object")


def get_rel_macro(rel_type: str) -> str:
    """Map Neo4j relationships to ArchiMate PlantUML relationship macros."""
    if rel_type.startswith("Rel_"):
        return rel_type

    mapping = {
        "TRIGGERS":      "Rel_Triggering_Up",
        "FLOWS_TO":      "Rel_Flow_Up",
        "ASSIGNED_TO":   "Rel_Assignment",
        "ACCESSES":      "Rel_Access",
        "REALIZES":      "Rel_Realization_Up",
        "ASSOCIATED_WITH": "Rel_Association",
        "INFLUENCES":    "Rel_Influence",
    }
    return mapping.get(rel_type, "Rel_Association")


def generate_visualisation(uri, user, password):
    """Query Neo4j and build the PlantUML string."""
    auth = basic_auth(user, password)
    puml = [
        "@startuml Business",
        "title ArchiMate Business Layer View",
        "!include <archimate/archimate>",
        "' skinparam linetype ortho",
        "",
    ]

    try:
        with GraphDatabase.driver(uri, auth=auth) as driver:
            with driver.session() as session:
                # 1. Fetch Business Layer nodes + Strategy_Capability (cross-layer context)
                logger.info("Fetching nodes from Neo4j...")
                nodes = session.run("""
                    MATCH (n)
                    WHERE any(l IN labels(n) WHERE l STARTS WITH 'Business_')
                       OR (n:Strategy_Capability AND EXISTS {
                             MATCH (n)-[]-(b)
                             WHERE any(l IN labels(b) WHERE l STARTS WITH 'Business_')
                           })
                    RETURN n, labels(n)[0] as label
                    ORDER BY labels(n)[0], n.identifier
                """)
                for record in nodes:
                    node = record["n"]
                    label = record["label"]
                    macro = get_puml_macro(label)
                    id_clean = sanitize_id(node["identifier"])
                    name = escape_puml(node.get("name", node["identifier"]))
                    puml.append(f"{macro}({id_clean}, '{name}')")

                puml.append("")

                # 2. Fetch relationships where at least one end is a Business Layer node
                logger.info("Fetching relationships from Neo4j...")
                rels = session.run("""
                    MATCH (s)-[r]->(t)
                    WHERE (any(l IN labels(s) WHERE l STARTS WITH 'Business_') OR s:Strategy_Capability)
                      AND (any(l IN labels(t) WHERE l STARTS WITH 'Business_') OR t:Strategy_Capability)
                    RETURN s.identifier as source, t.identifier as target, type(r) as type, r.name as name, r.mode as mode
                    ORDER BY type(r), s.identifier
                """)
                for record in rels:
                    src = sanitize_id(record["source"])
                    tgt = sanitize_id(record["target"])
                    name = escape_puml(record.get("name"))
                    mode = record.get("mode")
                    if record["type"] == "ACCESSES":
                        access_map = {
                            "read":      "Rel_Access_r",
                            "write":     "Rel_Access_w",
                            "readwrite": "Rel_Access_rw",
                        }
                        macro = access_map.get(mode, "Rel_Access")
                        label_text = f", '{name}'" if name else ""
                    else:
                        macro = get_rel_macro(record["type"])
                        label_text = f", '{name}'" if name else ""
                    puml.append(f"{macro}({src}, {tgt}{label_text})")

        puml.append("")
        puml.append("@enduml")
        return "\n".join(puml)

    except Exception as e:
        logger.error(f"Failed to generate visualisation: {e}")
        return None


def main():
    """Main entry point."""
    load_environment()

    uri = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "neo4j")

    logger.info("Starting visualisation generation...")
    puml_content = generate_visualisation(uri, user, password)

    if puml_content:
        output_path = Path(__file__).parent / "business_diagram.puml"
        output_path.write_text(puml_content)
        logger.info(f"Diagram generated successfully: {output_path}")

        print("\n" + "=" * 20)
        print(" PLANTUML OUTPUT")
        print("=" * 20 + "\n")
        print(puml_content)


if __name__ == "__main__":
    main()
