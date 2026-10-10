# Traceability: specs/002-neo4j-schema-ui/spec.md, API-level criteria only.
# UI rendering criteria (FR-003, SC-003, US2) moved to schema-visualizer-ui (#55).
#
# Criterion                                        -> Scenario (tags)
# US1 AS1 element list with sample nodes           -> "Element list shows sample nodes"          @US1 @FR-001 @FR-002
# US1 AS2 relationship + source/target ids         -> "Association shows source and target"      @US1 @FR-002
# US3 AS1 refresh gives same overview              -> "Refreshing the sample view"               @US3 @FR-004
# Edge 1 type without sample nodes (FR-005)        -> "Type with no sample nodes"                @edge @FR-005
# Edge 2 nodes sharing identifiers                 -> "Nodes share identifiers"                  @edge
# Edge 2 duplicate associations                    -> "Duplicate associations"
# Edge 3 other namespace -> status invalid         -> "Sample on another namespace"              @edge
# Edge 4 / FR-006 sample cannot be loaded          -> "Sample cannot be loaded" (+ no-Neo4j variant @needs-clarification)
# SC-005 2-second target                           -> "Schema visualisation responds within 2 seconds"
# SC-006 retry, non-blocking warning, <=5 min      -> "Automatic retry ..." and "Retry interval ..." scenarios
# FR-007 / SC-007 credential: not API-observable, not covered here.

Feature: Schema visualiser API
  As a data analyst
  I want to see the node, relationship, and view types defined in the Neo4j dataset
  So that I can confidently plan queries and reports that align with the existing model

  Background:
    Given the visualiser API is running against the sample data

  @US1 @FR-001 @FR-002
  Scenario: Element list shows sample nodes
    Given the sample dataset is loaded
    When they inspect the element list
    Then each element type from the schema is shown with one or more sample nodes (e.g., ValueStream VS1, BusinessService Governance Service) drawn from "sample-data/sample-00/Test Model Full.xml"

  @US1 @FR-002
  Scenario: Association shows source and target
    Given the schema contains relationships (Association)
    When the user selects that relationship type
    Then the visualiser highlights the actual relationships between the sample nodes (e.g., the Association between VS1 and the Governance Service) and shows the source/target identifiers
    # NOTE: highlighting is UI (#55); the API half is asserted.

  @US3 @FR-004
  Scenario: Refreshing the sample view
    Given the visualiser loads the provided sample data
    When the reviewer refreshes the sample view
    Then the overview again presents the same nodes and relationships together with the specification that defines each type

  @edge @FR-005
  Scenario: Type with no sample nodes
    Given the schema references a type (e.g., a new ArchiMate element) with no sample nodes in "sample-data/sample-00"
    When the schema payload is requested
    Then that type is flagged as lacking a sample entry and the rest of the schema is still returned

  @edge
  Scenario: Nodes share identifiers
    Given "Test Model Full.xml" has nodes that share identifiers
    When the schema payload is requested
    Then the payload warns about the duplicate identifier and is still returned

  @edge
  Scenario: Duplicate associations
    Given "Test Model Full.xml" defines multiple relationships between the same pair of elements (e.g., duplicate associations)
    When the schema payload is requested
    Then every parallel relationship is listed and no duplicate warning is raised

  @edge
  Scenario: Sample on another namespace
    Given the sample data declares a namespace other than the ArchiMate 3.0 one
    When the schema payload status is requested
    Then sample_file_status is "invalid" and a warning names the expected namespace

  @edge @FR-006
  Scenario: Sample cannot be loaded
    Given "sample-data/sample-00/Test Model Full.xml" cannot be loaded and Neo4j supplies the schema
    When the schema payload is requested
    Then the warning "Sample data unavailable" appears and the schema element list stays accessible

  @edge @FR-006 @needs-clarification
  Scenario: Sample cannot be loaded and Neo4j is not configured
    Given "sample-data/sample-00/Test Model Full.xml" cannot be loaded and no Neo4j is configured
    When the schema payload is requested
    Then the schema summary stays accessible
    # NOTE: the service returns 503 with the warning only on /schema-payload/status; FR-006
    # says the summary stays accessible. Decide whether a type-system-only payload is wanted.

  @SC-005
  Scenario: Schema visualisation responds within 2 seconds
    When the schema payload is requested with the cache bypassed
    Then the response arrives within 2 seconds

  @SC-006
  Scenario: Automatic retry after a failed Neo4j load
    Given Neo4j fails on the first load and then recovers
    When the schema payload is requested
    Then the payload is returned with a non-blocking warning
    And a background retry is pending
    And the retry loads the schema without a manual refresh

  @SC-006
  Scenario: Retry interval is at most 5 minutes
    Then the default retry interval is 300 seconds
    And a RETRY_INTERVAL_SECONDS above 300 is rejected
