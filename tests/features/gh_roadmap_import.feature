Feature: Import the GitHub roadmap into the architecture model
  As an architect
  I want one on-demand run that never half-updates and changes nothing when GitHub has not
  So that I can review the generated roadmap layer in version control

  Scenario: Re-running with no GitHub change produces no difference
    Given the roadmap has been imported
    When the roadmap is imported again with no change on GitHub
    Then no file of the roadmap layer differs

  Scenario: Closing one issue changes only that issue
    Given the roadmap has been imported
    When issue 44 is closed on GitHub and the roadmap is imported again
    Then only the state of issue 44 differs in the roadmap layer

  Scenario: Unreachable GitHub leaves the layer untouched
    Given the roadmap has been imported
    When GitHub is unreachable and the roadmap is imported again
    Then the import fails with exit status 2 naming the failing call
    And no file of the roadmap layer differs
