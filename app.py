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
        # Convert 'schedule_Fall_2026.csv' -> 'Fall 2026'
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
        # Replace underscores with spaces
        df['Division'] = df['Division'].str.replace("_", " ", regex=False)
        # Remove the word "Division"
        df['Division'] = df['Division'].str.replace("Division", "", case=False, regex=False)
        # Remove parentheses and everything inside them e.g. (A)
        df['Division'] = df['Division'].str.replace(r'\(.*?\)', '', regex=True)
        
        # --- 3. Whitespace Cleanup ---
        for col in ['Location', 'Division']:
            df[col] = df[col].str.replace(r'\s+', ' ', regex=True).str.strip()

        # --- 4. Winner Indicator Logic ---
        def format_scores(row):
            if pd.isna(row['Away_Score']) or pd.isna(row['Home_Score']):
                return f"{row['Away_Score']} - {row['Home_Score']}"
            try:
                a_score = int(float(row['Away_Score']))
                h_score = int(float(row['Home_Score']))
                a_disp = f"🏆 {a_score}" if a_score > h_score else str(a_score)
                h_disp = f"{h_score} 🏆" if h_score > a_score else str(h_score)
                return f"{a_disp} - {h_disp}"
            except:
                return f"{row['Away_Score']} - {row['Home_Score']}"

        df['Score'] = df.apply(format_scores, axis=1)
        return df
    return None

st.title("🏈 PIT Football Schedule")

# --- Season Selection ---
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

    all_teams = sorted(list(set(df['Home_Team'].dropna()) | set(df['Away_Team'].dropna())))
    selected_teams = st.sidebar.multiselect("Select Team(s):", options=all_teams)

    # --- Filtering Logic ---
    filtered_df = df.copy()
    if selected_league != "All":
        filtered_df = filtered_df[filtered_df['League'] == selected_league]
    if selected_div != "All":
        filtered_df = filtered_df[filtered_df['Division'] == selected_div]
    if selected_teams:
        filtered_df = filtered_df[
            (filtered_df['Home_Team'].isin(selected_teams)) | 
            (filtered_df['Away_Team'].isin(selected_teams))
        ]

    # --- Data Grid Configuration ---
    # These are the only columns that will appear in the Export and the Visibility (eye) menu
    view_columns = ["Date", "Time", "Away_Team", "Score", "Home_Team", "Location", "League", "Division", "Summary"]

    st.dataframe(
        filtered_df,
        column_config={
            "Away_Team": st.column_config.LinkColumn(
                "Away Team", 
                url_template=filtered_df["Away_Link"]
            ),
            "Home_Team": st.column_config.LinkColumn(
                "Home Team", 
                url_template=filtered_df["Home_Link"]
            ),
            "Score": st.column_config.TextColumn(
                "Score", 
                help="🏆 indicates the winner"
            ),
            "Summary": st.column_config.LinkColumn(
                "Summary", 
                display_text="View Summary"
            ),
            # Hide raw utility columns from UI, Export, and Eye Icon
            "Away_Link": None,
            "Home_Link": None,
            "Away_Score": None,
            "Home_Score": None
        },
        column_order=view_columns,
        use_container_width=True, 
        hide_index=True
    )
    
    st.caption(f"Showing {len(filtered_df)} games for {selected_display}")

else:
    st.warning("Please ensure your CSV files are located in the 'data/' folder.")