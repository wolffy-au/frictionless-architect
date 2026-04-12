#!/usr/bin/env python3
"""Script to generate a PlantUML ArchiMate diagram from the Neo4j database."""

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
        "Motivation_Stakeholder": "Motivation_Stakeholder",
        "Motivation_Driver": "Motivation_Driver",
        "Motivation_Assessment": "Motivation_Assessment",
        "Motivation_Goal": "Motivation_Goal",
        "Motivation_Outcome": "Motivation_Outcome",
        "Motivation_Principle": "Motivation_Principle",
        "Motivation_Requirement": "Motivation_Requirement",
        "Motivation_Constraint": "Motivation_Constraint",
        "Strategy_CourseOfAction": "Strategy_CourseOfAction",
        "Strategy_Resource": "Strategy_Resource",
        "Strategy_Capability": "Strategy_Capability",
        "Strategy_ValueStream": "Strategy_ValueStream",
        "Business_Role": "Business_Role",
        "Business_Event": "Business_Event",
        "Business_Process": "Business_Process",
        "Business_Object": "Business_Object",
    }
    # Default to a generic ArchiMate element if label not found
    return mapping.get(label, "Motivation_Requirement")


def get_rel_macro(rel_type: str) -> str:
    """Map Neo4j relationships to ArchiMate PlantUML relationship macros."""
    # If the database already uses a valid PlantUML macro name, return it
    if rel_type.startswith("Rel_"):
        return rel_type

    mapping = {
        "REALIZES": "Rel_Realization_Up",
        "ASSOCIATED_WITH": "Rel_Association",
        "INFLUENCES": "Rel_Influence",
        "TRIGGERS": "Rel_Triggering",
        "FLOWS_TO": "Rel_Flow",
        "ASSIGNED_TO": "Rel_Assignment",
        "ACCESSES": "Rel_Access",
    }
    return mapping.get(rel_type, "Rel_Association")


def generate_visualisation(uri, user, password):
    """Query Neo4j and build the PlantUML string."""
    auth = basic_auth(user, password)
    puml = [
        "@startuml Motivation",
        "title ArchiMate Motivation View",
        "!include <archimate/archimate>",
        "' skinparam linetype ortho",
        "",
    ]

    try:
        with GraphDatabase.driver(uri, auth=auth) as driver:
            with driver.session() as session:
                # 1. Fetch Nodes (Motivation and Strategy layers only)
                logger.info("Fetching nodes from Neo4j...")
                nodes = session.run("""
                    MATCH (n)
                    WHERE any(l IN labels(n) WHERE l STARTS WITH 'Motivation_' OR l STARTS WITH 'Strategy_')
                    RETURN n, labels(n)[0] as label
                """)
                for record in nodes:
                    node = record["n"]
                    label = record["label"]
                    macro = get_puml_macro(label)
                    id_clean = sanitize_id(node["identifier"])
                    name = escape_puml(node.get("name", node["identifier"]))
                    puml.append(f"{macro}({id_clean}, '{name}')")

                puml.append("")

                # 2. Fetch Relationships (within Motivation and Strategy layers only)
                logger.info("Fetching relationships from Neo4j...")
                rels = session.run("""
                    MATCH (s)-[r]->(t)
                    WHERE any(l IN labels(s) WHERE l STARTS WITH 'Motivation_' OR l STARTS WITH 'Strategy_')
                      AND any(l IN labels(t) WHERE l STARTS WITH 'Motivation_' OR l STARTS WITH 'Strategy_')
                    RETURN s.identifier as source, t.identifier as target, type(r) as type, r.name as name
                """)
                for record in rels:
                    macro = get_rel_macro(record["type"])
                    src = sanitize_id(record["source"])
                    tgt = sanitize_id(record["target"])
                    name = escape_puml(record.get("name"))
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
        output_path = Path(__file__).parent / "motivation_diagram.puml"
        output_path.write_text(puml_content)
        logger.info(f"Diagram generated successfully: {output_path}")

        # Output to console for the user
        print("\n" + "=" * 20)
        print(" PLANTUML OUTPUT")
        print("=" * 20 + "\n")
        print(puml_content)


if __name__ == "__main__":
    main()
