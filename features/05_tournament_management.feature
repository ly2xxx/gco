# GCO Tournament Management Features

Feature: Tournament Management
  As a league administrator
  I need to manage tournament data
  So that tournament results are displayed correctly

  Scenario: Verify league tournaments exist
    Given tournaments are defined
    When I check league tournaments
    Then there should be at least one tournament

  Scenario: Verify outing matches exist
    Given outing matches are defined
    When I check outing matches
    Then there should be 4 outing matches
