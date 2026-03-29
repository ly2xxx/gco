"""
GCO 2026 Golf Club Events Management MVP
Main entrypoint page
"""
import streamlit as st
import datetime
from pages.theme import inject_theme, hero, section
from pages.data import load_announcements, load_events

st.set_page_config(
    page_title="GCO Golf Club",
    page_icon="⛳",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_theme(st)

# ── Home Hero ─────────────────────────────────────────────────────────────────
hero(st, "⛳ GCO Golf Club Dashboard", "Welcome to the 2026 Season", "GCO 2026")

# ── Dashboard Summary ─────────────────────────────────────────────────────────
col1, col2 = st.columns([2, 1])

with col1:
    section(st, "🔔", "最新动态 Latest")
    anns = load_announcements()
    # pinned and most recent
    anns_sorted = sorted(anns, key=lambda a: (not a.get("pinned", False), a["date"]))
    top_anns = anns_sorted[:2]
    
    if top_anns:
        for ann in top_anns:
            # Shorten body for preview
            body_preview = ann['body'][:100] + "..." if len(ann['body']) > 100 else ann['body']
            tags_html = "".join(f'<span class="gco-pill {"pill-pinned" if t == "重要" else "pill-league"}">{t}</span>' for t in ann.get("tags", []))
            
            st.markdown(f"""
            <div class="ann-card {'pinned' if ann.get('pinned') else ''}">
                <div class="ann-title">{"📌" if ann.get('pinned') else ""} {ann['title']}</div>
                <div class="ann-meta">{ann['date']} · {tags_html}</div>
                <div class="ann-body">{body_preview}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("暂无最新公告 No announcements yet.")
        
    st.page_link("pages/1_📢_Announcements.py", label="查看全部公告 View all announcements →", icon="📢")

with col2:
    section(st, "⏰", "近期赛事 Upcoming")
    events = load_events()
    today_str = str(datetime.date.today())
    upcoming = sorted([e for e in events if e["date"] >= today_str], key=lambda x: x["date"])[:3]
    
    if upcoming:
        for ev in upcoming:
            st.markdown(f"""
            <div class="gco-card" style="padding:1rem">
                <div style="color:var(--gold); font-weight:700; font-size:1.1rem">{ev['date']}</div>
                <div style="font-weight:600">{ev['name']}</div>
                <div style="color:var(--text-secondary); font-size:.85rem">{ev.get('details', '')}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("近期暂无赛事 No upcoming events.")
        
    st.page_link("pages/2_📅_Events.py", label="查看完整赛历 View full calendar →", icon="📅")

st.markdown("---")

# ── Quick Links ───────────────────────────────────────────────────────────────
section(st, "🔗", "快速导航 Quick Links")

ql_c1, ql_c2, ql_c3 = st.columns(3)

with ql_c1:
    st.markdown("""
        <div style="background:var(--surface1); border:1px solid var(--surface3); border-radius:12px; padding:1.5rem; text-align:center; height:100%">
            <div style="font-size:3rem; margin-bottom:1rem">🏆</div>
            <h3 style="margin:0 0 .5rem 0">个人联赛 League</h3>
            <p style="color:var(--text-secondary); margin-bottom:1.5rem">Order of Merit 净杆积分榜及个人成绩分析</p>
        </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/3_🏆_League.py", label="进入联赛 Enter →")

with ql_c2:
    st.markdown("""
        <div style="background:var(--surface1); border:1px solid var(--surface3); border-radius:12px; padding:1.5rem; text-align:center; height:100%">
            <div style="font-size:3rem; margin-bottom:1rem">🥊</div>
            <h3 style="margin:0 0 .5rem 0">个人杯赛 Cup</h3>
            <p style="color:var(--text-secondary); margin-bottom:1.5rem">Knockout Match Play 12人单淘汰赛程对阵</p>
        </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/4_🥊_Cup.py", label="进入杯赛 Enter →")

with ql_c3:
    st.markdown("""
        <div style="background:var(--surface1); border:1px solid var(--surface3); border-radius:12px; padding:1.5rem; text-align:center; height:100%">
            <div style="font-size:3rem; margin-bottom:1rem">🤝</div>
            <h3 style="margin:0 0 .5rem 0">对抗赛 Outing Match</h3>
            <p style="color:var(--text-secondary); margin-bottom:1.5rem">红队🔴 vs 黑队⚫ 4场团体比洞/比分为荣誉而战</p>
        </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/5_⛳_Outing.py", label="进入对抗赛 Enter →")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    """<div style='text-align:center; color:var(--text-muted); font-size:0.85rem'>
    GCO Golf Club Management Dashboard ©️ 2026<br>
    Built with <b>Streamlit</b> & <b>uv</b>
    </div>""", 
    unsafe_allow_html=True
)
