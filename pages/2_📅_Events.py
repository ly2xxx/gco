"""
GCO 2026 – Events Calendar page
"""
import streamlit as st
from datetime import date, datetime
from theme import inject_theme, hero, section, EVENT_COLORS
from data import load_events, save_events

st.set_page_config(page_title="GCO | 赛历", page_icon="📅", layout="wide")
inject_theme(st)

hero(st, "📅 2026赛历", "Season Schedule & Upcoming Events", "GCO 2026")

events = load_events()

# ── Filter bar ────────────────────────────────────────────────────────────────
col_f1, col_f2 = st.columns([3, 1])
with col_f1:
    type_filter = st.multiselect(
        "筛选类型 Filter by type",
        ["League", "Cup", "Outing", "Grand Final"],
        default=["League", "Cup", "Outing", "Grand Final"],
    )
with col_f2:
    show_past = st.checkbox("显示过去的赛事 Show past events", value=False)

today_str = str(date.today())
filtered = [
    e for e in events
    if e["type"] in type_filter and (show_past or e["date"] >= today_str)
]
filtered_sorted = sorted(filtered, key=lambda e: e["date"])

# ── Timeline display ──────────────────────────────────────────────────────────
section(st, "📆", "赛事日程")

if not filtered_sorted:
    st.info("📭 没有符合条件的赛事。")
else:
    all_cards_html = ""
    for ev in filtered_sorted:
        ev_date = datetime.strptime(ev["date"], "%Y-%m-%d")
        is_upcoming = ev["date"] >= today_str
        pill_cls, pill_label = EVENT_COLORS.get(ev["type"], ("pill-league", ev["type"]))
        days_to = (ev_date.date() - date.today()).days

        countdown_html = ""
        if is_upcoming:
            if days_to <= 7:
                countdown_html = f'<span style="color:#e74c3c;font-weight:700;margin-left:10px">⏰ {days_to}天后！</span>'
            elif days_to <= 30:
                countdown_html = f'<span style="color:#d4af37;font-weight:600;margin-left:10px">📌 {days_to}天后</span>'

        all_cards_html += f"""
        <div class="gco-card" style="display:flex;gap:1.5rem;align-items:center;padding:1.4rem;">
            <div style="min-width:80px;text-align:center;border-right:1px solid var(--surface3);padding-right:1rem;">
                <div style="font-size:1.8rem;font-weight:800;color:var(--gold);line-height:1;">{ev_date.day:02d}</div>
                <div style="font-size:.7rem;color:var(--text-muted);text-transform:uppercase;margin-top:4px;">
                    {ev_date.strftime('%b %Y')}
                </div>
            </div>
            <div style="flex:1;">
                <div style="display:flex;align-items:center;margin-bottom:6px;">
                    <span class="gco-pill {pill_cls}">{pill_label}</span>
                    {countdown_html}
                </div>
                <div style="font-size:1.1rem;font-weight:700;color:var(--text-primary);">
                    {ev['name']}
                </div>
                <div style="font-size:.85rem;color:var(--text-secondary);margin-top:4px;line-height:1.4">
                    {ev.get('details','')}
                </div>
            </div>
        </div>
        """
    st.html(all_cards_html)

# ── Admin: add / edit events ──────────────────────────────────────────────────
section(st, "⚙️", "管理赛事")

with st.expander("➕ 添加赛事 / Add Event", expanded=False):
    with st.form("add_event_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            ev_name = st.text_input("赛事名称 Name *")
            ev_date_input = st.date_input("日期 Date", value=date.today())
        with c2:
            ev_type = st.selectbox("类型 Type", ["League", "Cup", "Outing", "Grand Final"])
            ev_details = st.text_input("详情 Details", placeholder="Format, venue, etc.")
        submitted = st.form_submit_button("➕ 添加 Add", width='stretch')
        if submitted:
            if not ev_name.strip():
                st.error("请填写赛事名称！")
            else:
                events.append({
                    "date": str(ev_date_input),
                    "name": ev_name.strip(),
                    "type": ev_type,
                    "details": ev_details.strip(),
                })
                save_events(events)
                st.success("✅ 赛事已添加！请刷新查看。")
                st.rerun()
