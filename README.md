
# frictionless-architect Development Setup

This document outlines the steps to set up the development environment for the frictionless-architect project.

## Prerequisites

- Python 3.12
- pip
- virtualenv (or equivalent)

## Installation

1. **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd frictionless-architect
    ```

2. **Set up a virtual environment:**

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3. **Upgrade pip:**

    ```bash
    pip install --upgrade pip
    ```

4. **Install core dependencies:**

  ```bash
  pip install fastapi uvicorn sqlalchemy psycopg2-binary python-accounting pydantic
  ```

## Configuration

The project uses `pydantic`-backed settings to drive environment-specific values.
You can override the defaults by exporting these variables before running the app:

- `FRICTIONLESS_ARCHITECT_DATABASE_URL` – SQLAlchemy URL for the application's database (default: `sqlite:///./frictionless_architect.db`).
- `FRICTIONLESS_ARCHITECT_DATABASE_ECHO` – Enable SQLAlchemy logging when debugging (default `false`).
- `FRICTIONLESS_ARCHITECT_LOG_LEVEL` – Default log level consumed by the structured logger (`INFO`, `DEBUG`, etc.).
- `FRICTIONLESS_ARCHITECT_JWT_SECRET` and `FRICTIONLESS_ARCHITECT_JWT_ALGORITHM` – Placeholders for the future JWT authentication layer.
- `FRICTIONLESS_ARCHITECT_ENCRYPTION_KEY` – Symmetric key used when encrypting sensitive account metadata at rest.
- `FRICTIONLESS_ARCHITECT_SECURITY_ENABLED` – Toggle JWT/RBAC enforcement (`false` by default for local development).

Settings are automatically loaded from a `.env` file in the project root when present.

1. **Configure Database:**
    The project is configured to use SQLite for development purposes. The database connection string is defined in `src/core/config.py`.

    **For Production Environments (Reliability & Recovery)**:
    For production deployments, a PostgreSQL database is highly recommended to meet reliability (T052) and recovery (T053) non-functional requirements. The `psycopg2-binary` driver is already included.

    To configure PostgreSQL, set the `FRICTIONLESS_ARCHITECT_DATABASE_URL` environment variable to your PostgreSQL connection string, e.g.:
    `export FRICTIONLESS_ARCHITECT_DATABASE_URL="postgresql://user:password@host:port/dbname"`

    *Note: Ensure your PostgreSQL instance is properly secured and backed up according to your RPO/RTO requirements.*

2. **Run Tests:**
    All tests can be run using pytest:

    ```bash
    pytest
    ```

## API Pytest Quickstart

The dedicated API regression suite lives under `tests/api` and exercises the FastAPI endpoints through `httpx` clients. Follow these steps to run it:

1. **Prepare the environment**
   - Activate your virtual environment (e.g., `source .venv/bin/activate`).
   - Install project dependencies via the configured tooling (e.g., `poetry sync` or `pip install -r requirements.txt`).
   - Ensure the local API is running and reachable (`uvicorn src.main:app --reload` by default).

2. **Set required environment variables**
   - `FRICTIONLESS_ARCHITECT_SECURITY_ENABLED=true` (enforces JWT auth during the suite).
   - `FRICTIONLESS_ARCHITECT_JWT_SECRET` and `FRICTIONLESS_ARCHITECT_JWT_ALGORITHM=HS256` (match the fixtures’ expectations).
   - Optionally adjust `FRICTIONLESS_ARCHITECT_DATABASE_URL` if you want to run against a specific database.

3. **Run the API tests**

   ```bash
   pytest tests/api
   ```

   These tests seed deterministic accounts, rely on JWT-authenticated requests, and clean up after each scenario. Failures indicate regressions in account creation, listings, adjustments, or validation behavior.

4. **Key API endpoints covered by tests:**
   - Transaction management: `POST /transactions/` (tested in `tests/api/test_transactions.py`)
   - QuickFill suggestions and approvals: `GET /quickfill/`, `POST /quickfill/templates/{template_id}/approve` (tested in `tests/api/test_quickfill.py`)
   - Duplicate detection and merging: `GET /duplicates/`, `POST /duplicates/merge` (tested in `tests/api/test_duplicates.py`)
   - Account merging: `POST /accounts/merge` (tested in `tests/api/test_accounts.py`)

5. **Interpret results**
   - Passing suite: all acceptance criteria (account creation, hierarchy balances, validation errors, authentication guards) are satisfied.
   - Failing test: inspect the HTTP response payload logged by pytest; it pinpoints the endpoint or fixture needing attention.

6. **Optional workflows**
   - Run individual tests for faster iteration: `pytest tests/api/test_accounts.py::test_create_and_get_account`.
   - Use `-k` filters (e.g., `pytest tests/api -k balance`) to scope the suite.

## Running the Application

The application can be run using uvicorn:

```bash
uvicorn src.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## Schema Visualiser

The Neo4j schema visualiser ships with its own FastAPI entry point. To explore it:

1. Point your `.env` at the Neo4j instance and sample data:

   ```
   FRICTIONLESS_ARCHITECT_NEO4J_URI=bolt://localhost:7687
   FRICTIONLESS_ARCHITECT_NEO4J_USER=reader
   FRICTIONLESS_ARCHITECT_NEO4J_PASSWORD=reader
   FRICTIONLESS_ARCHITECT_SAMPLE_DATA_DIR=sample-data
   FRICTIONLESS_ARCHITECT_CACHE_DIR=.cache/visualiser
   FRICTIONLESS_ARCHITECT_WARNING_TEXT="Sample data unavailable"
   ```

2. Start the visualiser service:
  
```bash
   uvicorn frictionless_architect.visualizer:app --reload --port 8100
   ```

1. Visit `http://127.0.0.1:8100/schema-visualizer` to see the diagram, table, and schema summary driven by `/schema-payload`.

The interface keeps the schema list visible even when the banner reads “Sample data unavailable,” exposes `/schema-payload/refresh` for guaranteed freshness, and posts status info at `/schema-payload/status` so you can monitor cache age, Neo4j health, and warnings.

## Benchmarking

Use `python scripts/benchmark_workflow.py` to gather average timings for creation, adjustments, and hierarchy queries. The script runs against an in-memory SQLite database and prints the per-operation latency so you can compare before/after tuning.

## Manual Balance Adjustments

Manual balance adjustments live behind the `/accounts/{account_id}/adjust-balance` endpoint and always require the `operator` role (`require_role(Role.OPERATOR)` guards the route). The API writes a `ManualBalanceAdjustment` record even when the requested balance matches the ledger (zero-difference scenarios), and it routes approved adjustments through `TransactionService` to keep double-entry accounting intact.

Every adjustment call is recorded via `log_security_event(SecurityEvent.SENSITIVE_DATA_ACCESS)` (look for JSON blobs in `security.log`) and traced with duration metadata so you can monitor the milliseconds spent computing balances and persisting transactions. Failures emit `SecurityEvent.SYSTEM_ALERT` entries, providing an audit trail for denied adjustments.

To explore the feature manually:

1. Start the app (`uvicorn src.frictionless_architect.main:app --reload`) and source a JWT for an operator (`Role.OPERATOR`).
2. POST to `/accounts/{account_id}/adjust-balance` with `target_balance`, `effective_date`, and `submitted_by_user_id`.
3. Check `/accounts/{account_id}/reconciliation` for the accompanying reconciliation entry and examine `security.log` for the structured audit record.

## Notes on API Tests

The API regression suite is located under `tests/api/` and utilizes `pytest` to exercise the FastAPI endpoints via `httpx` clients.

To run these tests:
1. Ensure your virtual environment is active and project dependencies are installed (e.g., `poetry sync`).
2. Set the required environment variables: `FRICTIONLESS_ARCHITECT_SECURITY_ENABLED=true`, `FRICTIONLESS_ARCHITECT_JWT_SECRET`, and `FRICTIONLESS_ARCHITECT_JWT_ALGORITHM=HS256`.
3. Execute `pytest tests/api` in your project's root directory.

Key API endpoints covered by tests include:
- Transaction management (`POST /transactions/`)
- QuickFill suggestions and approvals (`GET /quickfill/`, `POST /quickfill/templates/{template_id}/approve`)
- Duplicate detection and merging (`GET /duplicates/`, `POST /duplicates/merge`)
- Account merging (`POST /accounts/merge`)

These tests seed deterministic accounts, rely on JWT-authenticated requests, and perform cleanup. Failures indicate regressions and should be investigated by inspecting the logged HTTP response payload. For more advanced filtering or running individual tests, refer to the `pytest` documentation or use its `-k` flag (e.g., `pytest tests/api -k balance`).
