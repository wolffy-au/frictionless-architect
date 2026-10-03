Feature: Control conversion playground - prose to candidate Markdown (AI path)
  As a Standards or Document Author checking the AI-assisted conversion path
  I want to paste control prose and see the AI step's candidate Markdown
  So that I can compare it against the deterministic reference before trusting it

  Scenario: Convert pasted control prose to candidate Markdown
    Given the control conversion playground is open
    When I paste the following control prose:
      """
      Account Management: The organization manages information system accounts, including
      establishing, activating, modifying, reviewing, disabling, and removing accounts.
      """
    And I click "Convert via AI (candidate)"
    Then the candidate Markdown output should contain "Account Management"

  Scenario: Empty prose surfaces a clear error without crashing the page
    Given the control conversion playground is open
    When I paste the following control prose:
      """
      """
    And I click "Convert via AI (candidate)"
    Then the playground should show a candidate error containing "Cannot convert empty prose"

  Scenario: Differing words are highlighted within a changed line
    Given the control conversion playground is open
    When I click "Convert via AI (candidate)"
    Then the changed words should be highlighted in both Markdown panes

  Scenario: Scrolling one Markdown pane scrolls the other
    Given the control conversion playground is open
    When I convert a long control in both paths
    And I scroll the candidate Markdown pane to the bottom
    Then the reference Markdown pane should have scrolled too
