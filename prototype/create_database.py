#!/usr/bin/env python3
"""Prototype script to connect to a local Neo4j instance and seed data from YAML files."""

import os
import yaml
import logging
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase, basic_auth
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("prototype_loader")

# ==========================================
# SCHEMA SECTION - ArchiMate Constraints
# ==========================================

CONSTRAINTS = [
    "CREATE CONSTRAINT driver_id IF NOT EXISTS FOR (n:Motivation_Driver) REQUIRE n.identifier IS UNIQUE",
    "CREATE CONSTRAINT assessment_id IF NOT EXISTS FOR (n:Motivation_Assessment) REQUIRE n.identifier IS UNIQUE",
    "CREATE CONSTRAINT goal_id IF NOT EXISTS FOR (n:Motivation_Goal) REQUIRE n.identifier IS UNIQUE",
    "CREATE CONSTRAINT stakeholder_id IF NOT EXISTS FOR (n:Motivation_Stakeholder) REQUIRE n.identifier IS UNIQUE",
    "CREATE CONSTRAINT outcome_id IF NOT EXISTS FOR (n:Motivation_Outcome) REQUIRE n.identifier IS UNIQUE",
    "CREATE CONSTRAINT principle_id IF NOT EXISTS FOR (n:Motivation_Principle) REQUIRE n.identifier IS UNIQUE",
    "CREATE CONSTRAINT requirement_id IF NOT EXISTS FOR (n:Motivation_Requirement) REQUIRE n.identifier IS UNIQUE",
    "CREATE CONSTRAINT constraint_id IF NOT EXISTS FOR (n:Motivation_Constraint) REQUIRE n.identifier IS UNIQUE",
    "CREATE CONSTRAINT capability_id IF NOT EXISTS FOR (n:Strategy_Capability) REQUIRE n.identifier IS UNIQUE",
    "CREATE CONSTRAINT business_role_id IF NOT EXISTS FOR (n:Business_Role) REQUIRE n.identifier IS UNIQUE",
    "CREATE CONSTRAINT business_event_id IF NOT EXISTS FOR (n:Business_Event) REQUIRE n.identifier IS UNIQUE",
    "CREATE CONSTRAINT business_process_id IF NOT EXISTS FOR (n:Business_Process) REQUIRE n.identifier IS UNIQUE",
    "CREATE CONSTRAINT business_object_id IF NOT EXISTS FOR (n:Business_Object) REQUIRE n.identifier IS UNIQUE",
]

def load_environment() -> None:
    """Load environment variables from .env file if it exists."""
    dotenv_path = Path(__file__).resolve().parents[1] / ".env"
    if dotenv_path.exists():
        logger.info(f"Loading environment from {dotenv_path}")
        load_dotenv(dotenv_path, override=True)
    else:
        logger.warning(".env file not found. Falling back to default environment variables.")

def load_yaml_data(file_name: str) -> Any:
    """Load data from a YAML file in the same directory."""
    file_path = Path(__file__).resolve().parent / file_name
    with file_path.open("r") as f:
        return yaml.safe_load(f)

def seed_database(uri: str, user: str, pword: str) -> None:
    """Connect to Neo4j and create sample nodes and relationships from YAML files."""
    auth = basic_auth(user, pword)
    
    # Load data from external YAML files
    nodes_data = load_yaml_data("nodes.yaml")
    relationships_data = load_yaml_data("relationships.yaml")

    logger.info(f"Connecting to Neo4j at {uri}...")

    try:
        with GraphDatabase.driver(uri, auth=auth) as driver:
            with driver.session() as session:
                # 0. Clear existing data
                logger.info("Clearing existing data...")
                session.run("MATCH (n) DETACH DELETE n")

                # 1. Apply Schema Constraints
                logger.info("Applying schema constraints...")
                for statement in CONSTRAINTS:
                    session.run(statement)

                # 2. Add objects (Nodes) in bulk using UNWIND
                logger.info(f"Creating {len(nodes_data)} prototype nodes in bulk...")
                if nodes_data:
                    # Group nodes by label (Cypher labels can't be parameterized)
                    by_label = {}
                    for node in nodes_data:
                        label = node["label"]
                        by_label.setdefault(label, []).append({
                            "id": node["identifier"],
                            "props": node["properties"]
                        })
                    
                    for label, batch in by_label.items():
                        session.run(f"""
                            UNWIND $batch AS data
                            MERGE (n:{label} {{identifier: data.id}})
                            SET n += data.props
                        """, batch=batch)

                # 3. Relate them in bulk using UNWIND
                logger.info(f"Creating {len(relationships_data)} prototype relationships in bulk...")
                if relationships_data:
                    # Group by relationship type (Relationship types can't be parameterized)
                    by_type = {}
                    for rel in relationships_data:
                        rel_type = rel["type"]
                        # Extract extra properties (e.g., 'name')
                        extra_props = {k: v for k, v in rel.items() if k not in ("source", "target", "type")}
                        by_type.setdefault(rel_type, []).append({
                            "source": rel["source"],
                            "target": rel["target"],
                            "props": extra_props
                        })
                    
                    for rel_type, batch in by_type.items():
                        session.run(f"""
                            UNWIND $batch AS data
                            MATCH (src {{identifier: data.source}})
                            MATCH (tgt {{identifier: data.target}})
                            MERGE (src)-[r:{rel_type}]->(tgt)
                            SET r += data.props
                        """, batch=batch)

                logger.info("Successfully seeded prototype data.")

    except Exception as e:
        logger.error(f"Failed to connect or seed database: {e}")
        raise

def main() -> None:
    """Main entry point for the prototype script."""
    load_environment()

    # Connection parameters
    uri = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "neo4j")

    seed_database(uri, user, password)

if __name__ == "__main__":
    main()
