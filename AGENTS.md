# 002-neo4j-schema-ui Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-04

## Active Technologies
- Python 3.12 (per `pyproject.toml`). + FastAPI 0.128.x, uvicorn, neo4j 5.x driver, python-dotenv/pydantic for settings and payload validation, httpx/pytest for endpoint tests, ruff/pyright/mypy for linting. (002-neo4j-schema-ui)
- Neo4j 5 cluster for live schema metadata; canonical ArchiMate schema files under `sample-data/schema` and the enriched `sample-data/sample-00/Test Model Full.xml` drive the payloads. The visualiser caches aggregated JSON payloads in `.cache/visualiser` for offline resilience. (002-neo4j-schema-ui)

- Python 3.12 (per `pyproject.toml` and repo README). + FastAPI 0.128.x, uvicorn for serving, `neo4j` 5.x driver, `python-dotenv`, `pydantic` v2 for settings/data validation, `httpx`/`pytest` for tests, `ruff`/`pyright`/`mypy` for quality checks. (002-neo4j-schema-ui)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.12 (per `pyproject.toml` and repo README).: Follow standard conventions

## Recent Changes
- 002-neo4j-schema-ui: Added Python 3.12 (per `pyproject.toml`). + FastAPI 0.128.x, uvicorn, neo4j 5.x driver, python-dotenv/pydantic for settings and payload validation, httpx/pytest for endpoint tests, ruff/pyright/mypy for linting.

- 002-neo4j-schema-ui: Added Python 3.12 (per `pyproject.toml` and repo README). + FastAPI 0.128.x, uvicorn for serving, `neo4j` 5.x driver, `python-dotenv`, `pydantic` v2 for settings/data validation, `httpx`/`pytest` for tests, `ruff`/`pyright`/`mypy` for quality checks.

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
