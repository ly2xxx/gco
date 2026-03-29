"""
Basic test suite for GCO Golf League Data Layer
"""
import pytest
import pandas as pd
import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pages.data import (
    load_scores,
    load_events,
    load_announcements,
    load_cup,
    load_outing
)

def test_load_scores():
    """Test that scores load properly as a DataFrame"""
    df = load_scores()
    assert isinstance(df, pd.DataFrame)
    if not df.empty:
        assert 'Player' in df.columns
        assert 'Tournament' in df.columns
        assert 'Net_Score' in df.columns

def test_load_events():
    """Test events load properly"""
    events = load_events()
    assert isinstance(events, list)
    if events:
        assert 'name' in events[0]
        assert 'date' in events[0]

def test_load_announcements():
    """Test announcements load properly"""
    announcements = load_announcements()
    assert isinstance(announcements, list)
    if announcements:
        assert 'title' in announcements[0]

def test_load_cup():
    """Test cup data loads properly"""
    cup = load_cup()
    assert isinstance(cup, dict)
    assert 'draw' in cup
    assert 'rounds' in cup

def test_load_outing():
    """Test outing data loads properly"""
    outing = load_outing()
    assert isinstance(outing, dict)
    assert 'red_team' in outing
    assert 'matches' in outing

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
