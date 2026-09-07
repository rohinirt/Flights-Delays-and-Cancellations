import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="Chicago ORD Flight Intelligence 2022",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling Injection
st.markdown("""
<style>
    .stApp { background-color: #0b0f19; }
    div[data-testid="metric-container"] {
        background-color: #151c2e;
        border: 1px solid #232d42;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    div[data-testid="metric-container"]:hover {
        border-color: #00f2fe;
        transition: border-color 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)

# ORD Coordinates
ORD_LAT, ORD_LON = 41.9742, -87.9073

# Airport Coordinates Mapping for PyDeck Arcs
AIRPORT_COORDS = {
    'LAX': (-118.4081, 33.9416), 'JFK': (-73.7781, 40.6413), 'LGA': (-73.8740, 40.7769),
    'SFO': (-122.3790, 37.6213), 'DFW': (-97.0403, 32.8998), 'DEN': (-104.6737, 39.8561),
    'ATL': (-84.4277, 33.6407), 'MIA': (-80.2870, 25.7959), 'SEA': (-122.3088, 47.4502),
    'BOS': (-71.0052, 42.3656), 'PHX': (-112.0078, 33.4352), 'LAS': (-115.1523, 36.0840),
    'MSP': (-93.2223, 44.8848), 'DTW': (-83.3534, 42.2162), 'MCO': (-81.3081, 28.4288)
}

@st.cache_resource
def get_db_connection():
    # Persistent in-memory DuckDB connection
    conn = duckdb.connect(database=':memory:')
    return conn

@st.cache_data
def load_data():
    conn = get_db_connection()
    # Read local CSV directly into DuckDB table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flights AS 
        SELECT * FROM read_csv_auto('flights_2022.csv')
    """)
    return True

# Initialize Data
try:
    load_data()
    conn = get_db_connection()
except Exception as e:
    st.error(f"Error loading CSV file: {e}. Please ensure 'flights_2022.csv' is present in the root folder.")
    st.stop()

# Sidebar Navigation
st.sidebar.title("✈️ ORD Analytics")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigation", ["Arrivals Intelligence", "Departures Intelligence", "Flight Deep-Dive"])

# Sidebar Global Filters
st.sidebar.markdown("---")
st.sidebar.subheader("Filter Data")
airlines = conn.execute("SELECT DISTINCT AIRLINE_CODE FROM flights WHERE AIRLINE_CODE IS NOT NULL").df()['AIRLINE_CODE'].tolist()[cite: 1]
selected_airline = st.sidebar.multiselect("Select Airline", options=airlines, default=[])

airline_filter = ""
if selected_airline:
    formatted_airlines = "', '".join(selected_airline)
    airline_filter = f"AND AIRLINE_CODE IN ('{formatted_airlines}')"

# ==================== PAGE 1: ARRIVALS ====================
if page == "Arrivals Intelligence":
    st.title("🛬 ORD Arrivals Intelligence (2022)")
    
    # KPI Query
    kpi_query = f"""
        SELECT 
            COUNT(*) as total_flights,
            AVG(CASE WHEN ARR_DELAY <= 0 THEN 1 ELSE 0 END) * 100 as on_time_pct,
            AVG(ARR_DELAY) as avg_delay,
            SUM(CANCELLED) as total_cancelled,
            SUM(DIVERTED) as total_diverted
        FROM flights 
        WHERE DEST = 'ORD' {airline_filter}
    """[cite: 1]
    kpis = conn.execute(kpi_query).df().iloc[0]
    
    # KPI Layout
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Arrivals", f"{int(kpis['total_flights']):,}")
    c2.metric("On-Time Arrival Rate", f"{kpis['on_time_pct']:.1f}%")
    c3.metric("Avg Arrival Delay", f"{kpis['avg_delay']:.1f} min")
    c4.metric("Cancellations / Diversions", f"{int(kpis['total_cancelled']):,} / {int(kpis['total_diverted']):,}")
    
    st.markdown("---")
    
    col_left, col_right = st.columns([1.2, 1])
    
    with col_left:
        st.subheader("3D Inbound Route Map")
        map_query = f"""
            SELECT ORIGIN, COUNT(*) as flight_count, AVG(ARR_DELAY) as avg_delay
            FROM flights
            WHERE DEST = 'ORD' {airline_filter}
            GROUP BY ORIGIN
            ORDER BY flight_count DESC
            LIMIT 15
        """[cite: 1]
        map_df = conn.execute(map_query).df()
        
        map_data = []
        for idx, row in map_df.iterrows():
            if row['ORIGIN'] in AIRPORT_COORDS:
                orig_lon, orig_lat = AIRPORT_COORDS[row['ORIGIN']]
                map_data.append({
                    'origin': row['ORIGIN'],
                    'from_lon': orig_lon,
                    'from_lat': orig_lat,
                    'to_lon': ORD_LON,
                    'to_lat': ORD_LAT,
                    'count': row['flight_count'],
                    'delay': max(0, row['avg_delay'])
                })
        
        if map_data:
            arc_df = pd.DataFrame(map_data)
            layer = pdk.Layer(
                "ArcLayer",
                data=arc_df,
                get_source_position=["from_lon", "from_lat"],
                get_target_position=["to_lon", "to_lat"],
                get_source_color="[255, 255 - delay * 3, 100]",
                get_target_color="[0, 242, 254]",
                get_width="count / 500",
                pickable=True
            )
            view_state = pdk.ViewState(latitude=39.8283, longitude=-98.5795, zoom=3.5, pitch=45)
            st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "Origin: {origin}\nFlights: {count}"}))
        else:
            st.info("Route mapping requires standard origin airports matching coordinate registry.")

    with col_right:
        st.subheader("Primary Delay Drivers")
        delay_query = f"""
            SELECT 
                AVG(DELAY_DUE_CARRIER) as Carrier,
                AVG(DELAY_DUE_WEATHER) as Weather,
                AVG(DELAY_DUE_NAS) as NAS,
                AVG(DELAY_DUE_SECURITY) as Security,
                AVG(DELAY_DUE_LATE_AIRCRAFT) as Late_Aircraft
            FROM flights
            WHERE DEST = 'ORD' {airline_filter}
        """[cite: 1]
        delays = conn.execute(delay_query).df().iloc[0].fillna(0)
        
        fig_delays = px.pie(
            values=delays.values, 
            names=delays.index,
            hole=0.5,
            color_discrete_sequence=px.colors.sequential.Cyan
        )
        fig_delays.update_layout(margin=dict(t=20, b=20, l=20, r=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_delays, use_container_width=True)

# ==================== PAGE 2: DEPARTURES ====================
elif page == "Departures Intelligence":
    st.title("🛫 ORD Departures Intelligence (2022)")
    
    # KPI Query
    kpi_query = f"""
        SELECT 
            COUNT(*) as total_flights,
            AVG(CASE WHEN DEP_DELAY <= 0 THEN 1 ELSE 0 END) * 100 as on_time_pct,
            AVG(DEP_DELAY) as avg_delay,
            AVG(TAXI_OUT) as avg_taxi_out
        FROM flights 
        WHERE ORIGIN = 'ORD' {airline_filter}
    """[cite: 1]
    kpis = conn.execute(kpi_query).df().iloc[0]
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Departures", f"{int(kpis['total_flights']):,}")
    c2.metric("On-Time Departure Rate", f"{kpis['on_time_pct']:.1f}%")
    c3.metric("Avg Departure Delay", f"{kpis['avg_delay']:.1f} min")
    c4.metric("Avg Taxi-Out Duration", f"{kpis['avg_taxi_out']:.1f} min")
    
    st.markdown("---")
    
    st.subheader("Hourly Tarmac Taxi-Out Bottlenecks")
    taxi_query = f"""
        SELECT 
            CAST(CRS_DEP_TIME / 100 AS INT) as hour_of_day,
            AVG(TAXI_OUT) as avg_taxi
        FROM flights
        WHERE ORIGIN = 'ORD' {airline_filter}
        GROUP BY hour_of_day
        ORDER BY hour_of_day
    """[cite: 1]
    taxi_df = conn.execute(taxi_query).df()
    
    fig_taxi = px.bar(
        taxi_df, x='hour_of_day', y='avg_taxi',
        labels={'hour_of_day': 'Hour of Day (24h)', 'avg_taxi': 'Avg Taxi Out (min)'},
        color='avg_taxi', color_continuous_scale='Blugrn'
    )
    fig_taxi.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_taxi, use_container_width=True)

# ==================== PAGE 3: FLIGHT DEEP-DIVE ====================
elif page == "Flight Deep-Dive":
    st.title("🔍 Individual Flight Inspector")
    
    flight_num = st.number_input("Enter Flight Number", min_value=1, value=100, step=1)
    
    inspect_query = f"""
        SELECT FL_DATE, AIRLINE_CODE, ORIGIN, DEST, DEP_DELAY, TAXI_OUT, AIR_TIME, TAXI_IN, ARR_DELAY, CANCELLED
        FROM flights
        WHERE FL_NUMBER = {flight_num} {airline_filter}
        ORDER BY FL_DATE DESC
        LIMIT 10
    """[cite: 1]
    flight_records = conn.execute(inspect_query).df()
    
    if not flight_records.empty:
        st.dataframe(flight_records, use_container_width=True)
        
        # Single Flight Waterfall Demonstration
        sample_flight = flight_records.iloc[0]
        st.subheader(f"Time Breakdown: Flight {flight_num} on {sample_flight['FL_DATE']}")
        
        fig_waterfall = go.Figure(go.Waterfall(
            name = "Timeline", orientation = "v",
            measure = ["relative", "relative", "relative", "relative", "total"],
            x = ["Dep Delay", "Taxi Out", "Air Time", "Taxi In", "Total Delay"],
            textposition = "outside",
            y = [sample_flight['DEP_DELAY'], sample_flight['TAXI_OUT'], sample_flight['AIR_TIME'], sample_flight['TAXI_IN'], sample_flight['ARR_DELAY']],
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
        ))
        fig_waterfall.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_waterfall, use_container_width=True)
    else:
        st.warning("No flight matching the specified criteria was found.")
