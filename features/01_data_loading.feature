# GCO Data Layer - Core Features

Feature: Data Loading
  As a GCO application
  I need to load data from various sources
  So that the dashboard displays accurate information

  Scenario: Load scores data
    Given the data directory exists
    When I load the scores data
    Then I should get a pandas DataFrame
    And the DataFrame should have required columns

  Scenario: Load events data
    Given the data directory exists
    When I load the events data
    Then events should be a list
    And each event should have required fields

  Scenario: Load announcements data
    Given the data directory exists
    When I load the announcements data
    Then announcements should be a list
    And each announcement should have required fields

  Scenario: Load cup data
    Given the data directory exists
    When I load the cup data
    Then cup data should be a dictionary
    And cup data should have draw key

  Scenario: Load outing data
    Given the data directory exists
    When I load the outing data
    Then outing data should be a dictionary
    And outing data should have red_team key
