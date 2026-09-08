import streamlit as st
import duckdb

# Define Pages using st.Page
main_page = st.Page("app.py", title="Home Overview", icon="🏠", default=True)
arrivals_page = st.Page("pages/1_🛬_Arrivals_Intelligence.py", title="Arrivals Intelligence", icon="🛬")
departures_page = st.Page("pages/2_🛫_Departures_Intelligence.py", title="Departures Intelligence", icon="🛫")
predictor_page = st.Page("pages/3_🔮_Delay_Predictor.py", title="Delay Predictor", icon="🔮")
deep_dive_page = st.Page("pages/4_🔍_Flight_Deep_Dive.py", title="Flight Deep Dive", icon="🔍")

# Initialize Navigation Router
pg = st.navigation({
    "Overview": [main_page],
    "Analytics & ML": [arrivals_page, departures_page, predictor_page, deep_dive_page]
})

# Global Page Configuration
st.set_page_config(
    page_title="Chicago O'Hare (ORD) Intelligence",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Shared Database Connection & Caching
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

# Render Selected Page Content
if pg == main_page:
    st.title("✈️ Chicago O'Hare (ORD) Flight Intelligence")
    st.markdown("""
    Welcome to the Operational Dashboard & Predictive Modeling System for Chicago O'Hare International Airport.

    ### **Navigation Overview**
    Use the sidebar menu to navigate through operational analytics and predictive models:

    * **🛬 Arrivals Intelligence:** Operational metrics, delay breakdowns, and inbound route analytics.
    * **🛫 Departures Intelligence:** Outbound throughput, destination hubs, and performance metrics.
    * **🔮 Delay Predictor:** Machine Learning classification for delay probability & severity tiers.
    * **🔍 Flight Deep-Dive:** Head-to-head route analysis, carrier efficiency, and time-of-day dynamics.
    """)
else:
    pg.run()
