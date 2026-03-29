"""
GCO 2026 – Announcements page
"""
import streamlit as st
from datetime import date
from theme import inject_theme, hero, section
from data import load_announcements, save_announcements

st.set_page_config(page_title="GCO | 公告", page_icon="📢", layout="wide")
inject_theme(st)

hero(st, "📢 俱乐部公告", "Club Announcements", "GCO 2026")

anns = load_announcements()
# Sort: pinned first, then by date desc
anns_sorted = sorted(anns, key=lambda a: (not a.get("pinned", False), a["date"]), reverse=False)
anns_sorted = sorted(anns_sorted, key=lambda a: (not a.get("pinned", False), a["date"]))

# ── Rulebook Download ─────────────────────────────────────────────────────────
section(st, "📚", "赛季章程 Rulebook")
st.info("了解 2026 赛季详细规则、积分系统及注意事项。")
try:
    with open("docs/gco-2026.pdf", "rb") as f:
        st.download_button(
            label="📄 下载 2026 赛季章程 (Download PDF)",
            data=f,
            file_name="GCO_2026_Rulebook.pdf",
            mime="application/pdf"
        )
except FileNotFoundError:
    st.error("Rulebook PDF not found.")

# ── Display existing announcements ────────────────────────────────────────────
section(st, "📌", "最新公告")

for ann in anns_sorted:
    pinned_cls = "pinned" if ann.get("pinned") else ""
    tags_html = "".join(
        f'<span class="gco-pill {"pill-pinned" if t == "重要" else "pill-league"}">{t}</span>'
        for t in ann.get("tags", [])
    )
    body_html = ann["body"].replace("\n\n", "<br><br>").replace("\n", "<br>")
    card_html = f"""
    <div class="ann-card {pinned_cls}">
        <div class="ann-title">{"📌 " if ann.get("pinned") else ""}{ann["title"]}</div>
        <div class="ann-meta">🗓 {ann["date"]}　✍️ {ann["author"]}　{tags_html}</div>
        <div class="ann-body">{body_html}</div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

# ── Admin: post new announcement ──────────────────────────────────────────────
section(st, "✏️", "发布新公告")

with st.expander("➕ 发布新公告 / Post New Announcement", expanded=False):
    with st.form("new_ann_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            new_title = st.text_input("标题 Title *", placeholder="e.g. 下一轮比赛通知")
        with col2:
            new_author = st.text_input("发布人 Author", value="组委会")

        new_body = st.text_area(
            "内容 Body *",
            height=200,
            placeholder="支持换行。Use blank lines between paragraphs.\n\n**markdown bold** is supported."
        )

        col3, col4, col5 = st.columns([2, 2, 1])
        with col3:
            new_date = st.date_input("日期 Date", value=date.today())
        with col4:
            raw_tags = st.text_input("标签 Tags (comma-separated)", placeholder="重要,杯赛")
        with col5:
            new_pinned = st.checkbox("📌 置顶 Pin", value=False)

        submitted = st.form_submit_button("📢 发布 Publish", width='stretch')
        if submitted:
            if not new_title.strip() or not new_body.strip():
                st.error("请填写标题和内容！")
            else:
                tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
                new_ann = {
                    "id": f"ann-{len(anns)+1:03d}",
                    "title": new_title.strip(),
                    "date": str(new_date),
                    "author": new_author.strip() or "组委会",
                    "pinned": new_pinned,
                    "body": new_body.strip(),
                    "tags": tags,
                }
                anns.append(new_ann)
                save_announcements(anns)
                st.success("✅ 公告已发布！请刷新页面查看。")
                st.balloons()
