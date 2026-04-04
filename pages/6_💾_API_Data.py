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
    save_to_backup, list_backups, compute_diff
)

st.set_page_config(page_title="GCO | Data API", page_icon="💾", layout="wide")
inject_theme(st)

if not is_admin_user():
    st.error("Unauthorized: You need admin privileges to access this page.")
    st.stop()

hero(st, "💾 Data API & Management", "Export and Import Application Data", "GCO 2026 Admin")

# Aggregate all data into a single state payload
def export_app_state() -> dict:
    return {
        "version": "1.0",
        "export_date": datetime.now().isoformat(),
        "events": load_events(),
        "announcements": load_announcements(),
        "cup": load_cup(),
        "outing": load_outing(),
        "scores": load_scores().to_dict(orient="records"),
    }

def import_app_state(state: dict):
    if "events" in state: save_events(state["events"])
    if "announcements" in state: save_announcements(state["announcements"])
    if "cup" in state: save_cup(state["cup"])
    if "outing" in state: save_outing(state["outing"])
    if "scores" in state:
        import pandas as pd
        df = pd.DataFrame(state["scores"])
        save_scores(df)

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
    st.warning("Uploading a state JSON will OVERWRITE all existing local data files (Events, Cup, Scores, etc.).")
    uploaded_file = st.file_uploader("Upload GCO Data Backup", type=["json"])
    
    if uploaded_file is not None:
        try:
            uploaded_state = json.load(uploaded_file)
            if "export_date" in uploaded_state:
                st.success(f"Valid backup found from: {uploaded_state['export_date']}")
                
                if st.button("🚨 CONFIRM OVERWRITE STATE", type="primary"):
                    import_app_state(uploaded_state)
                    st.success("App state successfully overwritten! Please refresh the application.")
                    st.balloons()
            else:
                st.error("Invalid JSON format. Missing version/export_date metadata.")
        except json.JSONDecodeError:
            st.error("Could not parse JSON file. Please ensure it is correctly formatted.")
        except Exception as e:
            st.error(f"Error importing state: {str(e)}")

st.markdown("---")
section(st, "🧑‍💻", "Raw JSON Developer Preview")
st.json(state_data, expanded=False)

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
                            f"<tr style='background:{bg}'>"
                            f"<td style='padding:4px 8px;white-space:nowrap'><b>{field_val}</b></td>"
                            f"<td style='padding:4px 8px;color:#555;font-size:0.8em'>{icon}</td>"
                            f"<td style='padding:4px 8px;font-size:0.82em'>{_fmt(d['backup'])}</td>"
                            f"<td style='padding:4px 8px;font-size:0.82em'>{_fmt(d['current'])}</td>"
                            f"</tr>"
                        )

                    table_html = f"""
<table style='width:100%;border-collapse:collapse;font-family:sans-serif'>
  <thead>
    <tr style='background:#f0f0f0'>
      <th style='padding:4px 8px;text-align:left'>Record / Field</th>
      <th style='padding:4px 8px;text-align:left'>Change</th>
      <th style='padding:4px 8px;text-align:left'>Backup value</th>
      <th style='padding:4px 8px;text-align:left'>Current value</th>
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

