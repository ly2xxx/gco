# GCO Backup Management Features

Feature: Backup Management
  As a system admin
  I need to manage backup files
  So that I can restore previous states

  Scenario: List available backups
    Given backup files exist in the backup directory
    When I list the backups
    Then I should get a list of backups sorted by date

  Scenario: Compute diff between backup and current
    Given I have a backup and current state
    When I compute the diff
    Then I should get a dictionary showing differences
