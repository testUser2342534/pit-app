import streamlit as st
import pandas as pd
import os

# Set page title
st.set_page_config(page_title="PIT Football Schedule", layout="wide")

@st.cache_data
def load_data():
    path = 'data/compiled_schedule.csv'
    # Check if the file exists before trying to read it
    if os.path.exists(path):
        df = pd.read_csv(path)
        return df
    else:
        return None

st.title("🏈 PIT Football Schedule")

# Load the data
df = load_data()

if df is not None:
    # Add a search bar
    search = st.text_input("Search for your team:")
    
    if search:
        # Filter the dataframe based on search
        df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
    
    # Show the table
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.error("The schedule data file was not found. Please run the scraper or check the 'data' folder.")