"""
GCO 2026 – Individual League (联赛) standings and tournament leaderboards
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pages.theme import inject_theme, hero, section
from pages.data import load_scores, LEAGUE_TOURNAMENTS, PLAYERS

st.set_page_config(page_title="GCO | 联赛", page_icon="🏆", layout="wide")
inject_theme(st)

hero(st, "🏆 个人联赛", "Individual League Standings", "GCO 2026")

df = load_scores()

# ── Overall Order-of-Merit (OOM) ──────────────────────────────────────────────
section(st, "📊", "积分榜 Order of Merit")

oom = (
    df.groupby("Player")
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
oom = oom.sort_values(["Total_Net", "Eagles", "Birdies"], ascending=[True, False, False])
oom.insert(0, "Rank", range(1, len(oom) + 1))
oom["Avg_Net"] = (oom["Total_Net"] / oom["Games"]).round(2)
oom["Avg_Stableford"] = oom["Avg_Stableford"].round(1)

# rank medals
def rank_icon(r):
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(r, str(r))

oom["Rank"] = oom["Rank"].apply(rank_icon)

display_cols = ["Rank", "Player", "Games", "Total_Net", "Avg_Net",
                "Eagles", "Birdies", "Pars", "Bogeys", "DBogeys"]

st.dataframe(
    oom[display_cols].rename(columns={
        "Total_Net": "总净杆", "Avg_Net": "均净杆",
        "Eagles": "老鹰", "Birdies": "小鸟", "Pars": "标准",
        "Bogeys": "柏忌", "DBogeys": "双柏忌", "Games": "轮次",
    }),
    use_container_width=True,
    hide_index=True,
)

# ── OOM bar chart ─────────────────────────────────────────────────────────────
fig_oom = px.bar(
    oom.head(12),
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
)
st.plotly_chart(fig_oom, use_container_width=True)

# ── Per-tournament tabs ───────────────────────────────────────────────────────
section(st, "🏌️", "分赛段排名 Per-Tournament Standings")

tabs = st.tabs(list(LEAGUE_TOURNAMENTS.keys()))

for tab, (t_name, t_info) in zip(tabs, LEAGUE_TOURNAMENTS.items()):
    with tab:
        t_df = df[df["Tournament"] == t_name]
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
        lb.insert(0, "Rank", [rank_icon(i) for i in range(1, len(lb) + 1)])
        lb["Period"] = t_info["period"]

        st.caption(f"📅 赛期：{t_info['period']}")
        st.dataframe(
            lb.rename(columns={"Games": "轮次", "Total_Net": "净杆合计",
                                "Birdies": "小鸟", "Eagles": "老鹰"}),
            use_container_width=True,
            hide_index=True,
        )

        # Game-by-game scores for this tournament
        games = sorted(t_df["Game"].unique())
        if games:
            pivot = t_df.pivot_table(index="Player", columns="Game", values="Net_Score", aggfunc="first")
            pivot = pivot.reindex(columns=games)
            pivot["合计"] = pivot.sum(axis=1)
            pivot = pivot.sort_values("合计")
            st.dataframe(pivot, use_container_width=True)

# ── Player deep-dive ──────────────────────────────────────────────────────────
section(st, "👤", "球员详情 Player Deep-Dive")

selected = st.selectbox("选择球员", PLAYERS)
p_df = df[df["Player"] == selected].copy().sort_values("Game_No")

if not p_df.empty:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("平均净杆", f"{p_df['Net_Score'].mean():.1f}")
    c2.metric("最佳净杆", int(p_df['Net_Score'].min()))
    c3.metric("总小鸟数", int(p_df['Birdies'].sum()))
    c4.metric("总老鹰数", int(p_df['Eagles'].sum()))

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
    st.plotly_chart(fig_trend, use_container_width=True)

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
    st.plotly_chart(fig_donut, use_container_width=True)
