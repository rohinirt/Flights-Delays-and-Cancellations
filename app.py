import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="Chicago O'Hare (ORD) Flight Intelligence",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional High-Contrast Styling
st.markdown("""
<style>
    /* Base Page Theme */
    .stApp { 
        background-color: #f8fafc !important; 
        color: #0f172a !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /* Force Light Theme Text Colors */
    .stApp p, .stApp span, .stApp label, .stApp div, .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
        color: #0f172a !important;
    }

    /* Fix Streamlit Segmented Control Unselected Buttons */
    div[data-testid="stSegmentedControl"] button {
        background-color: #0A192F !important;
        border: 1px solid #1e293b !important;
    }
    div[data-testid="stSegmentedControl"] button p,
    div[data-testid="stSegmentedControl"] button span {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    div[data-testid="stSegmentedControl"] button[aria-selected="true"] {
        background-color: #38bdf8 !important;
        border-color: #0284c7 !important;
    }
    div[data-testid="stSegmentedControl"] button[aria-selected="true"] p,
    div[data-testid="stSegmentedControl"] button[aria-selected="true"] span {
        color: #090d16 !important;
        font-weight: 700 !important;
    }

    /* KPI Metrics Styling */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        padding: 12px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    }
    div[data-testid="stMetricLabel"] p {
        color: #475569 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="stMetricValue"] div {
        color: #0A192F !important;
        font-weight: 700 !important;
    }

    /* Flight Cards Styling */
    .flight-card-container {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-left: 5px solid #0066CC !important;
        border-radius: 8px !important;
        padding: 14px 18px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04) !important;
    }
    .flight-card-delay {
        border-left-color: #D00000 !important;
    }
    .card-title { 
        font-size: 1.05rem !important; 
        font-weight: 700 !important; 
        color: #0A192F !important; 
        margin: 0 !important; 
    }
    .card-subtitle { 
        font-size: 0.85rem !important; 
        color: #475569 !important; 
        margin-bottom: 8px !important; 
    }
    .card-metric { 
        font-size: 0.9rem !important; 
        font-weight: 600 !important; 
        color: #1e293b !important; 
    }

    /* Dark Sidebar Scope */
    section[data-testid="stSidebar"] {
        background-color: #0A192F !important;
    }
    section[data-testid="stSidebar"] * {
        color: #ffffff !important;
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
    conn = get_db_connection()
except Exception as e:
    st.error(f"Error loading CSV dataset: {e}. Ensure 'flights_2022.csv' is in root directory.")
    st.stop()

# Plotly High-Contrast Light Theme Config
PLOTLY_THEME = dict(
    font=dict(color="#0f172a", family="Segoe UI, sans-serif"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    title=dict(font=dict(color="#0f172a", size=16, family="Segoe UI, sans-serif")),
    xaxis=dict(
        title=dict(font=dict(color="#0f172a")),
        tickfont=dict(color="#0f172a"),
        gridcolor="#e2e8f0"
    ),
    yaxis=dict(
        title=dict(font=dict(color="#0f172a")),
        tickfont=dict(color="#0f172a"),
        gridcolor="#e2e8f0"
    ),
    legend=dict(font=dict(color="#0f172a"))
)

def create_kpi_bar_chart(data, x_col, y_col, color="#0066CC"):
    fig = px.bar(data, x=x_col, y=y_col)
    fig.update_traces(marker_color=color, opacity=0.85)
    fig.update_layout(
        margin=dict(l=0, r=0, t=2, b=0),
        height=38,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

# Sidebar Filters
st.sidebar.title("✈️ ORD Analytics")
st.sidebar.caption("Chicago O'Hare International Airport")
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

# ==================== ARRIVALS INTELLIGENCE PAGE ====================
if page == "Arrivals Intelligence":
    st.title("🛬 ORD Arrivals Intelligence")
    st.caption("2022 Operational Performance & Route Analytics")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 1. KPI Cards
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

    longest_dist_row = conn.execute(f'SELECT "FL_NUMBER", "ORIGIN", "DISTANCE" FROM flights WHERE "DEST" = \'ORD\' {airline_filter} ORDER BY "DISTANCE" DESC LIMIT 1').df().iloc[0]
    longest_time_row = conn.execute(f'SELECT "FL_NUMBER", "ORIGIN", "ELAPSED_TIME" FROM flights WHERE "DEST" = \'ORD\' {airline_filter} ORDER BY "ELAPSED_TIME" DESC LIMIT 1').df().iloc[0]

    monthly_trend = conn.execute(f"""
        SELECT 
            CAST(SUBSTR(CAST("FL_DATE" AS VARCHAR), 5, 2) AS INT) AS month,
            COUNT(*) AS flights,
            AVG("ARR_DELAY") AS delay,
            AVG(CASE WHEN "ARR_DELAY" <= 0 THEN 1 ELSE 0 END) * 100 AS on_time
        FROM flights 
        WHERE "DEST" = 'ORD' {airline_filter}
        GROUP BY month ORDER BY month
    """).df()

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    
    with c1:
        st.metric("Total Arrivals", f"{int(total_flights or 0):,}")
        st.plotly_chart(create_kpi_bar_chart(monthly_trend, 'month', 'flights', '#0066CC'), use_container_width=True)
    with c2:
        st.metric("On-Time %", f"{(on_time_pct or 0):.1f}%")
        st.plotly_chart(create_kpi_bar_chart(monthly_trend, 'month', 'on_time', '#10B981'), use_container_width=True)
    with c3:
        st.metric("Avg Delay", f"{(avg_delay or 0):.1f}m")
        st.plotly_chart(create_kpi_bar_chart(monthly_trend, 'month', 'delay', '#D00000'), use_container_width=True)
    with c4:
        st.metric("Cancelled", f"{int(total_cancelled or 0):,}")
    with c5:
        st.metric("Diverted", f"{int(total_diverted or 0):,}")
    with c6:
        st.metric("Max Distance", f"{int(longest_dist_row.iloc[2])} mi", f"FL {int(longest_dist_row.iloc[0])} ({longest_dist_row.iloc[1]})")
    with c7:
        st.metric("Max Flight Time", f"{int(longest_time_row.iloc[2])} min", f"FL {int(longest_time_row.iloc[0])} ({longest_time_row.iloc[1]})")

    st.markdown("---")

    # 2. Controls & Horizontal Bar Charts
    st.subheader("Top Performers Breakdown")
    
    measure = st.segmented_control(
        "Select Performance Metric:",
        ["Flights Count", "On-Time %", "Cancellations", "Avg Delay (min)"],
        default="Avg Delay (min)"
    )
    
    measure_map = {
        "Flights Count": ("COUNT(*)", "DESC"),
        "On-Time %": ('AVG(CASE WHEN "ARR_DELAY" <= 0 THEN 1 ELSE 0 END) * 100', "DESC"),
        "Cancellations": ('SUM("CANCELLED")', "DESC"),
        "Avg Delay (min)": ('AVG("ARR_DELAY")', "DESC")
    }
    sql_val, sql_ord = measure_map[measure]

    col_air, col_orig = st.columns(2)

    with col_air:
        air_df = conn.execute(f"""
            SELECT "AIRLINE_CODE" AS label, {sql_val} AS val
            FROM flights WHERE "DEST" = 'ORD' {airline_filter}
            GROUP BY label ORDER BY val {sql_ord} LIMIT 5
        """).df()
        
        fig_air = px.bar(
            air_df, y='label', x='val', orientation='h',
            labels={'label': 'Airline', 'val': measure},
            title=f"Top 5 Airlines by {measure}"
        )
        fig_air.update_traces(marker_color='#0066CC')
        fig_air.update_layout(**PLOTLY_THEME)
        fig_air.update_layout(yaxis=dict(autorange="reversed"), margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_air, use_container_width=True)

    with col_orig:
        orig_df = conn.execute(f"""
            SELECT "ORIGIN" AS label, {sql_val} AS val
            FROM flights WHERE "DEST" = 'ORD' {airline_filter}
            GROUP BY label ORDER BY val {sql_ord} LIMIT 5
        """).df()
        
        fig_orig = px.bar(
            orig_df, y='label', x='val', orientation='h',
            labels={'label': 'Origin Airport', 'val': measure},
            title=f"Top 5 Origin Hubs by {measure}"
        )
        fig_orig.update_traces(marker_color='#0A192F')
        fig_orig.update_layout(**PLOTLY_THEME)
        fig_orig.update_layout(yaxis=dict(autorange="reversed"), margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_orig, use_container_width=True)

    st.markdown("---")

    # 3. Vertical Cards Side-by-Side
    col_longest, col_delayed = st.columns(2)

    with col_longest:
        st.subheader("✈️ Top 5 Longest Inbound Routes")
        card_toggle = st.segmented_control("Sort Longest Routes By:", ["Distance (Miles)", "Elapsed Time (Minutes)"], default="Distance (Miles)")
        sort_col = '"DISTANCE"' if card_toggle == "Distance (Miles)" else '"ELAPSED_TIME"'
        
        longest_df = conn.execute(f"""
            SELECT DISTINCT "FL_NUMBER", "AIRLINE_CODE", "ORIGIN", "ORIGIN_CITY", "DISTANCE", "ELAPSED_TIME"
            FROM flights WHERE "DEST" = 'ORD' {airline_filter}
            ORDER BY {sort_col} DESC LIMIT 5
        """).df()

        for idx, row in longest_df.iterrows():
            st.markdown(f"""
            <div class="flight-card-container">
                <div class="card-title">Flight #{int(row.iloc[0])} — {row.iloc[1]}</div>
                <div class="card-subtitle">Origin: <b style="color:#0A192F;">{row.iloc[2]}</b> ({row.iloc[3]})</div>
                <div style="display: flex; justify-content: space-between;">
                    <span class="card-metric">📏 Distance: <b>{int(row.iloc[4])} mi</b></span>
                    <span class="card-metric">⏱️ Time: <b>{int(row.iloc[5] or 0)} mins</b></span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_delayed:
        st.subheader("⚠️ Top 5 Most Delayed Inbound Flights")
        delay_toggle = st.segmented_control("Sort Delay By:", ["Arrival Delay", "Carrier Delay"], default="Arrival Delay")
        delay_sort_col = '"ARR_DELAY"' if delay_toggle == "Arrival Delay" else '"DELAY_DUE_CARRIER"'

        delayed_df = conn.execute(f"""
            SELECT "FL_NUMBER", "AIRLINE_CODE", "ORIGIN", "ORIGIN_CITY", "ARR_DELAY", "DELAY_DUE_CARRIER"
            FROM flights WHERE "DEST" = 'ORD' {airline_filter}
            ORDER BY {delay_sort_col} DESC LIMIT 5
        """).df()

        for idx, row in delayed_df.iterrows():
            st.markdown(f"""
            <div class="flight-card-container flight-card-delay">
                <div class="card-title">Flight #{int(row.iloc[0])} — {row.iloc[1]}</div>
                <div class="card-subtitle">Origin: <b style="color:#0A192F;">{row.iloc[2]}</b> ({row.iloc[3]})</div>
                <div style="display: flex; justify-content: space-between;">
                    <span class="card-metric" style="color: #D00000 !important;">🔴 Arr Delay: <b>{int(row.iloc[4] or 0)} mins</b></span>
                    <span class="card-metric">🏢 Carrier Delay: <b>{int(row.iloc[5] or 0)} mins</b></span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # 4. Temporal Heatmap & Delay Drivers
    c_heat, c_delay = st.columns([1.4, 1])

    with c_heat:
        st.subheader("Arrival Volume Heatmap")
        heat_dim = st.segmented_control("Perspective:", ["Month vs. Hour", "Day of Week vs. Hour"], default="Month vs. Hour")
        
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
                    DAYOFWEEK(CAST(SUBSTR(CAST("FL_DATE" AS VARCHAR), 1, 4) || '-' || SUBSTR(CAST("FL_DATE" AS VARCHAR), 5, 2) || '-' || SUBSTR(CAST("FL_DATE" AS VARCHAR), 7, 2) AS DATE)) AS row_dim,
                    CAST("CRS_ARR_TIME" / 100 AS INT) AS hour,
                    COUNT(*) AS flights
                FROM flights WHERE "DEST" = 'ORD' {airline_filter}
                GROUP BY row_dim, hour ORDER BY row_dim, hour
            """).df()
            y_label = "Day of Week (1=Sun, 7=Sat)"

        pivot_heat = heat_df.pivot(index='row_dim', columns='hour', values='flights').fillna(0)
        fig_heat = px.imshow(
            pivot_heat, 
            labels=dict(x="Hour of Day (24h)", y=y_label, color="Flights"),
            color_continuous_scale="Blues"
        )
        fig_heat.update_layout(**PLOTLY_THEME)
        fig_heat.update_layout(coloraxis_colorbar=dict(title=dict(font=dict(color="#0f172a")), tickfont=dict(color="#0f172a")))
        st.plotly_chart(fig_heat, use_container_width=True)

    with c_delay:
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
            hole=0.45,
            color_discrete_sequence=['#0066CC', '#0A192F', '#D00000', '#64748B', '#38BDF8']
        )
        fig_pie.update_layout(**PLOTLY_THEME)
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # 5. Multi-Route Carrier Network Flow
    st.subheader("🕸️ Airline to Hub Network Flow")
    st.caption("Visualizing airline connectivity and route distribution across major inbound origin hubs.")

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
        node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=labels, color="#0066CC"),
        link=dict(source=sources, target=targets, value=values, color="rgba(0, 102, 204, 0.2)")
    )])
    fig_sankey.update_layout(**PLOTLY_THEME)
    fig_sankey.update_layout(height=350)
    st.plotly_chart(fig_sankey, use_container_width=True)

    st.markdown("---")

    # 6. Flight Records Inspector Table
    st.subheader("📋 Inbound Flight Records Table")
    table_df = conn.execute(f"""
        SELECT "FL_DATE", "AIRLINE_CODE", "FL_NUMBER", "ORIGIN", "ARR_DELAY", "CANCELLED", "DISTANCE"
        FROM flights WHERE "DEST" = 'ORD' {airline_filter}
        ORDER BY "FL_DATE" DESC LIMIT 100
    """).df()
    st.dataframe(table_df, use_container_width=True, height=300)

# ==================== OTHER PAGES ====================
elif page == "Departures Intelligence":
    st.title("🛫 ORD Departures Intelligence")
    st.info("Departures Analytics Dashboard")

elif page == "Flight Deep-Dive":
    st.title("🔍 Individual Flight Inspector")
    st.info("Flight Analysis Engine")
