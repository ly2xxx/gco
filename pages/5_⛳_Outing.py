"""
GCO 2026 – Outing Day (Red vs Black 对抗赛)
"""
import streamlit as st
import plotly.graph_objects as go
from theme import inject_theme, hero, section
from data import load_outing, save_outing
from auth import is_admin_user

st.set_page_config(page_title="GCO | Outing Day", page_icon="⛳", layout="wide")
inject_theme(st)

hero(st, "⛳ Outing Day 对抗赛", "Red vs Black Team Outings", "GCO 2026")

outing_data = load_outing()
red_t = outing_data["red_team"]
black_t = outing_data["black_team"]
matches = outing_data["matches"]
tot_pts = outing_data["total_points"]
win_thresh = outing_data["winning_threshold"]

# Calculate current score
red_score = 0.0
black_score = 0.0
for m in matches:
    if m["status"] == "completed" and m["red_score"] is not None and m["black_score"] is not None:
        red_score += float(m["red_score"])
        black_score += float(m["black_score"])

# ── Roster display ─────────────────────────────────────────────────────────────
section(st, "👥", "两队阵容 Rosters")

col_r, col_b = st.columns(2)

with col_r:
    st.markdown("""
    <div style="background:var(--surface2); border-left:4px solid var(--red-team); border-radius:8px; padding:1rem; margin-bottom:1rem">
        <h3 style="margin-top:0;color:var(--red-team)">🔴 红队 Red Team</h3>
        <p style="font-size:1.1rem; line-height:1.8">
    """ + " • ".join(red_t) + """
        </p>
    </div>
    """, unsafe_allow_html=True)

with col_b:
    st.markdown("""
    <div style="background:var(--surface2); border-left:4px solid var(--black-team); border-radius:8px; padding:1rem; margin-bottom:1rem">
        <h3 style="margin-top:0;color:#aaa">⚫ 黑队 Black Team</h3>
        <p style="font-size:1.1rem; line-height:1.8">
    """ + " • ".join(black_t) + """
        </p>
    </div>
    """, unsafe_allow_html=True)

# ── Current Score ──────────────────────────────────────────────────────────────
section(st, "📈", "当前赛况 Current Score")

# Visual progress bar
red_pct = min(100, max(0, (red_score / tot_pts) * 100))

html_score = f"""
<div style="text-align:center; margin-bottom:1rem">
    <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:5px">
        <h2 style="margin:0; color:var(--red-team)">🔴 {red_score} pts</h2>
        <span style="color:var(--text-muted); font-size:1rem">捧杯条件：先得 {win_thresh} 分即获胜</span>
        <h2 style="margin:0; color:#aaa">{black_score} pts ⚫</h2>
    </div>
    <div class="score-bar-wrap">
        <div class="score-bar-red" style="width: {red_pct}%;"></div>
    </div>
</div>
"""
st.markdown(html_score, unsafe_allow_html=True)

if red_score >= win_thresh:
    st.success("🏆 恭喜红队获得 GCO 2026 团队对抗赛最高荣誉！")
    st.balloons()
elif black_score >= win_thresh:
    st.info("🏆 恭喜黑队获得 GCO 2026 团队对抗赛最高荣誉！")
    st.balloons()

# ── Match details ──────────────────────────────────────────────────────────────
section(st, "⚔️", "比赛概况 Matches")

for m in matches:
    col1, col2 = st.columns([3, 1])
    is_done = m["status"] == "completed"
    
    with col1:
        st.markdown(f"#### {m['name']}")
        st.caption(f"🗓 日期 Date: {m['date']}　📍 场地 Venue: {m['venue']}")
        
        # Display participating players
        r_players = m.get("red_players", [])
        b_players = m.get("black_players", [])
        if r_players or b_players:
            p_cols = st.columns(2)
            with p_cols[0]:
                st.markdown(f"<span style='color:var(--red-team); font-size:0.85rem'>🔴 {' • '.join(r_players) if r_players else 'TBD'}</span>", unsafe_allow_html=True)
            with p_cols[1]:
                st.markdown(f"<span style='color:#aaa; font-size:0.85rem'>⚫ {' • '.join(b_players) if b_players else 'TBD'}</span>", unsafe_allow_html=True)

    with col2:
        if is_done:
            r_pts = float(m["red_score"] or 0)
            b_pts = float(m["black_score"] or 0)
            st.markdown(f"""
            <div style="background:var(--surface3); text-align:center; padding:10px; border-radius:8px; font-weight:800; font-size:1.2rem">
                <span style="color:var(--red-team)">{r_pts}</span>
                <span style="color:var(--text-muted); font-size:1rem; margin:0 5px">vs</span>
                <span style="color:#aaa">{b_pts}</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:var(--surface1); border:1px solid var(--surface3); text-align:center; padding:10px; border-radius:8px; color:var(--text-muted)">
                ⏳ 未进行 Pending
            </div>
            """, unsafe_allow_html=True)
            
    if is_admin_user():
        with st.expander(f"⚙️ 编辑/更新 {m['name']}"):
            with st.form(f"outing_form_{m['id']}"):
                st.markdown("**📝 比赛信息 Match Info**")
                new_name = st.text_input("比赛标题 Title", value=m["name"], key=f"name_{m['id']}")
                col_meta1, col_meta2 = st.columns(2)
                with col_meta1:
                    new_date = st.text_input("🗓 日期 Date (YYYY-MM-DD)", value=m["date"], key=f"date_{m['id']}")
                with col_meta2:
                    new_venue = st.text_input("📍 场地 Venue", value=m["venue"], key=f"venue_{m['id']}")

                st.markdown("**👥 参赛名单 Lineups (Max 4 per team)**")
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    new_red_players = st.multiselect(
                        "🔴 红队选手", 
                        options=red_t, 
                        default=m.get("red_players", []),
                        max_selections=9,
                        key=f"red_p_{m['id']}"
                    )
                with col_p2:
                    new_black_players = st.multiselect(
                        "⚫ 黑队选手", 
                        options=black_t, 
                        default=m.get("black_players", []),
                        max_selections=9,
                        key=f"black_p_{m['id']}"
                    )

                st.markdown("**📊 赛果 Scores**")
                col_in1, col_in2, col_in3 = st.columns(3)
                with col_in1:
                    new_red = st.number_input("🔴 红队得分", min_value=0.0, max_value=2.0, step=0.5, value=float(m["red_score"] or 0))
                with col_in2:
                    new_black = st.number_input("⚫ 黑队得分", min_value=0.0, max_value=2.0, step=0.5, value=float(m["black_score"] or 0))
                with col_in3:
                    new_status = st.selectbox("状态 Status", ["upcoming", "completed"], index=1 if is_done else 0)

                if st.form_submit_button("✅ 保存更新 Update"):
                    m["name"] = new_name.strip() or m["name"]
                    m["date"] = new_date.strip() or m["date"]
                    m["venue"] = new_venue.strip() or m["venue"]
                    m["red_score"] = new_red
                    m["black_score"] = new_black
                    m["red_players"] = new_red_players
                    m["black_players"] = new_black_players
                    m["status"] = new_status
                    save_outing(outing_data)
                    st.success("比赛信息及赛果已更新！Match updated successfully!")
                    st.rerun()
    st.markdown("---")
