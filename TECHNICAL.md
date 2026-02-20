# Technical Specifications and Guidelines

This document consolidates technical specifications, patterns, utilities, and preferred libraries.

## Code Style

* **Indentation**: 4 spaces; no tabs.
* **Line Length**: Maximum 120 characters; break after operators; use backslash for line continuation.
* **Naming Conventions**:
  * Variables and functions: `snake_case`
  * Classes: `PascalCase`
  * Constants: `UPPER_CASE`
  * Avoid single-character variable names (except loop counters).
* **Comments**:
  * Single-line: `#`
  * Docstrings: `"""`
  * Comment complex logic.
  * Update comments when code changes.

## File Structure

* **File Naming**: Descriptive names in `snake_case`.
* **Modularity**: Keep related functionality in the same module.
* **Separation of Concerns**: Separate concerns into different files.
* **Reusability**: Separate reusable components into different packages.
* **Package Initialization**: Use `__init__.py` for package initialization.

## Patterns and Practices

* **Testing**:
  * Write tests for all new functionality.
  * Stub functions to facilitate testing before production code is fully implemented.
  * Aim for greater than 90% test coverage.
  * Test positive and negative cases.
  * Use descriptive test function names.
  * Follow the TDD (Test-Driven Development) principle implicitly by writing tests for new functionality.
  * (Implied by `pytest` usage) Utilize fixtures and parameterization for efficient testing.
* **Documentation**:
  * Document all public functions with docstrings.
  * Include type hints where appropriate.
  * Keep documentation up-to-date with code changes.
  * Use Google-style docstrings.
* **Version Control**:
  * Commit frequently with meaningful messages.
  * Use present tense in commit messages.
  * Follow semantic versioning.
  * Keep commits small and focused.
  * Use `commitizen` for managing version changes.
* **Security**:
  * Never commit sensitive information.
  * Use environment variables for configuration.
  * Validate all user inputs.
  * Follow secure coding practices, referencing resources like OWASP guidelines.
* **Performance**:
  * Avoid unnecessary computations.
  * Use efficient data structures.
  * Profile code when performance is critical.
  * Consider memory usage for large datasets.
* **Code Quality**:
  * Keep functions small and focused.
  * Avoid code duplication.
  * Use meaningful variable names.
  * Follow the DRY (Don't Repeat Yourself) principle.
  * Write readable and maintainable code.
  * Use strict type casting.
  * Use native types (e.g., `list`, `dict`) over `typing` library equivalents (e.g., `List`, `Dict`).
* **Diagramming**:
  * When documenting in UML and C4, use PlantUML.
  * Primarily focus on structural representation.
  * When documenting instance information, use appropriate diagram types such as UML Object diagrams, and include examples in parentheses.

## Error Management

* **Consistent Error Responses**: Define a standard format for API error responses (e.g., JSON structure including error code, message, and details) for predictable client-side handling.
* **Exception Handling**: Implement robust try-except blocks to catch and handle exceptions gracefully, preventing application crashes.
* **Meaningful Error Codes**: Utilize standardized HTTP status codes for API errors and define custom error codes for specific application-level issues.

## Observability and Logging

* **Structured Logging**: Implement structured logging (e.g., JSON format) to facilitate easier parsing and analysis of log data.
* **Log Levels**: Utilize standard log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) appropriately to categorize messages.
* **Centralized Logging**: Consider strategies for aggregating logs from different services/components into a central system for monitoring and analysis.
* **Metrics Collection**: Instrument the application to collect key performance indicators (KPIs) and system metrics (e.g., request latency, error rates, resource usage) for monitoring and alerting.
* **Distributed Tracing**: For microservices or complex workflows, implement distributed tracing to track requests across multiple services.

## Continuous Integration and Continuous Deployment (CI/CD)

* **Automated Pipelines**: Establish CI/CD pipelines for automated building, testing, linting, and deployment.
* **Build Automation**: Ensure consistent and reproducible builds.
* **Automated Testing**: Integrate all automated tests (unit, integration, BDD) into the CI pipeline to run on every commit.
* **Linting and Formatting**: Integrate `Ruff` or similar tools into the pipeline to enforce code style and quality.
* **Deployment Strategy**: Define clear deployment strategies (e.g., blue-green, canary releases) and automate deployment processes where feasible.

## API Design Principles

* **RESTful Conventions**: Adhere to RESTful principles for API design, including resource-based URLs, appropriate HTTP methods (GET, POST, PUT, DELETE), and status codes.
* **API Versioning**: Implement a clear versioning strategy (e.g., URL path versioning) for managing API evolution.
* **Authentication and Authorization**: Define secure mechanisms for authenticating API consumers and authorizing access to resources.
* **Data Validation**: Utilize `Pydantic V2` for request and response data validation to ensure data integrity.

## Software Architectural Patterns

* **Model-View-Controller (MVC)**: A common pattern for structuring applications, separating concerns into model (data and business logic), view (UI), and controller (handles input and updates).
* **Two-Tier and Three-Tier Architectures**: Understand and apply standard architectural patterns for client-server applications, separating presentation, application logic, and data management layers as appropriate for the solution.

## Domain-Driven Design (DDD)

* **Ubiquitous Language**: Establish and use a common language shared by developers and domain experts throughout the project.
* **Bounded Contexts**: Define clear boundaries for different parts of the domain model, managing complexity and allowing for independent evolution.
* **Aggregates and Entities**: Design domain models around aggregates to enforce invariants and manage consistency.

## Utilities and Frameworks

* **Testing Frameworks**: `pytest`, `pytest-mock`, `behave` (for BDD)
* **Linters/Formatters**: `Ruff`
* **Type Checkers**: `MyPy`, `PyRight`
* **Build/Dependency Management**: `Poetry`
* **Package Installation/Running**: `UV` (as a fast alternative for package installation)
* **API Framework**: `FastAPI`
* **UI Frameworks**: `Streamlit`, `Chainlit` (for building interactive UIs and LLM-based applications)
* **Messaging/Orchestration**: `CrewAI` (implied by usage context)
* **Utilities for LLM**: `LiteLLM`
* **Data Validation**: `Pydantic V2`
