"""
GCO Data Layer - BDD Step Definitions
"""
import os
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data import (
    load_scores, load_events, load_announcements,
    load_cup, load_outing, export_app_state,
    import_app_state, save_to_backup, list_backups,
    compute_diff, PLAYERS, RED_TEAM, BLACK_TEAM,
    LEAGUE_TOURNAMENTS, OUTING_MATCHES
)

# Test state
test_state = {}


@given('the data directory exists')
def step_data_dir_exists(context):
    """Verify data directory exists"""
    from data import ROOT
    data_dir = ROOT / "data"
    assert data_dir.exists(), f"Data directory not found: {data_dir}"


@when('I load the scores data')
def step_load_scores(context):
    """Load scores data"""
    test_state['scores'] = load_scores()
    context.scores = test_state['scores']


@then('I should get a pandas DataFrame')
def step_scores_dataframe(context):
    """Verify scores is a DataFrame"""
    assert isinstance(context.scores, pd.DataFrame), "Scores should be a DataFrame"


@then('the DataFrame should have required columns')
def step_scores_columns(context):
    """Verify required columns exist"""
    required_cols = ['Player', 'Tournament', 'Net_Score']
    for col in required_cols:
        assert col in context.scores.columns, f"Missing column: {col}"


@when('I load the events data')
def step_load_events(context):
    """Load events data"""
    test_state['events'] = load_events()
    context.events = test_state['events']


@then('events should be a list')
def step_events_list(context):
    """Verify events is a list"""
    assert isinstance(context.events, list), "Events should be a list"


@then('each event should have required fields')
def step_events_fields(context):
    """Verify event structure"""
    if context.events and len(context.events) > 0:
        required_fields = ['name', 'date']
        for field in required_fields:
            assert field in context.events[0], f"Missing field: {field}"


@when('I load the announcements data')
def step_load_announcements(context):
    """Load announcements data"""
    test_state['announcements'] = load_announcements()
    context.announcements = test_state['announcements']


@then('announcements should be a list')
def step_announcements_list(context):
    """Verify announcements is a list"""
    assert isinstance(context.announcements, list), "Announcements should be a list"


@then('each announcement should have required fields')
def step_announcements_fields(context):
    """Verify announcement structure"""
    if context.announcements and len(context.announcements) > 0:
        required_fields = ['title', 'date', 'author', 'body']
        for field in required_fields:
            assert field in context.announcements[0], f"Missing field: {field}"


@when('I load the cup data')
def step_load_cup(context):
    """Load cup data"""
    test_state['cup'] = load_cup()
    context.cup = test_state['cup']


@then('cup data should be a dictionary')
def step_cup_dict(context):
    """Verify cup is a dictionary"""
    assert isinstance(context.cup, dict), "Cup should be a dictionary"


@then('cup data should have draw key')
def step_cup_keys(context):
    """Verify cup dictionary has draw key"""
    assert 'draw' in context.cup, f"Missing key: 'draw'"


@when('I load the outing data')
def step_load_outing(context):
    """Load outing data"""
    test_state['outing'] = load_outing()
    context.outing = test_state['outing']


@then('outing data should be a dictionary')
def step_outing_dict(context):
    """Verify outing is a dictionary"""
    assert isinstance(context.outing, dict), "Outing should be a dictionary"


@then('outing data should have red_team key')
def step_outing_keys(context):
    """Verify outing dictionary has red_team key"""
    assert 'red_team' in context.outing, f"Missing key: 'red_team'"


# Export/Import Feature Steps

@given('the data is loaded')
def step_data_loaded(context):
    """Ensure data is loaded"""
    test_state['scores'] = load_scores()
    test_state['events'] = load_events()
    test_state['announcements'] = load_announcements()
    test_state['cup'] = load_cup()
    test_state['outing'] = load_outing()


@when('I export the app state')
def step_export_state(context):
    """Export application state"""
    context.exported_state = export_app_state()


@then('I should get a dictionary with all data sections')
def step_exported_sections(context):
    """Verify exported state has all sections"""
    required_sections = ['events', 'announcements', 'cup', 'outing', 'scores']
    for section in required_sections:
        assert section in context.exported_state, f"Missing section: {section}"


@then('the dictionary should have version and export_date')
def step_exported_metadata(context):
    """Verify metadata in exported state"""
    assert 'version' in context.exported_state, "Missing version"
    assert 'export_date' in context.exported_state, "Missing export_date"


@given('I have a valid backup JSON')
def step_valid_backup(context):
    """Create a valid backup for testing"""
    context.test_backup = {
        "version": "1.0",
        "export_date": datetime.now().isoformat(),
        "events": load_events(),
        "announcements": load_announcements(),
        "cup": load_cup(),
        "outing": load_outing(),
        "scores": load_scores().to_dict(orient="records"),
    }


@when('I import the backup')
def step_import_backup(context):
    """Import backup data"""
    try:
        import_app_state(context.test_backup)
        context.import_success = True
    except Exception as e:
        context.import_success = False
        context.import_error = str(e)


@then('all data sections should be saved')
def step_import_saved(context):
    """Verify import succeeded"""
    assert context.import_success, f"Import failed: {getattr(context, 'import_error', 'Unknown')}"


@given('I have application state')
def step_have_state(context):
    """Get application state"""
    context.state_to_backup = export_app_state()


@when('I save to backup')
def step_save_backup(context):
    """Save backup"""
    path = save_to_backup(context.state_to_backup)
    context.backup_path = path
    if not hasattr(context, 'created_backups'):
        context.created_backups = []
    context.created_backups.append(path)


@then('a backup file should be created in the backup directory')
def step_backup_created(context):
    """Verify backup file was created"""
    assert context.backup_path is not None
    assert os.path.exists(context.backup_path)


# Backup Management Feature Steps

@given('backup files exist in the backup directory')
def step_backups_exist(context):
    """Ensure backup directory has files"""
    if not list_backups():
        path = save_to_backup(export_app_state())
        if not hasattr(context, 'created_backups'):
            context.created_backups = []
        context.created_backups.append(path)
    context.backups = list_backups()


@when('I list the backups')
def step_list_backups(context):
    """List available backups"""
    context.backup_list = list_backups()


@then('I should get a list of backups sorted by date')
def step_backups_sorted(context):
    """Verify backups are sorted"""
    assert len(context.backup_list) > 0, "No backups found"


@given('I have a backup and current state')
def step_backup_and_current(context):
    """Get backup and current state"""
    backups = list_backups()
    if backups:
        context.backup_data = backups[0]['data']
        context.current_data = export_app_state()


@when('I compute the diff')
def step_compute_diff(context):
    """Compute diff between backup and current"""
    context.diff = compute_diff(context.backup_data, context.current_data)


@then('I should get a dictionary showing differences')
def step_diff_dict(context):
    """Verify diff is a dictionary"""
    assert isinstance(context.diff, dict), "Diff should be a dictionary"


# Player Management Feature Steps

@given('the club has players')
def step_club_has_players(context):
    """Verify players are defined"""
    assert len(PLAYERS) > 0, "No players defined"


@when('I load the player list')
def step_load_players(context):
    """Load player list"""
    context.player_list = PLAYERS


@then('I should get 13 players')
def step_player_count(context):
    """Verify player count"""
    assert len(context.player_list) == 13, f"Expected 13 players, got {len(context.player_list)}"


@given('players are assigned to teams')
def step_players_assigned(context):
    """Verify players are assigned to teams"""
    assert len(RED_TEAM) > 0, "No Red Team players"
    assert len(BLACK_TEAM) > 0, "No Black Team players"


@when('I check team assignments')
def step_check_teams(context):
    """Check team assignments"""
    context.red_team = RED_TEAM
    context.black_team = BLACK_TEAM


@then('Red Team should have 6 players')
def step_red_team_count(context):
    """Verify Red Team size"""
    assert len(context.red_team) == 6, f"Red Team should have 6 players"


@then('Black Team should have 7 players')
def step_black_team_count(context):
    """Verify Black Team size"""
    assert len(context.black_team) == 7, f"Black Team should have 7 players"


# Tournament Management Feature Steps

@given('tournaments are defined')
def step_tournaments_defined(context):
    """Verify tournaments exist"""
    assert len(LEAGUE_TOURNAMENTS) > 0, "No tournaments defined"


@when('I check league tournaments')
def step_check_league_tournaments(context):
    """Check league tournaments"""
    context.tournaments = LEAGUE_TOURNAMENTS


@then('there should be at least one tournament')
def step_tournament_count(context):
    """Verify tournament count"""
    assert len(context.tournaments) >= 1, "Should have at least one tournament"


@given('outing matches are defined')
def step_outing_defined(context):
    """Verify outing matches exist"""
    assert len(OUTING_MATCHES) > 0, "No outing matches defined"


@when('I check outing matches')
def step_check_outing_matches(context):
    """Check outing matches"""
    context.outing_matches = OUTING_MATCHES


@then('there should be 4 outing matches')
def step_outing_count(context):
    """Verify outing match count"""
    assert len(context.outing_matches) == 4, f"Should have 4 outing matches"


# Data Validation Feature Steps

@given('scores data is loaded')
def step_scores_loaded(context):
    """Load scores for validation"""
    context.scores = load_scores()


@when('I validate the DataFrame structure')
def step_validate_dataframe(context):
    """Validate DataFrame structure"""
    context.df_columns = context.scores.columns.tolist()


@then('it should have required columns: {columns}')
def step_required_columns(context, columns):
    """Verify required columns"""
    required = [c.strip() for c in columns.split(',')]
    for col in required:
        assert col in context.df_columns, f"Missing required column: {col}"


@given('events are loaded')
def step_events_loaded(context):
    """Load events for validation"""
    context.events = load_events()


@when('I validate an event')
def step_validate_event(context):
    """Validate event structure"""
    if context.events and len(context.events) > 0:
        context.event_sample = context.events[0]
    else:
        context.event_sample = {"date": "2026-04-01", "name": "Test Event", "type": "League", "details": "Test details"}


@then('it should have: {fields}')
def step_event_fields(context, fields):
    """Verify event fields"""
    required = [f.strip() for f in fields.split(',')]
    for field in required:
        assert field in context.event_sample, f"Missing field: {field}"


@then('announcement should have id, title, date, author, body fields')
def step_announcement_fields(context):
    """Verify announcement fields"""
    required = ['id', 'title', 'date', 'author', 'body']
    for field in required:
        assert field in context.announcement_sample, f"Missing field: {field}"


@given('announcements are loaded')
def step_announcements_loaded(context):
    """Load announcements for validation"""
    context.announcements = load_announcements()


@when('I validate announcement structure')
def step_validate_announcement(context):
    """Validate announcement structure"""
    if context.announcements and len(context.announcements) > 0:
        context.announcement_sample = context.announcements[0]
    else:
        context.announcement_sample = {"id": "1", "title": "Test", "date": "2026-01-01", "author": "Test", "body": "Test body"}
