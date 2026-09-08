import streamlit as st
import duckdb
import pandas as pd

# Global Page Config
st.set_page_config(
    page_title="Chicago O'Hare (ORD) Intelligence",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; max-width: 100% !important; }
    .stApp { background-color: #F8FAFC !important; }
    section[data-testid="stSidebar"] { background-color: #0A192F !important; }
    section[data-testid="stSidebar"] * { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_db_connection():
    return duckdb.connect(database=':memory:')

@st.cache_data
def load_data():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flights AS 
        SELECT * FROM read_csv_auto('flights_2022.csv')
    """)
    return True

try:
    load_data()
except Exception as e:
    st.error(f"Error loading dataset: {e}. Ensure 'flights_2022.csv' is in the root directory.")
    st.stop()

st.title("✈️ Chicago O'Hare (ORD) Flight Intelligence")
st.markdown("""
Welcome to the Operational Dashboard & Predictive Modeling System for Chicago O'Hare International Airport.

### **Navigation Overview**
* **🛬 Arrivals Intelligence:** Operational metrics, delay breakdowns, and inbound route maps.
* **🛫 Departures Intelligence:** Outbound throughput, destination hubs, and performance charts.
* **🔮 Delay Predictor:** Machine Learning classification for delay probability & severity tiers.
* **🔍 Flight Deep-Dive:** Head-to-head route analysis, carrier efficiency, and time-of-day dynamics.
""")
