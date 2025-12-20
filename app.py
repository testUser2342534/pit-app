import streamlit as st

@st.cache_data
def load_data():
    # Points to the new folder location
    return pd.read_csv('data/compiled_schedule.csv')