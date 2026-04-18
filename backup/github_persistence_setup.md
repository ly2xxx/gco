# GitHub Persistence — Setup Guide

## How it works

Every `save_*` call (scores, cup, events, announcements, outing) now also pushes
the **complete** app state as a single JSON file (`gco_state.json`) to your GitHub
repo via the Contents API. On startup, before anything else, Streamlit fetches
that file and hydrates `data/` — so a fresh cloud instance picks up exactly where
you left off.

```
Admin saves cup result
  └─ save_cup()          writes cup.json locally
  └─ _schedule_github_push()  background thread →
        export_app_state()   reads all data/
        github_push_state()  PUT /repos/{owner}/gco/contents/gco_state.json
```

```
Streamlit Cloud restarts (disk wiped)
  └─ data.py module load
        github_load_state()  GET gco_state.json from GitHub
        _sync_github_to_local()  writes data/ files
        app renders with latest data ✅
```

Fallback priority: **GitHub → local backup/ → defaults**

---

## One-time setup (≈ 5 minutes)

### Step 1 — Create a GitHub Personal Access Token (PAT)

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens**
   (or Classic tokens with `repo` scope also works)
2. Click **Generate new token (fine-grained)**
3. Set:
   - **Repository access**: `Only selected repositories` → pick your `gco` repo
   - **Permissions → Contents**: `Read and Write`
4. Click **Generate** and **copy** the token (you only see it once)

### Step 2 — Add secrets locally

Edit `.streamlit/secrets.toml`:

```toml
ADMIN_TOKEN = "me"

GITHUB_TOKEN     = "github_pat_xxxxxxxxxxxx"   # ← paste your PAT here
GITHUB_REPO      = "your-username/gco"         # ← your repo slug
GITHUB_DATA_PATH = "gco_state.json"            # ← can leave as-is
```

> [!CAUTION]
> `secrets.toml` is already gitignored (`!.streamlit/secrets.toml`). Never commit your token.

### Step 3 — Add secrets to Streamlit Cloud

1. Open your app in **Streamlit Cloud**
2. Click **⋮ → Settings → Secrets**
3. Paste the same three keys:

```toml
GITHUB_TOKEN     = "github_pat_xxxxxxxxxxxx"
GITHUB_REPO      = "your-username/gco"
GITHUB_DATA_PATH = "gco_state.json"
```

4. Click **Save** — the app restarts automatically

### Step 4 — Do an initial push

1. Run the app locally (`streamlit run streamlit_app.py`)
2. Open **💾 Data API** page
3. In the **🐙 GitHub Persistence** section you should see:
   > ✅ GitHub sync is active — repo: `you/gco`, file: `gco_state.json`
4. Click **🚀 Push to GitHub Now** to seed the initial state
5. Verify `gco_state.json` appears in your GitHub repo

From that point on, every admin save automatically keeps it up to date.

---

## What gets stored

The file `gco_state.json` in your repo contains the full snapshot:

| Key | Source |
|---|---|
| `scores` | `data/scores.csv` |
| `events` | `data/events.json` |
| `announcements` | `data/announcements.json` |
| `cup` | `data/cup.json` |
| `outing` | `data/outing.json` |

> [!NOTE]
> The file is committed as a real Git commit by the PAT, so you get a full
> history of every save in your repo's commit log — useful for auditing or
> rolling back accidental changes via GitHub's UI.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| ⚠️ "GitHub sync is not configured" on Data API page | `GITHUB_TOKEN` or `GITHUB_REPO` not set in secrets |
| ❌ "Push failed" on manual push | Token scope missing `Contents: Write`, or wrong repo slug |
| Data still resets on restart | Token/secrets not saved in Streamlit Cloud (check App Settings → Secrets) |
| `gco_state.json` not found (404) | Normal on first run — click **Push to GitHub Now** once |
