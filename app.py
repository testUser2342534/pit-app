import streamlit as st
import pandas as pd
import os
import glob
import re
import datetime

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
    """
    Loads and cleans data. The 'last_modified' argument ensures the 
    cache refreshes automatically if the physical file changes.
    """
    path = os.path.join('data', filename)
    if os.path.exists(path):
        df = pd.read_csv(path).copy()
        
        # --- 1. Clean Location ---
        remove_locs = ["- U of M Complex", "- Garden City Complex"]
        for text in remove_locs:
            df['Location'] = df['Location'].str.replace(text, "", case=False, regex=False)
        
        # --- 2. Clean Division ---
        df['Division'] = df['Division'].str.replace("_", " ", regex=False)
        df['Division'] = df['Division'].str.replace("Division", "", case=False, regex=False)
        df['Division'] = df['Division'].str.replace(r'\(.*?\)', '', regex=True)

        # --- 3. Shorten Type for Table Display ---
        if 'Type' in df.columns:
            df['Type'] = df['Type'].str.strip().str.upper()
            df['Type'] = df['Type'].replace({
                "REGULAR": "REG", 
                "PLAYOFFS": "PO", 
                "PLAYOFF": "PO"
            }, regex=True)
        
        # --- 4. Whitespace Cleanup ---
        for col in ['Location', 'Division']:
            df[col] = df[col].str.replace(r'\s+', ' ', regex=True).str.strip()

        # --- 5. Winner & Link Logic ---
        def process_game_row(row):
            away_display = str(row['Away_Team'])
            home_display = str(row['Home_Team'])
            
            if pd.isna(row['Away_Score']) or pd.isna(row['Home_Score']):
                score_display = None
            else:
                try:
                    a_score = int(float(row['Away_Score']))
                    h_score = int(float(row['Home_Score']))
                    if a_score > h_score:
                        away_display = f"{away_display} 🏆"
                    elif h_score > a_score:
                        home_display = f"{home_display} 🏆"
                    score_display = f"{a_score} - {h_score}"
                except:
                    score_display = None

            row['Away_Link_Display'] = f"{row['Away_Link']}#{away_display}"
            row['Home_Link_Display'] = f"{row['Home_Link']}#{home_display}"
            row['Final_Score'] = score_display
            return row

        df = df.apply(process_game_row, axis=1)
        return df
    return None

# --- Main UI Start ---
st.title("🏈 PIT Football Schedule")

season_map = get_season_mapping()
if not season_map:
    st.error("No schedule files found in the 'data/' directory.")
    st.stop()

# Sorting Ranks: Winter -> Spring -> Summer -> Fall
season_order = {"Winter": 1, "Spring": 2, "Summer": 3, "Fall": 4}

def sort_key(display_name):
    parts = display_name.split()
    if len(parts) >= 2:
        season = parts[0]
        try:
            year = int(parts[1])
        except ValueError:
            year = 0
        return (year, season_order.get(season, 0))
    return (0, 0)

sorted_seasons = sorted(list(season_map.keys()), key=sort_key, reverse=True)
selected_display = st.sidebar.selectbox("Select Season:", sorted_seasons)

# --- Automatic Refresh & Timestamp Logic ---
file_name = season_map[selected_display]
file_path = os.path.join('data', file_name)
mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0

# Format and display the Last Updated note directly under the Title
last_updated_dt = datetime.datetime.fromtimestamp(mtime)
st.markdown(f"**Last synced:** {last_updated_dt.strftime('%b %d, %I:%M %p')}")
st.divider() # Adds a clean line between the header and the data

df = load_data(file_name, mtime)

if df is not None:
    st.sidebar.header("Filters")
    
    # League Filter
    leagues = ["All"] + sorted(df['League'].unique().tolist())
    selected_league = st.sidebar.selectbox("League:", leagues)

    # Division Filter
    div_query = df.copy()
    if selected_league != "All":
        div_query = div_query[div_query['League'] == selected_league]
    divisions = ["All"] + sorted(div_query['Division'].unique().tolist())
    selected_div = st.sidebar.selectbox("Division:", divisions)

    # Game Type Filter
    type_options = {"All": "All", "Regular": "REG", "Playoffs": "PO"}
    selected_type_label = st.sidebar.selectbox("Game Type:", list(type_options.keys()))
    selected_type_val = type_options[selected_type_label]

    # Team Filter
    all_teams = sorted(list(set(df['Away_Team'].dropna()) | set(df['Home_Team'].dropna())))
    selected_teams = st.sidebar.multiselect("Select Team(s):", options=all_teams)

    # --- Filtering Logic ---
    filtered_df = df.copy()
    if selected_league != "All":
        filtered_df = filtered_df[filtered_df['League'] == selected_league]
    if selected_div != "All":
        filtered_df = filtered_df[filtered_df['Division'] == selected_div]
    if selected_type_val != "All":
        filtered_df = filtered_df[filtered_df['Type'] == selected_type_val]
    if selected_teams:
        filtered_df = filtered_df[
            (filtered_df['Away_Team'].isin(selected_teams)) | 
            (filtered_df['Home_Team'].isin(selected_teams))
        ]

    # --- Data Grid ---
    view_columns = ["Date", "Time", "Away_Link_Display", "Final_Score", "Home_Link_Display", "Location", "League", "Division", "Type", "Summary"]

    st.dataframe(
        filtered_df,
        column_config={
            "Away_Link_Display": st.column_config.LinkColumn("Away Team", display_text=r"#(.+)$"),
            "Home_Link_Display": st.column_config.LinkColumn("Home Team", display_text=r"#(.+)$"),
            "Final_Score": st.column_config.TextColumn("Score", help="Winning teams are marked with a 🏆"),
            "Summary": st.column_config.LinkColumn("Boxscore", display_text="View Summary"),
            "Type": st.column_config.TextColumn("Type"),
            "Away_Team": None, "Home_Team": None, "Away_Score": None, "Home_Score": None,
            "Away_Link": None, "Home_Link": None, "Final_Score": "Score"
        },
        column_order=view_columns,
        width="stretch",
        hide_index=True
    )
    
    st.caption(f"Showing {len(filtered_df)} games for {selected_display}")
else:
    st.warning("Please ensure your CSV files are located in the 'data/' folder.")