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

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
        border: 1px solid #CBD5E1 !important;
        padding: 8px 12px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
        margin-bottom: 6px !important;
    }

    div[data-testid="stColumn"] div[data-testid="stVerticalBlockBorderWrapper"] {
        border: none !important;
        box-shadow: none !important;
        padding: 0px !important;
    }

    div[data-testid="stColumn"] > div {
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
            visible=True,
            type='category',
            categoryorder='array',
            categoryarray=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            tickfont=dict(size=8, color='#475569'),
            showgrid=False, zeroline=False, fixedrange=True, title="", showline=False
        ),
        yaxis=dict(visible=False, showgrid=False, fixedrange=True, autorange=True)
    )
    return fig

def create_3d_arrivals_map_all(conn):
    origins_df = conn.execute("""
        SELECT "ORIGIN", COUNT(*) AS flight_count
        FROM flights 
        WHERE UPPER("DEST") = 'ORD'
        GROUP BY "ORIGIN" 
        ORDER BY flight_count DESC
    """).df()

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
            line=dict(width=1.5, color='#38BDF8'),
            opacity=0.6,
            hoverinfo='text',
            text=f"{orig} ➔ ORD ({count:,} flights)",
            showlegend=False
        ))

    fig.add_trace(go.Scattergeo(
        lon=[ord_lon], lat=[ord_lat],
        mode='markers+text',
        marker=dict(size=10, color='#F87171', symbol='circle'),
        text=['ORD'],
        textposition='top center',
        showlegend=False
    ))

    fig.update_layout(
        title=dict(text="🌐 Dynamic Inbound Route Globe", font=dict(size=14, color="#0f172a")),
        geo=dict(
            scope='north america',
            projection_type='orthographic',
            showland=True, landcolor="#1E293B",
            showocean=True, oceancolor="#0F172A",
            countrycolor="#475569", coastlinecolor="#475569",
            showlakes=True, lakecolor="#0F172A",
            bgcolor="#FFFFFF",
            center=dict(lat=38.0, lon=-97.0),
            projection_scale=1.15
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        height=320,
        paper_bgcolor="#FFFFFF"
    )
    return fig

def create_airline_connectivity_barchart(conn):
    try:
        raw_df = conn.execute("SELECT * FROM flights LIMIT 10000").df()
        raw_df.columns = [c.upper() for c in raw_df.columns]
        
        airline_col = 'AIRLINE_CODE' if 'AIRLINE_CODE' in raw_df.columns else ('AIRLINE' if 'AIRLINE' in raw_df.columns else None)
        origin_col = 'ORIGIN' if 'ORIGIN' in raw_df.columns else None
        dest_col = 'DEST' if 'DEST' in raw_df.columns else None

        if airline_col and origin_col:
            if dest_col:
                filtered_df = raw_df[raw_df[dest_col].str.upper() == 'ORD']
            else:
                filtered_df = raw_df

            df = filtered_df.groupby(airline_col).agg(
                unique_routes=(origin_col, 'nunique'),
                total_flights=(origin_col, 'count')
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

    fig = px.bar(
        df,
        y='airline_name',
        x='unique_routes',
        orientation='h',
        text='unique_routes',
        labels={'unique_routes': 'Direct Connected Hubs', 'airline_name': 'Airline'}
    )

    fig.update_traces(
        marker_color='#0066CC',
        textposition='outside',
        hovertemplate="<b>%{y}</b><br>Connected Origins: %{x}<extra></extra>"
    )

    fig = apply_white_chart_theme(fig)
    fig.update_layout(
        title=dict(text="✈️ Top 10 Airlines by Hub Connectivity (Unique Direct Routes)", font=dict(size=14, color="#0F172A")),
        yaxis=dict(autorange="reversed", title=""),
        xaxis=dict(title="Connected Origin Airports"),
        height=380,
        margin=dict(l=10, r=30, t=40, b=10)
    )
    return fig

from plotly.subplots import make_subplots

def create_airline_radar_chart(conn, selected_airlines=None):
    """Radar Charts in a subplots grid layout (2 rows x 3 columns) for individual airline viewing."""
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
            fig.add_annotation(text="Airline column not found in dataset", showarrow=False)
            return fig

        if 'DEST' in df_raw.columns:
            df_filtered = df_raw[df_raw['DEST'].astype(str).str.upper() == 'ORD'].copy()
        else:
            df_filtered = df_raw.copy()

        if selected_airlines:
            df_filtered = df_filtered[df_filtered[airline_col].astype(str).isin(selected_airlines)]

        df_filtered = df_filtered.dropna(subset=[airline_col])

        if df_filtered.empty:
            fig = go.Figure()
            fig.add_annotation(text="No flight data matches current airline filter", showarrow=False)
            return fig

        arr_delay = df_filtered['ARR_DELAY'] if 'ARR_DELAY' in df_filtered.columns else pd.Series(0, index=df_filtered.index)
        cancelled = df_filtered['CANCELLED'] if 'CANCELLED' in df_filtered.columns else pd.Series(0, index=df_filtered.index)

        df_filtered['is_ontime'] = (arr_delay <= 15).astype(int)
        df_filtered['pos_delay'] = arr_delay.apply(lambda x: x if pd.notna(x) and x > 0 else 0)
        df_filtered['is_cancelled'] = (cancelled == 1).astype(int)

        df_grouped = df_filtered.groupby(airline_col).agg(
            total_flights=(airline_col, 'count'),
            on_time_pct=('is_ontime', lambda x: round(x.mean() * 100, 2)),
            avg_delay=('pos_delay', lambda x: round(x.mean(), 2)),
            cancellation_rate=('is_cancelled', lambda x: round(x.mean() * 100, 2))
        ).reset_index()

        df_grouped = df_grouped.sort_values(by='total_flights', ascending=False).head(6)

    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Radar calculation error: {str(e)}", showarrow=False)
        return fig

    num_airlines = len(df_grouped)
    if num_airlines == 0:
        fig = go.Figure()
        fig.add_annotation(text="No airline performance data found", showarrow=False)
        return fig

    categories = ['Flights (Scaled)', 'Cancellation Rate (%)', 'Avg Delay (mins)', 'On-Time %']
    max_flights = df_grouped['total_flights'].max() if df_grouped['total_flights'].max() > 0 else 1
    df_grouped['flights_scaled'] = (df_grouped['total_flights'] / max_flights) * 100

    # Grid dimensions (Up to 3 columns, auto rows)
    cols = min(3, num_airlines)
    rows = (num_airlines + cols - 1) // cols

    subplot_titles = [
        f"<b>{str(row[airline_col])}</b> ({AIRLINE_NAMES.get(str(row[airline_col]), 'Carrier')})" 
        for _, row in df_grouped.iterrows()
    ]

    fig = make_subplots(
        rows=rows, 
        cols=cols, 
        specs=[[{'type': 'polar'} for _ in range(cols)] for _ in range(rows)],
        subplot_titles=subplot_titles,
        vertical_spacing=0.18,
        horizontal_spacing=0.08
    )

    colors = ['#0066CC', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']

    for idx, row in df_grouped.reset_index(drop=True).iterrows():
        r_idx = (idx // cols) + 1
        c_idx = (idx % cols) + 1
        
        airline_code = str(row[airline_col])
        airline_label = f"{airline_code} ({AIRLINE_NAMES.get(airline_code, 'Carrier')})"

        r_values = [
            row['flights_scaled'],
            row['cancellation_rate'],
            row['avg_delay'],
            row['on_time_pct']
        ]

        hover_text = (
            f"<b>{airline_label}</b><br>"
            f"Total Flights: {int(row['total_flights']):,}<br>"
            f"Cancellation Rate: {row['cancellation_rate']}%<br>"
            f"Avg Delay: {row['avg_delay']} mins<br>"
            f"On-Time: {row['on_time_pct']}%"
        )

        fig.add_trace(
            go.Scatterpolar(
                r=r_values + [r_values[0]],
                theta=categories + [categories[0]],
                fill='toself',
                name=airline_label,
                hoverinfo='text',
                text=hover_text,
                line=dict(color=colors[idx % len(colors)], width=2),
                opacity=0.45,
                showlegend=False
            ),
            row=r_idx, col=c_idx
        )

    # Apply uniform axis styling across all subplots
    for i in range(1, (rows * cols) + 1):
        axis_key = f"polar{i}" if i > 1 else "polar"
        fig.update_layout({
            axis_key: dict(
                radialaxis=dict(visible=True, range=[0, 100], color="#94A3B8", tickfont=dict(size=8)),
                angularaxis=dict(color="#0F172A", tickfont=dict(size=9, weight="bold"))
            )
        })

    fig.update_layout(
        title=dict(text="🎯 Airline Performance Radar Comparison (Grid View)", font=dict(size=15, color="#0F172A")),
        height=320 * rows,
        margin=dict(l=30, r=30, t=50, b=30),
        paper_bgcolor="#FFFFFF"
    )
    return fig

def render_flight_card_clean(row, is_delayed=False):
    origin_code = row['ORIGIN']
    airline_code = row['AIRLINE_CODE']
    fl_number = row['FL_NUMBER']
    
    elapsed_time = safe_int(row['elapsed_time'])
    hours, mins = divmod(elapsed_time, 60)
    time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
    
    dep_time = format_time_str(row['crs_dep'])
    actual_arr_time = format_time_str(row['actual_arr'])
    delay_val = safe_int(row['arr_delay'])

    card_class = "delayed" if is_delayed else "normal"
    badge_class = "badge-delay" if is_delayed else "badge-normal"
    delay_text = f"+{delay_val}m" if delay_val > 0 else f"{delay_val}m"

    st.markdown(f"""
    <div class="flight-clean-card {card_class}">
        <div>
            <div class="flight-code-title">{airline_code} {fl_number} · {origin_code} ➔ ORD</div>
            <div class="flight-sub-info">Dep: {dep_time} | Arr: {actual_arr_time} | Duration: {time_str}</div>
        </div>
        <div class="flight-badge-status {badge_class}">
            {delay_text if is_delayed else 'On-Time'}
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

try:
    cols_df = conn.execute("DESCRIBE flights").df()
    cols = [c.upper() for c in cols_df['column_name'].tolist()]
    airline_col_name = 'AIRLINE_CODE' if 'AIRLINE_CODE' in cols else ('AIRLINE' if 'AIRLINE' in cols else 'OP_UNIQUE_CARRIER')
    airlines = conn.execute(f'SELECT DISTINCT "{airline_col_name}" FROM flights WHERE "{airline_col_name}" IS NOT NULL').df().iloc[:, 0].dropna().tolist()
except Exception:
    airlines = []

selected_airline = st.sidebar.multiselect("Select Airline", options=airlines, default=[])

where_clause = "WHERE UPPER(\"DEST\") = 'ORD'"
params = []
if selected_airline:
    placeholders = ", ".join(["?"] * len(selected_airline))
    where_clause += f" AND \"{airline_col_name}\" IN ({placeholders})"
    params.extend(selected_airline)

# ==================== ARRIVALS INTELLIGENCE PAGE ====================
if page == "Arrivals Intelligence":
    st.title("🛬 ORD Arrivals Intelligence")
    st.caption("2022 Operational Performance & Route Analytics")
    
    kpi_query = f"""
        SELECT 
            COUNT(*) AS total_flights,
            AVG(CASE WHEN "ARR_DELAY" <= 15 THEN 1 ELSE 0 END) * 100 AS on_time_pct,
            AVG("ARR_DELAY") AS avg_delay,
            SUM("CANCELLED") AS total_cancelled,
            SUM("DIVERTED") AS total_diverted
        FROM flights {where_clause}
    """
    kpi_df = conn.execute(kpi_query, params).df()
    total_flights, on_time_pct, avg_delay, total_cancelled, total_diverted = kpi_df.iloc[0]

    monthly_trend = conn.execute(f"""
        SELECT 
            MONTH(TRY_CAST(CAST("FL_DATE" AS VARCHAR) AS DATE)) AS month,
            COUNT(*) AS flights, AVG("ARR_DELAY") AS delay,
            AVG(CASE WHEN "ARR_DELAY" <= 15 THEN 1 ELSE 0 END) * 100 AS on_time,
            SUM("CANCELLED") AS cancelled, SUM("DIVERTED") AS diverted
        FROM flights {where_clause}
        GROUP BY month HAVING month IS NOT NULL ORDER BY month
    """, params).df()

    # KPI Top Row Section
    c1, c2, c3, c4, c5 = st.columns(5)
    
    with c1:
        st.markdown(f"<div style='text-align: center;'><div style='font-size: 0.72rem; font-weight: 700; color: #475569;'>TOTAL ARRIVALS</div><div style='font-size: 1.3rem; font-weight: 800; color: #0A192F;'>{safe_int(total_flights):,}</div></div>", unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'flights', '#0066CC'), use_container_width=True, config={'displayModeBar': False})

    with c2:
        st.markdown(f"<div style='text-align: center;'><div style='font-size: 0.72rem; font-weight: 700; color: #475569;'>ON-TIME % (≤15M)</div><div style='font-size: 1.3rem; font-weight: 800; color: #10B981;'>{(on_time_pct or 0):.1f}%</div></div>", unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'on_time', '#10B981'), use_container_width=True, config={'displayModeBar': False})

    with c3:
        st.markdown(f"<div style='text-align: center;'><div style='font-size: 0.72rem; font-weight: 700; color: #475569;'>AVG DELAY</div><div style='font-size: 1.3rem; font-weight: 800; color: #D00000;'>{(avg_delay or 0):.1f}m</div></div>", unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'delay', '#D00000'), use_container_width=True, config={'displayModeBar': False})

    with c4:
        st.markdown(f"<div style='text-align: center;'><div style='font-size: 0.72rem; font-weight: 700; color: #475569;'>CANCELLED</div><div style='font-size: 1.3rem; font-weight: 800; color: #0A192F;'>{safe_int(total_cancelled):,}</div></div>", unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'cancelled', '#64748B'), use_container_width=True, config={'displayModeBar': False})

    with c5:
        st.markdown(f"<div style='text-align: center;'><div style='font-size: 0.72rem; font-weight: 700; color: #475569;'>DIVERTED</div><div style='font-size: 1.3rem; font-weight: 800; color: #0A192F;'>{safe_int(total_diverted):,}</div></div>", unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'diverted', '#38BDF8'), use_container_width=True, config={'displayModeBar': False})

    col_left, col_right = st.columns([1, 1])

    with col_left:
        with st.container(border=True):
            measure = st.segmented_control(
                "",
                ["Flights Count", "On-Time %", "Cancellations", "Avg Delay (min)"],
                default="Avg Delay (min)",
                label_visibility="collapsed"
            )

            measure_map = {
                "Flights Count": ("COUNT(*)", "DESC"),
                "On-Time %": ('AVG(CASE WHEN "ARR_DELAY" <= 15 THEN 1 ELSE 0 END) * 100', "DESC"),
                "Cancellations": ('SUM("CANCELLED")', "DESC"),
                "Avg Delay (min)": ('AVG("ARR_DELAY")', "DESC")
            }
            sql_val, sql_ord = measure_map[measure]

            # Top 10 Origins
            origins_df = conn.execute(f"""
                SELECT "ORIGIN" AS code, {sql_val} AS val
                FROM flights {where_clause}
                GROUP BY code ORDER BY val {sql_ord} LIMIT 10
            """, params).df()
            origins_df['full_label'] = origins_df['code'].apply(lambda x: f"{x} ({AIRPORT_CITY_NAMES.get(x, 'Origin')})")

            fig_orig = px.bar(
                origins_df, y='full_label', x='val', orientation='h',
                title=f"Top 10 Origin Destinations by {measure}",
                text_auto='.1f' if 'Delay' in measure or 'Time' in measure else True
            )
            fig_orig.update_traces(marker_color="#0066CC", textposition="outside")
            fig_orig = apply_white_chart_theme(fig_orig)
            fig_orig.update_layout(yaxis=dict(autorange="reversed", title=""), xaxis=dict(title=measure), margin=dict(l=10, r=25, t=35, b=10), height=320)
            st.plotly_chart(fig_orig, use_container_width=True)

            # Top 10 Airlines
            airlines_df = conn.execute(f"""
                SELECT "{airline_col_name}" AS code, {sql_val} AS val
                FROM flights {where_clause}
                GROUP BY code ORDER BY val {sql_ord} LIMIT 10
            """, params).df()
            airlines_df['full_label'] = airlines_df['code'].apply(lambda x: f"{x} ({AIRLINE_NAMES.get(str(x), 'Carrier')})")

            fig_air = px.bar(
                airlines_df, y='full_label', x='val', orientation='h',
                title=f"Top 10 Airlines by {measure}",
                text_auto='.1f' if 'Delay' in measure or 'Time' in measure else True
            )
            fig_air.update_traces(marker_color="#0066CC", textposition="outside")
            fig_air = apply_white_chart_theme(fig_air)
            fig_air.update_layout(yaxis=dict(autorange="reversed", title=""), xaxis=dict(title=measure), margin=dict(l=10, r=25, t=35, b=10), height=320)
            st.plotly_chart(fig_air, use_container_width=True)

    with col_right:
        with st.container(border=True):
            st.plotly_chart(create_3d_arrivals_map_all(conn), use_container_width=True)

        with st.container(border=True):
            st.plotly_chart(create_airline_connectivity_barchart(conn), use_container_width=True)

    # Flight Cards Section
    col_longest, col_delayed = st.columns(2)

    with col_longest:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color: #0F172A; margin-bottom: 8px;'>✈️ Top 5 Longest Inbound Routes</div>", unsafe_allow_html=True)
            longest_df = conn.execute(f"""
                SELECT "FL_NUMBER", "{airline_col_name}" AS AIRLINE_CODE, "ORIGIN", "FL_DATE",
                    COALESCE("CRS_DEP_TIME", 0) AS crs_dep, COALESCE("ARR_TIME", 0) AS actual_arr,
                    COALESCE("ELAPSED_TIME", 0) AS elapsed_time, COALESCE("ARR_DELAY", 0) AS arr_delay
                FROM flights {where_clause} ORDER BY "ELAPSED_TIME" DESC LIMIT 5
            """, params).df()

            for idx, row in longest_df.iterrows():
                render_flight_card_clean(row, is_delayed=False)

    with col_delayed:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color: #0F172A; margin-bottom: 8px;'>⚠️ Top 5 Most Delayed Inbound Flights</div>", unsafe_allow_html=True)
            delayed_df = conn.execute(f"""
                SELECT "FL_NUMBER", "{airline_col_name}" AS AIRLINE_CODE, "ORIGIN", "FL_DATE",
                    COALESCE("CRS_DEP_TIME", 0) AS crs_dep, COALESCE("ARR_TIME", 0) AS actual_arr,
                    COALESCE("ELAPSED_TIME", 0) AS elapsed_time, COALESCE("ARR_DELAY", 0) AS arr_delay
                FROM flights {where_clause} ORDER BY "ARR_DELAY" DESC LIMIT 5
            """, params).df()

            for idx, row in delayed_df.iterrows():
                render_flight_card_clean(row, is_delayed=True)

    # Heatmap & Delay Drivers Section
    c_heat, c_delay = st.columns([1.3, 1])

    with c_heat:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color: #0F172A; margin-bottom: 6px;'>Arrival Volume Heatmap</div>", unsafe_allow_html=True)
            heat_dim = st.segmented_control("", ["Month vs. Hour", "Day of Week vs. Hour"], default="Month vs. Hour", label_visibility="collapsed")
            
            if heat_dim == "Month vs. Hour":
                heat_df = conn.execute(f"""
                    SELECT MONTH(TRY_CAST(CAST("FL_DATE" AS VARCHAR) AS DATE)) AS row_dim,
                        CAST("CRS_ARR_TIME" / 100 AS INT) AS hour, COUNT(*) AS flights
                    FROM flights {where_clause} GROUP BY row_dim, hour ORDER BY row_dim, hour
                """, params).df()
                y_label = "Month"
                month_names = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
                heat_df['row_dim'] = heat_df['row_dim'].map(month_names)
            else:
                heat_df = conn.execute(f"""
                    SELECT DAYOFWEEK(TRY_CAST(CAST("FL_DATE" AS VARCHAR) AS DATE)) AS row_dim,
                        CAST("CRS_ARR_TIME" / 100 AS INT) AS hour, COUNT(*) AS flights
                    FROM flights {where_clause} GROUP BY row_dim, hour ORDER BY row_dim, hour
                """, params).df()
                y_label = "Day of Week"
                day_names = {0:'Sun', 1:'Mon', 2:'Tue', 3:'Wed', 4:'Thu', 5:'Fri', 6:'Sat'}
                heat_df['row_dim'] = heat_df['row_dim'].map(day_names)

            pivot_heat = heat_df.pivot(index='row_dim', columns='hour', values='flights').fillna(0)
            
            fig_heat = go.Figure(data=go.Heatmap(z=pivot_heat.values, x=pivot_heat.columns, y=pivot_heat.index, colorscale="Blues"))
            fig_heat.update_traces(xgap=2, ygap=2)
            fig_heat = apply_white_chart_theme(fig_heat)
            fig_heat.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Hour of Day (24h)", yaxis_title=y_label)
            st.plotly_chart(fig_heat, use_container_width=True)

    with c_delay:
        with st.container(border=True):
            st.markdown("<div style='font-weight: 700; color: #0F172A; margin-bottom: 6px;'>Arrival Delay Drivers</div>", unsafe_allow_html=True)
            delay_df = conn.execute(f"""
                SELECT AVG("DELAY_DUE_CARRIER") AS Carrier, AVG("DELAY_DUE_WEATHER") AS Weather,
                    AVG("DELAY_DUE_NAS") AS NAS, AVG("DELAY_DUE_SECURITY") AS Security,
                    AVG("DELAY_DUE_LATE_AIRCRAFT") AS "Late Aircraft"
                FROM flights {where_clause}
            """, params).df()
            
            delay_data = delay_df.iloc[0].fillna(0).reset_index()
            delay_data.columns = ['Driver', 'Avg_Minutes']
            delay_data = delay_data.sort_values(by='Avg_Minutes', ascending=False)

            fig_delay_bar = px.bar(delay_data, x='Driver', y='Avg_Minutes', title="Avg Delay Contribution (Minutes)", text_auto='.1f')
            fig_delay_bar.update_traces(marker_color='#0066CC', textposition='outside')
            fig_delay_bar = apply_white_chart_theme(fig_delay_bar)
            fig_delay_bar.update_layout(height=280, margin=dict(l=10, r=10, t=35, b=10), xaxis=dict(title=""), yaxis=dict(title="Minutes"))
            st.plotly_chart(fig_delay_bar, use_container_width=True)

    # Flight Records Table Section
    with st.container(border=True):
        st.markdown("<div style='font-weight: 700; color: #0F172A; margin-bottom: 8px;'>📋 Inbound Flight Records Table</div>", unsafe_allow_html=True)
        table_df = conn.execute(f"""
            SELECT "FL_DATE", "{airline_col_name}" AS AIRLINE, "FL_NUMBER", "ORIGIN", "ARR_DELAY", "CANCELLED", "DISTANCE"
            FROM flights {where_clause} ORDER BY "FL_DATE" DESC LIMIT 100
        """, params).df()
        st.dataframe(table_df, use_container_width=True, height=240)

    # Radar Chart Render
    with st.container(border=True):
        st.plotly_chart(create_airline_radar_chart(conn, selected_airline), use_container_width=True)

# ==================== OTHER PAGES ====================
elif page == "Departures Intelligence":
    st.title("🛫 ORD Departures Intelligence")
    st.info("Departures Analytics Dashboard")

elif page == "Flight Deep-Dive":
    st.title("🔍 Individual Flight Inspector")
    st.info("Flight Analysis Engine")
