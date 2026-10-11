Feature: Propose and see a validated change (US1, spec.md)
  As an enterprise or solution architect
  I want to describe a model change in plain language
  So that I can see it validated and rendered without hand-editing a model file or
  manually running a render command

  Background:
    Given a new authoring session

  Scenario: A valid, unambiguous change validates cleanly and applies (Acceptance Scenario 1)
    Given an architect describes a valid, unambiguous model change "Add a new reporting function"
    When the agent proposes the delta
    Then it validates cleanly against the metamodel and configured conventions
    When the architect applies the change
    Then the change is written to the model

  Scenario: Automatic rendering shows the change without the architect asking (Acceptance Scenario 2)
    Given rendering is configured to happen automatically
    And an architect describes a valid, unambiguous model change that extends "res-ea-practice"
    When the agent proposes the delta
    And the architect applies the change
    Then the corresponding diagram renders immediately without the architect asking

  Scenario: On-request rendering shows the requested view (Acceptance Scenario 3)
    Given rendering is configured to happen on request
    And an architect describes a valid, unambiguous model change that extends "res-ea-practice"
    And the agent proposes the delta
    And the architect applies the change
    When the architect asks to see the affected element
    Then the corresponding diagram renders immediately, reflecting the current state of the conversation
