"""
GCO 2026 – Individual League (联赛) standings and tournament leaderboards
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from theme import inject_theme, hero, section, flash, show_flash, sync_status
from data import load_scores, save_scores, LEAGUE_TOURNAMENTS, PLAYERS, github_upload_image
from ai_summary import render_season_summary
from ai_summary import render_follow_up_questions
from auth import is_admin_user, get_admin_name
from dataclasses import replace
from datetime import date, datetime
from typing import Any
import importlib
import os
import league_scorecard

# A redeploy replaces league_scorecard.py, but a running app keeps the module it imported
# before (sys.modules), so names added since then fail to import until the app reboots.
# Reload it whenever the file on disk isn't the one it was loaded from.
if getattr(league_scorecard, "LOADED_FROM_MTIME", None) != os.path.getmtime(league_scorecard.__file__):
    importlib.reload(league_scorecard)

from league_scorecard import (  # noqa: E402
    LEAGUE_SCORECARD_FIELD_KEYS,
    LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY,
    LeagueScorecardPlayersResult,
    ScorecardPlayerEntry,
    apply_selected_player_scorecard_updates,
    read_league_scorecard_players,
    scorecard_field_updates,
    scorecard_upload_fingerprint,
    venue_names_from_records,
)

# ── Scorecard auto-fill (admin score form) ───────────────────────────────────
LEAGUE_SCORECARD_WIDGET_KEYS: dict[str, str] = {
    "date": "league_sc_date",
    "venue": "league_sc_venue",
    "net": "league_sc_net",
    "gross": "league_sc_gross",
    "stableford": "league_sc_stableford",
    "eagles": "league_sc_eagles",
    "birdies": "league_sc_birdies",
    "pars": "league_sc_pars",
    "bogeys": "league_sc_bogeys",
    "double_bogeys_or_worse": "league_sc_double_bogeys_or_worse",
}
LEAGUE_SCORECARD_UPLOAD_KEY = "league_scorecard_upload"
LEAGUE_SCORECARD_LAST_READ_KEY = "league_scorecard_last_read"
LEAGUE_SCORECARD_NOTICE_KEY = "league_scorecard_notice"
LEAGUE_SCORECARD_PLAYERS_KEY = "league_scorecard_players"
LEAGUE_SCORECARD_APPLIED_PICK_KEY = "league_scorecard_applied_pick"
LEAGUE_SCORECARD_PLAYER_PLACEHOLDER = "选择记分卡上的球员 / Choose the player on the card"
# Card-level facts: a player read without them takes the card's date and venue.
LEAGUE_SCORECARD_CARD_FIELDS = ("date", "venue")
LEAGUE_SCORECARD_SNAPSHOT_KEY = "league_sc_defaults_snapshot"
AUTOFILL_UNAVAILABLE_NOTICE = "Auto-fill from the scorecard image was unavailable — please enter the values manually."
# Image types Save uploads from the picker: the form's original JPG/PNG plus the other
# images the scorecard reader accepts (league_scorecard.SUPPORTED_IMAGE_MIME_TYPES).
SCORECARD_SAVE_EXTENSIONS = ("jpg", "jpeg", "png", "webp", "gif")


def _scorecard_widget_default(field: str, fallback: Any) -> dict[str, Any]:
    """Widget kwargs: the key, plus `fallback` as the value unless session state already holds one.

    Whole-number fields also get step=1: without a value, st.number_input would
    otherwise turn into a float input (0.00) once the key is in session state.
    """
    kwargs: dict[str, Any] = {"key": LEAGUE_SCORECARD_WIDGET_KEYS[field]}
    if isinstance(fallback, int) and not isinstance(fallback, bool):
        kwargs["step"] = 1
    if LEAGUE_SCORECARD_WIDGET_KEYS[field] not in st.session_state:
        kwargs["value"] = fallback
    return kwargs


def _scorecard_known_venues() -> list[str]:
    """Venue names already used in league rounds, for matching the venue read off a card."""
    try:
        return venue_names_from_records(df[df["Venue"].notna()].to_dict("records"))
    except Exception:
        return []


def _scorecard_defaults_snapshot(**base: object) -> tuple[str, ...]:
    return tuple(f"{name}={value!r}" for name, value in sorted(base.items()))


def _scorecard_players_for_form(result: LeagueScorecardPlayersResult) -> LeagueScorecardPlayersResult:
    """Each player's fields as the form uses them.

    The venue is matched to a venue already used in league rounds. A player read
    without the card's date or venue takes them from the card (the first player
    that has them); a player's own scores are never borrowed from another player.
    """
    if not result.players:
        return result
    card: dict[str, object] = {}
    for player in result.players:
        for field in LEAGUE_SCORECARD_CARD_FIELDS:
            if field in player.found_fields and field not in card:
                card[field] = player.found_fields[field]
    known_venues = _scorecard_known_venues()
    players = [
        replace(
            player,
            found_fields=scorecard_field_updates(
                {**{f: v for f, v in card.items() if f not in player.found_fields}, **player.found_fields},
                known_venues=known_venues,
            ),
        )
        for player in result.players
    ]
    return LeagueScorecardPlayersResult(players, result.unavailable_reason)


def _scorecard_duplicate_suffix(players: list[ScorecardPlayerEntry], index: int) -> str:
    """Suffix " (n)" when a printed label repeats on the card, so each entry stays selectable.

    Streamlit maps a selectbox choice back by its shown text, so two identical
    labels would otherwise both select the first of them. Unique labels get "".
    """
    label = players[index].label
    same = [p.index for p in players if p.label == label]
    return f" ({same.index(index) + 1})" if len(same) > 1 else ""


st.set_page_config(page_title="GCO | 联赛", page_icon="🏆", layout="wide")
inject_theme(st)

hero(st, "🏆 个人联赛", "Individual League Standings", "GCO 2026")
show_flash(st)

df = load_scores()

# ── Filter for played rounds ─────────────────────────────────────────────────
df_played = df[df["Gross_Score"] > 0].copy()

# ── Overall Order-of-Merit (OOM) ──────────────────────────────────────────────
section(st, "📊", "积分榜 Order of Merit")

oom = (
    df_played.groupby("Player")
    .agg(
        Total_Net=("Net_Score", "sum"),
        Games=("Game", "count"),
        Eagles=("Eagles", "sum"),
        Birdies=("Birdies", "sum"),
        Pars=("Pars", "sum"),
        Bogeys=("Bogeys", "sum"),
        DBogeys=("Double_Bogeys", "sum"),
        Avg_Stableford=("Stableford", "mean"),
    )
    .reset_index()
)
oom = (
    oom.set_index("Player")
    .reindex(PLAYERS)
    .fillna(0)
    .reset_index()
)

# Sorting: played rounds first, then by score. 0-round players go to the bottom.
oom["Has_Played"] = oom["Games"] > 0
oom = oom.sort_values(
    ["Has_Played", "Total_Net", "Eagles", "Birdies"], 
    ascending=[False, True, False, False]
).drop(columns=["Has_Played"])

oom.insert(0, "Rank", range(1, len(oom) + 1))
oom["Avg_Net"] = (oom["Total_Net"] / oom["Games"]).fillna(0).round(2)
oom["Avg_Stableford"] = oom["Avg_Stableford"].round(1)

# rank medals (only for those who have played)
def rank_icon(row):
    r = row["Rank"]
    if row["Games"] == 0:
        return "-"
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(r, str(r))

oom["Rank"] = oom.apply(rank_icon, axis=1)

display_cols = ["Rank", "Player", "Games", "Total_Net", "Avg_Net",
                "Eagles", "Birdies", "Pars", "Bogeys", "DBogeys"]

st.dataframe(
    oom[display_cols].rename(columns={
        "Total_Net": "总净杆", "Avg_Net": "均净杆",
        "Eagles": "老鹰", "Birdies": "小鸟", "Pars": "标准",
        "Bogeys": "柏忌", "DBogeys": "双柏忌+", "Games": "轮次",
    }),
    width='stretch',
    hide_index=True,
)

# ── OOM bar chart ─────────────────────────────────────────────────────────────
fig_oom = px.bar(
    oom,
    x="Player",
    y="Total_Net",
    color="Total_Net",
    color_continuous_scale=["#52b788", "#d4af37", "#e74c3c"],
    title="积分榜 – 总净杆数（越低越好）",
    template="plotly_dark",
    text="Total_Net",
)
fig_oom.update_traces(textposition="outside")
fig_oom.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(30,61,44,.4)",
    coloraxis_showscale=False,
    xaxis=dict(tickfont=dict(size=11)),
    xaxis_title=None,
)
st.plotly_chart(fig_oom, width='stretch')

# ── Per-tournament tabs ───────────────────────────────────────────────────────
section(st, "🏌️", "轮次成绩单 Round-by-Round Breakdown")

tabs = st.tabs(list(LEAGUE_TOURNAMENTS.keys()))

for tab, (t_name, t_info) in zip(tabs, LEAGUE_TOURNAMENTS.items()):
    with tab:
        t_df = df_played[df_played["Tournament"] == t_name]
        if t_df.empty:
            st.info("暂无数据")
            continue

        lb = (
            t_df.groupby("Player")
            .agg(
                Games=("Game", "count"),
                Total_Net=("Net_Score", "sum"),
                Birdies=("Birdies", "sum"),
                Eagles=("Eagles", "sum"),
            )
            .reset_index()
            .sort_values(["Total_Net", "Eagles", "Birdies"], ascending=[True, False, False])
        )
        
        # Ensure all players are listed in tournament leaderboards too
        lb = (
            lb.set_index("Player")
            .reindex(PLAYERS)
            .fillna(0)
            .reset_index()
        )
        lb["Has_Played"] = lb["Games"] > 0
        lb = lb.sort_values(
            ["Has_Played", "Total_Net", "Eagles", "Birdies"], 
            ascending=[False, True, False, False]
        ).drop(columns=["Has_Played"])

        lb.insert(0, "Rank", [rank_icon({"Rank": i, "Games": g}) for i, g in zip(range(1, len(lb) + 1), lb["Games"])])
        lb["Period"] = t_info["period"]

        st.caption(f"📅 赛期：{t_info['period']}")
        st.dataframe(
            lb.rename(columns={"Games": "轮次", "Total_Net": "净杆合计",
                                "Birdies": "小鸟", "Eagles": "老鹰"}),
            width='stretch',
            hide_index=True,
        )

        # Game-by-game scores for this tournament
        games = sorted(t_df["Game"].unique())
        if games:
            pivot = t_df.pivot_table(index="Player", columns="Game", values="Net_Score", aggfunc="first")
            pivot = pivot.reindex(columns=games)
            pivot["合计"] = pivot.sum(axis=1)
            pivot = pivot.sort_values("合计")
            st.dataframe(pivot, width='stretch')

# ── Player deep-dive ──────────────────────────────────────────────────────────
section(st, "👤", "球员详情 Player Deep-Dive")

selected = st.selectbox("选择球员", PLAYERS)
p_df = df_played[df_played["Player"] == selected].copy().sort_values("Game_No")

if not p_df.empty:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("平均净杆", f"{p_df['Net_Score'].mean():.1f}")
    c2.metric("最佳净杆", int(p_df['Net_Score'].min()))
    c3.metric("总小鸟数", int(p_df['Birdies'].sum()))
    c4.metric("总老鹰数", int(p_df['Eagles'].sum()))
    player_name = selected
    season_rounds = p_df.to_dict(orient="records")
    summary = render_season_summary(player_name, season_rounds)
    if summary:
        render_follow_up_questions(player_name, season_rounds, summary)

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=p_df["Game"], y=p_df["Net_Score"],
        mode="lines+markers+text",
        text=p_df["Net_Score"],
        textposition="top center",
        line=dict(color="#52b788", width=3),
        marker=dict(size=9, color="#d4af37"),
        name="Net Score",
    ))
    fig_trend.add_hline(y=0, line_dash="dash", line_color="#6b9a7a", annotation_text="E (Even)")
    fig_trend.update_layout(
        title=f"{selected} — 成绩走势",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(30,61,44,.4)",
        xaxis_title="轮次", yaxis_title="净杆数",
    )
    st.plotly_chart(fig_trend, width='stretch')

    # Scoring profile donut
    totals = {
        "老鹰 Eagle": int(p_df["Eagles"].sum()),
        "小鸟 Birdie": int(p_df["Birdies"].sum()),
        "标准 Par": int(p_df["Pars"].sum()),
        "柏忌 Bogey": int(p_df["Bogeys"].sum()),
        "双柏忌+": int(p_df["Double_Bogeys"].sum()),
    }
    fig_donut = px.pie(
        names=list(totals.keys()),
        values=list(totals.values()),
        title=f"{selected} — 得分分布",
        hole=0.55,
        color_discrete_sequence=["#d4af37", "#52b788", "#2d6a4f", "#e67e22", "#e74c3c"],
        template="plotly_dark",
    )
    fig_donut.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
    )
    st.plotly_chart(fig_donut, width='stretch')

# ── Admin: Record Results ─────────────────────────────────────────────────────
if is_admin_user():
    section(st, "⚙️", "管理 Admin: Record Results")
    sync_status(st)

    with st.expander("📝 录入或修改成绩 Record / Edit Scores", expanded=False):
        t_names = list(LEAGUE_TOURNAMENTS.keys())
        t_sel = st.selectbox("赛事 Tournament", t_names) if len(t_names) > 1 else t_names[0]
        
        t_info = LEAGUE_TOURNAMENTS[t_sel]
        available_games = [f"Game {i}" for i in range(1, t_info["games"] + 1)]
        
        c1, c2 = st.columns(2)
        with c1:
            p_sel = st.selectbox("球员 Player", PLAYERS)
        with c2:
            g_sel = st.selectbox("轮次 Game", available_games)

        mask = (df["Player"] == p_sel) & (df["Tournament"] == t_sel) & (df["Game"] == g_sel)
        existing_row = df[mask]

        # Placeholder rows (Gross_Score 0) mean the game hasn't been played —
        # treat them as "no score yet", not as an existing record.
        has_real_score = (
            not existing_row.empty
            and pd.notna(existing_row.iloc[0].get("Gross_Score"))
            and float(existing_row.iloc[0]["Gross_Score"]) > 0
        )

        if has_real_score:
            rec = existing_row.iloc[0].to_dict()
            played_on = str(rec["Date"]) if pd.notna(rec.get("Date")) else "未知日期"
            entered_by = str(rec["Updated_By"]) if pd.notna(rec.get("Updated_By")) else ""
            entered_at = str(rec["Updated_At"]) if pd.notna(rec.get("Updated_At")) else ""
            audit_txt = ""
            if entered_by or entered_at:
                audit_txt = f"（{entered_by or '管理员'} 录入于 {entered_at or '未知时间'}）"
            st.info(
                f"💡 该场次已有成绩{audit_txt}：净杆 **{int(rec.get('Net_Score', 0))}** · "
                f"总杆 **{int(rec.get('Gross_Score', 0))}** · 比赛日期 {played_on}。"
                f"如需修改请直接编辑下方表单，保存后将覆盖此纪录。\n\n"
                f"Existing score: Net {int(rec.get('Net_Score', 0))}, "
                f"Gross {int(rec.get('Gross_Score', 0))}, played {played_on}. "
                f"Saving will overwrite it."
            )
        else:
            rec = {
                "Net_Score": 0, "Gross_Score": 72, "Stableford": 36,
                "Eagles": 0, "Birdies": 0, "Pars": 0, "Bogeys": 0, "Double_Bogeys": 0
            }
            st.info(f"🆕 {p_sel} 的 {g_sel} 暂无成绩，保存后将创建新纪录。 No score recorded yet — saving will create one.")

        # Scorecard picker above the form: a new image is read once and pre-fills the
        # fields it finds; Save below still uploads it via github_upload_image.
        uploaded_scorecard = st.file_uploader(
            "Scorecard image / 记分卡图片（自动填写）", type=None, key=LEAGUE_SCORECARD_UPLOAD_KEY
        )

        # Today's form defaults: the existing score when editing, otherwise 72/36/0.
        _base_date = date.today()
        if "Date" in rec and pd.notna(rec.get("Date")):
            try:
                _base_date = datetime.strptime(str(rec["Date"]), "%Y-%m-%d").date()
            except:
                pass
        _base_venue = str(rec.get("Venue", ""))
        _base_net = int(rec.get("Net_Score", 0))
        _base_gross = int(rec.get("Gross_Score", 72))
        _base_stableford = int(rec.get("Stableford", 36))
        _base_eagles = int(rec.get("Eagles", 0))
        _base_birdies = int(rec.get("Birdies", 0))
        _base_pars = int(rec.get("Pars", 0))
        _base_bogeys = int(rec.get("Bogeys", 0))
        _base_double_bogeys_or_worse = int(rec.get("Double_Bogeys", 0))

        # A different round (player/game) or a saved score means new defaults: drop the
        # widgets' stored values before they render so the form shows them.
        _base_values = {
            "date": _base_date, "venue": _base_venue, "net": _base_net, "gross": _base_gross,
            "stableford": _base_stableford, "eagles": _base_eagles, "birdies": _base_birdies,
            "pars": _base_pars, "bogeys": _base_bogeys,
            "double_bogeys_or_worse": _base_double_bogeys_or_worse,
        }
        # The round itself is part of the snapshot: two unplayed rounds share 72/36/0
        # defaults, and one round's prefill must never carry over to another.
        _snapshot = _scorecard_defaults_snapshot(round=(t_sel, p_sel, g_sel), **_base_values)
        if st.session_state.get(LEAGUE_SCORECARD_SNAPSHOT_KEY) != _snapshot:
            # Write the round's values instead of dropping the keys: the browser keeps
            # showing a keyed widget's old value unless it is set through st.session_state.
            for _field, _key in LEAGUE_SCORECARD_WIDGET_KEYS.items():
                st.session_state[_key] = _base_values[_field]
            # The card's player pick belongs to the round it was made for.
            st.session_state[LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY] = None
            st.session_state.pop(LEAGUE_SCORECARD_APPLIED_PICK_KEY, None)
            st.session_state[LEAGUE_SCORECARD_SNAPSHOT_KEY] = _snapshot

        # A new card is read once; every player found on it is kept for the picker below.
        widget_keys = LEAGUE_SCORECARD_WIDGET_KEYS
        players_result = LeagueScorecardPlayersResult([])
        if uploaded_scorecard is not None:
            image_bytes = uploaded_scorecard.getvalue()
            mime_type = uploaded_scorecard.type
            fingerprint = scorecard_upload_fingerprint(uploaded_scorecard.name, image_bytes)
            if st.session_state.get(LEAGUE_SCORECARD_LAST_READ_KEY) != fingerprint:
                st.session_state[LEAGUE_SCORECARD_LAST_READ_KEY] = fingerprint
                with st.spinner("正在识别记分卡… Reading the scorecard…"):
                    players_result: LeagueScorecardPlayersResult = read_league_scorecard_players(image_bytes, mime_type)
                players_result = _scorecard_players_for_form(players_result)
                st.session_state[LEAGUE_SCORECARD_PLAYERS_KEY] = players_result
                # A new card starts with nobody picked and the round's own values in the form.
                st.session_state[LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY] = None
                st.session_state.pop(LEAGUE_SCORECARD_APPLIED_PICK_KEY, None)
                for _field, _key in widget_keys.items():
                    st.session_state[_key] = _base_values[_field]
                if players_result.unavailable_reason is not None or not players_result.players:
                    st.session_state[LEAGUE_SCORECARD_NOTICE_KEY] = AUTOFILL_UNAVAILABLE_NOTICE
                else:
                    st.session_state.pop(LEAGUE_SCORECARD_NOTICE_KEY, None)
                st.rerun()
            players_result = st.session_state.get(LEAGUE_SCORECARD_PLAYERS_KEY) or players_result
        else:
            st.session_state[LEAGUE_SCORECARD_NOTICE_KEY] = AUTOFILL_UNAVAILABLE_NOTICE
            # Selecting the same card again after clearing it is a new, manual read.
            st.session_state.pop(LEAGUE_SCORECARD_LAST_READ_KEY, None)
            st.session_state.pop(LEAGUE_SCORECARD_PLAYERS_KEY, None)

        if st.session_state.get(LEAGUE_SCORECARD_NOTICE_KEY):
            st.info(st.session_state[LEAGUE_SCORECARD_NOTICE_KEY])

        # Every player read off the card, labelled as printed; the admin picks whose scores to use.
        selected_index: int | None = None
        if players_result.players:
            selected_index: int | None = st.selectbox(
                "Player",
                options=[player.index for player in players_result.players],
                format_func=lambda index: players_result.players[index].label
                + _scorecard_duplicate_suffix(players_result.players, index),
                index=None,
                key=LEAGUE_SCORECARD_PLAYER_SELECTOR_KEY,
                placeholder=LEAGUE_SCORECARD_PLAYER_PLACEHOLDER,
            )
            # Apply only when the pick (or the card) changes, before the form's widgets
            # render. Every other rerun, Save included, keeps the form as the admin left it.
            _pick = (st.session_state.get(LEAGUE_SCORECARD_LAST_READ_KEY), selected_index)
            if st.session_state.get(LEAGUE_SCORECARD_APPLIED_PICK_KEY) != _pick:
                st.session_state[LEAGUE_SCORECARD_APPLIED_PICK_KEY] = _pick
                _applied = apply_selected_player_scorecard_updates(
                    players_result,
                    selected_index,
                    widget_keys,
                    st.session_state,
                )
                if "date" in _applied:
                    try:
                        st.session_state[widget_keys["date"]] = date.fromisoformat(
                            str(st.session_state[widget_keys["date"]])
                        )
                    except ValueError:
                        _applied.remove("date")
                # Fields the picked player has none of show the round's own values again,
                # never the previous pick's (written, so the browser updates them too).
                for _field in LEAGUE_SCORECARD_FIELD_KEYS:
                    if _field not in _applied:
                        st.session_state[widget_keys[_field]] = _base_values[_field]
                if _applied:
                    st.success(
                        f"🤖 已根据记分卡自动填写 {len(_applied)} 项，请核对后保存。 "
                        f"Auto-filled from the scorecard: {', '.join(_applied)}. Check them, then Save."
                    )

        # The picker's image is the scorecard Save uploads, when it is an image type.
        scorecard_pic = (
            uploaded_scorecard
            if uploaded_scorecard is not None
            and uploaded_scorecard.name.rsplit(".", 1)[-1].lower() in SCORECARD_SAVE_EXTENSIONS
            else None
        )

        with st.form("league_score_form"):
            vc1, vc2 = st.columns(2)
            in_date = vc1.date_input("日期 Date", **_scorecard_widget_default("date", _base_date))
            in_venue = vc2.text_input("场地 Venue", **_scorecard_widget_default("venue", _base_venue))

            sc1, sc2, sc3 = st.columns(3)
            in_net = sc1.number_input("净杆 Net Score", **_scorecard_widget_default("net", _base_net))
            in_gross = sc2.number_input("总杆 Gross Score", **_scorecard_widget_default("gross", _base_gross))
            in_stable = sc3.number_input("稳定福分 Stableford", **_scorecard_widget_default("stableford", _base_stableford))

            st.write("击球统计 Stats:")
            bc1, bc2, bc3, bc4, bc5 = st.columns(5)
            in_eg = bc1.number_input("老鹰 Eagle", min_value=0, **_scorecard_widget_default("eagles", _base_eagles))
            in_bd = bc2.number_input("小鸟 Birdie", min_value=0, **_scorecard_widget_default("birdies", _base_birdies))
            in_par = bc3.number_input("标准 Par", min_value=0, **_scorecard_widget_default("pars", _base_pars))
            in_bg = bc4.number_input("柏忌 Bogey", min_value=0, **_scorecard_widget_default("bogeys", _base_bogeys))
            in_dbg = bc5.number_input("双柏忌+ D.Bogey+", min_value=0, **_scorecard_widget_default("double_bogeys_or_worse", _base_double_bogeys_or_worse))

            if st.form_submit_button("✅ 保存成绩 Save", width='stretch'):
                total_holes = in_eg + in_bd + in_par + in_bg + in_dbg
                if total_holes > 18:
                    st.error(f"❌ 错误：各项击球统计之和（{total_holes}）不能超过 18 洞。 Total holes cannot exceed 18.")
                else:
                    if not existing_row.empty:
                        df = df[~mask]

                    try:
                        game_no = int(g_sel.split()[-1])
                    except:
                        game_no = 1

                    new_row = pd.DataFrame([{
                        "Player": p_sel,
                        "Tournament": t_sel,
                        "Game": g_sel,
                        "Game_No": game_no,
                        "Date": str(in_date),
                        "Venue": in_venue.strip(),
                        "Net_Score": in_net,
                        "Gross_Score": in_gross,
                        "Stableford": in_stable,
                        "Eagles": in_eg,
                        "Birdies": in_bd,
                        "Pars": in_par,
                        "Bogeys": in_bg,
                        "Double_Bogeys": in_dbg,
                        "Updated_At": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Updated_By": get_admin_name(),
                    }])
                    df = pd.concat([df, new_row], ignore_index=True)

                    # Upload scorecard image first if provided
                    upload_success = True
                    if scorecard_pic is not None:
                        filename = f"league_{t_sel}_{g_sel}_{p_sel}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{scorecard_pic.name.split('.')[-1]}"
                        filename = filename.replace(" ", "_")
                        upload_success = github_upload_image(scorecard_pic.getvalue(), filename)

                    # Save scores (triggers background push of gco_state.json)
                    save_scores(df)

                    # Queue feedback so it survives the rerun
                    action = "已更新" if has_real_score else "已保存"
                    verb = "updated" if has_real_score else "saved"
                    flash(st, f"✅ {action} {p_sel} · {t_sel} {g_sel}：净杆 {in_net}，总杆 {in_gross}。 "
                              f"Score {verb} for {p_sel}.")
                    if scorecard_pic is not None:
                        if upload_success:
                            flash(st, "🖼️ 计分卡已成功上传。 Scorecard uploaded.")
                        else:
                            flash(st, "⚠️ 成绩已保存，但计分卡上传失败，请稍后重试。 Scorecard upload failed — please retry.", kind="warning")
                    st.rerun()

