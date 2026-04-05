# GCO Data Export/Import Features

Feature: Data Export/Import
  As an admin user
  I need to export and import application state
  So that I can backup and restore data

  Scenario: Export application state
    Given the data is loaded
    When I export the app state
    Then I should get a dictionary with all data sections
    And the dictionary should have version and export_date

  Scenario: Import valid backup
    Given I have a valid backup JSON
    When I import the backup
    Then all data sections should be saved

  Scenario: Save backup to file
    Given I have application state
    When I save to backup
    Then a backup file should be created in the backup directory
