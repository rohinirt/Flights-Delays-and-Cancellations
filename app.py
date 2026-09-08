import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import urllib.request

# Page Configuration
st.set_page_config(
    page_title="Chicago O'Hare (ORD) Flight Intelligence",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper function to safely convert potential NaN/None values to integers
def safe_int(val, default=0):
    if pd.isna(val) or val is None:
        return default
    return int(val)

# Helper function to format military time strings
def format_time_str(time_val):
    if pd.isna(time_val) or time_val is None:
        return "--:--"
    time_str = str(int(time_val)).zfill(4)
    hours = int(time_str[:2])
    mins = int(time_str[2:])
    period = "am" if hours < 12 else "pm"
    display_hour = hours if hours % 12 != 0 else 12
    if display_hour > 12:
        display_hour -= 12
    return f"{display_hour}:{mins:02d} {period}"

# Name Reference Dictionaries
AIRLINE_NAMES = {
    'AA': 'American Airlines', 'UA': 'United Airlines', 'DL': 'Delta Air Lines',
    'WN': 'Southwest Airlines', 'B6': 'JetBlue Airways', 'NK': 'Spirit Airlines',
    'F9': 'Frontier Airlines', 'AS': 'Alaska Airlines', 'G4': 'Allegiant Air',
    'OH': 'Piedmont Airlines', 'YX': 'Republic Airways', 'MQ': 'Envoy Air',
    'OO': 'SkyWest Airlines', '9E': 'Endeavor Air'
}

AIRPORT_CITY_NAMES = {
    'LAX': 'Los Angeles', 'JFK': 'New York', 'DFW': 'Dallas/Fort Worth',
    'DEN': 'Denver', 'ATL': 'Atlanta', 'SFO': 'San Francisco',
    'SEA': 'Seattle', 'LAS': 'Las Vegas', 'MCO': 'Orlando',
    'PHX': 'Phoenix', 'EWR': 'Newark', 'CLT': 'Charlotte',
    'MSP': 'Minneapolis', 'BOS': 'Boston', 'LGA': 'New York (LGA)',
    'DTW': 'Detroit', 'IAH': 'Houston', 'MIA': 'Miami',
    'SAN': 'San Diego', 'SLC': 'Salt Lake City'
}

# Global Styling Rules
st.markdown("""
<style>
    :root {
        --background-color: #f8fafc !important;
        --secondary-background-color: #ffffff !important;
        --text-color: #0f172a !important;
    }

    /* Outer Wrapper Padding */
    .stApp { 
        background-color: #f8fafc !important; 
        color: #0f172a !important;
        padding: 20px !important;
    }

    .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp caption {
        color: #0f172a !important;
    }

    /* Solid White Card Containers */
    .chart-card-container {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px !important;
        padding: 16px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }

    /* Single Box Combined KPI Card Container */
    .kpi-unified-card {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px !important;
        padding: 14px 12px 6px 12px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
        text-align: center;
        margin-bottom: 10px;
    }

    /* Segmented Control Styling */
    div[data-testid="stSegmentedControl"] {
        background-color: #f1f5f9 !important;
        border-radius: 8px !important;
        padding: 3px !important;
        margin-bottom: 8px !important;
    }
    div[data-testid="stSegmentedControl"] button {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
    }
    div[data-testid="stSegmentedControl"] button * {
        color: #0f172a !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
    }
    div[data-testid="stSegmentedControl"] button[aria-selected="true"] {
        background-color: #0066CC !important;
    }
    div[data-testid="stSegmentedControl"] button[aria-selected="true"] * {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* Flight Card Styling */
    .flight-widget-card {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        margin-bottom: 10px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
    }
    .flight-card-badge {
        background-color: #f1f5f9;
        color: #0f172a;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 4px;
        border: 1px solid #cbd5e1;
        display: inline-block;
        margin-bottom: 6px;
    }
    .flight-route-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 6px;
    }
    .airport-code {
        font-size: 1.4rem;
        font-weight: 800;
        color: #0F172A;
        line-height: 1;
    }
    .route-line-container {
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 0 12px;
        margin-top: 2px;
    }
    .flight-duration {
        font-size: 0.75rem;
        color: #475569;
        font-weight: 600;
        margin-bottom: 2px;
    }
    .route-line {
        width: 100%;
        height: 1px;
        background-color: #cbd5e1;
        position: relative;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    .plane-icon {
        font-size: 0.8rem;
        color: #0066CC;
        background-color: #ffffff;
        padding: 0 4px;
    }
    .flight-details-grid {
        display: grid;
        grid-template-columns: 1fr 1.2fr;
        gap: 8px;
        border-top: 1px solid #f1f5f9;
        padding-top: 8px;
        margin-top: 6px;
    }
    .flight-column-left {
        border-right: 1px solid #f1f5f9;
        padding-right: 6px;
    }
    .time-display {
        font-size: 0.95rem;
        font-weight: 700;
        margin-top: 1px;
    }
    .detail-label {
        color: #64748B;
        font-size: 0.7rem;
        font-weight: 500;
    }

    /* Sidebar Styling */
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

@st.cache_data
def load_airport_coordinates():
    base_coords = {
        'ORD': (41.9742, -87.9073), 'LAX': (33.9416, -118.4085), 'JFK': (40.6413, -73.7781),
        'DFW': (32.8998, -97.0403), 'DEN': (39.8561, -104.6737), 'ATL': (33.6407, -84.4277),
        'SFO': (37.6213, -122.3790), 'SEA': (47.4502, -122.3088), 'LAS': (36.0840, -115.1537),
        'MCO': (28.4312, -81.3081), 'PHX': (33.4352, -112.0101), 'EWR': (40.6895, -74.1745),
        'CLT': (35.2140, -80.9431), 'MSP': (44.8848, -93.2223), 'BOS': (42.3656, -71.0096),
        'LGA': (40.7769, -73.8740), 'DTW': (42.2162, -83.3554), 'IAH': (29.9902, -95.3368),
        'MIA': (25.7959, -80.2870), 'SAN': (32.7338, -117.1933), 'SLC': (40.7899, -111.9791)
    }
    try:
        url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
        response = urllib.request.urlopen(url, timeout=3)
        lines = response.read().decode('utf-8').splitlines()
        for line in lines:
            parts = [p.strip('"') for p in line.split(',')]
            if len(parts) >= 8:
                iata, lat, lon = parts[4], parts[6], parts[7]
                if iata and iata != r"\N":
                    try:
                        base_coords[iata] = (float(lat), float(lon))
                    except ValueError:
                        pass
    except Exception:
        pass
    return base_coords

def apply_white_chart_theme(fig):
    fig.update_layout(
        template="plotly_white",
        font=dict(color="#0f172a", family="sans-serif"),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        title=dict(font=dict(color="#0f172a", size=15, weight="bold")),
        xaxis=dict(
            title=dict(font=dict(color="#0f172a")),
            tickfont=dict(color="#0f172a"),
            gridcolor="#f1f5f9"
        ),
        yaxis=dict(
            title=dict(font=dict(color="#0f172a")),
            tickfont=dict(color="#0f172a"),
            gridcolor="#f1f5f9"
        ),
        legend=dict(font=dict(color="#0f172a")),
        coloraxis_colorbar=dict(
            title=dict(font=dict(color="#0f172a")),
            tickfont=dict(color="#0f172a")
        )
    )
    return fig

def create_monthly_kpi_chart(data, x_col, y_col, bar_color="#0066CC"):
    data = data.copy()
    month_map = {
        1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun',
        7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'
    }
    data['month_code'] = data[x_col].map(month_map)
    
    fig = px.bar(data, x='month_code', y=y_col)
    fig.update_traces(
        marker_color=bar_color, 
        opacity=0.9, 
        hovertemplate="%{x}: %{y:,.1f}<extra></extra>"
    )
    fig.update_layout(
        margin=dict(l=2, r=2, t=5, b=15),
        height=75,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        xaxis=dict(
            type='category',
            categoryorder='array',
            categoryarray=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            tickfont=dict(size=8, color='#475569', weight='bold'),
            showgrid=False,
            zeroline=False,
            fixedrange=True,
            title="",
            showline=False
        ),
        yaxis=dict(
            visible=False, 
            showgrid=False, 
            fixedrange=True,
            autorange=True
        )
    )
    return fig

def create_3d_arrivals_map_all(conn, selected_airlines=None):
    where_clause = "WHERE \"DEST\" = 'ORD'"
    params = []
    if selected_airlines:
        placeholders = ", ".join(["?"] * len(selected_airlines))
        where_clause += f" AND \"AIRLINE_CODE\" IN ({placeholders})"
        params.extend(selected_airlines)

    origins_df = conn.execute(f"""
        SELECT 
            "ORIGIN",
            COUNT(*) AS flight_count
        FROM flights 
        {where_clause}
        GROUP BY "ORIGIN"
        ORDER BY flight_count DESC
    """, params).df()

    airport_coords = load_airport_coordinates()
    ord_lat, ord_lon = airport_coords['ORD']
    fig = go.Figure()

    for _, row in origins_df.iterrows():
        orig = row['ORIGIN']
        count = row['flight_count']
        orig_lat, orig_lon = airport_coords.get(orig, (39.8283, -98.5795))
        
        fig.add_trace(go.Scattergeo(
            locationmode='USA-states',
            lon=[orig_lon, ord_lon],
            lat=[orig_lat, ord_lat],
            mode='lines+markers',
            line=dict(width=1, color='#0066CC'),
            opacity=0.45,
            hoverinfo='text',
            text=f"{orig} ➔ ORD ({count:,} flights)",
            showlegend=False
        ))

    fig.add_trace(go.Scattergeo(
        lon=[ord_lon], lat=[ord_lat],
        mode='markers+text',
        marker=dict(size=12, color='#D00000', symbol='star'),
        text=['Chicago (ORD)'],
        textposition='top center',
        showlegend=False
    ))

    fig.update_layout(
        title=dict(text="🌐 3D Dynamic Arrivals Map", font=dict(size=15, color="#0f172a")),
        geo=dict(
            scope='north america',
            projection_type='orthographic',
            showland=True,
            landcolor="#F1F5F9",
            countrycolor="#CBD5E1",
            coastlinecolor="#94A3B8",
            showlakes=True,
            lakecolor="#E2E8F0",
            bgcolor="#FFFFFF",
            center=dict(lat=38.0, lon=-97.0),
            projection_scale=1.15
        ),
        margin=dict(l=0, r=0, t=35, b=0),
        height=320,
        paper_bgcolor="#FFFFFF"
    )
    return fig

def create_airline_to_origin_sankey(conn, selected_airlines=None):
    where_clause = "WHERE \"DEST\" = 'ORD'"
    params = []
    if selected_airlines:
        placeholders = ", ".join(["?"] * len(selected_airlines))
        where_clause += f" AND \"AIRLINE_CODE\" IN ({placeholders})"
        params.extend(selected_airlines)

    sankey_data = conn.execute(f"""
        SELECT 
            "AIRLINE_CODE",
            "ORIGIN",
            COUNT(*) AS flight_count
        FROM flights
        {where_clause}
        GROUP BY "AIRLINE_CODE", "ORIGIN"
        ORDER BY flight_count DESC
        LIMIT 20
    """, params).df()

    if sankey_data.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available for Sankey diagram", showarrow=False)
        return fig

    airlines_list = list(sankey_data['AIRLINE_CODE'].unique())
    origins_list = list(sankey_data['ORIGIN'].unique())
    all_nodes = airlines_list + origins_list
    
    node_dict = {node: i for i, node in enumerate(all_nodes)}

    sources, targets, values = [], [], []

    for _, row in sankey_data.iterrows():
        sources.append(node_dict[row['AIRLINE_CODE']])
        targets.append(node_dict[row['ORIGIN']])
        values.append(int(row['flight_count']))

    node_colors = ['#0066CC'] * len(airlines_list) + ['#0A192F'] * len(origins_list)

    fig = go.Figure(data=[go.Sankey(
        arrangement="fixed",
        node=dict(
            pad=14,
            thickness=18,
            line=dict(color="#CBD5E1", width=1),
            label=all_nodes,
            color=node_colors
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color='rgba(0, 102, 204, 0.25)'
        )
    )])

    fig.update_layout(
        title=dict(text="🔀 Airline ➔ Origin Connectivity Flow", font=dict(size=15, color="#0F172A")),
        font=dict(size=11, color='#0F172A', family="sans-serif"),
        height=320,
        margin=dict(l=10, r=10, t=35, b=10),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF"
    )
    return fig

def render_flight_card(row, is_delayed=False):
    origin_code = row['ORIGIN']
    origin_city = row['ORIGIN_CITY']
    airline_code = row['AIRLINE_CODE']
    fl_number = row['FL_NUMBER']
    fl_date = str(row['FL_DATE'])
    formatted_date = f"{fl_date[6:8]}/{fl_date[4:6]}/{fl_date[:4]}" if len(fl_date) == 8 else fl_date
    
    elapsed_time = safe_int(row['elapsed_time'])
    hours, mins = divmod(elapsed_time, 60)
    time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
    
    dep_time = format_time_str(row['crs_dep'])
    crs_arr_time = format_time_str(row['crs_arr'])
    actual_arr_time = format_time_str(row['actual_arr'])
    delay_val = safe_int(row['arr_delay'])

    if is_delayed:
        card_style = 'style="border-left: 4px solid #D00000 !important;"'
        badge_style = 'style="background-color: #FEF2F2; color: #D00000; border-color: #FCA5A5;"'
        badge_prefix = "⚠️ "
        duration_style = 'style="color: #D00000; font-weight: 700;"'
        icon_style = 'style="color: #D00000;"'
        delay_color = "#D00000"
    else:
        card_style = ""
        badge_style = ""
        badge_prefix = "✈️ "
        duration_style = ""
        icon_style = ""
        delay_color = "#10B981" if delay_val <= 0 else "#D00000"

    st.markdown(f"""
    <div class="flight-widget-card" {card_style}>
        <div>
            <span class="flight-card-badge" {badge_style}>{badge_prefix}{airline_code} #{fl_number}</span>
        </div>
        <div class="flight-route-header">
            <div>
                <div class="airport-code">{origin_code}</div>
            </div>
            <div class="route-line-container">
                <span class="flight-duration" {duration_style}>{time_str}</span>
                <div class="route-line">
                    <span class="plane-icon" {icon_style}>✈️</span>
                </div>
            </div>
            <div style="text-align: right;">
                <div class="airport-code">ORD</div>
            </div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #475569;">
            <div><strong>{origin_city}</strong> · {formatted_date}</div>
            <div><strong>Chicago</strong> · {formatted_date}</div>
        </div>
        <div class="flight-details-grid">
            <div class="flight-column-left">
                <div class="detail-label">Sched. Dep</div>
                <div class="time-display" style="color: #0066CC;">{dep_time}</div>
            </div>
            <div>
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <div class="detail-label">Sched. Arr</div>
                        <div class="time-display" style="color: #0F172A;">{crs_arr_time}</div>
                    </div>
                    <div style="text-align: right;">
                        <div class="detail-label">Actual / Delay</div>
                        <div class="time-display" style="color: {delay_color};">{actual_arr_time} ({delay_val:+}m)</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Sidebar Controls
st.sidebar.title("✈️ ORD Analytics")
st.sidebar.caption("Chicago O'Hare International Airport")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigation", ["Arrivals Intelligence", "Departures Intelligence", "Flight Deep-Dive"])

st.sidebar.markdown("---")
st.sidebar.subheader("Filter Data")
airlines = conn.execute('SELECT DISTINCT "AIRLINE_CODE" FROM flights WHERE "AIRLINE_CODE" IS NOT NULL').df().iloc[:, 0].dropna().tolist()
selected_airline = st.sidebar.multiselect("Select Airline", options=airlines, default=[])

where_clause = "WHERE \"DEST\" = 'ORD'"
params = []
if selected_airline:
    placeholders = ", ".join(["?"] * len(selected_airline))
    where_clause += f" AND \"AIRLINE_CODE\" IN ({placeholders})"
    params.extend(selected_airline)

# ==================== ARRIVALS INTELLIGENCE PAGE ====================
if page == "Arrivals Intelligence":
    st.title("🛬 ORD Arrivals Intelligence")
    st.caption("2022 Operational Performance & Route Analytics")
    st.markdown("<br>", unsafe_allow_html=True)
    
    kpi_query = f"""
        SELECT 
            COUNT(*) AS total_flights,
            AVG(CASE WHEN "ARR_DELAY" <= 15 THEN 1 ELSE 0 END) * 100 AS on_time_pct,
            AVG("ARR_DELAY") AS avg_delay,
            SUM("CANCELLED") AS total_cancelled,
            SUM("DIVERTED") AS total_diverted
        FROM flights 
        {where_clause}
    """
    kpi_df = conn.execute(kpi_query, params).df()
    total_flights, on_time_pct, avg_delay, total_cancelled, total_diverted = kpi_df.iloc[0]

    monthly_trend = conn.execute(f"""
        SELECT 
            MONTH(TRY_CAST(CAST("FL_DATE" AS VARCHAR) AS DATE)) AS month,
            COUNT(*) AS flights,
            AVG("ARR_DELAY") AS delay,
            AVG(CASE WHEN "ARR_DELAY" <= 15 THEN 1 ELSE 0 END) * 100 AS on_time,
            SUM("CANCELLED") AS cancelled,
            SUM("DIVERTED") AS diverted
        FROM flights 
        {where_clause}
        GROUP BY month 
        HAVING month IS NOT NULL
        ORDER BY month
    """, params).df()

    # Unified KPI Box Container Row
    c1, c2, c3, c4, c5 = st.columns(5)
    
    with c1:
        st.markdown(f"""
            <div class="kpi-unified-card">
                <div style="font-size: 0.72rem; font-weight: 700; color: #475569; text-transform: uppercase;">TOTAL ARRIVALS</div>
                <div style="font-size: 1.4rem; font-weight: 800; color: #0A192F; margin-bottom: 4px;">{safe_int(total_flights):,}</div>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'flights', '#0066CC'), use_container_width=True, config={'displayModeBar': False})

    with c2:
        st.markdown(f"""
            <div class="kpi-unified-card">
                <div style="font-size: 0.72rem; font-weight: 700; color: #475569; text-transform: uppercase;">ON-TIME % (≤15m)</div>
                <div style="font-size: 1.4rem; font-weight: 800; color: #10B981; margin-bottom: 4px;">{(on_time_pct or 0):.1f}%</div>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'on_time', '#10B981'), use_container_width=True, config={'displayModeBar': False})

    with c3:
        st.markdown(f"""
            <div class="kpi-unified-card">
                <div style="font-size: 0.72rem; font-weight: 700; color: #475569; text-transform: uppercase;">AVG DELAY</div>
                <div style="font-size: 1.4rem; font-weight: 800; color: #D00000; margin-bottom: 4px;">{(avg_delay or 0):.1f}m</div>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'delay', '#D00000'), use_container_width=True, config={'displayModeBar': False})

    with c4:
        st.markdown(f"""
            <div class="kpi-unified-card">
                <div style="font-size: 0.72rem; font-weight: 700; color: #475569; text-transform: uppercase;">CANCELLED</div>
                <div style="font-size: 1.4rem; font-weight: 800; color: #0A192F; margin-bottom: 4px;">{safe_int(total_cancelled):,}</div>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'cancelled', '#64748B'), use_container_width=True, config={'displayModeBar': False})

    with c5:
        st.markdown(f"""
            <div class="kpi-unified-card">
                <div style="font-size: 0.72rem; font-weight: 700; color: #475569; text-transform: uppercase;">DIVERTED</div>
                <div style="font-size: 1.4rem; font-weight: 800; color: #0A192F; margin-bottom: 4px;">{safe_int(total_diverted):,}</div>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'diverted', '#38BDF8'), use_container_width=True, config={'displayModeBar': False})

    st.markdown("<br>", unsafe_allow_html=True)

    # Main Grid Layout
    col_left, col_right = st.columns([1, 1])

    with col_left:
        # Segmented Control & Bar Charts inside white background wrapper
        with st.container():
            measure = st.segmented_control(
                "Select Metric for Charts Below:",
                ["Flights Count", "On-Time %", "Cancellations", "Avg Delay (min)"],
                default="Avg Delay (min)"
            )

            measure_map = {
                "Flights Count": ("COUNT(*)", "DESC"),
                "On-Time %": ('AVG(CASE WHEN "ARR_DELAY" <= 15 THEN 1 ELSE 0 END) * 100', "DESC"),
                "Cancellations": ('SUM("CANCELLED")', "DESC"),
                "Avg Delay (min)": ('AVG("ARR_DELAY")', "DESC")
            }
            sql_val, sql_ord = measure_map[measure]

            # Top 5 Airlines Bar Chart
            airlines_df = conn.execute(f"""
                SELECT "AIRLINE_CODE" AS code, {sql_val} AS val
                FROM flights {where_clause}
                GROUP BY code ORDER BY val {sql_ord} LIMIT 5
            """, params).df()
            airlines_df['full_label'] = airlines_df['code'].apply(lambda x: f"{x} ({AIRLINE_NAMES.get(x, 'Carrier')})")

            fig_air = px.bar(
                airlines_df, y='full_label', x='val', orientation='h',
                title=f"Top 5 Airlines by {measure}"
            )
            fig_air.update_traces(marker_color="#0066CC")
            fig_air = apply_white_chart_theme(fig_air)
            fig_air.update_layout(yaxis=dict(autorange="reversed", title=""), xaxis=dict(title=measure), margin=dict(l=10, r=10, t=35, b=10), height=250)
            st.plotly_chart(fig_air, use_container_width=True)

            # Top 5 Destinations Bar Chart
            origins_df = conn.execute(f"""
                SELECT "ORIGIN" AS code, {sql_val} AS val
                FROM flights {where_clause}
                GROUP BY code ORDER BY val {sql_ord} LIMIT 5
            """, params).df()
            origins_df['full_label'] = origins_df['code'].apply(lambda x: f"{x} ({AIRPORT_CITY_NAMES.get(x, 'Origin')})")

            fig_orig = px.bar(
                origins_df, y='full_label', x='val', orientation='h',
                title=f"Top 5 Origin Destinations by {measure}"
            )
            fig_orig.update_traces(marker_color="#0066CC")
            fig_orig = apply_white_chart_theme(fig_orig)
            fig_orig.update_layout(yaxis=dict(autorange="reversed", title=""), xaxis=dict(title=measure), margin=dict(l=10, r=10, t=35, b=10), height=250)
            st.plotly_chart(fig_orig, use_container_width=True)

    with col_right:
        # 3D Globe Map
        with st.container():
            st.plotly_chart(create_3d_arrivals_map_all(conn, selected_airline), use_container_width=True)

        # Airline to Origin Sankey Chart
        with st.container():
            st.plotly_chart(create_airline_to_origin_sankey(conn, selected_airline), use_container_width=True)

    # Flight Cards
    col_longest, col_delayed = st.columns(2)

    with col_longest:
        st.subheader("✈️ Top 5 Longest Inbound Routes")
        longest_df = conn.execute(f"""
            SELECT 
                "FL_NUMBER", "AIRLINE_CODE", "ORIGIN", "ORIGIN_CITY", "FL_DATE",
                COALESCE("CRS_DEP_TIME", 0) AS crs_dep,
                COALESCE("CRS_ARR_TIME", 0) AS crs_arr,
                COALESCE("ARR_TIME", 0) AS actual_arr,
                COALESCE("ELAPSED_TIME", 0) AS elapsed_time,
                COALESCE("ARR_DELAY", 0) AS arr_delay
            FROM flights {where_clause}
            ORDER BY "ELAPSED_TIME" DESC LIMIT 5
        """, params).df()

        for idx, row in longest_df.iterrows():
            render_flight_card(row, is_delayed=False)

    with col_delayed:
        st.subheader("⚠️ Top 5 Most Delayed Inbound Flights")
        delayed_df = conn.execute(f"""
            SELECT 
                "FL_NUMBER", "AIRLINE_CODE", "ORIGIN", "ORIGIN_CITY", "FL_DATE",
                COALESCE("CRS_DEP_TIME", 0) AS crs_dep,
                COALESCE("CRS_ARR_TIME", 0) AS crs_arr,
                COALESCE("ARR_TIME", 0) AS actual_arr,
                COALESCE("ELAPSED_TIME", 0) AS elapsed_time,
                COALESCE("ARR_DELAY", 0) AS arr_delay
            FROM flights {where_clause}
            ORDER BY "ARR_DELAY" DESC LIMIT 5
        """, params).df()

        for idx, row in delayed_df.iterrows():
            render_flight_card(row, is_delayed=True)

    # Temporal Heatmap & Vertical Delay Bar Drivers
    c_heat, c_delay = st.columns([1.3, 1])

    with c_heat:
        with st.container():
            st.subheader("Arrival Volume Heatmap")
            heat_dim = st.segmented_control("Perspective:", ["Month vs. Hour", "Day of Week vs. Hour"], default="Month vs. Hour")
            
            if heat_dim == "Month vs. Hour":
                heat_df = conn.execute(f"""
                    SELECT 
                        MONTH(TRY_CAST(CAST("FL_DATE" AS VARCHAR) AS DATE)) AS row_dim,
                        CAST("CRS_ARR_TIME" / 100 AS INT) AS hour,
                        COUNT(*) AS flights
                    FROM flights {where_clause}
                    GROUP BY row_dim, hour ORDER BY row_dim, hour
                """, params).df()
                y_label = "Month"
                month_names = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
                heat_df['row_dim'] = heat_df['row_dim'].map(month_names)
            else:
                heat_df = conn.execute(f"""
                    SELECT 
                        DAYOFWEEK(TRY_CAST(CAST("FL_DATE" AS VARCHAR) AS DATE)) AS row_dim,
                        CAST("CRS_ARR_TIME" / 100 AS INT) AS hour,
                        COUNT(*) AS flights
                    FROM flights {where_clause}
                    GROUP BY row_dim, hour ORDER BY row_dim, hour
                """, params).df()
                y_label = "Day of Week"
                day_names = {0:'Sun', 1:'Mon', 2:'Tue', 3:'Wed', 4:'Thu', 5:'Fri', 6:'Sat'}
                heat_df['row_dim'] = heat_df['row_dim'].map(day_names)

            pivot_heat = heat_df.pivot(index='row_dim', columns='hour', values='flights').fillna(0)
            
            # Heatmap implementation
            fig_heat = px.imshow(
                pivot_heat, 
                labels=dict(x="Hour of Day (24h)", y=y_label, color="Flights"),
                color_continuous_scale="Blues"
            )
            # Add cell borders via trace update
            fig_heat.update_traces(xgap=2, ygap=2)
            fig_heat = apply_white_chart_theme(fig_heat)
            fig_heat.update_layout(height=300, margin=dict(l=10, r=10, t=25, b=10))
            st.plotly_chart(fig_heat, use_container_width=True)

    with c_delay:
        with st.container():
            st.subheader("Arrival Delay Drivers")
            delay_df = conn.execute(f"""
                SELECT 
                    AVG("DELAY_DUE_CARRIER") AS Carrier,
                    AVG("DELAY_DUE_WEATHER") AS Weather,
                    AVG("DELAY_DUE_NAS") AS NAS,
                    AVG("DELAY_DUE_SECURITY") AS Security,
                    AVG("DELAY_DUE_LATE_AIRCRAFT") AS "Late Aircraft"
                FROM flights {where_clause}
            """, params).df()
            
            delay_data = delay_df.iloc[0].fillna(0).reset_index()
            delay_data.columns = ['Driver', 'Avg_Minutes']
            delay_data = delay_data.sort_values(by='Avg_Minutes', ascending=False)

            fig_delay_bar = px.bar(
                delay_data,
                x='Driver',
                y='Avg_Minutes',
                title="Avg Delay Contribution (Minutes)",
                text_auto='.1f'
            )
            fig_delay_bar.update_traces(marker_color='#0066CC')
            fig_delay_bar = apply_white_chart_theme(fig_delay_bar)
            fig_delay_bar.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=35, b=10),
                xaxis=dict(title=""),
                yaxis=dict(title="Minutes")
            )
            st.plotly_chart(fig_delay_bar, use_container_width=True)

    # Flight Records Inspector Table
    with st.container():
        st.subheader("📋 Inbound Flight Records Table")
        table_df = conn.execute(f"""
            SELECT "FL_DATE", "AIRLINE_CODE", "FL_NUMBER", "ORIGIN", "ARR_DELAY", "CANCELLED", "DISTANCE"
            FROM flights {where_clause}
            ORDER BY "FL_DATE" DESC LIMIT 100
        """, params).df()
        st.dataframe(table_df, use_container_width=True, height=280)

# ==================== OTHER PAGES ====================
elif page == "Departures Intelligence":
    st.title("🛫 ORD Departures Intelligence")
    st.info("Departures Analytics Dashboard")

elif page == "Flight Deep-Dive":
    st.title("🔍 Individual Flight Inspector")
    st.info("Flight Analysis Engine")
