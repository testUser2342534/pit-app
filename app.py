import streamlit as st
import pandas as pd
import extra_streamlit_components as stx
import os
import glob
import re
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
# Using a key ensures the component stays active during script reruns
cookie_manager = stx.CookieManager(key="mngr")

# --- CONFIGURATION ---
SYNC_FILE = "Winter_2026.csv"

def get_season_mapping():
    """Maps clean season names to their actual CSV filenames."""
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
        
        # --- Cleaning Logic ---
        remove_locs = ["- U of M Complex", "- Garden City Complex"]
        for text in remove_locs:
            df['Location'] = df['Location'].str.replace(text, "", case=False, regex=False)
        
        df['Division'] = df['Division'].str.replace("_", " ", regex=False)
        df['Division'] = df['Division'].str.replace("Division", "", case=False, regex=False)
        df['Division'] = df['Division'].str.replace(r'\(.*?\)', '', regex=True)

        if 'Type' in df.columns:
            df['Type'] = df['Type'].str.strip().str.upper()
            df['Type'] = df['Type'].replace({"REGULAR": "REG", "PLAYOFFS": "PO", "PLAYOFF": "PO"}, regex=True)
        
        for col in ['Location', 'Division']:
            df[col] = df[col].str.replace(r'\s+', ' ', regex=True).str.strip()

        def process_game_row(row):
            away_display = str(row['Away_Team'])
            home_display = str(row['Home_Team'])
            if pd.isna(row['Away_Score']) or pd.isna(row['Home_Score']):
                score_display = None
            else:
                try:
                    a_score, h_score = int(float(row['Away_Score'])), int(float(row['Home_Score']))
                    if a_score > h_score: away_display += " 🏆"
                    elif h_score > a_score: home_display += " 🏆"
                    score_display = f"{a_score} - {h_score}"
                except: score_display = None

            row['Away_Link_Display'] = f"{row['Away_Link']}#{away_display}"
            row['Home_Link_Display'] = f"{row['Home_Link']}#{home_display}"
            row['Final_Score'] = score_display
            return row

        return df.apply(process_game_row, axis=1)
    return None

# --- MAIN AREA ---
st.title("🏈 PIT Football Schedule")

season_map = get_season_mapping()
if not season_map:
    st.error("No schedule files found in the 'data/' directory.")
    st.stop()

# --- TIMESTAMP LOGIC ---
sync_path = os.path.join('data', SYNC_FILE)
if os.path.exists(sync_path):
    sync_df = pd.read_csv(sync_path, nrows=1)
    if 'Scraped_At' in sync_df.columns:
        raw_time = sync_df['Scraped_At'].iloc[0]
        dt_obj = datetime.datetime.strptime(raw_time, '%Y-%m-%d %H:%M:%S')
        st.markdown(f"**Last synced:** {dt_obj.strftime('%b %d, %I:%M %p')} CST")

st.divider()

# --- SIDEBAR ---
season_order = {"Winter": 1, "Spring": 2, "Summer": 3, "Fall": 4}
def sort_key(name):
    p = name.split()
    return (int(p[1]), season_order.get(p[0], 0)) if len(p) >= 2 else (0,0)

sorted_seasons = sorted(list(season_map.keys()), key=sort_key, reverse=True)
selected_display = st.sidebar.selectbox("Select Season to View:", sorted_seasons)

# --- LOAD SELECTED DATA ---
file_name = season_map[selected_display]
file_path = os.path.join('data', file_name)
mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0

df = load_data(file_name, mtime)

if df is not None:
    # Give the manager a moment to load from the browser
    if not cookie_manager:
        st.stop()

    # --- 3. FETCH SAVED DATA ---
    all_saved_data = cookie_manager.get(cookie="pit_prefs")
    if not isinstance(all_saved_data, dict):
        all_saved_data = {}
    
    season_prefs = all_saved_data.get(selected_display, {})

    st.sidebar.header("Filters")
    
    # --- LEAGUE FILTER ---
    leagues = ["All"] + sorted(df['League'].unique().tolist())
    saved_league = season_prefs.get("league", "All")
    l_idx = leagues.index(saved_league) if saved_league in leagues else 0
    selected_league = st.sidebar.selectbox("League:", leagues, index=l_idx)

    # --- DIVISION FILTER ---
    div_query = df[df['League'] == selected_league] if selected_league != "All" else df
    divisions = ["All"] + sorted(div_query['Division'].unique().tolist())
    saved_div = season_prefs.get("division", "All")
    d_idx = divisions.index(saved_div) if saved_div in divisions else 0
    selected_div = st.sidebar.selectbox("Division:", divisions, index=d_idx)

    # --- GAME TYPE FILTER ---
    type_map = {"All": "All", "Regular": "REG", "Playoffs": "PO"}
    type_options = list(type_map.keys())
    saved_type_label = season_prefs.get("type_label", "All")
    t_idx = type_options.index(saved_type_label) if saved_type_label in type_options else 0
    selected_type_label = st.sidebar.selectbox("Game Type:", type_options, index=t_idx)
    selected_type_val = type_map[selected_type_label]

    # --- TEAMS FILTER ---
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
                "type_label": selected_type_label,
                "teams": selected_teams
            }
            # Expires in 1 year
            expiry = datetime.date.today() + datetime.timedelta(days=365)
            cookie_manager.set("pit_prefs", all_saved_data, expires_at=expiry)
            st.toast(f"Filters saved for {selected_display}!", icon="✅")
            st.rerun()

    with col2:
        if st.button("Clear", type="secondary", use_container_width=True):
            if selected_display in all_saved_data:
                del all_saved_data[selected_display]
                cookie_manager.set("pit_prefs", all_saved_data)
                st.toast("Filters reset!", icon="🧹")
                st.rerun()

    # --- 7. FILTERING LOGIC ---
    f_df = df.copy()
    if selected_league != "All": 
        f_df = f_df[f_df['League'] == selected_league]
    if selected_div != "All": 
        f_df = f_df[f_df['Division'] == selected_div]
    if selected_type_val != "All": 
        f_df = f_df[f_df['Type'] == selected_type_val]
    if selected_teams:
        f_df = f_df[(f_df['Away_Team'].isin(selected_teams)) | (f_df['Home_Team'].isin(selected_teams))]

    # --- 8. RESTORED DISPLAY GRID ---
    st.dataframe(
        f_df,
        column_config={
            "Away_Link_Display": st.column_config.LinkColumn("Away Team", display_text=r"#(.+)$"),
            "Home_Link_Display": st.column_config.LinkColumn("Home Team", display_text=r"#(.+)$"),
            "Final_Score": st.column_config.TextColumn("Score", help="Winners have a 🏆"),
            "Summary": st.column_config.LinkColumn("Boxscore", display_text="View Summary"),
            "Type": st.column_config.TextColumn("Type"),
            "Away_Team": None, "Home_Team": None, "Away_Score": None, "Home_Score": None,
            "Away_Link": None, "Home_Link": None, "Scraped_At": None
        },
        column_order=["Date", "Time", "Away_Link_Display", "Final_Score", "Home_Link_Display", "Location", "League", "Division", "Type", "Summary"],
        width="stretch", hide_index=True
    )
    st.caption(f"Showing {len(f_df)} games for {selected_display}")
else:
    st.warning("Data file not found.")