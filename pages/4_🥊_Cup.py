"""
GCO 2026 – Individual Cup (Knockout Match Play) Bracket
"""
import streamlit as st
from pages.theme import inject_theme, hero, section
from pages.data import load_cup, save_cup, PLAYERS

st.set_page_config(page_title="GCO | 个人杯赛", page_icon="🥊", layout="wide")
inject_theme(st)

hero(st, "🥊 个人杯赛", "Knockout Match Play Bracket", "GCO 2026")

cup = load_cup()
draw = cup["draw"]        # {"P1": "刘北南", …}
rounds = cup["rounds"]    # {"R1": […], "R2": […], …}
byes = cup["byes"]        # ["P1", "P2", "P7", "P8"]

ROUND_LABELS = {"R1": "第一轮 Round 1", "R2": "第二轮 Round 2",
                "SF": "半决赛 Semi-Final", "F": "决赛 Final"}

# ── Draw display ──────────────────────────────────────────────────────────────
section(st, "🎰", "抽签结果 Draw")

cols = st.columns(4)
for i, (slot, player) in enumerate(draw.items()):
    bye_txt = "  ⚡ Auto-qualify" if slot in byes else ""
    cols[i % 4].markdown(
        f'<div class="bracket-match {"bracket-bye" if slot in byes else ""}">'
        f'<b style="color:var(--gold)">{slot}</b>　{player}{bye_txt}</div>',
        unsafe_allow_html=True,
    )

# ── Bracket ───────────────────────────────────────────────────────────────────
section(st, "🗺️", "赛程支架 Bracket")

round_tabs = st.tabs(list(ROUND_LABELS.values()))

for tab, (rk, rl) in zip(round_tabs, ROUND_LABELS.items()):
    with tab:
        matches = rounds.get(rk, [])
        if not matches:
            st.info(f"⏳ {rl} 对阵未确定（等待上一轮结果）")
        else:
            for i, m in enumerate(matches):
                slots = m["match"].split(" vs ")
                p1_name = draw.get(slots[0], slots[0])
                p2_name = draw.get(slots[1], slots[1]) if len(slots) > 1 else "TBD"
                winner_slot = m.get("winner")
                winner_name = draw.get(winner_slot, winner_slot) if winner_slot else None
                score_txt = m.get("score", "")
                home_slot = m.get("home")

                home_badge = f'<span class="gco-pill pill-league">🏠 Home</span>' if home_slot == slots[0] else ""
                home_badge2 = f'<span class="gco-pill pill-league">🏠 Home</span>' if len(slots) > 1 and home_slot == slots[1] else ""
                win_html = (
                    f'<span class="gco-pill pill-cup">🏆 Winner: {winner_name}</span>' if winner_name else
                    '<span class="gco-pill" style="background:#333;color:#aaa">🕐 Pending</span>'
                )

                card = f"""
                <div class="bracket-match {"bracket-winner" if winner_name else ""}">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <b>{p1_name}</b> {home_badge}
                            <span style="color:var(--text-muted);margin:0 .5rem">vs</span>
                            <b>{p2_name}</b> {home_badge2}
                            {"<span style='color:var(--text-secondary);font-size:.82rem;margin-left:.5rem'>　" + score_txt + "</span>" if score_txt else ""}
                        </div>
                        <div>{win_html}</div>
                    </div>
                </div>
                """
                st.markdown(card, unsafe_allow_html=True)

            # Record result form
            with st.expander(f"✏️ 录入 {rl} 结果"):
                with st.form(f"form_{rk}"):
                    match_options = [m["match"] for m in matches if not m.get("winner")]
                    if not match_options:
                        st.success("✅ 本轮所有比赛结果已录入。")
                    else:
                        chosen_match = st.selectbox("选择对阵", match_options)
                        m_obj = next(m for m in matches if m["match"] == chosen_match)
                        slots2 = chosen_match.split(" vs ")
                        p1n = draw.get(slots2[0], slots2[0])
                        p2n = draw.get(slots2[1], slots2[1]) if len(slots2) > 1 else "TBD"
                        winner_choice = st.radio("胜者 Winner", [p1n, p2n], horizontal=True)
                        score_input = st.text_input("比分 Score (e.g. 3&2)", "")
                        if st.form_submit_button("💾 保存 Save"):
                            winner_slot_save = slots2[0] if winner_choice == p1n else slots2[1]
                            m_obj["winner"] = winner_slot_save
                            m_obj["score"] = score_input.strip()
                            save_cup(cup)
                            st.success(f"✅ 已记录：{winner_choice} 获胜！")
                            st.rerun()

# ── Admin: advance to next round ──────────────────────────────────────────────
section(st, "⚙️", "管理 Admin")

with st.expander("🔧 推进赛程 Advance Rounds"):
    st.write("如需手动设置下一轮对阵，请在此填写：")
    with st.form("advance_form"):
        rk_select = st.selectbox("目标轮次 Target Round", ["R2", "SF", "F"])
        match_input = st.text_area(
            "对阵（每行一场，格式：P1 vs P3/P4之间的胜者 → 填写slot，如 P1 vs P3）",
            placeholder="P1 vs P3\nP2 vs P5\nP7 vs P9\nP8 vs P11"
        )
        home_input = st.text_area("主场权（每行，格式 P1）", placeholder="P1\nP2\nP7\nP8")
        if st.form_submit_button("➕ 设置对阵 Set Fixtures"):
            match_lines = [ln.strip() for ln in match_input.strip().split("\n") if ln.strip()]
            home_lines = [ln.strip() for ln in home_input.strip().split("\n") if ln.strip()]
            new_matches = []
            for idx, ml in enumerate(match_lines):
                hm = home_lines[idx] if idx < len(home_lines) else None
                new_matches.append({"match": ml, "home": hm, "winner": None, "score": ""})
            cup["rounds"][rk_select] = new_matches
            save_cup(cup)
            st.success(f"✅ {ROUND_LABELS[rk_select]} 对阵已设置！")
            st.rerun()
