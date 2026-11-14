@ui
Feature: Visualiser placeholder page (FR-001, FR-002, FR-009)

  Browser-level smoke coverage for the visualiser's minimal placeholder
  landing page, run against a live app instance (FR-003) with the
  sample-data fallback standing in for Neo4j (FR-004).

  Scenario: The placeholder page loads with no console error
    When a browser opens the visualiser placeholder page
    Then the page loads with no JavaScript console error

  Scenario: The placeholder page renders its schema summary
    When a browser opens the visualiser placeholder page
    Then the rendered status text confirms the page loaded
    And the schema summary reflects the sample-data fallback
