"""
GCO 2026 – Individual Cup (Knockout Match Play) Bracket
"""
import streamlit as st
import json
import datetime

import streamlit as st
from theme import inject_theme, hero, section, flash, show_flash, sync_status
from data import load_cup, save_cup, PLAYERS, github_upload_image
from auth import is_admin_user

st.set_page_config(page_title="GCO | 个人杯赛", page_icon="🥊", layout="wide")
inject_theme(st)

hero(st, "🥊 个人杯赛", "Knockout Match Play Bracket", "GCO 2026")
show_flash(st)

cup = load_cup()
draw = cup["draw"]        # {"P1": "刘北南", …}
rounds = cup["rounds"]    # {"R1": […], "R2": […], …}
byes = cup["byes"]        # ["P1", "P2", "P7", "P8"]
play_by_dates = cup.get("play_by_dates", {})

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

# ── Visual Bracket ──────────────────────────────────────────────────────────────
section(st, "🗺️", "赛程支架 Visual Bracket")

st.markdown("""
<style>
/* Modern Matchplay Bracket Style */
.brkt-col {
    display: flex;
    flex-direction: column;
    justify-content: space-around;
    height: 100%;
}
.brkt-match {
    background: #f4f6f8;
    border: 1px solid #e1e4e8;
    border-radius: 8px;
    margin-bottom: 20px;
    font-family: 'Inter', sans-serif;
    color: #2c2c2c;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    font-size: 0.85rem;
}
.brkt-header {
    background: #eef1f4;
    padding: 4px 8px;
    font-size: 0.7rem;
    color: #6b7280;
    border-bottom: 1px solid #e1e4e8;
}
.brkt-player-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 10px;
    border-bottom: 1px solid #e1e4e8;
}
.brkt-player-row:last-child {
    border-bottom: none;
}
.brkt-player-row.winner {
    background: #4ce0b3; /* Bright cyan/green for winner */
    font-weight: 700;
}
.brkt-score {
    background: rgba(0,0,0,0.1);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.75rem;
}
.seed-txt {
    color: #9ca3af;
    font-size: 0.75rem;
    margin-left: 4px;
}
</style>
""", unsafe_allow_html=True)

# Use 4 columns for the 4 rounds
cols = st.columns(4)

for col_idx, (rk, rl) in enumerate(ROUND_LABELS.items()):
    with cols[col_idx]:
        st.markdown(f"<div style='text-align:center; font-weight:bold; color:var(--gold); margin-bottom:0.2rem;'>{rl}</div>", unsafe_allow_html=True)
        date_str = play_by_dates.get(rk, "未设置 Not Set")
        st.markdown(f"<div style='text-align:center; font-size:0.8rem; color:#6b7280; margin-bottom:1rem;'>📅 Play by: {date_str}</div>", unsafe_allow_html=True)
        matches = rounds.get(rk, [])
        if not matches:
            st.info("待定 TBD")
        else:
            # We add blank spacing to align next rounds to the middle of previous rounds
            # For simplicity, we just render them vertically spaced
            for idx, m in enumerate(matches):
                slots = m["match"].split(" vs ")
                p1_slot = slots[0]
                p2_slot = slots[1] if len(slots) > 1 else None
                
                p1_name = draw.get(p1_slot, "TBD") if p1_slot else "BYE"
                p2_name = draw.get(p2_slot, "TBD") if p2_slot else "BYE"
                
                home_slot = m.get("home")
                if home_slot:
                    if home_slot == p1_slot:
                        p1_name += " *"
                    elif home_slot == p2_slot:
                        p2_name += " *"
                
                winner = m.get("winner")
                score = m.get("score", "")

                p1_class = "winner" if winner == p1_slot else ""
                p2_class = "winner" if winner == p2_slot else ""

                score_html_1 = f"<div class='brkt-score'>{score} FINAL</div>" if p1_class and score else ""
                score_html_2 = f"<div class='brkt-score'>{score} FINAL</div>" if p2_class and score else ""

                m_html = f"""<div class="brkt-col">
  <div class="brkt-match">
    <div class="brkt-header">Match {idx+1}</div>
    <div class="brkt-player-row {p1_class}">
      <div>🏴󠁧󠁢󠁳󠁣󠁴󠁿 {p1_name} <span class="seed-txt">({p1_slot})</span></div>
      {score_html_1}
    </div>
    <div class="brkt-player-row {p2_class}">
      <div>🏴󠁧󠁢󠁳󠁣󠁴󠁿 {p2_name} <span class="seed-txt">({p2_slot if p2_slot else 'BYE'})</span></div>
      {score_html_2}
    </div>
  </div>
</div>"""
                st.html(m_html)

# ── Record Match Result Forms ─────────────────────────────────────────────────
if is_admin_user():
    section(st, "✏️", "录入赛果 Record Results")
    sync_status(st)
    round_tabs = st.tabs(list(ROUND_LABELS.values()))
    for tab, (rk, rl) in zip(round_tabs, ROUND_LABELS.items()):
        with tab:
            matches = rounds.get(rk, [])
            if matches:
                match_options = [m["match"] for m in matches if not m.get("winner")]
                if not match_options:
                    st.success("✅ 本轮所有比赛结果已录入。")
                else:
                    chosen_match = st.selectbox("选择对阵", match_options, key=f"sel_m_{rk}")
                    m_obj = next(m for m in matches if m["match"] == chosen_match)
                    slots2 = chosen_match.split(" vs ")
                    p1n = draw.get(slots2[0], slots2[0])
                    p2n = draw.get(slots2[1], slots2[1]) if len(slots2) > 1 else "TBD"
                    
                    with st.form(f"form_{rk}"):
                        winner_opts = [p1n, p2n] if len(slots2) > 1 else [p1n]
                        winner_choice = st.radio("胜者 Winner", winner_opts, horizontal=True)
                        score_input = st.text_input("比分 Score (e.g. 3&2)", "")
                        
                        st.write("可选：上传计分卡 Optional: Upload Scorecard")
                        scorecard_pic = st.file_uploader("支持格式 / Supported formats: JPG, PNG", type=["jpg", "jpeg", "png"], key=f"file_{rk}")
                        
                        if st.form_submit_button("💾 保存 Save"):
                            if len(slots2) > 1:
                                winner_slot_save = slots2[0] if winner_choice == p1n else slots2[1]
                            else:
                                winner_slot_save = slots2[0]
                            m_obj["winner"] = winner_slot_save
                            m_obj["score"] = score_input.strip()
                            # Upload scorecard image first if provided
                            upload_success = True
                            if scorecard_pic is not None:
                                p2_slot_name = slots2[1] if len(slots2) > 1 else 'BYE'
                                filename = f"cup_{rk}_{slots2[0]}_vs_{p2_slot_name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.{scorecard_pic.name.split('.')[-1]}"
                                filename = filename.replace(" ", "_").replace("/", "_")
                                upload_success = github_upload_image(scorecard_pic.getvalue(), filename)
                            
                            # Save cup data (triggers background push of gco_state.json)
                            save_cup(cup)

                            # Queue feedback so it survives the rerun
                            score_txt = f"（{score_input.strip()}）" if score_input.strip() else ""
                            flash(st, f"✅ 已记录 {rl}：{winner_choice} 获胜{score_txt}！ Result saved: {winner_choice} wins.")
                            if scorecard_pic is not None:
                                if upload_success:
                                    flash(st, "🖼️ 计分卡已成功上传。 Scorecard uploaded.")
                                else:
                                    flash(st, "⚠️ 赛果已保存，但计分卡上传失败，请稍后重试。 Scorecard upload failed — please retry.", kind="warning")
                            st.rerun()

    # ── Admin: advance to next round ──────────────────────────────────────────────
    section(st, "⚙️", "管理 Admin")

    with st.expander("📅 设置完赛日期 Set Play-by Dates"):
        st.write("为各个轮次设置最晚完赛日期：")
        with st.form("play_by_form"):
            new_dates = {}
            for rk, rl in ROUND_LABELS.items():
                current_date_str = play_by_dates.get(rk, "")
                try:
                    current_date_obj = datetime.datetime.strptime(current_date_str, "%Y-%m-%d").date() if current_date_str else None
                except ValueError:
                    current_date_obj = None
                new_dates[rk] = st.date_input(f"{rl} 完赛日期 (Play-by Date)", value=current_date_obj)
                
            if st.form_submit_button("💾 保存日期 Save Dates"):
                cup["play_by_dates"] = {k: v.strftime("%Y-%m-%d") for k, v in new_dates.items() if v}
                save_cup(cup)
                flash(st, "✅ 完赛日期已更新！ Play-by dates saved.")
                st.rerun()

    with st.expander("🔧 推进赛程 Advance Rounds & Fixtures"):
        st.write("如需手动设置下一轮对阵，请在此填写：")
        with st.form("advance_form"):
            rk_select = st.selectbox("目标轮次 Target Round", ["R1", "R2", "SF", "F"])
            match_input = st.text_area(
                "对阵（每行一场，格式：P1 vs P3/P4之间的胜者 → 填写slot，如 P1 vs P3）\n"
                "If someone has a BYE, just put their slot (e.g. P1)",
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
                flash(st, f"✅ {ROUND_LABELS[rk_select]} 对阵已设置（共 {len(new_matches)} 场）！ Fixtures saved.")
                st.rerun()

    with st.expander("👥 管理初始抽签名单 Manage Initial Draw"):
        st.write("将球员分配至抽签位 (Assign players to draw slots):")
        with st.form("manage_draw_form"):
            # We need P1 through P12, maybe up to P16
            new_draw = {}
            for i in range(1, 13):
                slot = f"P{i}"
                current_val = draw.get(slot, "")
                # Provide an empty option as default
                player_opts = ["TBD"] + PLAYERS
                if current_val in player_opts:
                    idx = player_opts.index(current_val)
                else:
                    idx = 0
                selected_p = st.selectbox(f"Slot {slot}", player_opts, index=idx, key=f"sel_{slot}")
                new_draw[slot] = selected_p
                
            if st.form_submit_button("💾 保存名单 Save Draw Configuration"):
                cup["draw"] = new_draw
                save_cup(cup)
                flash(st, "✅ 抽签名单已更新！ Draw configuration saved.")
                st.rerun()
