"""
GCO 2026 – Announcements page
"""
import streamlit as st
from datetime import date
from theme import inject_theme, hero, section
from data import load_announcements, save_announcements
from auth import is_admin_user

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
if is_admin_user():
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

    # ── Admin: edit / delete existing announcements ────────────────────────────
    if anns:
        with st.expander("✏️ 编辑/删除公告 / Edit or Delete Announcement", expanded=False):
            ann_labels = [f"{a['date']} — {a['title']}" for a in anns]
            sel_idx = st.selectbox(
                "选择要编辑的公告 Select announcement to edit",
                range(len(anns)),
                format_func=lambda i: ann_labels[i],
                key="edit_ann_select",
            )
            sel = anns[sel_idx]

            with st.form("edit_ann_form"):
                ec1, ec2 = st.columns([3, 1])
                with ec1:
                    edit_title = st.text_input("标题 Title *", value=sel["title"])
                with ec2:
                    edit_author = st.text_input("发布人 Author", value=sel.get("author", "组委会"))

                edit_body = st.text_area("内容 Body *", value=sel["body"], height=200)

                ec3, ec4, ec5 = st.columns([2, 2, 1])
                with ec3:
                    edit_date = st.date_input(
                        "日期 Date",
                        value=date.fromisoformat(sel["date"]),
                    )
                with ec4:
                    edit_raw_tags = st.text_input(
                        "标签 Tags (comma-separated)",
                        value=", ".join(sel.get("tags", [])),
                    )
                with ec5:
                    edit_pinned = st.checkbox("📌 置顶 Pin", value=sel.get("pinned", False))

                save_col, del_col = st.columns(2)
                with save_col:
                    save_edit = st.form_submit_button("💾 保存修改 Save", width="stretch")
                with del_col:
                    delete_ann = st.form_submit_button("🗑️ 删除 Delete", width="stretch")

            if save_edit:
                if not edit_title.strip() or not edit_body.strip():
                    st.error("请填写标题和内容！")
                else:
                    anns[sel_idx].update({
                        "title": edit_title.strip(),
                        "author": edit_author.strip() or "组委会",
                        "body": edit_body.strip(),
                        "date": str(edit_date),
                        "tags": [t.strip() for t in edit_raw_tags.split(",") if t.strip()],
                        "pinned": edit_pinned,
                    })
                    save_announcements(anns)
                    st.success("✅ 公告已更新！")
                    st.rerun()

            if delete_ann:
                anns.pop(sel_idx)
                save_announcements(anns)
                st.success("🗑️ 公告已删除！")
                st.rerun()
