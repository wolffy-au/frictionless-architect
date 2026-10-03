Feature: Control conversion playground - OSCAL to Trestle Markdown
  As a Standards or Document Author validating the deterministic conversion path
  I want to paste a single OSCAL control and see Trestle's own Markdown rendering
  So that I have a known-good reference before comparing it against AI-assisted output

  Scenario: Convert a pasted OSCAL control to Trestle Markdown
    Given the control conversion playground is open
    When I paste the following OSCAL control YAML:
      """
      id: ac-2
      class: SP800-53
      title: Account Management
      parts:
        - id: ac-2_smt
          name: statement
          prose: The organization manages information system accounts.
      """
    And I click "Convert to Markdown"
    Then the Trestle Markdown output should contain "Account Management"
    And the Trestle Markdown output should contain "The organization manages information system accounts."

  Scenario: Invalid OSCAL YAML surfaces a clear error without crashing the page
    Given the control conversion playground is open
    When I paste the following OSCAL control YAML:
      """
      { not valid
      """
    And I click "Convert to Markdown"
    Then the playground should show an error containing "valid YAML"

  Scenario: The reference Markdown is populated as soon as the playground opens
    Given the control conversion playground is open
    Then the Trestle Markdown output should contain "Event Logging"

  Scenario: The reference Markdown has no extra line breaks
    Given the control conversion playground is open
    Then the reference Markdown pane should show each line once, with no extra line breaks

  Scenario: Copy the reference Markdown
    Given the control conversion playground is open
    When I click the copy button for "reference"
    Then the clipboard should contain "Event Logging"
    And the clipboard should hold the reference Markdown without extra line breaks

  Scenario: Copy the OSCAL input
    Given the control conversion playground is open
    When I click the copy button for "oscal-input"
    Then the clipboard should contain "id: au-2"
