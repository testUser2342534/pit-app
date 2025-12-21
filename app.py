import streamlit as st
import pandas as pd
import os
import glob
import re

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
def load_data(filename):
    path = os.path.join('data', filename)
    if os.path.exists(path):
        df = pd.read_csv(path)
        
        # --- 1. Clean Location ---
        remove_locs = ["- U of M Complex", "- Garden City Complex"]
        for text in remove_locs:
            df['Location'] = df['Location'].str.replace(text, "", case=False, regex=False)
        
        # --- 2. Clean Division ---
        df['Division'] = df['Division'].str.replace("_", " ", regex=False)
        df['Division'] = df['Division'].str.replace("Division", "", case=False, regex=False)
        df['Division'] = df['Division'].str.replace(r'\(.*?\)', '', regex=True)
        
        # --- 3. Whitespace Cleanup ---
        for col in ['Location', 'Division']:
            df[col] = df[col].str.replace(r'\s+', ' ', regex=True).str.strip()

        # --- 4. Winner & Link Logic ---
        def process_game_row(row):
            # Default display names
            away_display = str(row['Away_Team'])
            home_display = str(row['Home_Team'])
            score_display = f"{row['Away_Score']} - {row['Home_Score']}"
            
            try:
                if not pd.isna(row['Away_Score']) and not pd.isna(row['Home_Score']):
                    a_score = int(float(row['Away_Score']))
                    h_score = int(float(row['Home_Score']))
                    
                    # Update names with trophies
                    if a_score > h_score:
                        away_display = f"🏆 {away_display}"
                    elif h_score > a_score:
                        home_display = f"{home_display} 🏆"
                    
                    # Update score string to be clean integers
                    score_display = f"{a_score} - {h_score}"
            except:
                pass

            # Update the Link columns to include the display text after a #
            row['Away_Link_Display'] = f"{row['Away_Link']}#{away_display}"
            row['Home_Link_Display'] = f"{row['Home_Link']}#{home_display}"
            row['Final_Score'] = score_display
            return row

        df = df.apply(process_game_row, axis=1)
        return df
    return None

st.title("🏈 PIT Football Schedule")

season_map = get_season_mapping()
if not season_map:
    st.error("No schedule files found in the 'data/' directory.")
    st.stop()

selected_display = st.sidebar.selectbox("Select Season:", sorted(list(season_map.keys()), reverse=True))
df = load_data(season_map[selected_display])

if df is not None:
    # --- Sidebar Filters ---
    st.sidebar.header("Filters")
    leagues = ["All"] + sorted(df['League'].unique().tolist())
    selected_league = st.sidebar.selectbox("League:", leagues)

    div_query = df.copy()
    if selected_league != "All":
        div_query = div_query[div_query['League'] == selected_league]
    
    divisions = ["All"] + sorted(div_query['Division'].unique().tolist())
    selected_div = st.sidebar.selectbox("Division:", divisions)

    all_teams = sorted(list(set(df['Away_Team'].dropna()) | set(df['Home_Team'].dropna())))
    selected_teams = st.sidebar.multiselect("Select Team(s):", options=all_teams)

    # --- Filtering Logic ---
    filtered_df = df.copy()
    if selected_league != "All":
        filtered_df = filtered_df[filtered_df['League'] == selected_league]
    if selected_div != "All":
        filtered_df = filtered_df[filtered_df['Division'] == selected_div]
    if selected_teams:
        filtered_df = filtered_df[
            (filtered_df['Away_Team'].isin(selected_teams)) | 
            (filtered_df['Home_Team'].isin(selected_teams))
        ]

    # --- Data Grid ---
    # We display 'Away_Link_Display' but it will show as 'Away Team'
    view_columns = ["Date", "Time", "Away_Link_Display", "Final_Score", "Home_Link_Display", "Location", "League", "Division", "Summary"]

    st.dataframe(
        filtered_df,
        column_config={
            "Away_Link_Display": st.column_config.LinkColumn(
                "Away Team",
                display_text=r"#(.+)$" 
            ),
            "Home_Link_Display": st.column_config.LinkColumn(
                "Home Team",
                display_text=r"#(.+)$"
            ),
            "Final_Score": st.column_config.TextColumn(
                "Score", 
                help="Winning teams are marked with a 🏆"
            ),
            "Summary": st.column_config.LinkColumn(
                "Boxscore", 
                display_text="View Summary"
            ),
            # Hide all original data columns to keep the UI and Export clean
            "Away_Team": None, "Home_Team": None, "Away_Score": None, "Home_Score": None,
            "Away_Link": None, "Home_Link": None, "Final_Score": "Score"
        },
        column_order=view_columns,
        use_container_width=True, 
        hide_index=True
    )
    
    st.caption(f"Showing {len(filtered_df)} games for {selected_display}")
else:
    st.warning("Please ensure your CSV files are located in the 'data/' folder.")