# GCO Data Validation Features

Feature: Data Validation
  As a data integrity system
  I need to validate data structures
  So that the application doesn't crash on invalid data

  Scenario: Scores DataFrame structure
    Given scores data is loaded
    When I validate the DataFrame structure
    Then it should have required columns: Player, Tournament, Game, Net_Score, Gross_Score, Birdies, Pars, Bogeys, Double_Bogeys, Eagles, Stableford

  Scenario: Events have required fields
    Given events are loaded
    When I validate an event
    Then it should have: date, name, type, details

  Scenario: Announcements have required fields
    Given announcements are loaded
    When I validate announcement structure
    Then announcement should have id, title, date, author, body fields
