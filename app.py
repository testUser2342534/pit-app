import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="PIT Football Schedule", layout="wide")

@st.cache_data
def load_data():
    path = 'data/compiled_schedule.csv'
    if os.path.exists(path):
        return pd.read_csv(path)
    return None

st.title("🏈 PIT Football Schedule")

df = load_data()

if df is not None:
    # --- Sidebar Filters ---
    st.sidebar.header("Filters")
    
    # 1. Season Filter
    seasons = sorted(df['Season'].unique().tolist(), reverse=True)
    selected_season = st.sidebar.selectbox("Season:", seasons)

    # 2. League Filter (Cascading)
    leagues_in_season = df[df['Season'] == selected_season]['League'].unique().tolist()
    leagues = ["All"] + sorted(leagues_in_season)
    selected_league = st.sidebar.selectbox("League:", leagues)

    # 3. Division Filter (Cascading)
    div_query = df[df['Season'] == selected_season]
    if selected_league != "All":
        div_query = div_query[div_query['League'] == selected_league]
    
    divisions = ["All"] + sorted(div_query['Division'].unique().tolist())
    selected_div = st.sidebar.selectbox("Division:", divisions)

    # 4. Game Type Filter
    game_types = ["All"] + sorted(df['Type'].unique().tolist())
    selected_type = st.sidebar.selectbox("Game Type:", game_types)

    # 5. Multi-Team Selection
    all_teams = sorted(list(set(df['Home_Team'].dropna()) | set(df['Away_Team'].dropna())))
    selected_teams = st.sidebar.multiselect("Select Team(s):", options=all_teams)

    # --- Apply Filtering Logic ---
    filtered_df = df[df['Season'] == selected_season].copy()

    if selected_league != "All":
        filtered_df = filtered_df[filtered_df['League'] == selected_league]

    if selected_div != "All":
        filtered_df = filtered_df[filtered_df['Division'] == selected_div]
        
    if selected_type != "All":
        filtered_df = filtered_df[filtered_df['Type'] == selected_type]

    if selected_teams:
        filtered_df = filtered_df[
            (filtered_df['Home_Team'].isin(selected_teams)) | 
            (filtered_df['Away_Team'].isin(selected_teams))
        ]

    # --- Clickable Link Trick ---
    # Streamlit's LinkColumn uses the cell value as the URL.
    # To show the Name but click the Link, we swap them and use display_text logic.
    display_df = filtered_df.copy()

    # --- Display Results ---
    st.write(f"Showing **{len(display_df)}** games for season **{selected_season}**")

    st.dataframe(
        display_df,
        column_config={
            "Away_Link": st.column_config.LinkColumn(
                "Away Team",
                display_text=None # This will show the URL unless we format data
            ),
            "Home_Link": st.column_config.LinkColumn(
                "Home Team",
                display_text=None
            ),
            # We use the actual Team Name columns as static text
            "Away_Team": "Away Team", 
            "Home_Team": "Home Team",
            "Summary": st.column_config.LinkColumn(
                "Boxscore", 
                display_text="View Summary"
            ),
            # Hide the redundant raw link columns and Season (since it's filtered)
            "Away_Link": None,
            "Home_Link": None,
            "Season": None,
            "League": None if selected_league != "All" else "League"
        },
        use_container_width=True, 
        hide_index=True
    )

else:
    st.error("The schedule data file was not found in 'data/compiled_schedule.csv'.")