"""Single home for the pinned announcement records and the shared display selector.

Both the home page (``streamlit_app.py``, the 最新动态 block) and the
Announcements page (``pages/1_📢_Announcements.py``) import
``get_display_announcements`` from here. Importing this module must stay free of
I/O, Streamlit imports and network access.
"""
from __future__ import annotations


PINNED_ANNOUNCEMENTS: list[dict] = [
    {
        "id": "pinned-2026-season-winners",
        "title": "🎉 2026 赛季个人冠军公告",
        "date": "2026-09-15",
        "author": "GCO 组委会",
        "pinned": True,
        "body": (
            "2026赛季个人荣誉揭晓！\n\n"
            "恭喜 张纬 获得 2026 个人联赛冠军！\n"
            "恭喜 王文龙 获得 2026 个人杯赛冠军！\n\n"
            "感谢所有成员的参与，期待下个赛季再创佳绩！"
        ),
        "tags": ["2026", "冠军"],
    },
    {
        "id": "pinned-2026-outing-day-result",
        "title": "🎉 2026 Outing Day 对抗赛结果公告",
        "date": "2026-08-16",
        "author": "GCO 组委会",
        "pinned": True,
        "body": (
            "🏌️ Outing Day 对抗赛结果\n"
            "\n"
            "红队 Red Team 5.0 pts 战胜 黑队 Black Team 3.0 pts\n"
            "红队阵容：刘北南 • 李扬 • 赵鲲 • 张纬 • Justin • 曾诚"
        ),
        "tags": ["Outing Day", "对抗赛"],
    },
]


def get_display_announcements(announcements: list[dict] | None = None) -> list[dict]:
    """Return the announcements to display, pinned records first.

    Order: the records in ``PINNED_ANNOUNCEMENTS`` (in that order), then any
    additional pinned records from ``announcements`` in input order, then the
    remaining input records in input order. Input records whose ``id`` already
    appears in ``PINNED_ANNOUNCEMENTS`` are not repeated. The argument is never
    mutated and the result is never truncated.
    """
    if not announcements:
        return list(PINNED_ANNOUNCEMENTS)

    known_ids = {record.get("id") for record in PINNED_ANNOUNCEMENTS}
    remaining = [record for record in announcements if record.get("id") not in known_ids]
    extra_pinned = [record for record in remaining if record.get("pinned")]
    others = [record for record in remaining if not record.get("pinned")]

    return list(PINNED_ANNOUNCEMENTS) + extra_pinned + others
