import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import urllib.request
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder

# Page Configuration
st.set_page_config(
    page_title="Chicago O'Hare (ORD) Flight Intelligence",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def safe_int(val, default=0):
    if pd.isna(val) or val is None:
        return default
    return int(val)

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

# Compact Styling CSS
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 100% !important;
    }

    .stApp { background-color: #F8FAFC !important; }

    /* Single source of truth for the "card" look. Every st.container(border=True)
       gets exactly ONE border, whether it sits at the page level or inside a
       st.columns() cell. Do NOT add any other rule elsewhere that also puts a
       border/box-shadow on a stColumn's child div - that's what caused the
       double-border effect previously. */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
        border: 1px solid #CBD5E1 !important;
        padding: 8px 12px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
        margin-bottom: 6px !important;
    }

    /* Plain (non-bordered) columns, e.g. the KPI strip, still get a light card
       treatment - but only when they don't already contain a bordered
       container, so nothing is ever double-boxed. */
    div[data-testid="stColumn"] > div:not(:has(div[data-testid="stVerticalBlockBorderWrapper"])) {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        padding: 6px 4px 2px 4px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
    }

    div[data-testid="stSegmentedControl"] {
        background-color: #F1F5F9 !important;
        border-radius: 6px !important;
        padding: 2px !important;
        margin-bottom: 4px !important;
    }

    div[data-testid="stDataFrame"], 
    div[data-testid="stDataFrame"] > div,
    div[data-testid="stDataFrame"] iframe {
        background-color: #FFFFFF !important;
        border-radius: 6px !important;
    }

    .flight-clean-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 6px 10px;
        margin-bottom: 6px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .flight-clean-card.delayed { border-left: 4px solid #D00000; }
    .flight-clean-card.normal { border-left: 4px solid #0066CC; }
    .flight-code-title { font-size: 0.85rem; font-weight: 700; color: #0F172A; }
    .flight-sub-info { font-size: 0.72rem; color: #64748B; }
    .flight-badge-status { font-size: 0.75rem; font-weight: 700; padding: 2px 6px; border-radius: 4px; text-align: right; }
    .badge-delay { background-color: #FEF2F2; color: #D00000; }
    .badge-normal { background-color: #F0FDF4; color: #10B981; }

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
        title=dict(font=dict(color="#0f172a", size=14, weight="bold")),
        xaxis=dict(title=dict(font=dict(color="#0f172a")), tickfont=dict(color="#0f172a"), gridcolor="#f1f5f9"),
        yaxis=dict(title=dict(font=dict(color="#0f172a")), tickfont=dict(color="#0f172a"), gridcolor="#f1f5f9"),
        legend=dict(font=dict(color="#0f172a"))
    )
    return fig

def create_monthly_kpi_chart(data, x_col, y_col, bar_color="#0066CC"):
    data = data.copy()
    month_map = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
    data['month_code'] = data[x_col].map(month_map)
    
    fig = px.bar(data, x='month_code', y=y_col)
    fig.update_traces(marker_color=bar_color, opacity=0.9, hovertemplate="%{x}: %{y:,.1f}<extra></extra>")
    fig.update_layout(
        margin=dict(l=2, r=2, t=4, b=22),
        height=80,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        xaxis=dict(
            visible=True, type='category', categoryorder='array',
            categoryarray=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            tickfont=dict(size=8, color='#475569'), showgrid=False, zeroline=False, fixedrange=True, title="", showline=False
        ),
        yaxis=dict(visible=False, showgrid=False, fixedrange=True, autorange=True)
    )
    return fig

def create_3d_flight_map(conn, mode="ARRIVALS"):
    if mode == "ARRIVALS":
        query = "SELECT \"ORIGIN\" AS airport, COUNT(*) AS flight_count FROM flights WHERE UPPER(\"DEST\") = 'ORD' GROUP BY \"ORIGIN\" ORDER BY flight_count DESC"
        title = "🌐 Dynamic Inbound Route Globe"
    else:
        query = "SELECT \"DEST\" AS airport, COUNT(*) AS flight_count FROM flights WHERE UPPER(\"ORIGIN\") = 'ORD' GROUP BY \"DEST\" ORDER BY flight_count DESC"
        title = "🌐 Dynamic Outbound Route Globe"

    routes_df = conn.execute(query).df()
    airport_coords = load_airport_coordinates()
    ord_lat, ord_lon = airport_coords['ORD']
    fig = go.Figure()

    for _, row in routes_df.iterrows():
        apt = row['airport']
        count = row['flight_count']
        apt_lat, apt_lon = airport_coords.get(apt, (39.8283, -98.5795))
        
        lons = [apt_lon, ord_lon] if mode == "ARRIVALS" else [ord_lon, apt_lon]
        lats = [apt_lat, ord_lat] if mode == "ARRIVALS" else [ord_lat, apt_lat]
        text_lbl = f"{apt} ➔ ORD ({count:,} flights)" if mode == "ARRIVALS" else f"ORD ➔ {apt} ({count:,} flights)"

        fig.add_trace(go.Scattergeo(
            locationmode='USA-states', lon=lons, lat=lats, mode='lines+markers',
            line=dict(width=1.5, color='#38BDF8'), opacity=0.6, hoverinfo='text',
            text=text_lbl, showlegend=False
        ))

    fig.add_trace(go.Scattergeo(
        lon=[ord_lon], lat=[ord_lat], mode='markers+text',
        marker=dict(size=10, color='#F87171', symbol='circle'), text=['ORD'],
        textposition='top center', showlegend=False
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#0f172a")),
        geo=dict(
            scope='north america', projection_type='orthographic',
            showland=True, landcolor="#1E293B", showocean=True, oceancolor="#0F172A",
            countrycolor="#475569", coastlinecolor="#475569", showlakes=True, lakecolor="#0F172A",
            bgcolor="#FFFFFF", center=dict(lat=38.0, lon=-97.0), projection_scale=1.15
        ),
        margin=dict(l=0, r=0, t=30, b=0), height=320, paper_bgcolor="#FFFFFF"
    )
    return fig

def create_airline_connectivity_barchart(conn, mode="ARRIVALS"):
    try:
        raw_df = conn.execute("SELECT * FROM flights LIMIT 10000").df()
        raw_df.columns = [c.upper() for c in raw_df.columns]
        
        airline_col = 'AIRLINE_CODE' if 'AIRLINE_CODE' in raw_df.columns else ('AIRLINE' if 'AIRLINE' in raw_df.columns else None)
        target_col = 'ORIGIN' if mode == "ARRIVALS" else 'DEST'
        filter_col = 'DEST' if mode == "ARRIVALS" else 'ORIGIN'

        if airline_col and target_col and filter_col in raw_df.columns:
            filtered_df = raw_df[raw_df[filter_col].str.upper() == 'ORD']
            df = filtered_df.groupby(airline_col).agg(
                unique_routes=(target_col, 'nunique'),
                total_flights=(target_col, 'count')
            ).reset_index()

            df = df.rename(columns={airline_col: 'airline'})
            df = df.sort_values(by=['unique_routes', 'total_flights'], ascending=[False, False]).head(10)
        else:
            df = pd.DataFrame()
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No connectivity data available", showarrow=False)
        return fig

    df['airline_name'] = df['airline'].apply(lambda x: f"{x} ({AIRLINE_NAMES.get(str(x), 'Carrier')})")
    x_title = "Connected Origin Airports" if mode == "ARRIVALS" else "Connected Destination Airports"

    fig = px.bar(df, y='airline_name', x='unique_routes', orientation='h', text='unique_routes')
    fig.update_traces(marker_color='#0066CC', textposition='outside', hovertemplate="<b>%{y}</b><br>Connected Hubs: %{x}<extra></extra>")
    fig = apply_white_chart_theme(fig)
    fig.update_layout(
        title=dict(text=f"✈️ Top 10 Airlines by Hub Connectivity ({mode.title()})", font=dict(size=14, color="#0F172A")),
        yaxis=dict(autorange="reversed", title=""), xaxis=dict(title=x_title), height=380, margin=dict(l=10, r=30, t=40, b=10)
    )
    return fig

def create_airline_radar_chart(conn, selected_airline_code=None, mode="ARRIVALS"):
    try:
        df_raw = conn.execute("SELECT * FROM flights").df()
        df_raw.columns = [c.upper() for c in df_raw.columns]

        airline_col = None
        for col in ['AIRLINE_CODE', 'AIRLINE', 'OP_UNIQUE_CARRIER', 'CARRIER']:
            if col in df_raw.columns:
                airline_col = col
                break

        if not airline_col:
            fig = go.Figure()
            fig.add_annotation(text="Airline column not found", showarrow=False)
            return fig

        filter_col = 'DEST' if mode == "ARRIVALS" else 'ORIGIN'
        delay_col_name = 'ARR_DELAY' if mode == "ARRIVALS" else 'DEP_DELAY'

        if filter_col in df_raw.columns:
            df_ord = df_raw[df_raw[filter_col].astype(str).str.upper() == 'ORD'].copy()
        else:
            df_ord = df_raw.copy()

        df_ord = df_ord.dropna(subset=[airline_col])
        if df_ord.empty:
            fig = go.Figure()
            fig.add_annotation(text="No flight data found", showarrow=False)
            return fig

        delay_series = df_ord[delay_col_name] if delay_col_name in df_ord.columns else pd.Series(0, index=df_ord.index)
        cancelled_series = df_ord['CANCELLED'] if 'CANCELLED' in df_ord.columns else pd.Series(0, index=df_ord.index)

        df_ord['is_ontime'] = (delay_series <= 15).astype(int)
        df_ord['pos_delay'] = delay_series.apply(lambda x: x if pd.notna(x) and x > 0 else 0)
        df_ord['is_cancelled'] = (cancelled_series == 1).astype(int)

        all_stats = df_ord.groupby(airline_col).agg(
            total_flights=(airline_col, 'count'),
            on_time_pct=('is_ontime', lambda x: round(x.mean() * 100, 2)),
            avg_delay=('pos_delay', lambda x: round(x.mean(), 2)),
            cancellation_rate=('is_cancelled', lambda x: round(x.mean() * 100, 2))
        ).reset_index()

        max_f, min_f = all_stats['total_flights'].max(), all_stats['total_flights'].min()
        all_stats['flights_score'] = all_stats['total_flights'].apply(
            lambda x: round(((x - min_f) / (max_f - min_f)) * 100, 2) if max_f > min_f else 100
        )

        if not selected_airline_code or selected_airline_code not in all_stats[airline_col].astype(str).values:
            selected_airline_code = all_stats.sort_values('total_flights', ascending=False).iloc[0][airline_col]

        row = all_stats[all_stats[airline_col].astype(str) == str(selected_airline_code)].iloc[0]

        total_flights = int(row['total_flights'])
        on_time_pct = float(row['on_time_pct'])
        avg_delay = float(row['avg_delay'])
        cancellation_rate = float(row['cancellation_rate'])
        flights_score = float(row['flights_score'])

    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Radar calculation error: {str(e)}", showarrow=False)
        return fig

    categories = ['Volume Score (0-100)', 'Cancellation Rate (%)', 'Avg Delay (mins)', 'On-Time %']
    r_values = [flights_score, cancellation_rate, avg_delay, on_time_pct]

    carrier_name = AIRLINE_NAMES.get(str(selected_airline_code), 'Carrier')
    airline_label = f"{selected_airline_code} ({carrier_name})"

    hover_text = (
        f"<b>{airline_label}</b><br>"
        f"Total Flights: {total_flights:,} (Relative Score: {flights_score}/100)<br>"
        f"Cancellation Rate: {cancellation_rate}%<br>"
        f"Avg Delay: {avg_delay} mins<br>"
        f"On-Time: {on_time_pct}%"
    )

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=r_values + [r_values[0]], theta=categories + [categories[0]],
        fill='toself', name=airline_label, hoverinfo='text', text=hover_text,
        line=dict(color='#0066CC', width=2), fillcolor='rgba(0, 102, 204, 0.25)'
    ))

    fig.update_layout(
        title=dict(text=f"🎯 {airline_label} Performance ({mode.title()})", font=dict(size=14, color="#0F172A")),
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], color="#64748B"), angularaxis=dict(color="#0F172A")),
        showlegend=False, height=320, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="#FFFFFF"
    )
    return fig

def render_flight_card_clean(row, is_delayed=False, mode="ARRIVALS"):
    apt_code = row['ORIGIN'] if mode == "ARRIVALS" else row['DEST']
    route_str = f"{apt_code} ➔ ORD" if mode == "ARRIVALS" else f"ORD ➔ {apt_code}"
    airline_code = row['AIRLINE_CODE']
    fl_number = row['FL_NUMBER']
    
    elapsed_time = safe_int(row['elapsed_time'])
    hours, mins = divmod(elapsed_time, 60)
    time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
    
    dep_time = format_time_str(row['crs_dep'])
    arr_time = format_time_str(row['actual_arr'])
    delay_val = safe_int(row['delay_val'])

    card_class = "delayed" if is_delayed else "normal"
    badge_class = "badge-delay" if is_delayed else "badge-normal"
    delay_text = f"+{delay_val}m" if delay_val > 0 else f"{delay_val}m"

    st.markdown(f"""
    <div class="flight-clean-card {card_class}">
        <div>
            <div class="flight-code-title">{airline_code} {fl_number} · {route_str}</div>
            <div class="flight-sub-info">Dep: {dep_time} | Arr: {arr_time} | Duration: {time_str}</div>
        </div>
        <div class="flight-badge-status {badge_class}">
            {delay_text if is_delayed else 'On-Time'}
        </div>
    </div>
    """, unsafe_allow_html=True)

# Advanced ML Engine Setup: Delay Severity Multi-class & Cancellation Classifier
@st.cache_resource
def train_enhanced_prediction_models(_conn):
    try:
        cols_df = _conn.execute("DESCRIBE flights").df()
        cols = [c.upper() for c in cols_df['column_name'].tolist()]
        
        air_col = 'AIRLINE_CODE' if 'AIRLINE_CODE' in cols else ('AIRLINE' if 'AIRLINE' in cols else 'OP_UNIQUE_CARRIER')
        dep_col = 'DEP_DELAY' if 'DEP_DELAY' in cols else ('ARR_DELAY' if 'ARR_DELAY' in cols else None)

        if not dep_col or air_col not in cols:
            return None, None, None, [], []

        df = _conn.execute(f"""
            SELECT 
                "{air_col}" AS AIRLINE_CODE, 
                "ORIGIN", 
                "DEST",
                MONTH(TRY_CAST(CAST("FL_DATE" AS VARCHAR) AS DATE)) AS month,
                CAST(COALESCE("CRS_DEP_TIME", 1200) / 100 AS INT) AS dep_hour,
                COALESCE("DISTANCE", 500) AS DISTANCE,
                COALESCE("{dep_col}", 0) AS delay_mins,
                COALESCE("CANCELLED", 0) AS is_cancelled
            FROM flights 
            WHERE "{air_col}" IS NOT NULL
            LIMIT 60000
        """).df()

        df = df.dropna(subset=['AIRLINE_CODE', 'ORIGIN', 'DEST'])
        if df.empty or len(df) < 100:
            return None, None, None, [], []

        df['AIRLINE_CODE'] = df['AIRLINE_CODE'].astype(str)
        df['ORIGIN'] = df['ORIGIN'].astype(str)
        df['DEST'] = df['DEST'].astype(str)
        df['month'] = df['month'].fillna(6).astype(int)
        df['dep_hour'] = df['dep_hour'].fillna(12).astype(int)
        df['DISTANCE'] = df['DISTANCE'].fillna(500).astype(float)

        # Classify Delay Tiers: 0=On-time/Minor (<15m), 1=Moderate (15-45m), 2=Severe (>45m)
        def get_severity(m):
            if m < 15:
                return 0
            elif m <= 45:
                return 1
            return 2

        df['delay_tier'] = df['delay_mins'].apply(get_severity)

        X = df[['AIRLINE_CODE', 'ORIGIN', 'DEST', 'month', 'dep_hour', 'DISTANCE']]
        y_severity = df['delay_tier'].values
        y_cancelled = df['is_cancelled'].astype(int).values

        encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        cat_encoded = encoder.fit_transform(X[['AIRLINE_CODE', 'ORIGIN', 'DEST']])
        num_features = X[['month', 'dep_hour', 'DISTANCE']].values
        X_final = np.hstack((cat_encoded, num_features))

        # Train Multi-Class Severity Classifier
        severity_model = RandomForestClassifier(n_estimators=40, max_depth=9, random_state=42)
        severity_model.fit(X_final, y_severity)

        # Train Binary Cancellation Risk Model
        cancel_model = RandomForestClassifier(n_estimators=30, max_depth=7, random_state=42)
        cancel_model.fit(X_final, y_cancelled)

        origins = sorted(df['ORIGIN'].unique().tolist())
        dests = sorted(df['DEST'].unique().tolist())

        return severity_model, cancel_model, encoder, origins, dests
    except Exception:
        return None, None, None, [], []

# Sidebar Controls
st.sidebar.title("✈️ ORD Analytics")
st.sidebar.caption("Chicago O'Hare International Airport")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigation", ["Arrivals Intelligence", "Departures Intelligence", "🔮 Delay Predictor", "Flight Deep-Dive"])

st.sidebar.markdown("---")
st.sidebar.subheader("Filter Data")

try:
    cols_df = conn.execute("DESCRIBE flights").df()
    cols = [c.upper() for c in cols_df['column_name'].tolist()]
    airline_col_name = 'AIRLINE_CODE' if 'AIRLINE_CODE' in cols else ('AIRLINE' if 'AIRLINE' in cols else 'OP_UNIQUE_CARRIER')
    airlines = conn.execute(f'SELECT DISTINCT "{airline_col_name}" FROM flights WHERE "{airline_col_name}" IS NOT NULL ORDER BY 1').df().iloc[:, 0].dropna().astype(str).tolist()
except Exception:
    airlines = []

selected_airline = st.sidebar.multiselect("Select Airline", options=airlines, default=[], help="Leave empty to include all airlines")

if selected_airline:
    st.sidebar.caption(f"Filtering {len(selected_airline)} of {len(airlines)} airlines")

# Base SQL Filters
where_arr = "WHERE UPPER(\"DEST\") = 'ORD'"
where_dep = "WHERE UPPER(\"ORIGIN\") = 'ORD'"
params_arr, params_dep = [], []

if selected_airline:
    placeholders = ", ".join(["?"] * len(selected_airline))
    where_arr += f" AND \"{airline_col_name}\" IN ({placeholders})"
    where_dep += f" AND \"{airline_col_name}\" IN ({placeholders})"
    params_arr.extend(selected_airline)
    params_dep.extend(selected_airline)

# ==================== ARRIVALS INTELLIGENCE PAGE ====================
if page == "Arrivals Intelligence":
    st.title("🛬 ORD Arrivals Intelligence")
    st.caption("2022 Operational Performance & Inbound Route Analytics")
    
    kpi_df = conn.execute(f"""
        SELECT COUNT(*) AS total_flights,
            AVG(CASE WHEN "ARR_DELAY" <= 15 THEN 1 ELSE 0 END) * 100 AS on_time_pct,
            AVG("ARR_DELAY") AS avg_delay, SUM("CANCELLED") AS total_cancelled, SUM("DIVERTED") AS total_diverted
        FROM flights {where_arr}
    """, params_arr).df()
    total_flights, on_time_pct, avg_delay, total_cancelled, total_diverted = kpi_df.iloc[0]

    monthly_trend = conn.execute(f"""
        SELECT MONTH(TRY_CAST(CAST("FL_DATE" AS VARCHAR) AS DATE)) AS month,
            COUNT(*) AS flights, AVG("ARR_DELAY") AS delay,
            AVG(CASE WHEN "ARR_DELAY" <= 15 THEN 1 ELSE 0 END) * 100 AS on_time,
            SUM("CANCELLED") AS cancelled, SUM("DIVERTED") AS diverted
        FROM flights {where_arr} GROUP BY month HAVING month IS NOT NULL ORDER BY month
    """, params_arr).df()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"<div style='text-align: center;'><div style='font-size: 0.72rem; font-weight: 700; color: #475569;'>TOTAL ARRIVALS</div><div style='font-size: 1.3rem; font-weight: 800; color: #0A192F;'>{safe_int(total_flights):,}</div></div>", unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'flights', '#0066CC'), width='stretch', config={'displayModeBar': False})
    with c2:
        st.markdown(f"<div style='text-align: center;'><div style='font-size: 0.72rem; font-weight: 700; color: #475569;'>ON-TIME % (≤15M)</div><div style='font-size: 1.3rem; font-weight: 800; color: #10B981;'>{(on_time_pct or 0):.1f}%</div></div>", unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'on_time', '#10B981'), width='stretch', config={'displayModeBar': False})
    with c3:
        st.markdown(f"<div style='text-align: center;'><div style='font-size: 0.72rem; font-weight: 700; color: #475569;'>AVG DELAY</div><div style='font-size: 1.3rem; font-weight: 800; color: #D00000;'>{(avg_delay or 0):.1f}m</div></div>", unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'delay', '#D00000'), width='stretch', config={'displayModeBar': False})
    with c4:
        st.markdown(f"<div style='text-align: center;'><div style='font-size: 0.72rem; font-weight: 700; color: #475569;'>CANCELLED</div><div style='font-size: 1.3rem; font-weight: 800; color: #0A192F;'>{safe_int(total_cancelled):,}</div></div>", unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'cancelled', '#64748B'), width='stretch', config={'displayModeBar': False})
    with c5:
        st.markdown(f"<div style='text-align: center;'><div style='font-size: 0.72rem; font-weight: 700; color: #475569;'>DIVERTED</div><div style='font-size: 1.3rem; font-weight: 800; color: #0A192F;'>{safe_int(total_diverted):,}</div></div>", unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'diverted', '#38BDF8'), width='stretch', config={'displayModeBar': False})

    col_left, col_right = st.columns([1, 1])
    with col_left:
        with st.container(border=True):
            measure = st.segmented_control("Arrival Metric Select", ["Flights Count", "On-Time %", "Cancellations", "Avg Delay (min)"], default="Avg Delay (min)", label_visibility="collapsed")
            measure_map = {
                "Flights Count": ("COUNT(*)", "DESC"),
                "On-Time %": ('AVG(CASE WHEN "ARR_DELAY" <= 15 THEN 1 ELSE 0 END) * 100', "DESC"),
                "Cancellations": ('SUM("CANCELLED")', "DESC"),
                "Avg Delay (min)": ('AVG("ARR_DELAY")', "DESC")
            }
            sql_val, sql_ord = measure_map[measure]

            origins_df = conn.execute(f'SELECT "ORIGIN" AS code, {sql_val} AS val FROM flights {where_arr} GROUP BY code ORDER BY val {sql_ord} LIMIT 10', params_arr).df()
            origins_df['full_label'] = origins_df['code'].apply(lambda x: f"{x} ({AIRPORT_CITY_NAMES.get(x, 'Origin')})")

            fig_orig = px.bar(origins_df, y='full_label', x='val', orientation='h', title=f"Top 10 Origin Destinations by {measure}", text_auto='.1f' if 'Delay' in measure or 'Time' in measure else True)
            fig_orig.update_traces(marker_color="#0066CC", textposition="outside")
            fig_orig = apply_white_chart_theme(fig_orig)
            fig_orig.update_layout(yaxis=dict(autorange="reversed", title=""), xaxis=dict(title=measure), margin=dict(l=10, r=25, t=35, b=10), height=320)
            st.plotly_chart(fig_orig, width='stretch')

            airlines_df = conn.execute(f'SELECT "{airline_col_name}" AS code, {sql_val} AS val FROM flights {where_arr} GROUP BY code ORDER BY val {sql_ord} LIMIT 10', params_arr).df()
            airlines_df['full_label'] = airlines_df['code'].apply(lambda x: f"{x} ({AIRLINE_NAMES.get(str(x), 'Carrier')})")

            fig_air = px.bar(airlines_df, y='full_label', x='val', orientation='h', title=f"Top 10 Airlines by {measure}", text_auto='.1f' if 'Delay' in measure or 'Time' in measure else True)
            fig_air.update_traces(marker_color="#0066CC", textposition="outside")
            fig_air = apply_white_chart_theme(fig_air)
            fig_air.update_layout(yaxis=dict(autorange="reversed", title=""), xaxis=dict(title=measure), margin=dict(l=10, r=25, t=35, b=10), height=320)
            st.plotly_chart(fig_air, width='stretch')

    with col_right:
        with st.container(border=True):
            st.plotly_chart(create_3d_flight_map(conn, mode="ARRIVALS"), width='stretch')
        with st.container(border=True):
            st.plotly_chart(create_airline_connectivity_barchart(conn, mode="ARRIVALS"), width='stretch')

    col_longest, col_delayed = st.columns(2)
    with col_longest:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color: #0F172A; margin-bottom: 8px;'>✈️ Top 5 Longest Inbound Routes</div>", unsafe_allow_html=True)
            longest_df = conn.execute(f'SELECT "FL_NUMBER", "{airline_col_name}" AS AIRLINE_CODE, "ORIGIN", "FL_DATE", COALESCE("CRS_DEP_TIME", 0) AS crs_dep, COALESCE("ARR_TIME", 0) AS actual_arr, COALESCE("ELAPSED_TIME", 0) AS elapsed_time, COALESCE("ARR_DELAY", 0) AS delay_val FROM flights {where_arr} ORDER BY "ELAPSED_TIME" DESC LIMIT 5', params_arr).df()
            for _, row in longest_df.iterrows():
                render_flight_card_clean(row, is_delayed=False, mode="ARRIVALS")

    with col_delayed:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color: #0F172A; margin-bottom: 8px;'>⚠️ Top 5 Most Delayed Inbound Flights</div>", unsafe_allow_html=True)
            delayed_df = conn.execute(f'SELECT "FL_NUMBER", "{airline_col_name}" AS AIRLINE_CODE, "ORIGIN", "FL_DATE", COALESCE("CRS_DEP_TIME", 0) AS crs_dep, COALESCE("ARR_TIME", 0) AS actual_arr, COALESCE("ELAPSED_TIME", 0) AS elapsed_time, COALESCE("ARR_DELAY", 0) AS delay_val FROM flights {where_arr} ORDER BY "ARR_DELAY" DESC LIMIT 5', params_arr).df()
            for _, row in delayed_df.iterrows():
                render_flight_card_clean(row, is_delayed=True, mode="ARRIVALS")

    c_heat, c_delay = st.columns([1.3, 1])
    with c_heat:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color: #0F172A; margin-bottom: 6px;'>Arrival Volume Heatmap</div>", unsafe_allow_html=True)
            heat_dim = st.segmented_control("Heatmap Grouping Select", ["Month vs. Hour", "Day of Week vs. Hour"], default="Month vs. Hour", label_visibility="collapsed")
            if heat_dim == "Month vs. Hour":
                heat_df = conn.execute(f'SELECT MONTH(TRY_CAST(CAST("FL_DATE" AS VARCHAR) AS DATE)) AS row_dim, CAST("CRS_ARR_TIME" / 100 AS INT) AS hour, COUNT(*) AS flights FROM flights {where_arr} GROUP BY row_dim, hour ORDER BY row_dim, hour', params_arr).df()
                heat_df['row_dim'] = heat_df['row_dim'].map({1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'})
                y_label = "Month"
            else:
                heat_df = conn.execute(f'SELECT DAYOFWEEK(TRY_CAST(CAST("FL_DATE" AS VARCHAR) AS DATE)) AS row_dim, CAST("CRS_ARR_TIME" / 100 AS INT) AS hour, COUNT(*) AS flights FROM flights {where_arr} GROUP BY row_dim, hour ORDER BY row_dim, hour', params_arr).df()
                heat_df['row_dim'] = heat_df['row_dim'].map({0:'Sun', 1:'Mon', 2:'Tue', 3:'Wed', 4:'Thu', 5:'Fri', 6:'Sat'})
                y_label = "Day of Week"

            pivot_heat = heat_df.pivot(index='row_dim', columns='hour', values='flights').fillna(0)
            fig_heat = go.Figure(data=go.Heatmap(z=pivot_heat.values, x=pivot_heat.columns, y=pivot_heat.index, colorscale="Blues"))
            fig_heat = apply_white_chart_theme(fig_heat)
            fig_heat.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Hour of Day (24h)", yaxis_title=y_label)
            st.plotly_chart(fig_heat, width='stretch')

    with c_delay:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color: #0F172A; margin-bottom: 6px;'>Arrival Delay Drivers</div>", unsafe_allow_html=True)
            delay_df = conn.execute(f'SELECT AVG("DELAY_DUE_CARRIER") AS Carrier, AVG("DELAY_DUE_WEATHER") AS Weather, AVG("DELAY_DUE_NAS") AS NAS, AVG("DELAY_DUE_SECURITY") AS Security, AVG("DELAY_DUE_LATE_AIRCRAFT") AS "Late Aircraft" FROM flights {where_arr}', params_arr).df()
            delay_data = delay_df.iloc[0].fillna(0).reset_index()
            delay_data.columns = ['Driver', 'Avg_Minutes']
            delay_data = delay_data.sort_values(by='Avg_Minutes', ascending=False)

            fig_delay_bar = px.bar(delay_data, x='Driver', y='Avg_Minutes', title="Avg Delay Contribution (Minutes)", text_auto='.1f')
            fig_delay_bar.update_traces(marker_color='#0066CC', textposition='outside')
            fig_delay_bar = apply_white_chart_theme(fig_delay_bar)
            fig_delay_bar.update_layout(height=280, margin=dict(l=10, r=10, t=35, b=10), xaxis=dict(title=""), yaxis=dict(title="Minutes"))
            st.plotly_chart(fig_delay_bar, width='stretch')

    col_table, col_radar = st.columns([1.3, 1])
    with col_table:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color: #0F172A; margin-bottom: 8px;'>📋 Inbound Flight Records Table</div>", unsafe_allow_html=True)
            table_df = conn.execute(f'SELECT "FL_DATE", "{airline_col_name}" AS AIRLINE, "FL_NUMBER", "ORIGIN", "ARR_DELAY", "CANCELLED", "DISTANCE" FROM flights {where_arr} ORDER BY "FL_DATE" DESC LIMIT 100', params_arr).df()
            st.dataframe(table_df, width='stretch', height=290)

    with col_radar:
        with st.container(border=True):
            radar_airlines = airlines if airlines else ['UA', 'AA', 'DL', 'OO', 'MQ', 'YX']
            selected_radar_airline = st.selectbox("Filter Radar Airline:", options=radar_airlines, format_func=lambda x: f"{x} - {AIRLINE_NAMES.get(str(x), 'Carrier')}", key="radar_arr_selector")
            st.plotly_chart(create_airline_radar_chart(conn, selected_radar_airline, mode="ARRIVALS"), width='stretch')

# ==================== DEPARTURES INTELLIGENCE PAGE ====================
elif page == "Departures Intelligence":
    st.title("🛫 ORD Departures Intelligence")
    st.caption("2022 Operational Performance & Outbound Route Analytics")

    kpi_df = conn.execute(f"""
        SELECT COUNT(*) AS total_flights,
            AVG(CASE WHEN "DEP_DELAY" <= 15 THEN 1 ELSE 0 END) * 100 AS on_time_pct,
            AVG("DEP_DELAY") AS avg_delay, SUM("CANCELLED") AS total_cancelled, SUM("DIVERTED") AS total_diverted
        FROM flights {where_dep}
    """, params_dep).df()
    total_flights, on_time_pct, avg_delay, total_cancelled, total_diverted = kpi_df.iloc[0]

    monthly_trend = conn.execute(f"""
        SELECT MONTH(TRY_CAST(CAST("FL_DATE" AS VARCHAR) AS DATE)) AS month,
            COUNT(*) AS flights, AVG("DEP_DELAY") AS delay,
            AVG(CASE WHEN "DEP_DELAY" <= 15 THEN 1 ELSE 0 END) * 100 AS on_time,
            SUM("CANCELLED") AS cancelled, SUM("DIVERTED") AS diverted
        FROM flights {where_dep} GROUP BY month HAVING month IS NOT NULL ORDER BY month
    """, params_dep).df()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"<div style='text-align: center;'><div style='font-size: 0.72rem; font-weight: 700; color: #475569;'>TOTAL DEPARTURES</div><div style='font-size: 1.3rem; font-weight: 800; color: #0A192F;'>{safe_int(total_flights):,}</div></div>", unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'flights', '#0066CC'), width='stretch', config={'displayModeBar': False})
    with c2:
        st.markdown(f"<div style='text-align: center;'><div style='font-size: 0.72rem; font-weight: 700; color: #475569;'>ON-TIME % (≤15M)</div><div style='font-size: 1.3rem; font-weight: 800; color: #10B981;'>{(on_time_pct or 0):.1f}%</div></div>", unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'on_time', '#10B981'), width='stretch', config={'displayModeBar': False})
    with c3:
        st.markdown(f"<div style='text-align: center;'><div style='font-size: 0.72rem; font-weight: 700; color: #475569;'>AVG DELAY</div><div style='font-size: 1.3rem; font-weight: 800; color: #D00000;'>{(avg_delay or 0):.1f}m</div></div>", unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'delay', '#D00000'), width='stretch', config={'displayModeBar': False})
    with c4:
        st.markdown(f"<div style='text-align: center;'><div style='font-size: 0.72rem; font-weight: 700; color: #475569;'>CANCELLED</div><div style='font-size: 1.3rem; font-weight: 800; color: #0A192F;'>{safe_int(total_cancelled):,}</div></div>", unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'cancelled', '#64748B'), width='stretch', config={'displayModeBar': False})
    with c5:
        st.markdown(f"<div style='text-align: center;'><div style='font-size: 0.72rem; font-weight: 700; color: #475569;'>DIVERTED</div><div style='font-size: 1.3rem; font-weight: 800; color: #0A192F;'>{safe_int(total_diverted):,}</div></div>", unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'diverted', '#38BDF8'), width='stretch', config={'displayModeBar': False})

    col_left, col_right = st.columns([1, 1])
    with col_left:
        with st.container(border=True):
            measure = st.segmented_control("Departure Metric Select", ["Flights Count", "On-Time %", "Cancellations", "Avg Delay (min)"], default="Avg Delay (min)", key="dep_measure_seg", label_visibility="collapsed")
            measure_map = {
                "Flights Count": ("COUNT(*)", "DESC"),
                "On-Time %": ('AVG(CASE WHEN "DEP_DELAY" <= 15 THEN 1 ELSE 0 END) * 100', "DESC"),
                "Cancellations": ('SUM("CANCELLED")', "DESC"),
                "Avg Delay (min)": ('AVG("DEP_DELAY")', "DESC")
            }
            sql_val, sql_ord = measure_map[measure]

            dests_df = conn.execute(f'SELECT "DEST" AS code, {sql_val} AS val FROM flights {where_dep} GROUP BY code ORDER BY val {sql_ord} LIMIT 10', params_dep).df()
            dests_df['full_label'] = dests_df['code'].apply(lambda x: f"{x} ({AIRPORT_CITY_NAMES.get(x, 'Destination')})")

            fig_dest = px.bar(dests_df, y='full_label', x='val', orientation='h', title=f"Top 10 Destination Hubs by {measure}", text_auto='.1f' if 'Delay' in measure or 'Time' in measure else True)
            fig_dest.update_traces(marker_color="#0066CC", textposition="outside")
            fig_dest = apply_white_chart_theme(fig_dest)
            fig_dest.update_layout(yaxis=dict(autorange="reversed", title=""), xaxis=dict(title=measure), margin=dict(l=10, r=25, t=35, b=10), height=320)
            st.plotly_chart(fig_dest, width='stretch')

            airlines_df = conn.execute(f'SELECT "{airline_col_name}" AS code, {sql_val} AS val FROM flights {where_dep} GROUP BY code ORDER BY val {sql_ord} LIMIT 10', params_dep).df()
            airlines_df['full_label'] = airlines_df['code'].apply(lambda x: f"{x} ({AIRLINE_NAMES.get(str(x), 'Carrier')})")

            fig_air = px.bar(airlines_df, y='full_label', x='val', orientation='h', title=f"Top 10 Airlines by {measure}", text_auto='.1f' if 'Delay' in measure or 'Time' in measure else True)
            fig_air.update_traces(marker_color="#0066CC", textposition="outside")
            fig_air = apply_white_chart_theme(fig_air)
            fig_air.update_layout(yaxis=dict(autorange="reversed", title=""), xaxis=dict(title=measure), margin=dict(l=10, r=25, t=35, b=10), height=320)
            st.plotly_chart(fig_air, width='stretch')

    with col_right:
        with st.container(border=True):
            st.plotly_chart(create_3d_flight_map(conn, mode="DEPARTURES"), width='stretch')
        with st.container(border=True):
            st.plotly_chart(create_airline_connectivity_barchart(conn, mode="DEPARTURES"), width='stretch')

    col_longest, col_delayed = st.columns(2)
    with col_longest:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color: #0F172A; margin-bottom: 8px;'>✈️ Top 5 Longest Outbound Routes</div>", unsafe_allow_html=True)
            longest_df = conn.execute(f'SELECT "FL_NUMBER", "{airline_col_name}" AS AIRLINE_CODE, "DEST", "FL_DATE", COALESCE("CRS_DEP_TIME", 0) AS crs_dep, COALESCE("ARR_TIME", 0) AS actual_arr, COALESCE("ELAPSED_TIME", 0) AS elapsed_time, COALESCE("DEP_DELAY", 0) AS delay_val FROM flights {where_dep} ORDER BY "ELAPSED_TIME" DESC LIMIT 5', params_dep).df()
            for _, row in longest_df.iterrows():
                render_flight_card_clean(row, is_delayed=False, mode="DEPARTURES")

    with col_delayed:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color: #0F172A; margin-bottom: 8px;'>⚠️ Top 5 Most Delayed Outbound Flights</div>", unsafe_allow_html=True)
            delayed_df = conn.execute(f'SELECT "FL_NUMBER", "{airline_col_name}" AS AIRLINE_CODE, "DEST", "FL_DATE", COALESCE("CRS_DEP_TIME", 0) AS crs_dep, COALESCE("ARR_TIME", 0) AS actual_arr, COALESCE("ELAPSED_TIME", 0) AS elapsed_time, COALESCE("DEP_DELAY", 0) AS delay_val FROM flights {where_dep} ORDER BY "DEP_DELAY" DESC LIMIT 5', params_dep).df()
            for _, row in delayed_df.iterrows():
                render_flight_card_clean(row, is_delayed=True, mode="DEPARTURES")

    c_heat, c_delay = st.columns([1.3, 1])
    with c_heat:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color: #0F172A; margin-bottom: 6px;'>Departure Volume Heatmap</div>", unsafe_allow_html=True)
            heat_dim = st.segmented_control("Departure Heatmap Select", ["Month vs. Hour", "Day of Week vs. Hour"], default="Month vs. Hour", key="dep_heat_seg", label_visibility="collapsed")
            if heat_dim == "Month vs. Hour":
                heat_df = conn.execute(f'SELECT MONTH(TRY_CAST(CAST("FL_DATE" AS VARCHAR) AS DATE)) AS row_dim, CAST("CRS_DEP_TIME" / 100 AS INT) AS hour, COUNT(*) AS flights FROM flights {where_dep} GROUP BY row_dim, hour ORDER BY row_dim, hour', params_dep).df()
                heat_df['row_dim'] = heat_df['row_dim'].map({1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'})
                y_label = "Month"
            else:
                heat_df = conn.execute(f'SELECT DAYOFWEEK(TRY_CAST(CAST("FL_DATE" AS VARCHAR) AS DATE)) AS row_dim, CAST("CRS_DEP_TIME" / 100 AS INT) AS hour, COUNT(*) AS flights FROM flights {where_dep} GROUP BY row_dim, hour ORDER BY row_dim, hour', params_dep).df()
                heat_df['row_dim'] = heat_df['row_dim'].map({0:'Sun', 1:'Mon', 2:'Tue', 3:'Wed', 4:'Thu', 5:'Fri', 6:'Sat'})
                y_label = "Day of Week"

            pivot_heat = heat_df.pivot(index='row_dim', columns='hour', values='flights').fillna(0)
            fig_heat = go.Figure(data=go.Heatmap(z=pivot_heat.values, x=pivot_heat.columns, y=pivot_heat.index, colorscale="Blues"))
            fig_heat = apply_white_chart_theme(fig_heat)
            fig_heat.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Hour of Day (24h)", yaxis_title=y_label)
            st.plotly_chart(fig_heat, width='stretch')

    with c_delay:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color: #0F172A; margin-bottom: 6px;'>Departure Delay Drivers</div>", unsafe_allow_html=True)
            delay_df = conn.execute(f'SELECT AVG("DELAY_DUE_CARRIER") AS Carrier, AVG("DELAY_DUE_WEATHER") AS Weather, AVG("DELAY_DUE_NAS") AS NAS, AVG("DELAY_DUE_SECURITY") AS Security, AVG("DELAY_DUE_LATE_AIRCRAFT") AS "Late Aircraft" FROM flights {where_dep}', params_dep).df()
            delay_data = delay_df.iloc[0].fillna(0).reset_index()
            delay_data.columns = ['Driver', 'Avg_Minutes']
            delay_data = delay_data.sort_values(by='Avg_Minutes', ascending=False)

            fig_delay_bar = px.bar(delay_data, x='Driver', y='Avg_Minutes', title="Avg Delay Contribution (Minutes)", text_auto='.1f')
            fig_delay_bar.update_traces(marker_color='#0066CC', textposition='outside')
            fig_delay_bar = apply_white_chart_theme(fig_delay_bar)
            fig_delay_bar.update_layout(height=280, margin=dict(l=10, r=10, t=35, b=10), xaxis=dict(title=""), yaxis=dict(title="Minutes"))
            st.plotly_chart(fig_delay_bar, width='stretch')

    col_table, col_radar = st.columns([1.3, 1])
    with col_table:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color: #0F172A; margin-bottom: 8px;'>📋 Outbound Flight Records Table</div>", unsafe_allow_html=True)
            table_df = conn.execute(f'SELECT "FL_DATE", "{airline_col_name}" AS AIRLINE, "FL_NUMBER", "DEST", "DEP_DELAY", "CANCELLED", "DISTANCE" FROM flights {where_dep} ORDER BY "FL_DATE" DESC LIMIT 100', params_dep).df()
            st.dataframe(table_df, width='stretch', height=290)

    with col_radar:
        with st.container(border=True):
            radar_airlines = airlines if airlines else ['UA', 'AA', 'DL', 'OO', 'MQ', 'YX']
            selected_radar_airline = st.selectbox("Filter Radar Airline:", options=radar_airlines, format_func=lambda x: f"{x} - {AIRLINE_NAMES.get(str(x), 'Carrier')}", key="radar_dep_selector")
            st.plotly_chart(create_airline_radar_chart(conn, selected_radar_airline, mode="DEPARTURES"), width='stretch')

# ==================== DELAY PREDICTOR PAGE ====================
elif page == "🔮 Delay Predictor":
    st.title("🔮 Enhanced Machine Learning Intelligence")
    st.caption("Multi-tiered Delay Severity & Cancellation Risk Prediction Models.")

    severity_model, cancel_model, encoder, origins_list, dests_list = train_enhanced_prediction_models(conn)

    if not severity_model or not cancel_model or not encoder:
        st.warning("Prediction model requires sufficient historical data. Please ensure 'flights_2022.csv' contains valid records.")
    else:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color: #0F172A; margin-bottom: 12px;'>✈️ Configure Flight Parameters</div>", unsafe_allow_html=True)
            p1, p2, p3 = st.columns(3)
            
            airline_opts = airlines if airlines else list(AIRLINE_NAMES.keys())
            orig_opts = origins_list if origins_list else ['ORD', 'LAX', 'JFK', 'DFW']
            dest_opts = dests_list if dests_list else ['ORD', 'LAX', 'JFK', 'DFW']

            with p1:
                input_airline = st.selectbox("Select Airline", options=airline_opts, format_func=lambda x: f"{x} - {AIRLINE_NAMES.get(str(x), 'Carrier')}")
                input_month = st.slider("Flight Month", 1, 12, 6)
            with p2:
                input_origin = st.selectbox("Origin Airport", options=orig_opts, index=orig_opts.index('ORD') if 'ORD' in orig_opts else 0)
                input_hour = st.slider("Scheduled Departure Hour (24h)", 0, 23, 14)
            with p3:
                input_dest = st.selectbox("Destination Airport", options=dest_opts, index=dest_opts.index('LAX') if 'LAX' in dest_opts else 0)
                input_dist = st.number_input("Route Distance (miles)", min_value=100, max_value=5000, value=800, step=50)

            run_predict = st.button("Run Predictive Risk Analysis", type="primary", width='stretch')

        if run_predict:
            try:
                cat_input = pd.DataFrame([[str(input_airline), str(input_origin), str(input_dest)]], columns=['AIRLINE_CODE', 'ORIGIN', 'DEST'])
                cat_encoded = encoder.transform(cat_input)
                num_features = np.array([[int(input_month), int(input_hour), float(input_dist)]])
                full_input = np.hstack((cat_encoded, num_features))

                # Predictions
                sev_probs = severity_model.predict_proba(full_input)[0]  # [On-time/Minor, Moderate, Severe]
                cancel_prob = cancel_model.predict_proba(full_input)[0][1] * 100

                pct_ontime = sev_probs[0] * 100
                pct_moderate = sev_probs[1] * 100
                pct_severe = sev_probs[2] * 100
                total_delay_prob = (sev_probs[1] + sev_probs[2]) * 100

                st.markdown("---")
                
                # Risk Gauges
                m1, m2, m3 = st.columns(3)
                with m1:
                    with st.container(border=True):
                        st.markdown("<div style='font-size: 0.8rem; font-weight:700; color:#475569;'>OVERALL DELAY PROBABILITY</div>", unsafe_allow_html=True)
                        if total_delay_prob > 35:
                            st.error(f"⚠️ **{total_delay_prob:.1f}% Risk**")
                        else:
                            st.success(f"✅ **{total_delay_prob:.1f}% Risk**")
                        st.progress(min(int(total_delay_prob), 100))

                with m2:
                    with st.container(border=True):
                        st.markdown("<div style='font-size: 0.8rem; font-weight:700; color:#475569;'>CANCELLATION RISK</div>", unsafe_allow_html=True)
                        if cancel_prob > 5:
                            st.warning(f"🚨 **{cancel_prob:.1f}% Probability**")
                        else:
                            st.info(f"🟢 **{cancel_prob:.1f}% Probability**")
                        st.progress(min(int(cancel_prob * 5), 100)) # Scale for visual visibility

                with m3:
                    with st.container(border=True):
                        st.markdown("<div style='font-size: 0.8rem; font-weight:700; color:#475569;'>PREDICTED DELAY SEVERITY</div>", unsafe_allow_html=True)
                        if pct_severe > 20:
                            st.markdown("<span style='color:#D00000; font-weight:800; font-size:1.1rem;'>High Severe Delay Risk (>45m)</span>", unsafe_allow_html=True)
                        elif pct_moderate > 25:
                            st.markdown("<span style='color:#D97706; font-weight:800; font-size:1.1rem;'>Moderate Delay Likely (15-45m)</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("<span style='color:#10B981; font-weight:800; font-size:1.1rem;'>On-Time / Minor Delay</span>", unsafe_allow_html=True)

                # Severity Breakdown Chart
                with st.container(border=True):
                    st.markdown("##### 📊 Delay Severity Tier Distribution")
                    tier_df = pd.DataFrame({
                        'Tier': ['On-Time / Minor (<15m)', 'Moderate Delay (15-45m)', 'Severe Delay (>45m)'],
                        'Probability': [pct_ontime, pct_moderate, pct_severe]
                    })
                    fig_tier = px.bar(tier_df, x='Tier', y='Probability', color='Tier',
                                      color_discrete_map={'On-Time / Minor (<15m)': '#10B981', 'Moderate Delay (15-45m)': '#F59E0B', 'Severe Delay (>45m)': '#EF4444'},
                                      text_auto='.1f')
                    fig_tier = apply_white_chart_theme(fig_tier)
                    fig_tier.update_layout(height=240, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="Probability (%)", showlegend=False)
                    st.plotly_chart(fig_tier, width='stretch')

            except Exception as e:
                st.error(f"Prediction failed: {str(e)}")

# ==================== FLIGHT DEEP-DIVE PAGE ====================
elif page == "Flight Deep-Dive":
    st.title("🔍 Route Pair Deep-Dive & Carrier Analytics")
    st.caption("Detailed Operational Benchmarking using Available Historical Records")

    # Route Pair Selectors
    with st.container(border=True):
        st.markdown("<div style='font-weight: 700; color: #0F172A; margin-bottom: 8px;'>🎯 Select Flight Corridor</div>", unsafe_allow_html=True)
        rc1, rc2 = st.columns(2)
        with rc1:
            all_origins = conn.execute("SELECT DISTINCT \"ORIGIN\" FROM flights WHERE \"ORIGIN\" IS NOT NULL ORDER BY 1").df().iloc[:, 0].tolist()
            selected_orig = st.selectbox("Origin Airport", options=all_origins, index=all_origins.index('ORD') if 'ORD' in all_origins else 0)
        with rc2:
            all_dests = conn.execute("SELECT DISTINCT \"DEST\" FROM flights WHERE \"DEST\" IS NOT NULL ORDER BY 1").df().iloc[:, 0].tolist()
            selected_dest = st.selectbox("Destination Airport", options=all_dests, index=all_dests.index('LAX') if 'LAX' in all_dests else 0)

    # Route Data Query
    route_df = conn.execute("""
        SELECT * FROM flights 
        WHERE UPPER("ORIGIN") = ? AND UPPER("DEST") = ?
    """, [selected_orig.upper(), selected_dest.upper()]).df()

    if route_df.empty:
        st.warning(f"No direct flight records found for route: **{selected_orig} ➔ {selected_dest}**")
    else:
        route_df.columns = [c.upper() for c in route_df.columns]
        airline_col = 'AIRLINE_CODE' if 'AIRLINE_CODE' in route_df.columns else ('AIRLINE' if 'AIRLINE' in route_df.columns else 'OP_UNIQUE_CARRIER')
        
        # Route Overview KPIs
        k1, k2, k3, k4 = st.columns(4)
        total_route_flights = len(route_df)
        avg_dep_delay = route_df['DEP_DELAY'].mean() if 'DEP_DELAY' in route_df.columns else 0
        ontime_rate = ((route_df['ARR_DELAY'] <= 15).mean() * 100) if 'ARR_DELAY' in route_df.columns else 0
        cancel_rate = (route_df['CANCELLED'].mean() * 100) if 'CANCELLED' in route_df.columns else 0

        with k1:
            st.metric("Total Route Flights", f"{total_route_flights:,}")
        with k2:
            st.metric("Avg Departure Delay", f"{avg_dep_delay:.1f} mins")
        with k3:
            st.metric("On-Time Arrival %", f"{ontime_rate:.1f}%")
        with k4:
            st.metric("Cancellation Rate", f"{cancel_rate:.1f}%")

        # Visual Row 1: Carrier Head-to-Head & Best Departure Hour
        c_carrier, c_hour = st.columns(2)
        with c_carrier:
            with st.container(border=True):
                st.markdown(f"##### ✈️ Carrier Reliability on {selected_orig} ➔ {selected_dest}")
                carrier_stats = route_df.groupby(airline_col).agg(
                    Flights=(airline_col, 'count'),
                    Avg_Delay=('ARR_DELAY', lambda x: round(x.mean(), 1)),
                    OnTime_Pct=('ARR_DELAY', lambda x: round((x <= 15).mean() * 100, 1))
                ).reset_index()
                carrier_stats['Carrier_Name'] = carrier_stats[airline_col].apply(lambda x: f"{x} ({AIRLINE_NAMES.get(str(x), 'Airline')})")
                
                fig_carrier = px.bar(carrier_stats, x='Carrier_Name', y='Avg_Delay', color='OnTime_Pct',
                                     color_continuous_scale='RdYlGn', text_auto=True,
                                     title="Avg Delay (Mins) & On-Time % Color Scale")
                fig_carrier = apply_white_chart_theme(fig_carrier)
                fig_carrier.update_layout(height=290, margin=dict(l=10, r=10, t=35, b=10), xaxis_title="")
                st.plotly_chart(fig_carrier, width='stretch')

        with c_hour:
            with st.container(border=True):
                st.markdown(f"##### ⏰ Optimal Flight Departure Time Windows")
                route_df['dep_hour'] = (route_df['CRS_DEP_TIME'] // 100).fillna(12).astype(int)
                hourly_stats = route_df.groupby('dep_hour').agg(
                    Avg_Delay=('DEP_DELAY', 'mean'),
                    Flights=('dep_hour', 'count')
                ).reset_index()
                
                fig_hour = px.line(hourly_stats, x='dep_hour', y='Avg_Delay', markers=True,
                                   title="Departure Delay Trend by Hour of Day (24h)")
                fig_hour.update_traces(line_color='#0066CC', line_width=3)
                fig_hour = apply_white_chart_theme(fig_hour)
                fig_hour.update_layout(height=290, margin=dict(l=10, r=10, t=35, b=10), xaxis_title="Scheduled Hour", yaxis_title="Avg Delay (min)")
                st.plotly_chart(fig_hour, width='stretch')

        # Visual Row 2: Delay Root Causes for Selected Route
        with st.container(border=True):
            st.markdown(f"##### 🩺 Operational Breakdown & Root Delay Causes for {selected_orig} ➔ {selected_dest}")
            delay_cols = ['DELAY_DUE_CARRIER', 'DELAY_DUE_WEATHER', 'DELAY_DUE_NAS', 'DELAY_DUE_SECURITY', 'DELAY_DUE_LATE_AIRCRAFT']
            existing_delays = [c for c in delay_cols if c in route_df.columns]
            
            if existing_delays:
                route_delay_sums = route_df[existing_delays].sum().reset_index()
                route_delay_sums.columns = ['Cause', 'Total_Minutes']
                route_delay_sums['Cause'] = route_delay_sums['Cause'].str.replace('DELAY_DUE_', '').str.title()
                
                fig_causes = px.pie(route_delay_sums, values='Total_Minutes', names='Cause', hole=0.4,
                                    color_discrete_sequence=px.colors.qualitative.Set2)
                fig_causes = apply_white_chart_theme(fig_causes)
                fig_causes.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_causes, width='stretch')
            else:
                st.info("Delay cause breakdown columns not available in dataset.")
