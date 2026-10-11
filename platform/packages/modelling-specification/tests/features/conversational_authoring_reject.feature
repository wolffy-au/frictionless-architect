Feature: Reject invalid, duplicate, or non-idiomatic proposals with an explanation (US2, spec.md)
  As an enterprise or solution architect
  I want invalid, duplicate, or non-idiomatic proposals to require an explicit decision
  So that the agent can be trusted to touch the canonical model

  Background:
    Given a new authoring session

  Scenario: A metamodel-violating change is rejected with a specific explanation (Acceptance Scenario 1)
    Given an architect describes a change that violates the metamodel
    When the agent proposes the delta
    Then the agent rejects the change with a specific, actionable explanation
    And no change is written to the model

  Scenario: A likely duplicate is surfaced and requires an explicit decision (Acceptance Scenario 2)
    Given an architect describes a change that resembles an existing element
    When the agent proposes the delta
    Then the agent surfaces the duplicate candidate
    When the architect rejects the duplicate
    Then no change is written to the model

  Scenario: A non-idiomatic but legal relationship is flagged with the established pattern (Acceptance Scenario 3)
    Given an established intermediary-element pattern for a relationship shape
    And an architect describes a direct relationship matching that shape
    When the agent proposes the delta
    Then the agent flags the pattern shortcut and explains the established pattern
    When the architect keeps the direct form anyway
    Then the change is written to the model

  Scenario: Overriding a rejection applies the change and records the override (Acceptance Scenario 4)
    Given an architect describes a change that violates a configured convention
    When the agent proposes the delta
    Then the agent rejects the change with a specific, actionable explanation
    When the architect overrides the objection with a rationale
    Then the change is written to the model
    And the override is recorded as a traceable decision
