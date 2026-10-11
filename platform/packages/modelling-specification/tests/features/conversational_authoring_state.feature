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

  Scenario: An ambiguous state is asked for rather than guessed (Acceptance Scenario 2)
    Given an architect describes a valid, unambiguous model change "Ambiguous State Test Function"
    And the agent proposes the delta
    When the architect applies the change without specifying its state
    Then the agent asks the architect to classify it rather than guessing
