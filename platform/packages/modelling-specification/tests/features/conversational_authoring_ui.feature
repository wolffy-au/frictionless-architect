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

  Scenario: Picking a view from the list renders it
    When the architect picks the view "view-stakeholder" from the list
    Then the render pane displays an SVG diagram spanning the full pane width

  Scenario: Pressing Enter sends the request, and a restarted server does not break the page
    Given an architect describes a valid, unambiguous model change "Enter Key Function"
    And the server has forgotten the architect's session
    When the architect sends that request by pressing Enter
    Then the chat pane shows no objections

  Scenario: The diagram can be zoomed, panned and reset
    When the architect picks the view "view-stakeholder" from the list
    And the architect zooms in on the diagram
    Then the diagram is larger
    When the architect resets the diagram size
    Then the diagram is back to its fitted size
    When the architect drags the diagram
    Then the diagram has moved with the mouse

  Scenario: An element in several views refreshes the view already on screen
    Given an architect describes a valid, unambiguous model change that extends "role-ea" without stubbing rendering
    And the architect turns on auto-render in the UI
    When the architect picks the view "view-gh108-conversational-authoring" from the list
    And the architect sends that request in the UI
    And the architect picks the state "Transition" and clicks Apply in the UI
    Then the view "view-gh108-conversational-authoring" is still selected
    And no view question is asked

  Scenario: The page remembers its settings across a reload
    When the architect sets state "Transition", auto-render on and the view "view-stakeholder"
    And the architect reloads the page
    Then the state is "Transition", auto-render is on and the view "view-stakeholder" is shown
