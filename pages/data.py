"""
GCO 2026 – shared data definitions and sample data generators.
All pages import from here so the schema stays consistent.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from datetime import date, datetime
import json, os, pathlib

# ── root data directory ──────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# ── Club constants ────────────────────────────────────────────────────────────
CLUB_NAME = "GCO Golf Club"
SEASON = "2026"

PLAYERS: list[str] = [
    "刘北南", "Jacky", "赵鲲", "杨子初", "Neo", "徐峥",
    "张纬", "曹振波", "李扬", "王文龙", "曾诚", "Justin",
]

# Red / Black team assignment (6 each)
RED_TEAM  = PLAYERS[:6]
BLACK_TEAM = PLAYERS[6:]

# Individual league tournaments (联赛)
LEAGUE_TOURNAMENTS: dict[str, dict] = {
    "2026个人联赛": {"period": "2026-04-01 ~ 2026-09-30", "games": 6},
}

# Team match types
TEAM_MATCHES: list[dict] = [
    {"id": "tm1", "name": "Fourball Betterball Match Play",  "format": "doubles", "hcp_allowance": "90%"},
    {"id": "tm2", "name": "Fourball Betterball Stableford",  "format": "doubles", "hcp_allowance": "85%"},
    {"id": "tm3", "name": "2-Man Scramble",                  "format": "doubles", "hcp_allowance": "35%/15%"},
    {"id": "tm4", "name": "4-Man Scramble",                  "format": "fours",   "hcp_allowance": "25%/20%/15%/10%"},
]

# ── Upcoming events (editable JSON) ──────────────────────────────────────────
EVENTS_FILE = DATA_DIR / "events.json"

DEFAULT_EVENTS: list[dict] = [
    {"date": "2026-04-04", "name": "联赛第1轮 - Stroke Play", "type": "League",       "details": "Stroke Play, OOM Qualifying"},
    {"date": "2026-04-12", "name": "个人杯赛第一轮开始",              "type": "Cup",          "details": "Knockout Match Play, R1 fixtures announced"},
    {"date": "2026-05-03", "name": "Fourball Betterball MP",         "type": "Team",         "details": "Red vs Black – Team Match 1"},
    {"date": "2026-05-17", "name": "联赛第2轮 - Stroke Play", "type": "League",       "details": "Stroke Play, OOM Qualifying"},
    {"date": "2026-06-07", "name": "联赛第3轮 - Stroke Play", "type": "League",       "details": "Stroke Play, OOM Qualifying"},
    {"date": "2026-06-14", "name": "个人杯赛半决赛",                  "type": "Cup",          "details": "Knockout Match Play Semi-Finals"},
    {"date": "2026-06-21", "name": "联赛第4轮 - Stroke Play",     "type": "League",       "details": "Stroke Play, OOM Qualifying"},
    {"date": "2026-07-05", "name": "2-Man Scramble",                 "type": "Team",         "details": "Red vs Black – Team Match 3"},
    {"date": "2026-07-19", "name": "联赛第5轮 - Stroke Play",     "type": "League",       "details": "Stroke Play, OOM Qualifying"},
    {"date": "2026-08-09", "name": "联赛第6轮 - Stroke Play",     "type": "League",       "details": "Stroke Play, OOM Qualifying"},
    {"date": "2026-08-23", "name": "个人杯赛决赛",                    "type": "Cup",          "details": "Knockout Match Play Final"},
    {"date": "2026-09-13", "name": "年终总决赛",                      "type": "Grand Final",  "details": "36-Hole Stroke Play + Beat the Champion"},
]

def load_events() -> list[dict]:
    if EVENTS_FILE.exists():
        return json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    return DEFAULT_EVENTS

def save_events(events: list[dict]) -> None:
    EVENTS_FILE.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")

# ── Announcements ─────────────────────────────────────────────────────────────
ANNOUNCEMENTS_FILE = DATA_DIR / "announcements.json"

DEFAULT_ANNOUNCEMENTS: list[dict] = [
    {
        "id": "ann-001",
        "title": "🏌️ 2026赛季正式开幕！",
        "date": "2026-03-29",
        "author": "组委会",
        "pinned": True,
        "body": (
            "全体GCO成员，2026赛季即将拉开帷幕！\n\n"
            "**赛历亮点：**\n"
            "- 个人联赛：6场 18-Hole Stroke Play，排名前三晋级总决赛\n"
            "- 个人杯赛：Knockout Match Play，12人单场淘汰赛决出冠军\n"
            "- 团队赛：红队 vs 黑队，双人赛×3 + 四人赛×1\n"
            "- 年终总决赛：36洞Stroke Play，排名前三+杯赛冠军\n\n"
            "请所有成员确认Scottish Golf账户有效，并关注微信群通知。\n\n"
            "预祝大家2026赛季愉快！⛳"
        ),
        "tags": ["赛季开幕", "重要"],
    },
    {
        "id": "ann-002",
        "title": "📋 个人杯赛抽签结果公布",
        "date": "2026-03-29",
        "author": "组委会",
        "pinned": False,
        "body": (
            "个人杯赛（Knockout Match Play）抽签已完成。\n\n"
            "**第一轮（April）对阵：**\n"
            "- P3 vs P4｜P5 vs P6｜P9 vs P10｜P11 vs P12\n\n"
            "P1、P2、P7、P8自动晋级第二轮。\n\n"
            "拥有主场权的选手请尽早联系对手确认比赛时间和场地。"
        ),
        "tags": ["杯赛", "抽签"],
    },
]

def load_announcements() -> list[dict]:
    if ANNOUNCEMENTS_FILE.exists():
        return json.loads(ANNOUNCEMENTS_FILE.read_text(encoding="utf-8"))
    return DEFAULT_ANNOUNCEMENTS

def save_announcements(anns: list[dict]) -> None:
    ANNOUNCEMENTS_FILE.write_text(json.dumps(anns, ensure_ascii=False, indent=2), encoding="utf-8")

# ── League score data ─────────────────────────────────────────────────────────
SCORES_FILE = DATA_DIR / "scores.csv"

def _sample_scores() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    game_id: int = 1
    for t_name, t_info in LEAGUE_TOURNAMENTS.items():
        for g in range(1, t_info["games"] + 1):
            game_label = f"Game {game_id}"
            for player in PLAYERS:
                rows.append({
                    "Player": player,
                    "Tournament": t_name,
                    "Game": game_label,
                    "Game_No": game_id,
                    "Net_Score": int(rng.integers(-10, 20)),
                    "Gross_Score": int(rng.integers(70, 100)),
                    "Birdies": int(rng.integers(0, 5)),
                    "Pars": int(rng.integers(4, 14)),
                    "Bogeys": int(rng.integers(0, 7)),
                    "Double_Bogeys": int(rng.integers(0, 4)),
                    "Eagles": int(rng.integers(0, 2)),
                    "Stableford": int(rng.integers(28, 42)),
                })
            game_id += 1
    return pd.DataFrame(rows)

def load_scores() -> pd.DataFrame:
    if SCORES_FILE.exists():
        return pd.read_csv(SCORES_FILE)
    return _sample_scores()

def save_scores(df: pd.DataFrame) -> None:
    df.to_csv(SCORES_FILE, index=False)

# ── Cup bracket data ──────────────────────────────────────────────────────────
CUP_FILE = DATA_DIR / "cup.json"

DEFAULT_CUP: dict = {
    "draw": {
        "P1": "刘北南", "P2": "Jacky", "P3": "Neo", "P4": "王文龙",
        "P5": "徐峥",   "P6": "赵鲲",  "P7": "曹振波",  "P8": "杨子初",
        "P9": "Justin",  "P10": "李扬","P11": "张纬", "P12": "曾诚",
    },
    "rounds": {
        "R1": [
            {"match": "P3 vs P4",   "home": "P3", "winner": None, "score": ""},
            {"match": "P5 vs P6",   "home": "P5", "winner": None, "score": ""},
            {"match": "P9 vs P10",  "home": "P9", "winner": None, "score": ""},
            {"match": "P11 vs P12", "home": "P11","winner": None, "score": ""},
        ],
        "R2": [],
        "SF": [],
        "F":  [],
    },
    "byes": ["P1", "P2", "P7", "P8"],
}

def load_cup() -> dict:
    if CUP_FILE.exists():
        return json.loads(CUP_FILE.read_text(encoding="utf-8"))
    return DEFAULT_CUP

def save_cup(cup: dict) -> None:
    CUP_FILE.write_text(json.dumps(cup, ensure_ascii=False, indent=2), encoding="utf-8")

# ── Team match data ───────────────────────────────────────────────────────────
TEAM_FILE = DATA_DIR / "team.json"

DEFAULT_TEAM: dict = {
    "red_team":  RED_TEAM,
    "black_team": BLACK_TEAM,
    "matches": [
        {
            "id": "tm1", "name": "Fourball Betterball Match Play",
            "date": "TBD", "venue": "TBD",
            "red_score": None, "black_score": None, "status": "upcoming"
        },
        {
            "id": "tm2", "name": "Fourball Betterball Stableford",
            "date": "TBD", "venue": "TBD",
            "red_score": None, "black_score": None, "status": "upcoming"
        },
        {
            "id": "tm3", "name": "2-Man Scramble",
            "date": "TBD", "venue": "TBD",
            "red_score": None, "black_score": None, "status": "upcoming"
        },
        {
            "id": "tm4", "name": "4-Man Scramble",
            "date": "TBD", "venue": "TBD",
            "red_score": None, "black_score": None, "status": "upcoming"
        },
    ],
    "total_points": 8,
    "winning_threshold": 4.5,
}

def load_team() -> dict:
    if TEAM_FILE.exists():
        return json.loads(TEAM_FILE.read_text(encoding="utf-8"))
    return DEFAULT_TEAM

def save_team(team: dict) -> None:
    TEAM_FILE.write_text(json.dumps(team, ensure_ascii=False, indent=2), encoding="utf-8")
