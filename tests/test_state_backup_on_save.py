"""Every successful state push also commits a dated copy to backup/ on GitHub.

The app falls back to the newest backup/gco_backup_*.json after a restart, so that
file must always hold the latest state (an old one there wiped 28 rounds once).
"""
import base64
import json
import re

import pytest
import streamlit

import data

STATE = {"version": 3, "scores": [{"Player": "李扬", "Game": "Game 5", "Gross_Score": 100}], "cup": {}}


class _Response:
    def __init__(self, status=200, body=b"{}"):
        self.status, self._body = status, body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def github(monkeypatch):
    """Records requests to the GitHub API; `fail` lists URL fragments whose PUT fails."""
    calls, settings = [], {"fail": ()}
    monkeypatch.setattr(streamlit, "secrets", {
        "GITHUB_TOKEN": "t", "GITHUB_REPO": "owner/repo", "GITHUB_DATA_PATH": "gco_state_live.json",
    })

    def fake_urlopen(request, timeout=None):
        method = request.get_method()
        calls.append((method, request.full_url, request.data))
        if method == "PUT" and any(part in request.full_url for part in settings["fail"]):
            raise OSError("boom")
        return _Response(200, json.dumps({"sha": "abc"}).encode())

    monkeypatch.setattr(data.urllib.request, "urlopen", fake_urlopen)
    return calls, settings


def _puts(calls):
    return [(url, json.loads(body)) for method, url, body in calls if method == "PUT"]


def test_successful_push_also_commits_a_dated_backup_with_the_same_state(github):
    calls, _ = github
    assert data.github_push_state(STATE) is True

    puts = _puts(calls)
    assert [url.rsplit("/contents/", 1)[1].split("/")[0] for url, _ in puts] == ["gco_state_live.json", "backup"]
    backup_url, backup_payload = puts[1]
    assert re.fullmatch(r".*/repos/owner/repo/contents/backup/gco_backup_\d{8}_\d{6}\.json", backup_url)
    assert json.loads(base64.b64decode(backup_payload["content"])) == STATE
    assert "sha" not in backup_payload, "a new file each time, never an overwrite"


def test_backup_name_is_found_as_the_newest_by_the_startup_fallback(github, tmp_path, monkeypatch):
    calls, _ = github
    data.github_push_state(STATE)
    name = _puts(calls)[1][0].rsplit("/", 1)[1]
    (tmp_path / "gco_backup_20260717_163523.json").write_text(json.dumps({"scores": []}), encoding="utf-8")
    (tmp_path / name).write_text(json.dumps(STATE, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(data, "BACKUP_DIR", tmp_path)

    loaded, path = data._load_latest_backup()
    assert path.name == name and loaded == STATE


def test_failed_state_push_writes_no_backup(github):
    calls, settings = github
    settings["fail"] = ("gco_state_live.json",)
    assert data.github_push_state(STATE) is False
    assert not any("/backup/" in url for url, _ in _puts(calls))


def test_failed_backup_does_not_fail_the_save(github):
    calls, settings = github
    settings["fail"] = ("/backup/",)
    assert data.github_push_state(STATE) is True
