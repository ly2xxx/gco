"""
GCO 2026 – Data API & Management
Provides UI for exporting and importing complete app state as JSON.
"""
import streamlit as st
import json
import base64
from datetime import datetime
from theme import inject_theme, hero, section
from auth import is_admin_user
from data import (
    load_scores, save_scores,
    load_events, save_events,
    load_announcements, save_announcements,
    load_cup, save_cup,
    load_outing, save_outing,
    save_to_backup, list_backups, compute_diff,
    export_app_state, import_app_state,
    github_push_state, github_load_state,
    BACKUP_DIR,
)

st.set_page_config(page_title="GCO | Data API", page_icon="💾", layout="wide")
inject_theme(st)

if not is_admin_user():
    st.error("Unauthorized: You need admin privileges to access this page.")
    st.stop()

hero(st, "💾 Data API & Management", "Export and Import Application Data", "GCO 2026 Admin")

state_data = export_app_state()
json_string = json.dumps(state_data, ensure_ascii=False, indent=2)

c1, c2 = st.columns(2)

with c1:
    section(st, "📥", "Export Data (Download JSON)")
    st.info("Download the entire application state into a portable JSON file. **A local copy will also be saved to the `backup/` folder automatically when you download.**")
    st.download_button(
        label="Download GCO Data Backup (.json)",
        data=json_string,
        file_name=f"gco_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        on_click=lambda: save_to_backup(state_data)
    )

with c2:
    section(st, "📤", "Import Data (Upload JSON)")
    st.info("Upload a previously exported JSON backup. It will be saved to the `backup/` folder — you can then choose whether to restore it below.")
    uploaded_file = st.file_uploader("Upload GCO Data Backup", type=["json"])

    if uploaded_file is not None:
        try:
            uploaded_state = json.load(uploaded_file)
            if "export_date" not in uploaded_state:
                st.error("Invalid JSON format. Missing version/export_date metadata.")
            else:
                # Derive destination filename from the uploaded file's original name
                # (preserves timestamp if it was exported from this app), otherwise
                # fall back to the export_date embedded in the JSON.
                import re as _re
                orig_name = uploaded_file.name
                if _re.match(r"gco_backup_\d{8}_\d{6}\.json", orig_name):
                    dest_name = orig_name
                else:
                    # Build a name from export_date: "2026-04-03T21:41:42.123456" → "20260403_214142"
                    ts_str = uploaded_state["export_date"].replace("-", "").replace(":", "").replace("T", "_")[:15]
                    dest_name = f"gco_backup_{ts_str}.json"

                dest_path = BACKUP_DIR / dest_name

                # Only write once per uploaded file (session_state guard prevents
                # re-writing on every Streamlit re-run while the file is still
                # sitting in the uploader widget).
                already_saved = st.session_state.get("_last_uploaded_backup") == dest_name
                if not already_saved:
                    dest_path.write_text(
                        json.dumps(uploaded_state, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    st.session_state["_last_uploaded_backup"] = dest_name

                st.success(
                    f"✅ Saved as **{dest_name}** (from {uploaded_state['export_date']}). "
                    "Use **♻️ Restore from Backup** below to apply it."
                )
        except json.JSONDecodeError:
            st.error("Could not parse JSON file. Please ensure it is correctly formatted.")
        except Exception as e:
            st.error(f"Error importing state: {str(e)}")

st.markdown("---")
section(st, "🧑‍💻", "Raw JSON Developer Preview")
st.json(state_data, expanded=False)

# ── GitHub Sync Status ──────────────────────────────────────────────────────
st.markdown("---")
section(st, "🐙", "GitHub Persistence")

try:
    import streamlit as _st
    _token = _st.secrets.get("GITHUB_TOKEN", "")
    _repo  = _st.secrets.get("GITHUB_REPO", "")
    _path  = _st.secrets.get("GITHUB_DATA_PATH", "gco_state.json")
except Exception:
    _token, _repo, _path = "", "", "gco_state.json"

if not _token or not _repo:
    st.warning(
        "⚠️ **GitHub sync is not configured.** "
        "Add `GITHUB_TOKEN`, `GITHUB_REPO` (and optionally `GITHUB_DATA_PATH`) "
        "to `.streamlit/secrets.toml` locally and to **Streamlit Cloud → App settings → Secrets**."
    )
else:
    st.success(
        f"✅ GitHub sync is **active** — repo: `{_repo}`, file: `{_path}`"
    )
    # Show what’s currently saved in GitHub vs current state
    gh_col, push_col = st.columns([3, 1])
    with gh_col:
        with st.expander("🔍 View state currently saved in GitHub"):
            gh_state = github_load_state()
            if gh_state:
                st.caption(f"Last saved: {gh_state.get('export_date', 'unknown')}")
                st.json(gh_state, expanded=False)
            else:
                st.info("No state file found in GitHub yet — it will be created on the next save.")
    with push_col:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Push to GitHub Now", help="Immediately sync current app state to GitHub"):
            with st.spinner("Pushing to GitHub…"):
                ok = github_push_state(state_data)
            if ok:
                st.success("✅ Pushed successfully!")
            else:
                st.error("❌ Push failed — check token/repo in secrets.")

# ── Restore from Backup ───────────────────────────────────────────────────────
st.markdown("---")
section(st, "♻️", "Restore from Backup")

backups = list_backups()
if not backups:
    st.info("No backup files found in the backup/ folder.")
else:
    # Build dropdown options – keyed so Streamlit always re-renders on change
    backup_options = [f"{b['filename']} ({b['date']})" for b in backups]
    selected = st.selectbox(
        "Select a backup to restore:",
        backup_options,
        index=0,
        key="restore_backup_select",
    )

    idx = backup_options.index(selected)
    backup = backups[idx]

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("**📄 Backup Contents:**")
        with st.expander("View backup JSON"):
            st.json(backup["data"], expanded=False)

    with col2:
        st.markdown("**🔄 Diff with Current Data:**")
        diff = compute_diff(backup["data"], state_data)
        if not diff:
            st.success("✅ Backup is identical to current data")
        else:
            st.warning(f"⚠️ {len(diff)} section(s) differ")
            for section_name, section_diff in diff.items():
                summary = section_diff.get("summary", "")
                details = section_diff.get("details", [])
                with st.expander(f"**{section_name}** — {summary}"):
                    # Colour-coded change table
                    _COLOR = {
                        "removed": "#ffd7d7",   # red tint
                        "added":   "#d4edda",   # green tint
                        "changed": "#fff3cd",   # amber tint
                    }
                    _ICON = {"removed": "🗑️ Removed", "added": "✅ Added", "changed": "✏️ Changed"}

                    rows_html = ""
                    for d in details:
                        ct = d["change_type"]
                        bg = _COLOR.get(ct, "#fff")
                        icon = _ICON.get(ct, ct)
                        field_val = str(d["field"])

                        # Format backup/current compactly
                        def _fmt(v):
                            if v == "(removed)" or v == "(added)":
                                return f"<em style='color:#999'>{v}</em>"
                            if isinstance(v, dict):
                                # Show only scalar fields to keep it readable
                                pairs = ", ".join(
                                    f"<b>{k}</b>: {vv}"
                                    for k, vv in v.items()
                                    if not isinstance(vv, (dict, list))
                                )
                                return pairs or json.dumps(v, ensure_ascii=False)[:80]
                            return str(v)[:120]

                        rows_html += (
                            f"<tr style='background:{bg};color:#1a1a1a'>"
                            f"<td style='padding:4px 8px;white-space:nowrap;color:#1a1a1a'><b>{field_val}</b></td>"
                            f"<td style='padding:4px 8px;color:#444;font-size:0.8em'>{icon}</td>"
                            f"<td style='padding:4px 8px;font-size:0.82em;color:#1a1a1a'>{_fmt(d['backup'])}</td>"
                            f"<td style='padding:4px 8px;font-size:0.82em;color:#1a1a1a'>{_fmt(d['current'])}</td>"
                            f"</tr>"
                        )

                    table_html = f"""
<table style='width:100%;border-collapse:collapse;font-family:sans-serif;color:#1a1a1a'>
  <thead>
    <tr style='background:#d0d8d4;color:#1a1a1a'>
      <th style='padding:4px 8px;text-align:left;color:#1a1a1a'>Record / Field</th>
      <th style='padding:4px 8px;text-align:left;color:#1a1a1a'>Change</th>
      <th style='padding:4px 8px;text-align:left;color:#1a1a1a'>Backup value</th>
      <th style='padding:4px 8px;text-align:left;color:#1a1a1a'>Current value</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>"""
                    st.markdown(table_html, unsafe_allow_html=True)

    # Revert button
    st.markdown("---")
    st.error("⚠️ **Warning:** Restoring will OVERWRITE all current data with the backup version!")

    if st.button("🚨 CONFIRM RESTORE FROM BACKUP", type="primary"):
        import_app_state(backup["data"])
        st.success("✅ Data successfully restored from backup! Please refresh the application.")
        st.balloons()

