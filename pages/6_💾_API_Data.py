"""
GCO 2026 – Data API & Management
Provides UI for exporting and importing complete app state as JSON.
"""
import streamlit as st
import json
import base64
from datetime import datetime
from theme import inject_theme, hero, section
from data import (
    load_scores, save_scores,
    load_events, save_events,
    load_announcements, save_announcements,
    load_cup, save_cup,
    load_outing, save_outing,
    save_to_backup
)

st.set_page_config(page_title="GCO | Data API", page_icon="💾", layout="wide")
inject_theme(st)

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
