Feature: Control conversion playground - OSCAL to Trestle Markdown
  As a Standards or Document Author validating the deterministic conversion path
  I want to paste a single OSCAL control and see Trestle's own Markdown rendering
  So that I have a known-good reference before comparing it against AI-assisted output

  Scenario: Convert a pasted OSCAL control to Trestle Markdown
    Given the control conversion playground is open
    When I paste the following OSCAL control JSON:
      """
      {
        "id": "ac-2",
        "class": "SP800-53",
        "title": "Account Management",
        "parts": [
          {
            "id": "ac-2_smt",
            "name": "statement",
            "prose": "The organization manages information system accounts."
          }
        ]
      }
      """
    And I click "Convert to Markdown"
    Then the Trestle Markdown output should contain "Account Management"
    And the Trestle Markdown output should contain "The organization manages information system accounts."

  Scenario: Invalid OSCAL JSON surfaces a clear error without crashing the page
    Given the control conversion playground is open
    When I paste the following OSCAL control JSON:
      """
      { not valid json
      """
    And I click "Convert to Markdown"
    Then the playground should show an error containing "valid JSON"
