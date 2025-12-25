import streamlit as st
import pandas as pd
import os
import glob
import re
import datetime
import pytz # Standard library for timezone conversions

st.set_page_config(page_title="PIT Football Schedule", layout="wide")

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

# --- SIDEBAR (Selection Only) ---
season_order = {"Winter": 1, "Spring": 2, "Summer": 3, "Fall": 4}
def sort_key(name):
    p = name.split()
    return (int(p[1]), season_order.get(p[0], 0)) if len(p) >= 2 else (0,0)

sorted_seasons = sorted(list(season_map.keys()), key=sort_key, reverse=True)
selected_display = st.sidebar.selectbox("Select Season:", sorted_seasons)

# --- CALCULATE TIME (US/Central) & SHOW IN MAIN AREA ---
file_name = season_map[selected_display]
file_path = os.path.join('data', file_name)
mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0

# 1. Create a UTC datetime from the file timestamp
utc_dt = datetime.datetime.fromtimestamp(mtime, tz=pytz.utc)
# 2. Convert that UTC time to US/Central
central_tz = pytz.timezone('US/Central')
last_updated_dt = utc_dt.astimezone(central_tz)



st.markdown(f"**Last synced:** {last_updated_dt.strftime('%b %d, %I:%M %p')} CST")
st.divider()

# --- LOAD DATA ---
df = load_data(file_name, mtime)

if df is not None:
    # Sidebar Filters
    st.sidebar.header("Filters")
    leagues = ["All"] + sorted(df['League'].unique().tolist())
    selected_league = st.sidebar.selectbox("League:", leagues)

    div_query = df[df['League'] == selected_league] if selected_league != "All" else df
    divisions = ["All"] + sorted(div_query['Division'].unique().tolist())
    selected_div = st.sidebar.selectbox("Division:", divisions)

    type_map = {"All": "All", "Regular": "REG", "Playoffs": "PO"}
    selected_type_val = type_map[st.sidebar.selectbox("Game Type:", list(type_map.keys()))]

    all_teams = sorted(list(set(df['Away_Team'].dropna()) | set(df['Home_Team'].dropna())))
    selected_teams = st.sidebar.multiselect("Select Team(s):", options=all_teams)

    # Filter Logic
    f_df = df.copy()
    if selected_league != "All": f_df = f_df[f_df['League'] == selected_league]
    if selected_div != "All": f_df = f_df[f_df['Division'] == selected_div]
    if selected_type_val != "All": f_df = f_df[f_df['Type'] == selected_type_val]
    if selected_teams:
        f_df = f_df[(f_df['Away_Team'].isin(selected_teams)) | (f_df['Home_Team'].isin(selected_teams))]

    # Display Grid
    st.dataframe(
        f_df,
        column_config={
            "Away_Link_Display": st.column_config.LinkColumn("Away Team", display_text=r"#(.+)$"),
            "Home_Link_Display": st.column_config.LinkColumn("Home Team", display_text=r"#(.+)$"),
            "Final_Score": st.column_config.TextColumn("Score", help="Winners have a 🏆"),
            "Summary": st.column_config.LinkColumn("Boxscore", display_text="View Summary"),
            "Type": st.column_config.TextColumn("Type"),
            "Away_Team": None, "Home_Team": None, "Away_Score": None, "Home_Score": None,
            "Away_Link": None, "Home_Link": None
        },
        column_order=["Date", "Time", "Away_Link_Display", "Final_Score", "Home_Link_Display", "Location", "League", "Division", "Type", "Summary"],
        width="stretch", hide_index=True
    )
    st.caption(f"Showing {len(f_df)} games for {selected_display}")
else:
    st.warning("Data file not found.")