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
    fig.update_traces(marker_color=bar_color, opacity=0.9, hovertemplate="%{x}: %{y:,.1f}")
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
            filtered_df = raw_df[raw_df[filter_col].astype(str).str.upper() == 'ORD']
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

    if df.empty or 'airline' not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No connectivity data available", showarrow=False)
        return fig

    df['airline_name'] = df['airline'].apply(lambda x: f"{x} ({AIRLINE_NAMES.get(str(x), 'Carrier')})")
    x_title = "Connected Origin Airports" if mode == "ARRIVALS" else "Connected Destination Airports"

    fig = px.bar(df, y='airline_name', x='unique_routes', orientation='h', text='unique_routes')
    fig.update_traces(marker_color='#0066CC', textposition='outside', hovertemplate="**%{y}**
