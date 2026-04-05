# GCO Player Management Features

Feature: Player Management
  As a league administrator
  I need to manage player information
  So that the league operates correctly

  Scenario: Load player list
    Given the club has players
    When I load the player list
    Then I should get 13 players

  Scenario: Verify team assignments
    Given players are assigned to teams
    When I check team assignments
    Then Red Team should have 6 players
    And Black Team should have 7 players
