"""The League page must survive a redeploy that changes league_scorecard.py.

A running Streamlit app keeps modules it imported earlier in sys.modules, so after
a redeploy the page re-runs with the new source but used to get the old
league_scorecard module and fail with ImportError (seen on Streamlit Cloud after
feature 012 shipped). The scenario runs in a subprocess so the reload it triggers
can't leak into other tests' imports.
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SCENARIO = r'''
import sys
sys.path.insert(0, ".")
from streamlit.testing.v1 import AppTest
import league_scorecard

# What the running app holds after a redeploy: the module from before the new names existed.
del league_scorecard.LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY
del league_scorecard.read_league_scorecard_players
league_scorecard.LOADED_FROM_MTIME = -1.0

at = AppTest.from_file("pages/3_\U0001f3c6_League.py", default_timeout=60).run()
errors = [e.value for e in at.exception]
print("EXCEPTIONS:", errors)
print("RELOADED:", hasattr(league_scorecard, "LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY"))
sys.exit(1 if errors else 0)
'''


def test_page_reloads_a_stale_league_scorecard_module():
    proc = subprocess.run(
        [sys.executable, "-c", SCENARIO],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "RELOADED: True" in proc.stdout, proc.stdout


def test_module_records_the_file_it_was_loaded_from():
    import os

    import league_scorecard

    assert league_scorecard.LOADED_FROM_MTIME == os.path.getmtime(league_scorecard.__file__)
