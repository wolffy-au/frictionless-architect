Feature: LLM settings
  As an Architect configuring AI features
  I want to choose the provider and model from the playground
  So that I don't edit configuration files by hand

  Scenario: Save a global default and see it persisted
    Given the control conversion playground is open
    When I open the LLM settings from the playground
    And I save the global default as provider "ollama" and model "test-model"
    Then the settings page should list the component "Control conversion (AI candidate)" as inheriting the default
