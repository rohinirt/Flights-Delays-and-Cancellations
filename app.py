import streamlit as st
import duckdb

# Global Page Config - Forces sidebar to stay visible
st.set_page_config(
    page_title="Chicago O'Hare (ORD) Intelligence",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Simplified CSS (Removes dark sidebar overrides that hid page navigation)
st.markdown("""
<style>
    .block-container { 
        padding-top: 1rem !important; 
        padding-bottom: 1rem !important; 
        max-width: 100% !important; 
    }
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

# Sidebar fallback navigation
with st.sidebar:
    st.title("✈️ Navigation")
    st.info("Select a page below if multi-page links are not appearing above:")
    
    st.page_link("app.py", label="Home Overview", icon="🏠")
    st.page_link("pages/1_🛬_Arrivals_Intelligence.py", label="Arrivals Intelligence", icon="🛬")
    st.page_link("pages/2_🛫_Departures_Intelligence.py", label="Departures Intelligence", icon="🛫")
    st.page_link("pages/3_🔮_Delay_Predictor.py", label="Delay Predictor", icon="🔮")
    st.page_link("pages/4_🔍_Flight_Deep_Dive.py", label="Flight Deep Dive", icon="🔍")

# Main Page Dashboard
st.title("✈️ Chicago O'Hare (ORD) Flight Intelligence")
st.markdown("""
Welcome to the Operational Dashboard & Predictive Modeling System for Chicago O'Hare International Airport.

### **Navigation Overview**
Use the sidebar on the left to navigate across modules:

* **🛬 Arrivals Intelligence:** Operational metrics, delay breakdowns, and inbound route maps.
* **🛫 Departures Intelligence:** Outbound throughput, destination hubs, and performance charts.
* **🔮 Delay Predictor:** Machine Learning classification for delay probability & severity tiers.
* **🔍 Flight Deep-Dive:** Head-to-head route analysis, carrier efficiency, and time-of-day dynamics.
""")
