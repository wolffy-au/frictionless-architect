# Quickstart Guide: Frictionless Architecture & Governance Platform

This guide provides essential steps to get started with the Frictionless Architecture & Governance Platform.

## Prerequisites

Ensure you have the following installed:

* **Python**: Version 3.11 or higher (as determined by research).
* **UV**: Python package installer.
* **Git**: For managing code versions and branches.
* **Podman (Docker)**: For running PostgreSQL and Neo4j databases (if applicable).
* **UV**: For running build and test commands.

## Project Setup

1. **Clone the Repository**:

    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2. **Set Up Python Environment**:

    ```bash
    python -m venv .venv
    source .venv/bin/activate # On Windows use `.venv\Scripts\activate`
    uv install -r requirements.txt # (Assuming a requirements.txt will be generated)
    ```

3. **Initialize Feature Specification (if needed)**:
    If you are starting a new feature, use the `specify` CLI tool:

    ```bash
    # Example: Creating a new feature branch for API authentication
    specify --create-feature "Implement JWT Authentication for API" --short-name jwt-auth
    ```

    This command will create a new branch (e.g., `002-jwt-auth`) and the corresponding specification files under `specs/`.

## Running the Platform

This platform consists of a core Python service and potentially other microservices.

### Core Service (CLI/API)

The core service is likely a Python application using FastAPI.

1. **Set up databases (if applicable)**:
    Refer to the database-specific setup instructions (e.g., Docker Compose for PostgreSQL and Neo4j).

2. **Run the core service**:

    ```bash
    # Example command - actual command may vary
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```

    (This assumes a FastAPI application named `app` in `main.py`)

### Running Specifications and Planning

Use the `specify` CLI commands for managing your architecture specifications:

* **Check prerequisites**:

    ```bash
    .specify/scripts/bash/check-prerequisites.sh
    ```

* **Start planning a feature**:

    ```bash
    .specify/scripts/bash/setup-plan.sh --json # Or use the interactive command
    ```

## Development Workflow

1. **Specify**: Define requirements in `specs/<branch>/spec.md`.
2. **Plan**: Run `setup-plan.sh` and `speckit.plan` to generate `plan.md`, `research.md`, `data-model.md`, `contracts/`, etc.
3. **Implement**: Use `speckit.tasks` to break down the plan and implement.
4. **Verify**: Ensure all tests pass and quality gates are met.

For more detailed information, refer to `TECHNICAL.md` and the generated specification files.
