# Quickstart Guide: Frictionless Architecture & Governance Platform

This guide provides essential steps to get started with the Frictionless Architecture & Governance Platform.

## Prerequisites

Ensure you have the following installed:

- **Python**: Version 3.11 or higher (as determined by research).
- **Poetry**: Dependency management and running build and test commands (ADR-0003).
- **Git**: For managing code versions and branches.
- **Podman (Docker)**: For running PostgreSQL and Neo4j databases (if applicable).

## Project Setup

1. **Clone the Repository**:

    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2. **Set Up Python Environment**:

    ```bash
    pipx install poetry # or: pip install --user poetry
    poetry install --with dev
    ```

3. **Initialize Feature Specification (if needed)**:
    If you are starting a new feature, use the `specify` CLI tool:

    ```bash
    # Example: Creating a new feature branch for API authentication
    specify --create-feature "Implement JWT Authentication for API" --short-name jwt-auth
    ```

    This command will create a new branch (e.g., `002-jwt-auth`) and the corresponding specification files under `specs/`.

## Running the Platform

To run what is built today (the Neo4j schema visualiser), see `README.md`.

## Running Specifications and Planning

Use the `specify` CLI commands for managing your architecture specifications:

- **Check prerequisites**:

    ```bash
    .specify/scripts/bash/check-prerequisites.sh
    ```

- **Start planning a feature**:

    ```bash
    .specify/scripts/bash/setup-plan.sh --json # Or use the interactive command
    ```

## Development Workflow

The six stages below are defined in `.specify/memory/constitution.md` §"Development Workflow",
which is authoritative if they ever differ.

1. **Specify** (`speckit-specify`): Define requirements and user stories in `specs/<feature>/spec.md`.
2. **Plan** (`speckit-plan`): Research technical approaches and generate `plan.md`, `research.md`,
   `data-model.md`, `contracts/`, etc.
3. **Record**: File or update an ADR under `docs/adr/` for every load-bearing choice the plan makes
   (Principle X).
4. **Break down** (`speckit-tasks`): Map the plan to tasks and requirements.
5. **Implement** (`speckit-implement`): Execute tasks following the Red-Green-Refactor cycle.
6. **Verify**: Pass all quality gates — `scripts/pre_commit_checks.sh` on every commit,
   `scripts/pre_merge_checks.sh` before merge.

For more detailed information, refer to `TECHNICAL.md` and the generated specification files.
