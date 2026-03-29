"""
GCO 2026 – Team Matches (红黑队赛)
"""
import streamlit as st
import plotly.graph_objects as go
from pages.theme import inject_theme, hero, section
from pages.data import load_team, save_team

st.set_page_config(page_title="GCO | 团队赛", page_icon="🤝", layout="wide")
inject_theme(st)

hero(st, "🤝 团队对抗赛", "Red vs Black Team Matches", "GCO 2026")

team_data = load_team()
red_t = team_data["red_team"]
black_t = team_data["black_team"]
matches = team_data["matches"]
tot_pts = team_data["total_points"]
win_thresh = team_data["winning_threshold"]

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
    st.success("🏆 恭喜红队获得 GCO 2026 团队赛最高荣誉！")
    st.balloons()
elif black_score >= win_thresh:
    st.info("🏆 恭喜黑队获得 GCO 2026 团队赛最高荣誉！")
    st.balloons()

# ── Match details ──────────────────────────────────────────────────────────────
section(st, "⚔️", "比赛概况 Matches")

for m in matches:
    col1, col2 = st.columns([3, 1])
    is_done = m["status"] == "completed"
    
    with col1:
        st.markdown(f"#### {m['name']}")
        st.caption(f"🗓 日期 Date: {m['date']}　📍 场地 Venue: {m['venue']}")
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
            
    with st.expander(f"⚙️ 更新 {m['name']} 赛果"):
        with st.form(f"team_form_{m['id']}"):
            st.write(f"录入 **{m['name']}** 的得分")
            col_in1, col_in2, col_in3 = st.columns(3)
            with col_in1:
                new_red = st.number_input("🔴 红队得分", min_value=0.0, max_value=2.0, step=0.5, value=float(m["red_score"] or 0))
            with col_in2:
                new_black = st.number_input("⚫ 黑队得分", min_value=0.0, max_value=2.0, step=0.5, value=float(m["black_score"] or 0))
            with col_in3:
                new_status = st.selectbox("状态 Status", ["upcoming", "completed"], index=1 if is_done else 0)
            
            if st.form_submit_button("✅ 保存更新 Update"):
                m["red_score"] = new_red
                m["black_score"] = new_black
                m["status"] = new_status
                save_team(team_data)
                st.success("比赛结果已更新！")
                st.rerun()
    st.markdown("---")
