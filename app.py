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
            
            # Using actual None for the grayed-out "None" look
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

st.title("🏈 PIT Football Schedule")

season_map = get_season_mapping()
if not season_map:
    st.error("No schedule files found in the 'data/' directory.")
    st.stop()

# Sorting R