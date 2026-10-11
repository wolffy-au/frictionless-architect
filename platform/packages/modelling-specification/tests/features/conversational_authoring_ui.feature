Feature: Split-screen conversational authoring UI (R15, plan.md UI Phase)
  As an enterprise or solution architect
  I want a browser UI over the conversational authoring API
  So that I can propose, review and apply a change, and see its effect rendered

  Background:
    Given the architect opens the authoring UI

  Scenario: Proposing, validating and applying a clean change (quickstart.md step 10)
    Given an architect describes a valid, unambiguous model change "UI Walkthrough Function"
    When the architect sends that request in the UI
    Then the chat pane shows no objections
    When the architect picks the state "Transition" and clicks Apply in the UI
    Then the chat pane confirms the change was applied

  Scenario: Applying a change renders the affected view automatically (FR-012, R18, R19)
    Given an architect describes a valid, unambiguous model change that extends "role-ea"
    And the architect turns on auto-render in the UI
    When the architect sends that request in the UI
    And the architect picks the state "Transition" and clicks Apply in the UI
    Then the render pane displays an SVG diagram spanning the full pane width
