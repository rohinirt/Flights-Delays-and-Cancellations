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

# Custom Glassmorphism UI Styling
st.markdown("""
<style>
    .stApp { background-color: #0b0f19; }
    div[data-testid="metric-container"] {
        background-color: #151c2e;
        border: 1px solid #232d42;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .flight-card {
        background-color: #151c2e;
        border: 1px solid #232d42;
        border-left: 4px solid #00f2fe;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
    }
    .flight-card:hover {
        border-color: #00f2fe;
        transition: all 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)

# Coordinates for PyDeck Map
ORD_LAT, ORD_LON = 41.9742, -87.9073
AIRPORT_COORDS = {
    'LAX': (-118.4081, 33.9416), 'JFK': (-73.7781, 40.6413), 'LGA': (-73.8740, 40.7769),
    'SFO': (-122.3790, 37.6213), 'DFW': (-97.0403, 32.8998), 'DEN': (-104.6737, 39.8561),
    'ATL': (-84.4277, 33.6407), 'MIA': (-80.2870, 25.7959), 'SEA': (-122.3088, 47.4502),
    'BOS': (-71.0052, 42.3656), 'PHX': (-112.0078, 33.4352), 'LAS': (-115.1523, 36.0840),
    'MSP': (-93.2223, 44.8848), 'DTW': (-83.3534, 42.2162), 'MCO': (-81.3081, 28.4288),
    'ANC': (-149.9963, 61.1743), 'HNL': (-157.9224, 21.3187), 'OGG': (-156.4305, 20.8986)
}

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
    conn = get_db_connection()
except Exception as e:
    st.error(f"Error loading CSV file: {e}. Please ensure 'flights_2022.csv' is in root directory.")
    st.stop()

# Helper for Sparkline Visuals
def create_sparkline(data, x_col, y_col, color="#00f2fe"):
    fig = px.line(data, x=x_col, y=y_col, render_mode="svg")
    fig.update_traces(line_color=color, line_width=2)
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=40,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

# Sidebar Filters
st.sidebar.title("✈️ ORD Analytics")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigation", ["Arrivals Intelligence", "Departures Intelligence", "Flight Deep-Dive"])

st.sidebar.markdown("---")
st.sidebar.subheader("Filter Data")
airlines = conn.execute('SELECT DISTINCT "AIRLINE_CODE" FROM flights WHERE "AIRLINE_CODE" IS NOT NULL').df().iloc[:, 0].dropna().tolist()
selected_airline = st.sidebar.multiselect("Select Airline", options=airlines, default=[])

airline_filter = ""
if selected_airline:
    formatted_airlines = "', '".join(selected_airline)
    airline_filter = f"AND \"AIRLINE_CODE\" IN ('{formatted_airlines}')"

# ==================== PAGE 1: ARRIVALS ====================
if page == "Arrivals Intelligence":
    st.title("🛬 ORD Arrivals Intelligence (2022)")
    
    # 1. KPI Cards with Sparklines
    kpi_query = f"""
        SELECT 
            COUNT(*) AS total_flights,
            AVG(CASE WHEN "ARR_DELAY" <= 0 THEN 1 ELSE 0 END) * 100 AS on_time_pct,
            AVG("ARR_DELAY") AS avg_delay,
            SUM("CANCELLED") AS total_cancelled,
            SUM("DIVERTED") AS total_diverted
        FROM flights 
        WHERE "DEST" = 'ORD' {airline_filter}
    """
    kpi_df = conn.execute(kpi_query).df()
    total_flights, on_time_pct, avg_delay, total_cancelled, total_diverted = kpi_df.iloc[0]

    # Extreme Flight Queries
    longest_dist_query = f'SELECT "FL_NUMBER", "ORIGIN", "DISTANCE", "AIRLINE_CODE" FROM flights WHERE "DEST" = \'ORD\' {airline_filter} ORDER BY "DISTANCE" DESC LIMIT 1'
    longest_time_query = f'SELECT "FL_NUMBER", "ORIGIN", "ELAPSED_TIME", "AIRLINE_CODE" FROM flights WHERE "DEST" = \'ORD\' {airline_filter} ORDER BY "ELAPSED_TIME" DESC LIMIT 1'
    
    max_dist_row = conn.execute(longest_dist_query).df().iloc[0]
    max_time_row = conn.execute(longest_time_query).df().iloc[0]

    # Monthly Trendline Query for Sparklines
    monthly_trend = conn.execute(f"""
        SELECT 
            CAST(SUBSTR(CAST("FL_DATE" AS VARCHAR), 5, 2) AS INT) AS month,
            COUNT(*) AS flights,
            AVG("ARR_DELAY") AS delay
        FROM flights 
        WHERE "DEST" = 'ORD' {airline_filter}
        GROUP BY month ORDER BY month
    """).df()

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    
    with c1:
        st.metric("Total Arrivals", f"{int(total_flights or 0):,}")
        st.plotly_chart(create_sparkline(monthly_trend, 'month', 'flights', '#00f2fe'), use_container_width=True)
    with c2:
        st.metric("On-Time %", f"{(on_time_pct or 0):.1f}%")
        st.plotly_chart(create_sparkline(monthly_trend, 'month', 'delay', '#00c6ff'), use_container_width=True)
    with c3:
        st.metric("Avg Delay", f"{(avg_delay or 0):.1f}m")
        st.plotly_chart(create_sparkline(monthly_trend, 'month', 'delay', '#ff7675'), use_container_width=True)
    with c4:
        st.metric("Cancelled", f"{int(total_cancelled or 0):,}")
    with c5:
        st.metric("Diverted", f"{int(total_diverted or 0):,}")
    with c6:
        st.metric("Max Distance", f"{int(max_dist_row.iloc[2])} mi", f"Flight {int(max_dist_row.iloc[0])} ({max_dist_row.iloc[1]})")
    with c7:
        st.metric("Max Flight Time", f"{int(max_time_row.iloc[2])} min", f"Flight {int(max_time_row.iloc[0])} ({max_time_row.iloc[1]})")

    st.markdown("---")

    # 2. Interactive Charts (Airlines & Origins Dynamic Toggle)
    col1, col2 = st.columns(2)
    
    measure = st.radio("Chart Measure Selector:", ["Flights Count", "On-Time %", "Cancellations", "Avg Delay (min)"], horizontal=True)
    
    measure_sql = {
        "Flights Count": ("COUNT(*)", "DESC"),
        "On-Time %": ('AVG(CASE WHEN "ARR_DELAY" <= 0 THEN 1 ELSE 0 END) * 100', "DESC"),
        "Cancellations": ('SUM("CANCELLED")', "DESC"),
        "Avg Delay (min)": ('AVG("ARR_DELAY")', "DESC")
    }[measure]

    with col1:
        st.subheader("Top 5 Airlines")
        air_df = conn.execute(f"""
            SELECT "AIRLINE_CODE" AS label, {measure_sql[0]} AS val
            FROM flights WHERE "DEST" = 'ORD' {airline_filter}
            GROUP BY label ORDER BY val {measure_sql[1]} LIMIT 5
        """).df()
        fig_air = px.bar(air_df, x='label', y='val', color='val', color_continuous_scale='Blugrn', labels={'label':'Airline', 'val': measure})
        fig_air.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig_air, use_container_width=True)

    with col2:
        st.subheader("Top 5 Origin Airports")
        orig_df = conn.execute(f"""
            SELECT "ORIGIN" AS label, {measure_sql[0]} AS val
            FROM flights WHERE "DEST" = 'ORD' {airline_filter}
            GROUP BY label ORDER BY val {measure_sql[1]} LIMIT 5
        """).df()
        fig_orig = px.bar(orig_df, x='label', y='val', color='val', color_continuous_scale='Darkmint', labels={'label':'Origin', 'val': measure})
        fig_orig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig_orig, use_container_width=True)

    st.markdown("---")

    # 3. Longest Flights Vertical Cards
    st.subheader("✈️ Top 5 Longest Inbound Routes")
    card_toggle = st.segmented_control("Sort Longest Flights By:", ["Distance (Miles)", "Elapsed Time (Minutes)"], default="Distance (Miles)")
    sort_col = '"DISTANCE"' if card_toggle == "Distance (Miles)" else '"ELAPSED_TIME"'
    
    cards_df = conn.execute(f"""
        SELECT DISTINCT "FL_NUMBER", "AIRLINE_CODE", "ORIGIN", "ORIGIN_CITY", "DISTANCE", "ELAPSED_TIME"
        FROM flights WHERE "DEST" = 'ORD' {airline_filter}
        ORDER BY {sort_col} DESC LIMIT 5
    """).df()

    card_cols = st.columns(5)
    for idx, row in cards_df.iterrows():
        with card_cols[idx]:
            st.markdown(f"""
            <div class="flight-card">
                <h4 style="margin:0; color:#00f2fe;">FL #{int(row.iloc[0])}</h4>
                <p style="margin:4px 0; color:#a0aec0;"><b>Airline:</b> {row.iloc[1]}</p>
                <p style="margin:4px 0; color:#a0aec0;"><b>From:</b> {row.iloc[2]} ({row.iloc[3].split(',')[0]})</p>
                <p style="margin:4px 0; color:#a0aec0;"><b>Distance:</b> {int(row.iloc[4])} mi</p>
                <p style="margin:4px 0; color:#a0aec0;"><b>Time:</b> {int(row.iloc[5] or 0)} mins</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # 4. Time Heatmap & 5. Delay Drivers
    col_heat, col_pie = st.columns([1.3, 1])
    
    with col_heat:
        st.subheader("Arrival Volume Temporal Heatmap")
        heat_dim = st.radio("Time Perspective:", ["Month vs. Hour", "Day of Week vs. Hour"], horizontal=True)
        
        if heat_dim == "Month vs. Hour":
            heat_df = conn.execute(f"""
                SELECT 
                    CAST(SUBSTR(CAST("FL_DATE" AS VARCHAR), 5, 2) AS INT) AS row_dim,
                    CAST("CRS_ARR_TIME" / 100 AS INT) AS hour,
                    COUNT(*) AS flights
                FROM flights WHERE "DEST" = 'ORD' {airline_filter}
                GROUP BY row_dim, hour ORDER BY row_dim, hour
            """).df()
            y_label = "Month"
        else:
            heat_df = conn.execute(f"""
                SELECT 
                    DAYOFWEEK(CAST(STRPTIME(CAST("FL_DATE" AS VARCHAR), '%Y%m%d') AS DATE)) AS row_dim,
                    CAST("CRS_ARR_TIME" / 100 AS INT) AS hour,
                    COUNT(*) AS flights
                FROM flights WHERE "DEST" = 'ORD' {airline_filter}
                GROUP BY row_dim, hour ORDER BY row_dim, hour
            """).df()
            y_label = "Day of Week (1=Mon)"

        pivot_heat = heat_df.pivot(index='row_dim', columns='hour', values='flights').fillna(0)
        fig_heat = px.imshow(pivot_heat, labels=dict(x="Hour of Day", y=y_label, color="Flights"), color_continuous_scale="Viridis")
        fig_heat.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_heat, use_container_width=True)

    with col_pie:
        st.subheader("Arrival Delay Drivers")
        delay_df = conn.execute(f"""
            SELECT 
                AVG("DELAY_DUE_CARRIER") AS Carrier,
                AVG("DELAY_DUE_WEATHER") AS Weather,
                AVG("DELAY_DUE_NAS") AS NAS,
                AVG("DELAY_DUE_SECURITY") AS Security,
                AVG("DELAY_DUE_LATE_AIRCRAFT") AS "Late Aircraft"
            FROM flights WHERE "DEST" = 'ORD' {airline_filter}
        """).df()
        
        fig_pie = px.pie(
            values=delay_df.iloc[0].fillna(0).values, 
            names=delay_df.columns.tolist(),
            hole=0.5,
            color_discrete_sequence=['#00f2fe', '#4facfe', '#00c6ff', '#0072ff', '#3a7bd5']
        )
        fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # 6. Suggested Flow Network Chart (Sankey Chart for Multi-Route Operations)
    st.subheader("🕸️ Airline to Origin Route Flow (Multi-Route Operations)")
    st.caption("Visualizing carrier connectivity across major origin hubs connecting to Chicago ORD.")

    sankey_df = conn.execute(f"""
        SELECT "AIRLINE_CODE", "ORIGIN", COUNT(*) AS flight_count
        FROM flights WHERE "DEST" = 'ORD' {airline_filter}
        GROUP BY "AIRLINE_CODE", "ORIGIN"
        ORDER BY flight_count DESC LIMIT 20
    """).df()

    labels = list(set(sankey_df['AIRLINE_CODE']).union(set(sankey_df['ORIGIN'])))
    label_map = {name: idx for idx, name in enumerate(labels)}

    sources = [label_map[row['AIRLINE_CODE']] for _, row in sankey_df.iterrows()]
    targets = [label_map[row['ORIGIN']] for _, row in sankey_df.iterrows()]
    values = sankey_df['flight_count'].tolist()

    fig_sankey = go.Figure(data=[go.Sankey(
        node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=labels, color="#00f2fe"),
        link=dict(source=sources, target=targets, value=values, color="rgba(0, 242, 254, 0.2)")
    )])
    fig_sankey.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=400)
    st.plotly_chart(fig_sankey, use_container_width=True)

    st.markdown("---")

    # 7. Airline / Flight Data Table
    st.subheader("📋 Flight Records Inspector")
    table_df = conn.execute(f"""
        SELECT "FL_DATE", "AIRLINE_CODE", "FL_NUMBER", "ORIGIN", "ARR_DELAY", "CANCELLED", "DISTANCE"
        FROM flights WHERE "DEST" = 'ORD' {airline_filter}
        ORDER BY "FL_DATE" DESC LIMIT 100
    """).df()
    st.dataframe(table_df, use_container_width=True, height=300)

# ==================== PAGE 2: DEPARTURES ====================
elif page == "Departures Intelligence":
    st.title("🛫 ORD Departures Intelligence (2022)")
    st.info("Departures Analytics Dashboard")

# ==================== PAGE 3: DEEP-DIVE ====================
elif page == "Flight Deep-Dive":
    st.title("🔍 Individual Flight Inspector")
    st.info("Flight Level Breakdown Engine")
