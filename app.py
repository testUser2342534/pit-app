import streamlit as st
import pandas as pd
import extra_streamlit_components as stx
import os
import glob
import datetime

st.set_page_config(page_title="PIT Football Schedule", layout="wide")

# --- 1. CSS FOR CLEAN BUTTONS ---
st.markdown("""
    <style>
    div.stButton > button[kind="primary"] {
        background-color: #2E7D32 !important;
        color: white !important;
        border: none;
    }
    div.stButton > button[kind="secondary"] {
        background-color: #E0E0E0 !important;
        color: #424242 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. INITIALIZE COOKIE MANAGER ---
# We give it a fixed key so it persists across script reruns
cookie_manager = stx.CookieManager(key="mngr")

# --- CONFIGURATION ---
SYNC_FILE = "Winter_2026.csv"

def get_season_mapping():
    files = glob.glob("data/*.csv")
    mapping = {}
    for f in files:
        fname = os.path.basename(f)
        display_name = fname.replace(".csv", "").replace("_", " ")
        mapping[display_name] = fname
    return mapping

@st.cache_data
def load_data(filename, last_modified):
    path = os.path.join('data', filename)
    if os.path.exists(path):
        df = pd.read_csv(path).copy()
        
        # Cleaning
        remove_locs = ["- U of M Complex", "- Garden City Complex"]
        for text in remove_locs:
            df['Location'] = df['Location'].str.replace(text, "", case=False, regex=False)
        df['Division'] = df['Division'].str.replace("_", " ", regex=False).str.replace("Division", "", case=False)
        
        if 'Type' in df.columns:
            df['Type'] = df['Type'].str.strip().str.upper().replace({"REGULAR": "REG", "PLAYOFFS": "PO"}, regex=True)

        def process_row(row):
            a_score, h_score = row.get('Away_Score'), row.get('Home_Score')
            score_display = f"{int(a_score)} - {int(h_score)}" if pd.notna(a_score) else None
            row['Away_Link_Display'] = f"{row['Away_Link']}#{row['Away_Team']}"
            row['Home_Link_Display'] = f"{row['Home_Link']}#{row['Home_Team']}"
            row['Final_Score'] = score_display
            return row

        return df.apply(process_row, axis=1)
    return None

st.title("🏈 PIT Football Schedule")
season_map = get_season_mapping()
sorted_seasons = sorted(list(season_map.keys()), reverse=True)
selected_display = st.sidebar.selectbox("Select Season:", sorted_seasons)

df = load_data(season_map[selected_display], 0)

if df is not None:
    # --- 3. FETCH SAVED DATA ---
    # Give the manager a second to load from the browser
    all_saved_data = cookie_manager.get(cookie="pit_prefs")
    
    if all_saved_data is None:
        all_saved_data = {}
    
    season_prefs = all_saved_data.get(selected_display, {})

    st.sidebar.header("Filters")
    
    leagues = ["All"] + sorted(df['League'].unique().tolist())
    saved_league = season_prefs.get("league", "All")
    l_idx = leagues.index(saved_league) if saved_league in leagues else 0
    selected_league = st.sidebar.selectbox("League:", leagues, index=l_idx)

    div_query = df[df['League'] == selected_league] if selected_league != "All" else df
    divisions = ["All"] + sorted(div_query['Division'].unique().tolist())
    saved_div = season_prefs.get("division", "All")
    d_idx = divisions.index(saved_div) if saved_div in divisions else 0
    selected_div = st.sidebar.selectbox("Division:", divisions, index=d_idx)

    all_teams = sorted(list(set(df['Away_Team'].dropna()) | set(df['Home_Team'].dropna())))
    saved_teams = season_prefs.get("teams", [])
    valid_saved_teams = [t for t in saved_teams if t in all_teams]
    selected_teams = st.sidebar.multiselect("Select Team(s):", options=all_teams, default=valid_saved_teams)

    st.sidebar.markdown("---")
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("Save Settings", type="primary", use_container_width=True):
            all_saved_data[selected_display] = {
                "league": selected_league,
                "division": selected_div,
                "teams": selected_teams
            }
            # Set expiry for 1 year so it doesn't vanish
            expiry = datetime.date.today() + datetime.timedelta(days=365)
            cookie_manager.set("pit_prefs", all_saved_data, expires_at=expiry)
            st.toast("Saved!")

    with col2:
        if st.button("Clear", type="secondary", use_container_width=True):
            if selected_display in all_saved_data:
                del all_saved_data[selected_display]
                cookie_manager.set("pit_prefs", all_saved_data)
                st.rerun()

    # Filtering & Display
    f_df = df.copy()
    if selected_league != "All": f_df = f_df[f_df['League'] == selected_league]
    if selected_div != "All": f_df = f_df[f_df['Division'] == selected_div]
    if selected_teams: f_df = f_df[(f_df['Away_Team'].isin(selected_teams)) | (f_df['Home_Team'].isin(selected_teams))]

    st.dataframe(f_df, hide_index=True)