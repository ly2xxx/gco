"""
GCO 2026 – shared data definitions and sample data generators.
All pages import from here so the schema stays consistent.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from datetime import date, datetime
import json, os, pathlib, base64, urllib.request, urllib.error, urllib.parse

# ── root data directory ──────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
BACKUP_DIR = ROOT / "backup"
BACKUP_DIR.mkdir(exist_ok=True)

def _load_latest_backup() -> tuple[dict | None, pathlib.Path | None]:
    """Scan backup/ folder for latest gco_backup_*.json file."""
    try:
        backups = sorted(BACKUP_DIR.glob("gco_backup_*.json"), reverse=True)
        if backups:
            return json.loads(backups[0].read_text(encoding="utf-8")), backups[0]
    except:
        pass
    return None, None

def save_to_backup(state_data: dict) -> str:
    """Save app state to backup folder with timestamp."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = BACKUP_DIR / f"gco_backup_{ts}.json"
    path.write_text(json.dumps(state_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)

# ── GitHub persistence helpers ────────────────────────────────────────────────
# Stores the entire app state as a single JSON file in the GitHub repo.
# Requires these keys in .streamlit/secrets.toml (and Streamlit Cloud secrets):
#   GITHUB_TOKEN     – Personal Access Token with repo (contents:write) scope
#   GITHUB_REPO      – "owner/repo-name" e.g. "alice/gco"
#   GITHUB_DATA_PATH – path inside repo, default "gco_state.json"

def _gh_headers() -> dict | None:
    """Return GitHub API auth headers, or None if secrets are not configured."""
    try:
        import streamlit as st
        token = st.secrets.get("GITHUB_TOKEN", "")
        if not token:
            return None
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        }
    except Exception:
        return None

def _gh_api_url() -> str | None:
    """Return the GitHub Contents API URL for the state file, or None."""
    try:
        import streamlit as st
        repo = st.secrets.get("GITHUB_REPO", "")
        path = st.secrets.get("GITHUB_DATA_PATH", "gco_state.json")
        if not repo:
            return None
        return f"https://api.github.com/repos/{repo}/contents/{path}"
    except Exception:
        return None

def github_load_state() -> dict | None:
    """Fetch persisted app state from GitHub. Returns None if unavailable."""
    headers = _gh_headers()
    url = _gh_api_url()
    if not headers or not url:
        return None
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read())
            content = base64.b64decode(payload["content"]).decode("utf-8")
            return json.loads(content)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None  # File not yet created in repo – first push will create it
        return None
    except Exception:
        return None

def github_push_state(state: dict) -> bool:
    """Push the full app state dict to GitHub. Returns True on success."""
    headers = _gh_headers()
    url = _gh_api_url()
    if not headers or not url:
        return False
    try:
        # Fetch the current file SHA so GitHub accepts the update.
        current_sha: str | None = None
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                current_sha = json.loads(resp.read()).get("sha")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                return False  # Unexpected error – bail out

        content_b64 = base64.b64encode(
            json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("ascii")

        payload: dict = {
            "message": f"chore: auto-save GCO state [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC]",
            "content": content_b64,
        }
        if current_sha:
            payload["sha"] = current_sha

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="PUT")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 201)
    except Exception:
        return False

def github_upload_image(file_bytes: bytes, file_name: str) -> bool:
    """Upload an image to GitHub repository under 'scorecard_images/' folder."""
    try:
        import streamlit as st
        token = st.secrets.get("GITHUB_TOKEN", "")
        repo = st.secrets.get("GITHUB_REPO", "")
        if not token or not repo:
            return False
            
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        }
        
        quoted_file_name = urllib.parse.quote(file_name)
        url = f"https://api.github.com/repos/{repo}/contents/scorecard_images/{quoted_file_name}"
        
        content_b64 = base64.b64encode(file_bytes).decode("ascii")
        payload = {
            "message": f"Upload scorecard image: {file_name}",
            "content": content_b64,
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="PUT")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 201)
    except Exception as e:
        print(f"Error uploading image to GitHub: {e}")
        return False

def _sync_github_to_local(gh_state: dict) -> None:
    """Write the GitHub state dict to local data/ files (only when missing)."""
    def _missing(fname: str) -> bool:
        return not (DATA_DIR / fname).exists()

    if _missing("scores.csv") and "scores" in gh_state:
        pd.DataFrame(gh_state["scores"]).to_csv(DATA_DIR / "scores.csv", index=False)
    if _missing("announcements.json") and "announcements" in gh_state:
        (DATA_DIR / "announcements.json").write_text(
            json.dumps(gh_state["announcements"], ensure_ascii=False, indent=2), encoding="utf-8")
    if _missing("events.json") and "events" in gh_state:
        (DATA_DIR / "events.json").write_text(
            json.dumps(gh_state["events"], ensure_ascii=False, indent=2), encoding="utf-8")
    if _missing("cup.json") and "cup" in gh_state:
        (DATA_DIR / "cup.json").write_text(
            json.dumps(gh_state["cup"], ensure_ascii=False, indent=2), encoding="utf-8")
    if _missing("outing.json") and "outing" in gh_state:
        (DATA_DIR / "outing.json").write_text(
            json.dumps(gh_state["outing"], ensure_ascii=False, indent=2), encoding="utf-8")

# ── Startup hydration ──────────────────────────────────────────────────────────
# Priority: GitHub (authoritative) → local backup/ → defaults
_GH_STATE = github_load_state()
if _GH_STATE:
    _sync_github_to_local(_GH_STATE)

# Initialize global fallback state from latest backup if available
_GLOBAL_BACKUP, _LATEST_BACKUP_PATH = _load_latest_backup()

def _sync_backup_to_local() -> None:
    if not _GLOBAL_BACKUP or not _LATEST_BACKUP_PATH: return
    backup_mtime = _LATEST_BACKUP_PATH.stat().st_mtime
    
    def is_backup_newer(file_name):
        file_path = DATA_DIR / file_name
        if not file_path.exists(): return True
        return backup_mtime > file_path.stat().st_mtime
        
    if is_backup_newer("scores.csv") and "scores" in _GLOBAL_BACKUP:
        pd.DataFrame(_GLOBAL_BACKUP["scores"]).to_csv(DATA_DIR / "scores.csv", index=False)
    if is_backup_newer("announcements.json") and "announcements" in _GLOBAL_BACKUP:
        (DATA_DIR / "announcements.json").write_text(json.dumps(_GLOBAL_BACKUP["announcements"], ensure_ascii=False, indent=2), encoding="utf-8")
    if is_backup_newer("events.json") and "events" in _GLOBAL_BACKUP:
        (DATA_DIR / "events.json").write_text(json.dumps(_GLOBAL_BACKUP["events"], ensure_ascii=False, indent=2), encoding="utf-8")
    if is_backup_newer("cup.json") and "cup" in _GLOBAL_BACKUP:
        (DATA_DIR / "cup.json").write_text(json.dumps(_GLOBAL_BACKUP["cup"], ensure_ascii=False, indent=2), encoding="utf-8")
    if is_backup_newer("outing.json") and "outing" in _GLOBAL_BACKUP:
        (DATA_DIR / "outing.json").write_text(json.dumps(_GLOBAL_BACKUP["outing"], ensure_ascii=False, indent=2), encoding="utf-8")

_sync_backup_to_local()

# ── Club constants ────────────────────────────────────────────────────────────
CLUB_NAME = "GCO Golf Club"
SEASON = "2026"

PLAYERS: list[str] = [
    "刘北南", "Jacky", "赵鲲", "杨子初", "Neo", "徐峥",
    "张纬", "曹振波", "李扬", "王文龙", "曾诚", "Justin", "杨明"
]

# Red / Black team assignment (6 each)
RED_TEAM  = PLAYERS[:6]
BLACK_TEAM = PLAYERS[6:]

# Individual league tournaments (联赛)
LEAGUE_TOURNAMENTS: dict[str, dict] = {
    "2026个人联赛": {"period": "2026-04-01 ~ 2026-09-30", "games": 6},
}

# Team match types (now referred to as Outing Days)
OUTING_MATCHES: list[dict] = [
    {"id": "om1", "name": "Outing Day 1: Fourball Betterball Match Play",  "format": "doubles", "hcp_allowance": "90%"},
    {"id": "om2", "name": "Outing Day 2: Fourball Betterball Stableford",  "format": "doubles", "hcp_allowance": "85%"},
    {"id": "om3", "name": "Outing Day 3: 2-Man Scramble",                  "format": "doubles", "hcp_allowance": "35%/15%"},
    {"id": "om4", "name": "Outing Day 4: 4-Man Scramble",                  "format": "fours",   "hcp_allowance": "25%/20%/15%/10%"},
]

# ── Upcoming events (editable JSON) ──────────────────────────────────────────
EVENTS_FILE = DATA_DIR / "events.json"

DEFAULT_EVENTS: list[dict] = [
    {
        "date": "2026-04-04",
        "name": "联赛第1轮 - Stroke Play",
        "type": "League",
        "details": "Stroke Play, OOM Qualifying"
    },
    {
        "date": "2026-04-12",
        "name": "个人杯赛第一轮开始",
        "type": "Cup",
        "details": "Knockout Match Play, R1 fixtures announced"
    },
    {
        "date": "2026-04-26",
        "name": "Outing Day 1 (Team Match)",
        "type": "Outing",
        "details": "Format: Fourball Betterball Match Play"
    },
    {
        "date": "2026-05-17",
        "name": "联赛第2轮 - Stroke Play",
        "type": "League",
        "details": "Stroke Play, OOM Qualifying"
    },
    {
        "date": "2026-05-31",
        "name": "Outing Day 2 (Team Match)",
        "type": "Outing",
        "details": "Format: Fourball Betterball Stableford"
    },
    {
        "date": "2026-06-07",
        "name": "联赛第3轮 - Stroke Play",
        "type": "League",
        "details": "Stroke Play, OOM Qualifying"
    },
    {
        "date": "2026-06-14",
        "name": "个人杯赛半决赛",
        "type": "Cup",
        "details": "Knockout Match Play Semi-Finals"
    },
    {
        "date": "2026-06-21",
        "name": "Outing Day 3 (Team Match)",
        "type": "Outing",
        "details": "Format: 2-Man Scramble + League Game 4"
    },
    {
        "date": "2026-07-19",
        "name": "联赛第5轮 - Stroke Play",
        "type": "League",
        "details": "Stroke Play, OOM Qualifying"
    },
    {
        "date": "2026-08-09",
        "name": "联赛第6轮 - Stroke Play",
        "type": "League",
        "details": "Stroke Play, OOM Qualifying"
    },
    {
        "date": "2026-08-23",
        "name": "Outing Day 4 (Team Match)",
        "type": "Outing",
        "details": "Format: 4-Man Scramble + Cup Final"
    },
    {
        "date": "2026-09-13",
        "name": "年终总决赛",
        "type": "Grand Final",
        "details": "36-Hole Stroke Play + Beat the Champion"
    }
]


def load_events() -> list[dict]:
    if EVENTS_FILE.exists():
        return json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    if _GLOBAL_BACKUP and "events" in _GLOBAL_BACKUP:
        return _GLOBAL_BACKUP["events"]
    return DEFAULT_EVENTS

def save_events(events: list[dict]) -> None:
    EVENTS_FILE.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    _schedule_github_push()

# ── Announcements ─────────────────────────────────────────────────────────────
ANNOUNCEMENTS_FILE = DATA_DIR / "announcements.json"

DEFAULT_ANNOUNCEMENTS: list[dict] = [
    {
        "id": "ann-001",
        "title": "🏌️ 2026赛季正式开幕！",
        "date": "2026-03-29",
        "author": "组委会",
        "pinned": True,
        "body": "全体GCO成员，2026赛季即将拉开帷幕！\n\n**赛历亮点：**\n- 个人联赛：6场 18-Hole Stroke Play，排名前三晋级总决赛\n- 个人杯赛：Knockout Match Play，12人单场淘汰赛决出冠军\n- 团队赛：红队 vs 黑队，4场 Outing Day 积分对抗赛\n- 年终总决赛：36洞Stroke Play，排名前三+杯赛冠军\n\n请所有成员确认Scottish Golf账户有效，并关注微信群通知。\n\n预祝大家2026赛季愉快！⛳",
        "tags": [
            "赛季开幕",
            "重要"
        ]
    },
    {
        "id": "ann-002",
        "title": "📋 个人杯赛抽签结果公布",
        "date": "2026-03-29",
        "author": "组委会",
        "pinned": False,
        "body": "个人杯赛（Knockout Match Play）抽签已完成。\n\n**第一轮（April）对阵：**\n- P3 vs P4｜P5 vs P6｜P9 vs P10｜P11 vs P12\n\nP1、P2、P7、P8自动晋级第二轮。\n\n拥有主场权的选手请尽早联系对手确认比赛时间和场地。",
        "tags": [
            "杯赛",
            "抽签"
        ]
    }
]


def load_announcements() -> list[dict]:
    if ANNOUNCEMENTS_FILE.exists():
        return json.loads(ANNOUNCEMENTS_FILE.read_text(encoding="utf-8"))
    if _GLOBAL_BACKUP and "announcements" in _GLOBAL_BACKUP:
        return _GLOBAL_BACKUP["announcements"]
    return DEFAULT_ANNOUNCEMENTS

def save_announcements(anns: list[dict]) -> None:
    ANNOUNCEMENTS_FILE.write_text(json.dumps(anns, ensure_ascii=False, indent=2), encoding="utf-8")
    _schedule_github_push()

# ── League score data ─────────────────────────────────────────────────────────
SCORES_FILE = DATA_DIR / "scores.csv"

def _sample_scores() -> pd.DataFrame:
    return pd.DataFrame([
    {
        "Player": "刘北南",
        "Tournament": "2026个人联赛",
        "Game": "Game 1",
        "Game_No": 1,
        "Net_Score": -8,
        "Gross_Score": 93,
        "Birdies": 3,
        "Pars": 8,
        "Bogeys": 3,
        "Double_Bogeys": 3,
        "Eagles": 0,
        "Stableford": 37
    },
    {
        "Player": "Jacky",
        "Tournament": "2026个人联赛",
        "Game": "Game 1",
        "Game_No": 1,
        "Net_Score": -4,
        "Gross_Score": 72,
        "Birdies": 2,
        "Pars": 13,
        "Bogeys": 5,
        "Double_Bogeys": 3,
        "Eagles": 1,
        "Stableford": 39
    },
    {
        "Player": "赵鲲",
        "Tournament": "2026个人联赛",
        "Game": "Game 1",
        "Game_No": 1,
        "Net_Score": 5,
        "Gross_Score": 73,
        "Birdies": 4,
        "Pars": 8,
        "Bogeys": 3,
        "Double_Bogeys": 1,
        "Eagles": 0,
        "Stableford": 40
    },
    {
        "Player": "杨子初",
        "Tournament": "2026个人联赛",
        "Game": "Game 1",
        "Game_No": 1,
        "Net_Score": 13,
        "Gross_Score": 89,
        "Birdies": 2,
        "Pars": 12,
        "Bogeys": 3,
        "Double_Bogeys": 1,
        "Eagles": 0,
        "Stableford": 31
    },
    {
        "Player": "杨明",
        "Tournament": "2026个人联赛",
        "Game": "Game 1",
        "Game_No": 1,
        "Net_Score": 13,
        "Gross_Score": 89,
        "Birdies": 3,
        "Pars": 12,
        "Bogeys": 3,
        "Double_Bogeys": 0,
        "Eagles": 0,
        "Stableford": 31
    },
    {
        "Player": "Neo",
        "Tournament": "2026个人联赛",
        "Game": "Game 1",
        "Game_No": 1,
        "Net_Score": -8,
        "Gross_Score": 86,
        "Birdies": 4,
        "Pars": 4,
        "Bogeys": 6,
        "Double_Bogeys": 3,
        "Eagles": 0,
        "Stableford": 36
    },
    {
        "Player": "徐峥",
        "Tournament": "2026个人联赛",
        "Game": "Game 1",
        "Game_No": 1,
        "Net_Score": -6,
        "Gross_Score": 92,
        "Birdies": 3,
        "Pars": 7,
        "Bogeys": 0,
        "Double_Bogeys": 3,
        "Eagles": 0,
        "Stableford": 40
    },
    {
        "Player": "张纬",
        "Tournament": "2026个人联赛",
        "Game": "Game 1",
        "Game_No": 1,
        "Net_Score": 10,
        "Gross_Score": 93,
        "Birdies": 3,
        "Pars": 5,
        "Bogeys": 2,
        "Double_Bogeys": 1,
        "Eagles": 0,
        "Stableford": 28
    },
    {
        "Player": "曹振波",
        "Tournament": "2026个人联赛",
        "Game": "Game 1",
        "Game_No": 1,
        "Net_Score": 6,
        "Gross_Score": 74,
        "Birdies": 3,
        "Pars": 10,
        "Bogeys": 6,
        "Double_Bogeys": 2,
        "Eagles": 0,
        "Stableford": 41
    },
    {
        "Player": "李扬",
        "Tournament": "2026个人联赛",
        "Game": "Game 1",
        "Game_No": 1,
        "Net_Score": 2,
        "Gross_Score": 79,
        "Birdies": 4,
        "Pars": 7,
        "Bogeys": 0,
        "Double_Bogeys": 1,
        "Eagles": 1,
        "Stableford": 30
    },
    {
        "Player": "王文龙",
        "Tournament": "2026个人联赛",
        "Game": "Game 1",
        "Game_No": 1,
        "Net_Score": 3,
        "Gross_Score": 73,
        "Birdies": 3,
        "Pars": 8,
        "Bogeys": 2,
        "Double_Bogeys": 0,
        "Eagles": 1,
        "Stableford": 37
    },
    {
        "Player": "曾诚",
        "Tournament": "2026个人联赛",
        "Game": "Game 1",
        "Game_No": 1,
        "Net_Score": 18,
        "Gross_Score": 83,
        "Birdies": 0,
        "Pars": 12,
        "Bogeys": 4,
        "Double_Bogeys": 2,
        "Eagles": 0,
        "Stableford": 32
    },
    {
        "Player": "Justin",
        "Tournament": "2026个人联赛",
        "Game": "Game 1",
        "Game_No": 1,
        "Net_Score": 13,
        "Gross_Score": 94,
        "Birdies": 2,
        "Pars": 12,
        "Bogeys": 5,
        "Double_Bogeys": 1,
        "Eagles": 1,
        "Stableford": 32
    },
    {
        "Player": "刘北南",
        "Tournament": "2026个人联赛",
        "Game": "Game 2",
        "Game_No": 2,
        "Net_Score": -3,
        "Gross_Score": 90,
        "Birdies": 3,
        "Pars": 5,
        "Bogeys": 5,
        "Double_Bogeys": 0,
        "Eagles": 1,
        "Stableford": 28
    },
    {
        "Player": "Jacky",
        "Tournament": "2026个人联赛",
        "Game": "Game 2",
        "Game_No": 2,
        "Net_Score": 13,
        "Gross_Score": 93,
        "Birdies": 3,
        "Pars": 10,
        "Bogeys": 3,
        "Double_Bogeys": 2,
        "Eagles": 0,
        "Stableford": 38
    },
    {
        "Player": "赵鲲",
        "Tournament": "2026个人联赛",
        "Game": "Game 2",
        "Game_No": 2,
        "Net_Score": 6,
        "Gross_Score": 83,
        "Birdies": 2,
        "Pars": 9,
        "Bogeys": 0,
        "Double_Bogeys": 0,
        "Eagles": 0,
        "Stableford": 29
    },
    {
        "Player": "杨子初",
        "Tournament": "2026个人联赛",
        "Game": "Game 2",
        "Game_No": 2,
        "Net_Score": 3,
        "Gross_Score": 90,
        "Birdies": 3,
        "Pars": 8,
        "Bogeys": 5,
        "Double_Bogeys": 2,
        "Eagles": 0,
        "Stableford": 38
    },
    {
        "Player": "Neo",
        "Tournament": "2026个人联赛",
        "Game": "Game 2",
        "Game_No": 2,
        "Net_Score": 7,
        "Gross_Score": 89,
        "Birdies": 2,
        "Pars": 9,
        "Bogeys": 0,
        "Double_Bogeys": 2,
        "Eagles": 1,
        "Stableford": 32
    },
    {
        "Player": "徐峥",
        "Tournament": "2026个人联赛",
        "Game": "Game 2",
        "Game_No": 2,
        "Net_Score": 8,
        "Gross_Score": 70,
        "Birdies": 1,
        "Pars": 8,
        "Bogeys": 6,
        "Double_Bogeys": 0,
        "Eagles": 0,
        "Stableford": 33
    },
    {
        "Player": "张纬",
        "Tournament": "2026个人联赛",
        "Game": "Game 2",
        "Game_No": 2,
        "Net_Score": 19,
        "Gross_Score": 95,
        "Birdies": 0,
        "Pars": 6,
        "Bogeys": 5,
        "Double_Bogeys": 0,
        "Eagles": 1,
        "Stableford": 31
    },
    {
        "Player": "曹振波",
        "Tournament": "2026个人联赛",
        "Game": "Game 2",
        "Game_No": 2,
        "Net_Score": 17,
        "Gross_Score": 78,
        "Birdies": 2,
        "Pars": 10,
        "Bogeys": 0,
        "Double_Bogeys": 2,
        "Eagles": 1,
        "Stableford": 38
    },
    {
        "Player": "李扬",
        "Tournament": "2026个人联赛",
        "Game": "Game 2",
        "Game_No": 2,
        "Net_Score": 19,
        "Gross_Score": 89,
        "Birdies": 2,
        "Pars": 8,
        "Bogeys": 2,
        "Double_Bogeys": 3,
        "Eagles": 0,
        "Stableford": 30
    },
    {
        "Player": "王文龙",
        "Tournament": "2026个人联赛",
        "Game": "Game 2",
        "Game_No": 2,
        "Net_Score": 0,
        "Gross_Score": 70,
        "Birdies": 0,
        "Pars": 4,
        "Bogeys": 5,
        "Double_Bogeys": 2,
        "Eagles": 1,
        "Stableford": 34
    },
    {
        "Player": "曾诚",
        "Tournament": "2026个人联赛",
        "Game": "Game 2",
        "Game_No": 2,
        "Net_Score": 11,
        "Gross_Score": 74,
        "Birdies": 4,
        "Pars": 9,
        "Bogeys": 6,
        "Double_Bogeys": 0,
        "Eagles": 0,
        "Stableford": 37
    },
    {
        "Player": "Justin",
        "Tournament": "2026个人联赛",
        "Game": "Game 2",
        "Game_No": 2,
        "Net_Score": 4,
        "Gross_Score": 83,
        "Birdies": 0,
        "Pars": 7,
        "Bogeys": 1,
        "Double_Bogeys": 1,
        "Eagles": 1,
        "Stableford": 36
    },
    {
        "Player": "刘北南",
        "Tournament": "2026个人联赛",
        "Game": "Game 3",
        "Game_No": 3,
        "Net_Score": 8,
        "Gross_Score": 80,
        "Birdies": 4,
        "Pars": 4,
        "Bogeys": 2,
        "Double_Bogeys": 0,
        "Eagles": 0,
        "Stableford": 41
    },
    {
        "Player": "Jacky",
        "Tournament": "2026个人联赛",
        "Game": "Game 3",
        "Game_No": 3,
        "Net_Score": 0,
        "Gross_Score": 97,
        "Birdies": 2,
        "Pars": 10,
        "Bogeys": 3,
        "Double_Bogeys": 1,
        "Eagles": 1,
        "Stableford": 41
    },
    {
        "Player": "赵鲲",
        "Tournament": "2026个人联赛",
        "Game": "Game 3",
        "Game_No": 3,
        "Net_Score": -3,
        "Gross_Score": 93,
        "Birdies": 1,
        "Pars": 11,
        "Bogeys": 5,
        "Double_Bogeys": 1,
        "Eagles": 1,
        "Stableford": 31
    },
    {
        "Player": "杨子初",
        "Tournament": "2026个人联赛",
        "Game": "Game 3",
        "Game_No": 3,
        "Net_Score": -8,
        "Gross_Score": 72,
        "Birdies": 2,
        "Pars": 13,
        "Bogeys": 0,
        "Double_Bogeys": 1,
        "Eagles": 1,
        "Stableford": 30
    },
    {
        "Player": "Neo",
        "Tournament": "2026个人联赛",
        "Game": "Game 3",
        "Game_No": 3,
        "Net_Score": 11,
        "Gross_Score": 79,
        "Birdies": 4,
        "Pars": 9,
        "Bogeys": 3,
        "Double_Bogeys": 0,
        "Eagles": 0,
        "Stableford": 39
    },
    {
        "Player": "徐峥",
        "Tournament": "2026个人联赛",
        "Game": "Game 3",
        "Game_No": 3,
        "Net_Score": -10,
        "Gross_Score": 92,
        "Birdies": 2,
        "Pars": 11,
        "Bogeys": 4,
        "Double_Bogeys": 1,
        "Eagles": 0,
        "Stableford": 36
    },
    {
        "Player": "张纬",
        "Tournament": "2026个人联赛",
        "Game": "Game 3",
        "Game_No": 3,
        "Net_Score": -6,
        "Gross_Score": 87,
        "Birdies": 0,
        "Pars": 10,
        "Bogeys": 4,
        "Double_Bogeys": 0,
        "Eagles": 1,
        "Stableford": 33
    },
    {
        "Player": "曹振波",
        "Tournament": "2026个人联赛",
        "Game": "Game 3",
        "Game_No": 3,
        "Net_Score": 13,
        "Gross_Score": 71,
        "Birdies": 0,
        "Pars": 8,
        "Bogeys": 1,
        "Double_Bogeys": 1,
        "Eagles": 1,
        "Stableford": 30
    },
    {
        "Player": "李扬",
        "Tournament": "2026个人联赛",
        "Game": "Game 3",
        "Game_No": 3,
        "Net_Score": 10,
        "Gross_Score": 73,
        "Birdies": 0,
        "Pars": 9,
        "Bogeys": 5,
        "Double_Bogeys": 0,
        "Eagles": 0,
        "Stableford": 40
    },
    {
        "Player": "王文龙",
        "Tournament": "2026个人联赛",
        "Game": "Game 3",
        "Game_No": 3,
        "Net_Score": 19,
        "Gross_Score": 87,
        "Birdies": 2,
        "Pars": 7,
        "Bogeys": 4,
        "Double_Bogeys": 2,
        "Eagles": 0,
        "Stableford": 28
    },
    {
        "Player": "曾诚",
        "Tournament": "2026个人联赛",
        "Game": "Game 3",
        "Game_No": 3,
        "Net_Score": -6,
        "Gross_Score": 98,
        "Birdies": 2,
        "Pars": 8,
        "Bogeys": 3,
        "Double_Bogeys": 3,
        "Eagles": 0,
        "Stableford": 29
    },
    {
        "Player": "Justin",
        "Tournament": "2026个人联赛",
        "Game": "Game 3",
        "Game_No": 3,
        "Net_Score": -2,
        "Gross_Score": 84,
        "Birdies": 3,
        "Pars": 8,
        "Bogeys": 3,
        "Double_Bogeys": 3,
        "Eagles": 0,
        "Stableford": 36
    },
    {
        "Player": "刘北南",
        "Tournament": "2026个人联赛",
        "Game": "Game 4",
        "Game_No": 4,
        "Net_Score": 6,
        "Gross_Score": 84,
        "Birdies": 4,
        "Pars": 6,
        "Bogeys": 6,
        "Double_Bogeys": 1,
        "Eagles": 1,
        "Stableford": 35
    },
    {
        "Player": "Jacky",
        "Tournament": "2026个人联赛",
        "Game": "Game 4",
        "Game_No": 4,
        "Net_Score": 15,
        "Gross_Score": 83,
        "Birdies": 1,
        "Pars": 4,
        "Bogeys": 2,
        "Double_Bogeys": 3,
        "Eagles": 0,
        "Stableford": 40
    },
    {
        "Player": "赵鲲",
        "Tournament": "2026个人联赛",
        "Game": "Game 4",
        "Game_No": 4,
        "Net_Score": 6,
        "Gross_Score": 74,
        "Birdies": 1,
        "Pars": 9,
        "Bogeys": 2,
        "Double_Bogeys": 0,
        "Eagles": 1,
        "Stableford": 37
    },
    {
        "Player": "杨子初",
        "Tournament": "2026个人联赛",
        "Game": "Game 4",
        "Game_No": 4,
        "Net_Score": -7,
        "Gross_Score": 78,
        "Birdies": 1,
        "Pars": 10,
        "Bogeys": 5,
        "Double_Bogeys": 2,
        "Eagles": 1,
        "Stableford": 38
    },
    {
        "Player": "Neo",
        "Tournament": "2026个人联赛",
        "Game": "Game 4",
        "Game_No": 4,
        "Net_Score": -1,
        "Gross_Score": 73,
        "Birdies": 3,
        "Pars": 13,
        "Bogeys": 6,
        "Double_Bogeys": 0,
        "Eagles": 0,
        "Stableford": 28
    },
    {
        "Player": "徐峥",
        "Tournament": "2026个人联赛",
        "Game": "Game 4",
        "Game_No": 4,
        "Net_Score": -6,
        "Gross_Score": 86,
        "Birdies": 2,
        "Pars": 7,
        "Bogeys": 2,
        "Double_Bogeys": 3,
        "Eagles": 0,
        "Stableford": 39
    },
    {
        "Player": "张纬",
        "Tournament": "2026个人联赛",
        "Game": "Game 4",
        "Game_No": 4,
        "Net_Score": 18,
        "Gross_Score": 79,
        "Birdies": 1,
        "Pars": 13,
        "Bogeys": 4,
        "Double_Bogeys": 1,
        "Eagles": 1,
        "Stableford": 35
    },
    {
        "Player": "曹振波",
        "Tournament": "2026个人联赛",
        "Game": "Game 4",
        "Game_No": 4,
        "Net_Score": 17,
        "Gross_Score": 77,
        "Birdies": 4,
        "Pars": 13,
        "Bogeys": 1,
        "Double_Bogeys": 0,
        "Eagles": 1,
        "Stableford": 28
    },
    {
        "Player": "李扬",
        "Tournament": "2026个人联赛",
        "Game": "Game 4",
        "Game_No": 4,
        "Net_Score": -2,
        "Gross_Score": 83,
        "Birdies": 4,
        "Pars": 13,
        "Bogeys": 1,
        "Double_Bogeys": 3,
        "Eagles": 0,
        "Stableford": 38
    },
    {
        "Player": "王文龙",
        "Tournament": "2026个人联赛",
        "Game": "Game 4",
        "Game_No": 4,
        "Net_Score": 15,
        "Gross_Score": 96,
        "Birdies": 1,
        "Pars": 12,
        "Bogeys": 0,
        "Double_Bogeys": 2,
        "Eagles": 0,
        "Stableford": 32
    },
    {
        "Player": "曾诚",
        "Tournament": "2026个人联赛",
        "Game": "Game 4",
        "Game_No": 4,
        "Net_Score": -10,
        "Gross_Score": 93,
        "Birdies": 1,
        "Pars": 10,
        "Bogeys": 2,
        "Double_Bogeys": 1,
        "Eagles": 1,
        "Stableford": 29
    },
    {
        "Player": "Justin",
        "Tournament": "2026个人联赛",
        "Game": "Game 4",
        "Game_No": 4,
        "Net_Score": 12,
        "Gross_Score": 92,
        "Birdies": 1,
        "Pars": 6,
        "Bogeys": 0,
        "Double_Bogeys": 3,
        "Eagles": 1,
        "Stableford": 31
    },
    {
        "Player": "刘北南",
        "Tournament": "2026个人联赛",
        "Game": "Game 5",
        "Game_No": 5,
        "Net_Score": -10,
        "Gross_Score": 73,
        "Birdies": 0,
        "Pars": 12,
        "Bogeys": 6,
        "Double_Bogeys": 0,
        "Eagles": 1,
        "Stableford": 30
    },
    {
        "Player": "Jacky",
        "Tournament": "2026个人联赛",
        "Game": "Game 5",
        "Game_No": 5,
        "Net_Score": 1,
        "Gross_Score": 87,
        "Birdies": 3,
        "Pars": 12,
        "Bogeys": 0,
        "Double_Bogeys": 0,
        "Eagles": 0,
        "Stableford": 32
    },
    {
        "Player": "赵鲲",
        "Tournament": "2026个人联赛",
        "Game": "Game 5",
        "Game_No": 5,
        "Net_Score": 19,
        "Gross_Score": 93,
        "Birdies": 1,
        "Pars": 13,
        "Bogeys": 3,
        "Double_Bogeys": 2,
        "Eagles": 0,
        "Stableford": 30
    },
    {
        "Player": "杨子初",
        "Tournament": "2026个人联赛",
        "Game": "Game 5",
        "Game_No": 5,
        "Net_Score": 18,
        "Gross_Score": 70,
        "Birdies": 0,
        "Pars": 6,
        "Bogeys": 1,
        "Double_Bogeys": 0,
        "Eagles": 0,
        "Stableford": 37
    },
    {
        "Player": "Neo",
        "Tournament": "2026个人联赛",
        "Game": "Game 5",
        "Game_No": 5,
        "Net_Score": 19,
        "Gross_Score": 73,
        "Birdies": 1,
        "Pars": 9,
        "Bogeys": 6,
        "Double_Bogeys": 2,
        "Eagles": 1,
        "Stableford": 36
    },
    {
        "Player": "徐峥",
        "Tournament": "2026个人联赛",
        "Game": "Game 5",
        "Game_No": 5,
        "Net_Score": 2,
        "Gross_Score": 75,
        "Birdies": 4,
        "Pars": 12,
        "Bogeys": 0,
        "Double_Bogeys": 2,
        "Eagles": 0,
        "Stableford": 38
    },
    {
        "Player": "张纬",
        "Tournament": "2026个人联赛",
        "Game": "Game 5",
        "Game_No": 5,
        "Net_Score": 14,
        "Gross_Score": 73,
        "Birdies": 2,
        "Pars": 5,
        "Bogeys": 3,
        "Double_Bogeys": 3,
        "Eagles": 0,
        "Stableford": 33
    },
    {
        "Player": "曹振波",
        "Tournament": "2026个人联赛",
        "Game": "Game 5",
        "Game_No": 5,
        "Net_Score": 19,
        "Gross_Score": 79,
        "Birdies": 0,
        "Pars": 8,
        "Bogeys": 3,
        "Double_Bogeys": 2,
        "Eagles": 0,
        "Stableford": 41
    },
    {
        "Player": "李扬",
        "Tournament": "2026个人联赛",
        "Game": "Game 5",
        "Game_No": 5,
        "Net_Score": 5,
        "Gross_Score": 78,
        "Birdies": 4,
        "Pars": 13,
        "Bogeys": 3,
        "Double_Bogeys": 0,
        "Eagles": 1,
        "Stableford": 35
    },
    {
        "Player": "王文龙",
        "Tournament": "2026个人联赛",
        "Game": "Game 5",
        "Game_No": 5,
        "Net_Score": -6,
        "Gross_Score": 89,
        "Birdies": 4,
        "Pars": 5,
        "Bogeys": 5,
        "Double_Bogeys": 0,
        "Eagles": 1,
        "Stableford": 33
    },
    {
        "Player": "曾诚",
        "Tournament": "2026个人联赛",
        "Game": "Game 5",
        "Game_No": 5,
        "Net_Score": -10,
        "Gross_Score": 98,
        "Birdies": 0,
        "Pars": 9,
        "Bogeys": 1,
        "Double_Bogeys": 3,
        "Eagles": 1,
        "Stableford": 39
    },
    {
        "Player": "Justin",
        "Tournament": "2026个人联赛",
        "Game": "Game 5",
        "Game_No": 5,
        "Net_Score": 2,
        "Gross_Score": 84,
        "Birdies": 3,
        "Pars": 11,
        "Bogeys": 5,
        "Double_Bogeys": 0,
        "Eagles": 1,
        "Stableford": 29
    },
    {
        "Player": "刘北南",
        "Tournament": "2026个人联赛",
        "Game": "Game 6",
        "Game_No": 6,
        "Net_Score": -2,
        "Gross_Score": 94,
        "Birdies": 1,
        "Pars": 11,
        "Bogeys": 3,
        "Double_Bogeys": 0,
        "Eagles": 0,
        "Stableford": 35
    },
    {
        "Player": "Jacky",
        "Tournament": "2026个人联赛",
        "Game": "Game 6",
        "Game_No": 6,
        "Net_Score": 12,
        "Gross_Score": 88,
        "Birdies": 4,
        "Pars": 12,
        "Bogeys": 5,
        "Double_Bogeys": 2,
        "Eagles": 0,
        "Stableford": 33
    },
    {
        "Player": "赵鲲",
        "Tournament": "2026个人联赛",
        "Game": "Game 6",
        "Game_No": 6,
        "Net_Score": -7,
        "Gross_Score": 81,
        "Birdies": 4,
        "Pars": 8,
        "Bogeys": 0,
        "Double_Bogeys": 2,
        "Eagles": 1,
        "Stableford": 40
    },
    {
        "Player": "杨子初",
        "Tournament": "2026个人联赛",
        "Game": "Game 6",
        "Game_No": 6,
        "Net_Score": -2,
        "Gross_Score": 83,
        "Birdies": 2,
        "Pars": 6,
        "Bogeys": 1,
        "Double_Bogeys": 0,
        "Eagles": 1,
        "Stableford": 38
    },
    {
        "Player": "Neo",
        "Tournament": "2026个人联赛",
        "Game": "Game 6",
        "Game_No": 6,
        "Net_Score": 15,
        "Gross_Score": 94,
        "Birdies": 4,
        "Pars": 5,
        "Bogeys": 6,
        "Double_Bogeys": 0,
        "Eagles": 0,
        "Stableford": 36
    },
    {
        "Player": "徐峥",
        "Tournament": "2026个人联赛",
        "Game": "Game 6",
        "Game_No": 6,
        "Net_Score": 0,
        "Gross_Score": 74,
        "Birdies": 0,
        "Pars": 12,
        "Bogeys": 2,
        "Double_Bogeys": 1,
        "Eagles": 1,
        "Stableford": 30
    },
    {
        "Player": "张纬",
        "Tournament": "2026个人联赛",
        "Game": "Game 6",
        "Game_No": 6,
        "Net_Score": 17,
        "Gross_Score": 97,
        "Birdies": 2,
        "Pars": 5,
        "Bogeys": 1,
        "Double_Bogeys": 1,
        "Eagles": 1,
        "Stableford": 30
    },
    {
        "Player": "曹振波",
        "Tournament": "2026个人联赛",
        "Game": "Game 6",
        "Game_No": 6,
        "Net_Score": 3,
        "Gross_Score": 73,
        "Birdies": 2,
        "Pars": 4,
        "Bogeys": 4,
        "Double_Bogeys": 0,
        "Eagles": 0,
        "Stableford": 30
    },
    {
        "Player": "李扬",
        "Tournament": "2026个人联赛",
        "Game": "Game 6",
        "Game_No": 6,
        "Net_Score": 14,
        "Gross_Score": 71,
        "Birdies": 2,
        "Pars": 9,
        "Bogeys": 3,
        "Double_Bogeys": 2,
        "Eagles": 1,
        "Stableford": 33
    },
    {
        "Player": "王文龙",
        "Tournament": "2026个人联赛",
        "Game": "Game 6",
        "Game_No": 6,
        "Net_Score": 14,
        "Gross_Score": 79,
        "Birdies": 4,
        "Pars": 9,
        "Bogeys": 5,
        "Double_Bogeys": 3,
        "Eagles": 1,
        "Stableford": 39
    },
    {
        "Player": "曾诚",
        "Tournament": "2026个人联赛",
        "Game": "Game 6",
        "Game_No": 6,
        "Net_Score": 6,
        "Gross_Score": 71,
        "Birdies": 2,
        "Pars": 5,
        "Bogeys": 6,
        "Double_Bogeys": 0,
        "Eagles": 0,
        "Stableford": 31
    },
    {
        "Player": "Justin",
        "Tournament": "2026个人联赛",
        "Game": "Game 6",
        "Game_No": 6,
        "Net_Score": 9,
        "Gross_Score": 87,
        "Birdies": 4,
        "Pars": 8,
        "Bogeys": 1,
        "Double_Bogeys": 0,
        "Eagles": 0,
        "Stableford": 33
    }
])

def load_scores() -> pd.DataFrame:
    if SCORES_FILE.exists():
        return pd.read_csv(SCORES_FILE)
    if _GLOBAL_BACKUP and "scores" in _GLOBAL_BACKUP:
        return pd.DataFrame(_GLOBAL_BACKUP["scores"])
    return _sample_scores()

def save_scores(df: pd.DataFrame) -> None:
    df.to_csv(SCORES_FILE, index=False)
    _schedule_github_push()

# ── Cup bracket data ──────────────────────────────────────────────────────────
CUP_FILE = DATA_DIR / "cup.json"

DEFAULT_CUP: dict = {
    "draw": {
        "P1": "刘北南",
        "P2": "Jacky",
        "P3": "Neo",
        "P4": "王文龙",
        "P5": "徐峥",
        "P6": "赵鲲",
        "P7": "曹振波",
        "P8": "杨明",
        "P9": "Justin",
        "P10": "李扬",
        "P11": "张纬",
        "P12": "曾诚"
    },
    "rounds": {
        "R1": [
            {
                "match": "P3 vs P4",
                "home": "P3",
                "winner": None,
                "score": ""
            },
            {
                "match": "P5 vs P6",
                "home": "P5",
                "winner": None,
                "score": ""
            },
            {
                "match": "P9 vs P10",
                "home": "P9",
                "winner": None,
                "score": ""
            },
            {
                "match": "P11 vs P12",
                "home": "P11",
                "winner": None,
                "score": ""
            }
        ],
        "R2": [],
        "SF": [],
        "F": []
    },
    "byes": [
        "P1",
        "P2",
        "P7",
        "P8"
    ]
}


def load_cup() -> dict:
    if CUP_FILE.exists():
        return json.loads(CUP_FILE.read_text(encoding="utf-8"))
    if _GLOBAL_BACKUP and "cup" in _GLOBAL_BACKUP:
        return _GLOBAL_BACKUP["cup"]
    return DEFAULT_CUP

def save_cup(cup: dict) -> None:
    CUP_FILE.write_text(json.dumps(cup, ensure_ascii=False, indent=2), encoding="utf-8")
    _schedule_github_push()

# ── Outing Match data (Red vs Black) ──────────────────────────────────────────
OUTING_FILE = DATA_DIR / "outing.json"

DEFAULT_OUTING: dict = {
    "red_team": [
        "刘北南",
        "李扬",
        "赵鲲",
        "张纬",
        "Justin",
        "曾诚"
    ],
    "black_team": [
        "Jacky",
        "曹振波",
        "杨明",
        "王文龙",
        "徐峥",
        "Neo"
    ],
    "matches": [
        {
            "id": "om1",
            "name": "Outing Day 1: Fourball Betterball Match Play",
            "date": "2026-04-26",
            "venue": "TBD",
            "red_score": None,
            "black_score": None,
            "status": "upcoming"
        },
        {
            "id": "om2",
            "name": "Outing Day 2: Fourball Betterball Stableford",
            "date": "2026-05-31",
            "venue": "TBD",
            "red_score": None,
            "black_score": None,
            "status": "upcoming"
        },
        {
            "id": "om3",
            "name": "Outing Day 3: 2-Man Scramble",
            "date": "2026-06-21",
            "venue": "TBD",
            "red_score": None,
            "black_score": None,
            "status": "upcoming"
        },
        {
            "id": "om4",
            "name": "Outing Day 4: 4-Man Scramble",
            "date": "2026-08-23",
            "venue": "TBD",
            "red_score": None,
            "black_score": None,
            "status": "upcoming"
        }
    ],
    "total_points": 8,
    "winning_threshold": 4.5
}


def load_outing() -> dict:
    if OUTING_FILE.exists():
        return json.loads(OUTING_FILE.read_text(encoding="utf-8"))
    if _GLOBAL_BACKUP and "outing" in _GLOBAL_BACKUP:
        return _GLOBAL_BACKUP["outing"]
    return DEFAULT_OUTING

def save_outing(outing: dict) -> None:
    OUTING_FILE.write_text(json.dumps(outing, ensure_ascii=False, indent=2), encoding="utf-8")
    _schedule_github_push()

# ── State Export/Import ────────────────────────────────────────────────────────────
def export_app_state() -> dict:
    """Export all application state as a dictionary."""
    return {
        "version": "1.0",
        "export_date": datetime.now().isoformat(),
        "events": load_events(),
        "announcements": load_announcements(),
        "cup": load_cup(),
        "outing": load_outing(),
        "scores": load_scores().to_dict(orient="records"),
    }

def _schedule_github_push() -> None:
    """Push the full app state to GitHub in a background thread.

    Running in a daemon thread means the Streamlit response is returned
    immediately — the GitHub API call (~200 ms) does not block the user.
    """
    import threading
    def _push():
        state = export_app_state()
        github_push_state(state)
    t = threading.Thread(target=_push, daemon=True)
    t.start()

def import_app_state(state: dict) -> None:
    """Import application state from a dictionary."""
    if "events" in state:
        save_events(state["events"])
    if "announcements" in state:
        save_announcements(state["announcements"])
    if "cup" in state:
        save_cup(state["cup"])
    if "outing" in state:
        save_outing(state["outing"])
    if "scores" in state:
        df = pd.DataFrame(state["scores"])
        save_scores(df)

# ── Backup management ────────────────────────────────────────────────────────────
def list_backups() -> list[dict]:
    """List all backup files with metadata."""
    backups = []
    for path in sorted(BACKUP_DIR.glob("gco_backup_*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            backups.append({
                "filename": path.name,
                "path": str(path),
                "date": data.get("export_date", path.stem.replace("gco_backup_", "")),
                "data": data
            })
        except:
            pass
    return backups

def compute_diff(backup: dict, current: dict) -> dict:
    """Compute granular differences between backup and current state.

    Returns a dict keyed by section name. Each value contains:
      - "summary": short human-readable description
      - "details": list of change dicts with keys "field", "backup", "current", "change_type"
        change_type is one of: "added", "removed", "changed"
    For list sections (scores, events, announcements) each record is compared
    individually; for dict sections (cup, outing) top-level keys are compared.
    """
    diff: dict = {}
    all_keys = set(backup.keys()) | set(current.keys())

    for key in all_keys:
        if key in ("version", "export_date"):
            continue
        b = backup.get(key)
        c = current.get(key)
        if b == c:
            continue

        details: list[dict] = []

        if isinstance(b, list) and isinstance(c, list):
            # ── List comparison: treat each element as a record ──────────────
            # Convert to JSON strings so we can do membership checks on dicts
            b_strs = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in b]
            c_strs = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in c]
            b_set = set(b_strs)
            c_set = set(c_strs)

            removed = b_set - c_set
            added = c_set - b_set

            for s in removed:
                item = json.loads(s)
                label = _record_label(key, item)
                details.append({"field": label, "backup": item, "current": "(removed)", "change_type": "removed"})
            for s in added:
                item = json.loads(s)
                label = _record_label(key, item)
                details.append({"field": label, "backup": "(added)", "current": item, "change_type": "added"})

            n_removed = len(removed)
            n_added = len(added)
            parts = []
            if n_removed:
                parts.append(f"{n_removed} removed")
            if n_added:
                parts.append(f"{n_added} added")
            summary = ", ".join(parts) if parts else "reordered"

        elif isinstance(b, dict) and isinstance(c, dict):
            # ── Dict comparison: key-by-key ───────────────────────────────────
            all_sub = set(b.keys()) | set(c.keys())
            for sub_key in sorted(all_sub):
                bv = b.get(sub_key)
                cv = c.get(sub_key)
                if bv == cv:
                    continue
                change_type = "added" if bv is None else "removed" if cv is None else "changed"
                details.append({"field": sub_key, "backup": bv, "current": cv, "change_type": change_type})
            n = len(details)
            summary = f"{n} field(s) changed"

        else:
            # ── Scalar / type mismatch ────────────────────────────────────────
            details.append({"field": key, "backup": b, "current": c, "change_type": "changed"})
            summary = "value changed"

        diff[key] = {"summary": summary, "details": details}

    return diff


def _record_label(section: str, record: dict) -> str:
    """Return a short human-readable label for a list record."""
    if section == "scores":
        return f"{record.get('Player', '?')} – {record.get('Game', '?')}"
    if section == "events":
        return record.get("title") or record.get("name") or record.get("id") or str(record)[:60]
    if section == "announcements":
        return record.get("title") or record.get("message", "")[:60] or str(record)[:60]
    return str(record)[:60]
