"""
GCO 2026 – shared CSS & theme helpers injected into every page.
"""

THEME_CSS = """
<style>
/* ── Google Font ─────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Root tokens ─────────────────────────────── */
:root {
    --green-dark:  #1a3a2a;
    --green-mid:   #2d6a4f;
    --green-light: #52b788;
    --gold:        #d4af37;
    --gold-light:  #f0d060;
    --red-team:    #c0392b;
    --black-team:  #2c2c2c;
    --surface0:    #0f1f17;
    --surface1:    #162b1f;
    --surface2:    #1e3d2c;
    --surface3:    #26503a;
    --text-primary:   #e8f5ee;
    --text-secondary: #a8c5b0;
    --text-muted:     #6b9a7a;
    --radius:      12px;
    --shadow:      0 4px 24px rgba(0,0,0,.45);
}

/* ── Base overrides ───────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--surface0) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stSidebar"] {
    background: var(--surface1) !important;
    border-right: 1px solid var(--surface3) !important;
}
[data-testid="stSidebar"] * { color: var(--text-primary) !important; }

/* ── Metric cards ─────────────────────────────── */
[data-testid="metric-container"] {
    background: var(--surface2) !important;
    border: 1px solid var(--surface3) !important;
    border-radius: var(--radius) !important;
    padding: 1.1rem 1.4rem !important;
}
[data-testid="metric-container"] label {
    color: var(--text-secondary) !important;
    font-size: .78rem !important;
    text-transform: uppercase;
    letter-spacing: .07em;
}
[data-testid="stMetricValue"] {
    color: var(--gold) !important;
    font-size: 1.9rem !important;
    font-weight: 700 !important;
}

/* ── DataFrames ───────────────────────────────── */
[data-testid="stDataFrame"] { border-radius: var(--radius); overflow: hidden; }

/* ── Buttons ──────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, var(--green-mid), var(--green-light)) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: transform .15s, box-shadow .15s;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(82,183,136,.35) !important;
}

/* ── Select boxes / inputs ────────────────────── */
[data-testid="stSelectbox"] > div,
[data-testid="stTextInput"] > div > div {
    background: var(--surface2) !important;
    border-color: var(--surface3) !important;
    color: var(--text-primary) !important;
    border-radius: 8px !important;
}

/* ── Expanders ────────────────────────────────── */
[data-testid="stExpander"] {
    background: var(--surface2) !important;
    border: 1px solid var(--surface3) !important;
    border-radius: var(--radius) !important;
}

/* ── Custom card helper ───────────────────────── */
.gco-card {
    background: var(--surface2);
    border: 1px solid var(--surface3);
    border-radius: var(--radius);
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: var(--shadow);
    transition: transform .15s, box-shadow .15s;
}
.gco-card:hover { transform: translateY(-3px); box-shadow: 0 8px 30px rgba(0,0,0,.6); }

.gco-pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: .72rem;
    font-weight: 600;
    letter-spacing: .05em;
    margin-right: 4px;
}
.pill-league    { background: #1a4731; color: #52b788; border: 1px solid #2d6a4f; }
.pill-cup       { background: #3a2a10; color: #d4af37; border: 1px solid #8a6a1f; }
.pill-team      { background: #2a1a3a; color: #9b59b6; border: 1px solid #5a2d8a; }
.pill-final     { background: #3a1a1a; color: #e74c3c; border: 1px solid #8a2d2d; }
.pill-pinned    { background: var(--gold); color: #1a1a1a; }
.pill-important { background: #e74c3c; color: #fff; }

/* ── Red / Black team colours ─────────────────── */
.team-red   { color: #e74c3c; font-weight: 700; }
.team-black { color: #bdc3c7; font-weight: 700; }

/* ── Section header ───────────────────────────── */
.section-header {
    display: flex;
    align-items: center;
    gap: .6rem;
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--gold);
    border-bottom: 2px solid var(--surface3);
    padding-bottom: .5rem;
    margin: 1.8rem 0 1rem;
}

/* ── Hero banner ──────────────────────────────── */
.hero-banner {
    background: linear-gradient(135deg, var(--green-dark) 0%, var(--green-mid) 60%, var(--surface0) 100%);
    border: 1px solid var(--green-mid);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    text-align: center;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.hero-banner::before {
    content: "⛳";
    position: absolute;
    font-size: 8rem;
    opacity: .06;
    top: -1rem;
    right: 1rem;
}
.hero-title   { font-size: 2.2rem; font-weight: 800; color: #fff; margin: 0; }
.hero-sub     { font-size: 1rem;   color: var(--text-secondary); margin-top: .4rem; }
.hero-season  { font-size: 1rem;   color: var(--gold); font-weight: 600; }

/* ── Bracket box ──────────────────────────────── */
.bracket-match {
    background: var(--surface2);
    border: 1px solid var(--surface3);
    border-radius: 10px;
    padding: .75rem 1rem;
    margin: .4rem 0;
    font-size: .9rem;
}
.bracket-winner { border-left: 3px solid var(--gold); }
.bracket-bye    { border-left: 3px solid var(--green-light); opacity: .85; }

/* ── Announcement card ────────────────────────── */
.ann-card {
    background: var(--surface2);
    border: 1px solid var(--surface3);
    border-radius: var(--radius);
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}
.ann-card.pinned { border-left: 4px solid var(--gold); }
.ann-title { font-size: 1.1rem; font-weight: 700; color: var(--text-primary); }
.ann-meta  { font-size: .76rem; color: var(--text-muted); margin: .25rem 0 .6rem; }
.ann-body  { font-size: .9rem;  color: var(--text-secondary); white-space: pre-wrap; }

/* ── Progress bar (team score) ────────────────── */
.score-bar-wrap { background: var(--surface3); border-radius: 999px; height: 10px; margin: .4rem 0; overflow: hidden; }
.score-bar-red  { background: var(--red-team); height: 10px; transition: width .4s; }
</style>
"""


def inject_theme(st_module):
    """Call once per page: st_module is the imported streamlit."""
    st_module.markdown(THEME_CSS, unsafe_allow_html=True)


def hero(st_module, title: str, subtitle: str = "", season: str = "2026赛季"):
    html = f"""
    <div class="hero-banner">
        <div class="hero-season">⛳ {season}</div>
        <div class="hero-title">{title}</div>
        {"<div class='hero-sub'>" + subtitle + "</div>" if subtitle else ""}
    </div>
    """
    st_module.markdown(html, unsafe_allow_html=True)


def section(st_module, icon: str, title: str):
    st_module.markdown(
        f'<div class="section-header"><span>{icon}</span><span>{title}</span></div>',
        unsafe_allow_html=True,
    )


EVENT_COLORS = {
    "League":      ("pill-league", "联赛"),
    "Cup":         ("pill-cup",    "杯赛"),
    "Team":        ("pill-team",   "团队"),
    "Grand Final": ("pill-final",  "总决赛"),
}
