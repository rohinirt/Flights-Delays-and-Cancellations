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

# Helper function to safely convert potential NaN/None values to integers
def safe_int(val, default=0):
    if pd.isna(val) or val is None:
        return default
    return int(val)

# Helper function to format military time strings (e.g., 1600 -> 4:00 pm)
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

# Global Styling Rules
st.markdown("""
<style>
    :root {
        --background-color: #f8fafc !important;
        --secondary-background-color: #ffffff !important;
        --text-color: #0f172a !important;
    }

    .stApp, [data-testid="stAppViewContainer"] { 
        background-color: #f8fafc !important; 
        color: #0f172a !important;
    }

    .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp caption {
        color: #0f172a !important;
    }

    /* Solid KPI Card Wrapper for Column Containers */
    div[data-testid="stColumn"] > div {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px !important;
        padding: 12px 8px 4px 8px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    }

    /* Segmented Control Styling */
    div[data-testid="stSegmentedControl"] {
        background-color: #e2e8f0 !important;
        border-radius: 8px !important;
        padding: 4px !important;
    }
    div[data-testid="stSegmentedControl"] button {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
    }
    div[data-testid="stSegmentedControl"] button * {
        color: #0f172a !important;
        font-weight: 600 !important;
    }
    div[data-testid="stSegmentedControl"] button[aria-selected="true"] {
        background-color: #0066CC !important;
    }
    div[data-testid="stSegmentedControl"] button[aria-selected="true"] * {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* Google Flight Card Widget Styling (Image 2 Style) */
    .flight-widget-card {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    }
    .flight-route-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 12px;
    }
    .airport-code {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0F172A;
        line-height: 1;
    }
    .route-line-container {
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 0 16px;
        margin-top: 4px;
    }
    .flight-duration {
        font-size: 0.85rem;
        color: #475569;
        font-weight: 600;
        margin-bottom: 6px;
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
        font-size: 0.9rem;
        color: #0066CC;
        background-color: #ffffff;
        padding: 0 6px;
    }
    .flight-subtitle {
        font-size: 0.85rem;
        color: #475569;
        margin-top: 4px;
    }
    .flight-details-grid {
        display: grid;
        grid-template-columns: 1fr 1.2fr;
        gap: 12px;
        border-top: 1px solid #f1f5f9;
        padding-top: 12px;
        margin-top: 10px;
    }
    .flight-column-left {
        border-right: 1px solid #f1f5f9;
        padding-right: 8px;
    }
    .time-display {
        font-size: 1.25rem;
        font-weight: 700;
        margin-top: 2px;
    }
    .detail-label {
        color: #64748B;
        font-size: 0.75rem;
        font-weight: 500;
    }

    /* Sidebar Isolation */
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

def apply_light_plotly_theme(fig):
    fig.update_layout(
        template="plotly_white",
        font=dict(color="#0f172a", family="sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title=dict(font=dict(color="#0f172a", size=16)),
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
        legend=dict(font=dict(color="#0f172a")),
        coloraxis_colorbar=dict(
            title=dict(font=dict(color="#0f172a")),
            tickfont=dict(color="#0f172a")
        )
    )
    return fig

# KPI Monthly Bar Chart Helper (Image 1 Style)
def create_monthly_kpi_chart(data, x_col, y_col, bar_color="#0066CC"):
    data = data.copy()
    month_map = {1:'J', 2:'F', 3:'M', 4:'A', 5:'M', 6:'J', 7:'J', 8:'A', 9:'S', 10:'O', 11:'N', 12:'D'}
    data['month_code'] = data[x_col].map(month_map)
    
    fig = px.bar(data, x='month_code', y=y_col)
    fig.update_traces(
        marker_color=bar_color, 
        opacity=0.95, 
        hovertemplate="%{x}: %{y:,.0f}<extra></extra>"
    )
    fig.update_layout(
        margin=dict(l=2, r=2, t=2, b=18),
        height=70,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            type='category',
            categoryorder='array',
            categoryarray=['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'],
            tickfont=dict(size=9, color='#475569', weight='bold'),
            showgrid=False,
            zeroline=False,
            fixedrange=True,
            title="",
            showline=False
        ),
        yaxis=dict(visible=False, showgrid=False, fixedrange=True)
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
    
    # KPI Queries
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

    # 1. Solid Color KPI Cards with Monthly Bar Charts
    c1, c2, c3, c4, c5 = st.columns(5)
    
    with c1:
        st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 0.75rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px;">TOTAL ARRIVALS</div>
                <div style="font-size: 1.5rem; font-weight: 800; color: #0A192F; margin: 2px 0 0 0;">{safe_int(total_flights):,}</div>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'flights', '#0066CC'), use_container_width=True, config={'displayModeBar': False})

    with c2:
        st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 0.75rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px;">ON-TIME %</div>
                <div style="font-size: 1.5rem; font-weight: 800; color: #10B981; margin: 2px 0 0 0;">{(on_time_pct or 0):.1f}%</div>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'on_time', '#10B981'), use_container_width=True, config={'displayModeBar': False})

    with c3:
        st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 0.75rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px;">AVG DELAY</div>
                <div style="font-size: 1.5rem; font-weight: 800; color: #D00000; margin: 2px 0 0 0;">{(avg_delay or 0):.1f}m</div>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'delay', '#D00000'), use_container_width=True, config={'displayModeBar': False})

    with c4:
        st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 0.75rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px;">CANCELLED</div>
                <div style="font-size: 1.5rem; font-weight: 800; color: #0A192F; margin: 2px 0 0 0;">{safe_int(total_cancelled):,}</div>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'flights', '#64748B'), use_container_width=True, config={'displayModeBar': False})

    with c5:
        st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 0.75rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px;">DIVERTED</div>
                <div style="font-size: 1.5rem; font-weight: 800; color: #0A192F; margin: 2px 0 0 0;">{safe_int(total_diverted):,}</div>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(create_monthly_kpi_chart(monthly_trend, 'month', 'flights', '#38BDF8'), use_container_width=True, config={'displayModeBar': False})

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
        fig_air = apply_light_plotly_theme(fig_air)
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
        fig_orig = apply_light_plotly_theme(fig_orig)
        fig_orig.update_layout(yaxis=dict(autorange="reversed"), margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_orig, use_container_width=True)

    st.markdown("---")

    # 3. Flight Boarding Pass Cards (Image 2 Style)
    col_longest, col_delayed = st.columns(2)

    with col_longest:
        st.subheader("✈️ Top 5 Longest Inbound Routes")
        
        longest_df = conn.execute(f"""
            SELECT 
                "FL_NUMBER", 
                "AIRLINE_CODE", 
                "ORIGIN", 
                "ORIGIN_CITY", 
                "FL_DATE",
                COALESCE("CRS_DEP_TIME", 0) AS crs_dep,
                COALESCE("CRS_ARR_TIME", 0) AS crs_arr,
                COALESCE("ARR_TIME", 0) AS actual_arr,
                COALESCE("ELAPSED_TIME", 0) AS elapsed_time,
                COALESCE("ARR_DELAY", 0) AS arr_delay
            FROM flights WHERE "DEST" = 'ORD' {airline_filter}
            ORDER BY "ELAPSED_TIME" DESC LIMIT 5
        """).df()

        for idx, row in longest_df.iterrows():
            origin_code = row['ORIGIN']
            origin_city = row['ORIGIN_CITY']
            fl_date = str(row['FL_DATE'])
            formatted_date = f"{fl_date[6:8]}/{fl_date[4:6]}/{fl_date[:4]}" if len(fl_date) == 8 else fl_date
            
            elapsed_time = safe_int(row['elapsed_time'])
            hours, mins = divmod(elapsed_time, 60)
            time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
            
            dep_time = format_time_str(row['crs_dep'])
            crs_arr_time = format_time_str(row['crs_arr'])
            actual_arr_time = format_time_str(row['actual_arr'])
            delay_val = safe_int(row['arr_delay'])
            delay_color = "#10B981" if delay_val <= 0 else "#D00000"

            st.markdown(f"""
            <div class="flight-widget-card">
                <div class="flight-route-header">
                    <div>
                        <div class="airport-code">{origin_code}</div>
                        <div class="flight-subtitle"><a href="#" style="color:#0066CC; text-decoration:none;">Airport info</a></div>
                    </div>
                    <div class="route-line-container">
                        <span class="flight-duration">{time_str}</span>
                        <div class="route-line">
                            <span class="plane-icon">✈️</span>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div class="airport-code">ORD</div>
                        <div class="flight-subtitle"><a href="#" style="color:#0066CC; text-decoration:none;">Airport info</a></div>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #475569; padding-bottom: 6px;">
                    <div><strong>{origin_city}</strong> · {formatted_date}</div>
                    <div><strong>Chicago</strong> · {formatted_date}</div>
                </div>
                <div class="flight-details-grid">
                    <div class="flight-column-left">
                        <div class="detail-label">Scheduled departure</div>
                        <div class="time-display" style="color: #0066CC;">{dep_time}</div>
                    </div>
                    <div>
                        <div style="display: flex; justify-content: space-between;">
                            <div>
                                <div class="detail-label">Scheduled arrival</div>
                                <div class="time-display" style="color: #0F172A;">{crs_arr_time}</div>
                            </div>
                            <div style="text-align: right;">
                                <div class="detail-label">Actual arrival / Delay</div>
                                <div class="time-display" style="color: {delay_color};">{actual_arr_time} ({delay_val:+}m)</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_delayed:
        st.subheader("⚠️ Top 5 Most Delayed Inbound Flights")

        delayed_df = conn.execute(f"""
            SELECT 
                "FL_NUMBER", 
                "AIRLINE_CODE", 
                "ORIGIN", 
                "ORIGIN_CITY", 
                "FL_DATE",
                COALESCE("CRS_DEP_TIME", 0) AS crs_dep,
                COALESCE("CRS_ARR_TIME", 0) AS crs_arr,
                COALESCE("ARR_TIME", 0) AS actual_arr,
                COALESCE("ELAPSED_TIME", 0) AS elapsed_time,
                COALESCE("ARR_DELAY", 0) AS arr_delay
            FROM flights WHERE "DEST" = 'ORD' {airline_filter}
            ORDER BY "ARR_DELAY" DESC LIMIT 5
        """).df()

        for idx, row in delayed_df.iterrows():
            origin_code = row['ORIGIN']
            origin_city = row['ORIGIN_CITY']
            fl_date = str(row['FL_DATE'])
            formatted_date = f"{fl_date[6:8]}/{fl_date[4:6]}/{fl_date[:4]}" if len(fl_date) == 8 else fl_date
            
            elapsed_time = safe_int(row['elapsed_time'])
            hours, mins = divmod(elapsed_time, 60)
            time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
            
            dep_time = format_time_str(row['crs_dep'])
            crs_arr_time = format_time_str(row['crs_arr'])
            actual_arr_time = format_time_str(row['actual_arr'])
            delay_val = safe_int(row['arr_delay'])

            st.markdown(f"""
            <div class="flight-widget-card" style="border-left: 5px solid #D00000 !important;">
                <div class="flight-route-header">
                    <div>
                        <div class="airport-code">{origin_code}</div>
                        <div class="flight-subtitle"><a href="#" style="color:#0066CC; text-decoration:none;">Airport info</a></div>
                    </div>
                    <div class="route-line-container">
                        <span class="flight-duration" style="color: #D00000; font-weight: 700;">{time_str}</span>
                        <div class="route-line">
                            <span class="plane-icon" style="color: #D00000;">✈️</span>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div class="airport-code">ORD</div>
                        <div class="flight-subtitle"><a href="#" style="color:#0066CC; text-decoration:none;">Airport info</a></div>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #475569; padding-bottom: 6px;">
                    <div><strong>{origin_city}</strong> · {formatted_date}</div>
                    <div><strong>Chicago</strong> · {formatted_date}</div>
                </div>
                <div class="flight-details-grid">
                    <div class="flight-column-left">
                        <div class="detail-label">Scheduled departure</div>
                        <div class="time-display" style="color: #0066CC;">{dep_time}</div>
                    </div>
                    <div>
                        <div style="display: flex; justify-content: space-between;">
                            <div>
                                <div class="detail-label">Scheduled arrival</div>
                                <div class="time-display" style="color: #0F172A;">{crs_arr_time}</div>
                            </div>
                            <div style="text-align: right;">
                                <div class="detail-label">Actual arrival / Delay</div>
                                <div class="time-display" style="color: #D00000;">{actual_arr_time} (+{delay_val}m)</div>
                            </div>
                        </div>
                    </div>
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
        fig_heat = apply_light_plotly_theme(fig_heat)
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
        fig_pie = apply_light_plotly_theme(fig_pie)
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
    fig_sankey = apply_light_plotly_theme(fig_sankey)
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
