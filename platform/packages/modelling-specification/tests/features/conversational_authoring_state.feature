Feature: Track and query Current/Transition/Target state (US3, spec.md)
  As an enterprise or solution architect
  I want every applied change classified Current, Transition, or Target
  So that I can query what state a change belongs to afterward

  Background:
    Given a new authoring session

  Scenario: An applied change's state is queryable afterward (Acceptance Scenario 1)
    Given an architect describes a valid, unambiguous model change "State Query Test Function"
    And the agent proposes the delta
    When the architect applies the change as state "Target"
    Then asking the agent what state the change belongs to answers "Target"

  Scenario: A change applies without a state (2026-10-12: state is optional)
    Given an architect describes a valid, unambiguous model change "No State Test Function"
    And the agent proposes the delta
    When the architect applies the change without specifying its state
    Then the change is written to the model
